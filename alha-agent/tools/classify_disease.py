"""Tool: classify_disease — run Rekognition custom labels on uploaded image."""
import asyncio
import base64
import json
from datetime import datetime

import boto3
import structlog
from botocore.exceptions import ClientError, ParamValidationError
from claude_agent_sdk import tool

from config import config

log = structlog.get_logger()

# Module-level boto3 clients — created once, reused per call
_rekognition = boto3.client("rekognition", region_name=config.aws_region)
_dynamodb = boto3.client("dynamodb", region_name=config.aws_region)
_s3 = boto3.client("s3", region_name=config.aws_region)
_bedrock_runtime = boto3.client("bedrock-runtime", region_name=config.aws_region)


def _get_model_arn(animal_type: str) -> str:
    """Look up Rekognition model ARN from DynamoDB; fall back to env var."""
    try:
        response = _dynamodb.get_item(
            TableName=config.disease_models_table,
            Key={"animal_type": {"S": animal_type}},
        )
        item = response.get("Item", {})
        arn = item.get("model_arn", {}).get("S", "")
        if arn:
            return arn
    except ClientError as exc:
        log.warning(
            "dynamodb_arn_lookup_failed",
            animal_type=animal_type,
            error=str(exc),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
    # Fallback to env var
    if animal_type == "poultry":
        return config.rekognition_poultry_arn
    return config.rekognition_cattle_arn


_EXT_TO_MEDIA_TYPE = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}

_SUPPORTED_MEDIA_TYPES = set(_EXT_TO_MEDIA_TYPE.values())


def _detect_media_type(s3_key: str, content_type: str) -> str:
    """Resolve Claude-supported media type from S3 ContentType or key extension.

    S3 may omit ContentType if the object was uploaded without the header,
    in which case extension-based detection is used as a fallback.
    NOTE: prefer _detect_media_type_from_bytes when image bytes are available —
    it is more reliable than S3 metadata (which may reflect the presigned URL's
    forced ContentType rather than the actual image format).
    """
    if content_type in _SUPPORTED_MEDIA_TYPES:
        return content_type
    # S3 ContentType absent or unrecognised — derive from key extension.
    ext = s3_key.rsplit(".", 1)[-1].lower() if "." in s3_key else ""
    media_type = _EXT_TO_MEDIA_TYPE.get(ext)
    if media_type:
        return media_type
    log.warning(
        "media_type_fallback_to_jpeg",
        s3_key=s3_key,
        content_type=content_type,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
    return "image/jpeg"


_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),   # confirmed as WebP below
]


def _detect_media_type_from_bytes(image_bytes: bytes) -> str | None:
    """Detect MIME type from magic bytes. Returns None if unrecognised."""
    for magic, media_type in _MAGIC_BYTES:
        if image_bytes[:len(magic)] == magic:
            if media_type == "image/webp" and image_bytes[8:12] != b"WEBP":
                continue
            return media_type if media_type in _SUPPORTED_MEDIA_TYPES else None
    return None


async def _claude_classify_image(s3_key: str, animal_type: str) -> dict:
    """Classify livestock disease from S3 image using Claude vision via Bedrock."""
    obj = _s3.get_object(Bucket=config.s3_image_bucket, Key=s3_key)
    media_type = _detect_media_type(s3_key, obj.get("ContentType", ""))
    if media_type == "image/gif":
        log.warning(
            "gif_upload_first_frame_only",
            s3_key=s3_key,
            note="Bedrock analyses only the first frame of animated GIFs",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
    image_bytes = obj["Body"].read()
    media_type = _detect_media_type_from_bytes(image_bytes) or media_type
    b64_data = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        f"You are a veterinary disease detection AI. Analyse this image of a {animal_type}. "
        "Identify the most visible disease or health condition. "
        "Respond ONLY with valid JSON, no markdown, no extra text: "
        '{"disease": "<snake_case_disease_name or null>", "confidence": <0-100>, '
        '"bbox": {"left": <0-1>, "top": <0-1>, "width": <0-1>, "height": <0-1>} or null}'
    )
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 256,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": media_type, "data": b64_data,
                }},
                {"type": "text", "text": prompt},
            ],
        }],
    })

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None,
        lambda: _bedrock_runtime.invoke_model(
            modelId=config.bedrock_vision_model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        ),
    )
    response_body = json.loads(response["body"].read())
    parsed = json.loads(response_body["content"][0]["text"].strip())

    disease = parsed.get("disease") or None
    confidence = round(float(parsed.get("confidence", 0.0)), 2)
    raw_bbox = parsed.get("bbox")
    bbox = None
    if raw_bbox and disease:
        bbox = {
            "left":   max(0.0, min(1.0, float(raw_bbox.get("left",   0.0)))),
            "top":    max(0.0, min(1.0, float(raw_bbox.get("top",    0.0)))),
            "width":  max(0.0, min(1.0, float(raw_bbox.get("width",  0.0)))),
            "height": max(0.0, min(1.0, float(raw_bbox.get("height", 0.0)))),
        }
    return {"disease": disease, "confidence": confidence, "bbox": bbox}


@tool(
    "classify_disease",
    "Classify animal disease from an uploaded S3 image using AWS Rekognition Custom Labels. "
    "Returns disease label, confidence score, and bounding box coordinates.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Active session ID"},
            "s3_image_key": {
                "type": "string",
                "description": "S3 object key for the uploaded image",
            },
            "animal_type": {
                "type": "string",
                "description": "Animal species: cattle, poultry, or buffalo",
            },
        },
        "required": ["session_id", "s3_image_key", "animal_type"],
    },
)
async def classify_disease(args: dict) -> dict:
    """Classify disease from S3 image using Rekognition Custom Labels."""
    session_id = args.get("session_id", "")
    s3_image_key = args.get("s3_image_key", "")
    animal_type = args.get("animal_type", "cattle")

    # Validate s3_image_key to prevent path traversal or cross-session access
    if (
        not s3_image_key
        or ".." in s3_image_key
        or not s3_image_key.startswith("uploads/")
    ):
        result = {
            "error": True,
            "code": "INVALID_KEY",
            "message": "Invalid image key.",
            "message_hi": "अमान्य छवि कुंजी।",
        }
        log.warning(
            "classify_disease_invalid_key",
            session_id=session_id,
            s3_image_key=s3_image_key,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    start_time = datetime.utcnow()

    try:
        # Branch 1: Claude-only (claude mode / Rekognition not configured)
        if config.rekognition_claude:
            log.warning(
                "rekognition_claude_active_using_claude",
                session_id=session_id,
                animal_type=animal_type,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            try:
                claude_result = await _claude_classify_image(s3_image_key, animal_type)
            except Exception as exc:
                log.error("claude_vision_error", session_id=session_id, error=str(exc),
                          timestamp=datetime.utcnow().isoformat() + "Z")
                result = {"error": True, "code": "REKOGNITION_ERROR",
                          "message": "Disease detection failed. Try again.",
                          "message_hi": "रोग पहचान विफल रही। पुनः प्रयास करें।"}
                return {"content": [{"type": "text", "text": json.dumps(result)}]}

            if not claude_result.get("disease"):
                # soft failure — fall through to WS dispatch so Flutter gets diagnosis message
                result = {"disease": None, "confidence": 0.0, "bbox": None,
                          "soft_failure": True,
                          "message": "Photo not clear enough. Please try again in better light.",
                          "message_hi": "फोटो स्पष्ट नहीं थी। कृपया बेहतर रोशनी में पुनः प्रयास करें।"}
            else:
                result = {**claude_result, "source": "claude"}

        else:
            # Branch 2: Rekognition + Claude double-check
            _rek_ext = s3_image_key.rsplit(".", 1)[-1].lower() if "." in s3_image_key else ""
            if _rek_ext not in ("jpg", "jpeg", "png"):
                log.warning(
                    "rekognition_unsupported_format",
                    session_id=session_id,
                    s3_key=s3_image_key,
                    ext=_rek_ext,
                    note="Rekognition supports JPEG/PNG only; expect ClientError fallback to Claude",
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )
            model_arn = _get_model_arn(animal_type)
            response = _rekognition.detect_custom_labels(
                ProjectVersionArn=model_arn,
                Image={"S3Object": {"Bucket": config.s3_image_bucket, "Name": s3_image_key}},
                MinConfidence=50,
            )
            labels = response.get("CustomLabels", [])

            if not labels:
                # soft failure — fall through to WS dispatch so Flutter gets diagnosis message
                result = {"disease": None, "confidence": 0.0, "bbox": None,
                          "soft_failure": True,
                          "message": "Photo not clear enough. Please try again in better light.",
                          "message_hi": "फोटो स्पष्ट नहीं थी। कृपया बेहतर रोशनी में पुनः प्रयास करें।"}
            else:
                top_label = max(labels, key=lambda lbl: lbl.get("Confidence", 0))
                rek_disease = top_label.get("Name", "unknown")
                rek_confidence = round(top_label.get("Confidence", 0.0), 2)
                geometry = top_label.get("Geometry", {})
                bb = geometry.get("BoundingBox", {})
                rek_bbox = None
                if bb:
                    rek_bbox = {
                        "left":   max(0.0, min(1.0, bb.get("Left",   0.0))),
                        "top":    max(0.0, min(1.0, bb.get("Top",    0.0))),
                        "width":  max(0.0, min(1.0, bb.get("Width",  0.0))),
                        "height": max(0.0, min(1.0, bb.get("Height", 0.0))),
                    }

                # Claude double-check
                try:
                    claude_result = await _claude_classify_image(s3_image_key, animal_type)
                except Exception as exc:
                    log.warning("claude_vision_error_using_rekognition", session_id=session_id,
                                error=str(exc), timestamp=datetime.utcnow().isoformat() + "Z")
                    claude_result = {}

                claude_disease = (claude_result.get("disease") or "").lower().strip()
                if claude_disease and claude_disease != rek_disease.lower().strip():
                    # Disagreement: Claude wins
                    result = {**claude_result, "source": "claude"}
                    log.warning("classification_disagreement",
                                session_id=session_id,
                                rekognition_disease=rek_disease,
                                claude_disease=claude_disease,
                                timestamp=datetime.utcnow().isoformat() + "Z")
                else:
                    # Agreement (or Claude had no opinion): Rekognition wins
                    result = {"disease": rek_disease, "confidence": rek_confidence,
                              "bbox": rek_bbox, "source": "rekognition"}

    except (ClientError, ParamValidationError) as exc:
        # Branch 3: Rekognition errored or ARN failed param validation — fall through to Claude
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        code = exc.response.get("Error", {}).get("Code", "Unknown") if isinstance(exc, ClientError) else type(exc).__name__
        log.warning(
            "rekognition_error_claude_fallback",
            session_id=session_id,
            error_code=code,
            error=str(exc),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        try:
            claude_result = await _claude_classify_image(s3_image_key, animal_type)
        except Exception as claude_exc:
            log.error("claude_vision_error", session_id=session_id,
                      error=str(claude_exc), timestamp=datetime.utcnow().isoformat() + "Z")
            result = {"error": True, "code": "REKOGNITION_ERROR",
                      "message": "Disease detection failed. Try again.",
                      "message_hi": "रोग पहचान विफल रही। पुनः प्रयास करें।"}
            return {"content": [{"type": "text", "text": json.dumps(result)}]}

        if not claude_result.get("disease"):
            # soft failure — fall through to WS dispatch so Flutter gets diagnosis message
            result = {"disease": None, "confidence": 0.0, "bbox": None,
                      "soft_failure": True,
                      "message": "Photo not clear enough. Please try again in better light.",
                      "message_hi": "फोटो स्पष्ट नहीं थी। कृपया बेहतर रोशनी में पुनः प्रयास करें।"}
        else:
            result = {**claude_result, "source": "claude_fallback"}

    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    if not result.get("soft_failure"):
        log.info(
            "tool_executed",
            tool_name="classify_disease",
            session_id=session_id,
            animal_type=animal_type,
            disease=result.get("disease"),
            confidence=result.get("confidence"),
            source=result.get("source", "unknown"),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    # Dispatch diagnosis WS message to Flutter
    from ws_map import _active_ws_map

    async def _send(ws_ref, payload: dict) -> None:
        try:
            await ws_ref.send_json(payload)
        except Exception as exc:
            log.warning(
                "ws_send_failed",
                tool_name="classify_disease",
                session_id=session_id,
                error=str(exc),
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    ws = _active_ws_map.get(session_id)
    if ws:
        ws_payload = {
            "type": "diagnosis",
            "session_id": session_id,
            "soft_failure": result.get("soft_failure", False),
            "disease": result.get("disease"),
            "confidence": result.get("confidence"),
            "bbox": result.get("bbox"),
            "s3_key": s3_image_key,
            "message": result.get("message"),
            "message_hi": result.get("message_hi"),
        }
        asyncio.create_task(_send(ws, ws_payload))

    return {"content": [{"type": "text", "text": json.dumps(result)}]}
