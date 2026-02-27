"""Tool: classify_disease — run Rekognition custom labels on uploaded image."""
import asyncio
import json
from datetime import datetime

import boto3
import structlog
from botocore.exceptions import ClientError
from claude_agent_sdk import tool

from config import config

log = structlog.get_logger()

# Module-level boto3 clients — created once, reused per call
_rekognition = boto3.client("rekognition", region_name=config.aws_region)
_dynamodb = boto3.client("dynamodb", region_name=config.aws_region)


# ==== MOCK START: REMOVE BEFORE PRODUCTION ====
# Mimics a real Rekognition detect_custom_labels response with realistic
# disease labels and bounding boxes per animal type.
# Activated when REKOGNITION_MOCK=true in environment.
# To remove: delete this function and the _mock_classify() call in classify_disease().
_MOCK_DISEASES: dict[str, dict] = {
    "cattle": {
        "Name": "lumpy_skin_disease",
        "Confidence": 87.5,
        "Geometry": {
            "BoundingBox": {"Left": 0.28, "Top": 0.22, "Width": 0.44, "Height": 0.38}
        },
    },
    "poultry": {
        "Name": "newcastle_disease",
        "Confidence": 82.3,
        "Geometry": {
            "BoundingBox": {"Left": 0.31, "Top": 0.19, "Width": 0.38, "Height": 0.42}
        },
    },
    "buffalo": {
        "Name": "foot_and_mouth",
        "Confidence": 79.1,
        "Geometry": {
            "BoundingBox": {"Left": 0.25, "Top": 0.30, "Width": 0.50, "Height": 0.35}
        },
    },
}


def _mock_rekognition_response(animal_type: str) -> list[dict]:
    """Return a fake Rekognition CustomLabels list for the given animal type.
    Falls back to cattle if animal_type is unrecognised.
    MOCK — REMOVE BEFORE PRODUCTION.
    """
    label = _MOCK_DISEASES.get(animal_type, _MOCK_DISEASES["cattle"])
    return [label]
# ==== MOCK END ====


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
        # ==== MOCK START: REMOVE BEFORE PRODUCTION ====
        # Bypasses DynamoDB ARN lookup and real Rekognition when REKOGNITION_MOCK=true.
        # Replace this entire block with the real call below once models are trained and running.
        if config.rekognition_mock:
            log.warning(
                "rekognition_mock_active",
                session_id=session_id,
                animal_type=animal_type,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            labels = _mock_rekognition_response(animal_type)
        else:
            # ==== MOCK END ====
            model_arn = _get_model_arn(animal_type)

            response = _rekognition.detect_custom_labels(
                ProjectVersionArn=model_arn,
                Image={"S3Object": {"Bucket": config.s3_image_bucket, "Name": s3_image_key}},
                MinConfidence=50,
            )

            labels = response.get("CustomLabels", [])
            # ==== MOCK START: REMOVE BEFORE PRODUCTION (closing else) ====
        # ==== MOCK END ====
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        if not labels:
            # Soft failure — 0 labels returned (blurry or unclear image)
            result = {
                "disease": None,
                "confidence": 0.0,
                "bbox": None,
                "soft_failure": True,
                "message": "Photo not clear enough. Please try again in better light.",
                "message_hi": "फोटो स्पष्ट नहीं थी। कृपया बेहतर रोशनी में पुनः प्रयास करें।",
            }
            log.info(
                "tool_executed",
                tool_name="classify_disease",
                session_id=session_id,
                animal_type=animal_type,
                disease=None,
                confidence=0.0,
                soft_failure=True,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            return {"content": [{"type": "text", "text": json.dumps(result)}]}

        # Extract top label by confidence
        top_label = max(labels, key=lambda lbl: lbl.get("Confidence", 0))
        disease_name = top_label.get("Name", "unknown")
        confidence = round(top_label.get("Confidence", 0.0), 2)

        # Extract bounding box (normalised 0-1 coordinates from Rekognition)
        bbox = None
        geometry = top_label.get("Geometry", {})
        bb = geometry.get("BoundingBox", {})
        if bb:
            # Clamp all coordinates to [0, 1] — Rekognition can return values
            # slightly outside range for objects near image edges.
            bbox = {
                "left": max(0.0, min(1.0, bb.get("Left", 0.0))),
                "top": max(0.0, min(1.0, bb.get("Top", 0.0))),
                "width": max(0.0, min(1.0, bb.get("Width", 0.0))),
                "height": max(0.0, min(1.0, bb.get("Height", 0.0))),
            }

        result = {
            "disease": disease_name,
            "confidence": confidence,
            "bbox": bbox,
        }

        log.info(
            "tool_executed",
            tool_name="classify_disease",
            session_id=session_id,
            animal_type=animal_type,
            disease=disease_name,
            confidence=confidence,
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
            asyncio.create_task(
                _send(
                    ws,
                    {
                        "type": "diagnosis",
                        "session_id": session_id,
                        "disease": disease_name,
                        "confidence": confidence,
                        "bbox": bbox,
                        "s3_key": s3_image_key,
                    },
                )
            )

        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    except ClientError as exc:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        log.error(
            "rekognition_error",
            session_id=session_id,
            error_code=code,
            error=str(exc),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        if code == "InvalidParameterException":
            result = {
                "error": True,
                "code": "REKOGNITION_MODEL_STOPPED",
                "message": "Disease detection model is warming up. Please try again in 5 minutes.",
                "message_hi": "रोग पहचान मॉडल तैयार हो रहा है। कृपया 5 मिनट में पुनः प्रयास करें।",
            }
        else:
            result = {
                "error": True,
                "code": "REKOGNITION_ERROR",
                "message": "Disease detection failed. Try again.",
                "message_hi": "रोग पहचान विफल रही। पुनः प्रयास करें।",
            }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
