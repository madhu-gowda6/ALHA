import asyncio
import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

import boto3
import httpx
import structlog
from botocore.exceptions import ClientError
from fastapi import FastAPI, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from pydantic import BaseModel

from agent import process_message
from config import config
from hooks.logging_hook import LoggingHook
import transcribe_service

log = structlog.get_logger()
_hook = LoggingHook()

app = FastAPI(title="ALHA Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Module-level AWS clients — created once, reused per request
_cognito = boto3.client("cognito-idp", region_name=config.aws_region)
_s3 = boto3.client("s3", region_name=config.aws_region)
_dynamodb = boto3.client("dynamodb", region_name=config.aws_region)

# JWKS cache — refreshed on validation failure
_jwks: Optional[dict] = None

# In-memory conversation history keyed by session_id.
# Each value is a list of {"role": "user"|"assistant", "content": str} dicts.
# Capped at _MAX_HISTORY entries to avoid unbounded growth.
_session_histories: dict[str, list[dict]] = {}
_MAX_HISTORY = 40

# Tracks which sessions are waiting for a specific message type from Flutter.
# Values: "symptom_answers" | "image_data" | None
_pending_action_sessions: dict[str, Optional[str]] = {}

# Per-session asyncio locks — ensures at most one process_message runs at a
# time for a given session, preventing concurrent history corruption.
_session_locks: dict[str, asyncio.Lock] = {}

# Per-session language — set on first "chat" message, reused for
# symptom_answers / image_data which don't include a language field.
_session_languages: dict[str, str] = {}

# Per-session farmer phone — extracted from Cognito JWT phone_number claim.
_session_farmer_phones: dict[str, str] = {}


def _get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


async def _fetch_jwks() -> dict:
    global _jwks
    if _jwks is None:
        url = (
            f"https://cognito-idp.{config.aws_region}.amazonaws.com"
            f"/{config.cognito_user_pool_id}/.well-known/jwks.json"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            _jwks = resp.json()
    return _jwks


def _get_rsa_key(token: str, jwks: dict) -> Optional[dict]:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def _validate_jwt(token: str) -> dict:
    """Validate a Cognito JWT and return claims. Raises JWTError on failure."""
    jwks = await _fetch_jwks()
    rsa_key = _get_rsa_key(token, jwks)

    if rsa_key is None:
        # Key not found — refresh JWKS once and retry
        global _jwks
        _jwks = None
        jwks = await _fetch_jwks()
        rsa_key = _get_rsa_key(token, jwks)

    if rsa_key is None:
        raise JWTError("No matching key found in JWKS")

    claims = jwt.decode(
        token,
        rsa_key,
        algorithms=["RS256"],
        audience=config.cognito_client_id,
        issuer=f"https://cognito-idp.{config.aws_region}.amazonaws.com/{config.cognito_user_pool_id}",
        options={"verify_at_hash": False},
    )

    if claims.get("token_use") != "id":
        raise JWTError("Invalid token_use: expected 'id'")

    return claims


def _extract_animal_type_from_history(history: list[dict]) -> str:
    """Best-effort extraction of animal_type from conversation history."""
    for entry in reversed(history):
        content = entry.get("content", "").lower()
        for animal in ("cattle", "poultry", "buffalo", "goat", "sheep"):
            if animal in content:
                return animal
    return "cattle"  # safe default


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/claude")
async def debug_claude():
    """Probe the claude CLI subprocess. Remove before production."""
    import asyncio as _asyncio
    import subprocess as _subprocess
    results = {}
    # 1. Basic binary check
    try:
        r = _subprocess.run(["which", "claude"], capture_output=True, text=True, timeout=5)
        results["which_claude"] = r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        results["which_claude"] = str(e)
    # 2. Version check
    try:
        r = _subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
        results["version_stdout"] = r.stdout.strip()
        results["version_stderr"] = r.stderr.strip()
        results["version_rc"] = r.returncode
    except Exception as e:
        results["version_error"] = str(e)
    # 3. Event loop type
    results["event_loop"] = type(_asyncio.get_event_loop()).__name__
    return results


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
async def auth_login(body: LoginRequest):
    try:
        resp = _cognito.initiate_auth(
            ClientId=config.cognito_client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": body.username,
                "PASSWORD": body.password,
            },
        )
        token = resp["AuthenticationResult"]["IdToken"]
        log.info(
            "auth_login_success",
            username=body.username,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        return {"success": True, "data": {"token": token, "username": body.username}, "error": None}

    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("NotAuthorizedException", "UserNotFoundException"):
            log.warning(
                "auth_login_failed",
                username=body.username,
                reason=code,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "AUTH_FAILED",
                        "message": "Invalid credentials",
                        "message_hi": "गलत उपयोगकर्ता नाम या पासवर्ड",
                    },
                },
            )
        log.error(
            "auth_login_error",
            username=body.username,
            error=str(exc),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "Authentication service error",
                    "message_hi": "प्रमाणीकरण सेवा में त्रुटि",
                },
            },
        )


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token")

    if not token:
        await ws.accept()
        await ws.send_json(
            {
                "type": "error",
                "session_id": "",
                "message": "Authentication required",
                "message_hi": "प्रमाणीकरण आवश्यक है",
            }
        )
        await ws.close(code=4001)
        return

    try:
        claims = await _validate_jwt(token)
    except JWTError as exc:
        await ws.accept()
        log.warning(
            "ws_auth_failed",
            error=str(exc),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        await ws.send_json(
            {
                "type": "error",
                "session_id": "",
                "message": "Invalid authentication token",
                "message_hi": "अमान्य प्रमाणीकरण टोकन",
            }
        )
        await ws.close(code=4001)
        return
    except Exception as exc:
        await ws.accept()
        log.error(
            "ws_jwks_fetch_failed",
            error=str(exc),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        await ws.send_json(
            {
                "type": "error",
                "session_id": "",
                "message": "Authentication service unavailable. Please try again.",
                "message_hi": "प्रमाणीकरण सेवा अनुपलब्ध है। कृपया पुनः प्रयास करें।",
            }
        )
        await ws.close(code=4002)
        return

    # Extract farmer phone from JWT — stored in Cognito phone_number claim
    farmer_phone = claims.get("phone_number", "")

    await ws.accept()
    log.info(
        "ws_connected",
        username=claims.get("cognito:username", "unknown"),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    # Per-connection send lock — prevents concurrent ws.send_json calls from
    # the main loop and background Transcribe tasks colliding.
    send_lock = asyncio.Lock()

    async def locked_send(payload: dict) -> None:
        async with send_lock:
            await ws.send_json(payload)

    # Active Transcribe tasks for this connection, keyed by session_id.
    active_transcriptions: dict[str, asyncio.Task] = {}

    try:
        while True:
            raw = await ws.receive_text()
            log.info(
                "ws_message_received",
                raw_length=len(raw),
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await locked_send(
                    {
                        "type": "error",
                        "session_id": "",
                        "message": "Invalid JSON",
                        "message_hi": "अमान्य संदेश प्रारूप",
                    }
                )
                continue

            msg_type = data.get("type")
            session_id = data.get("session_id", "")

            _hook.log_ws_message(session_id, msg_type, {"raw_length": len(raw)})

            if msg_type == "chat":
                message = data.get("message", "").strip()
                if not message:
                    continue
                if len(message) > 2000:
                    await locked_send(
                        {
                            "type": "error",
                            "session_id": session_id,
                            "message": "Message too long (max 2000 characters)",
                            "message_hi": "संदेश बहुत लंबा है (अधिकतम 2000 अक्षर)",
                        }
                    )
                    continue
                language = data.get("language", "en")
                _session_languages[session_id] = language
                _session_farmer_phones[session_id] = farmer_phone

                start_time = datetime.utcnow()
                await _hook.pre_tool_use(session_id, "chat", {"language": language})

                history = _session_histories.setdefault(session_id, [])
                async with _get_session_lock(session_id):
                    assistant_response = await process_message(
                        session_id, message, language, ws, history,
                        farmer_phone=_session_farmer_phones.get(session_id, ""),
                    )

                    # Store the exchange in history so the next message has context.
                    if assistant_response:
                        history.append({"role": "user", "content": message})
                        history.append({"role": "assistant", "content": assistant_response})
                        # Cap to prevent unbounded growth
                        if len(history) > _MAX_HISTORY:
                            _session_histories[session_id] = history[-_MAX_HISTORY:]

                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                await _hook.post_tool_use(session_id, "chat", {}, duration_ms)

            elif msg_type == "symptom_answers":
                # Farmer completed the SymptomInterviewOverlay — inject answers into history
                # and resume the agentic loop.
                raw_answers = data.get("answers", [])
                if not raw_answers or not isinstance(raw_answers, list):
                    continue
                # Cap to 10 answers and sanitise each entry
                if len(raw_answers) > 10:
                    raw_answers = raw_answers[:10]
                answers = []
                for a in raw_answers:
                    if not isinstance(a, dict):
                        continue
                    q = str(a.get("question", "")).strip()[:500]
                    ans = str(a.get("answer", "")).strip()[:1000]
                    if q and ans:
                        answers.append({"question": q, "answer": ans})
                if not answers:
                    continue

                history = _session_histories.setdefault(session_id, [])
                language = _session_languages.get(session_id, data.get("language", "en"))

                # Build a single history entry from all Q&A pairs
                qa_text = "Symptom answers:\n" + "\n".join(
                    f"Q: {a['question']}\nA: {a['answer']}" for a in answers
                )
                history.append({"role": "user", "content": qa_text})
                if len(history) > _MAX_HISTORY:
                    _session_histories[session_id] = history[-_MAX_HISTORY:]

                _pending_action_sessions.pop(session_id, None)

                log.info(
                    "symptom_answers_received",
                    session_id=session_id,
                    answer_count=len(answers),
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

                # Resume agent with the symptom answers (serialised per session)
                async with _get_session_lock(session_id):
                    assistant_response = await process_message(
                        session_id, qa_text, language, ws, history,
                        farmer_phone=_session_farmer_phones.get(session_id, ""),
                    )
                    if assistant_response:
                        history.append({"role": "assistant", "content": assistant_response})
                        if len(history) > _MAX_HISTORY:
                            _session_histories[session_id] = history[-_MAX_HISTORY:]

            elif msg_type == "image_data":
                # Flutter uploaded image to S3 — inject into history and resume agent
                s3_key = str(data.get("s3_key", "")).strip()
                # Validate key to prevent injecting arbitrary content into history
                if not s3_key or len(s3_key) > 500 or ".." in s3_key:
                    continue

                history = _session_histories.setdefault(session_id, [])
                language = _session_languages.get(session_id, data.get("language", "en"))
                animal_type = _extract_animal_type_from_history(history)

                image_message = (
                    f"Image uploaded. S3 key: {s3_key}. "
                    f"Animal type: {animal_type}. "
                    "Please classify the disease."
                )
                history.append({"role": "user", "content": image_message})
                if len(history) > _MAX_HISTORY:
                    _session_histories[session_id] = history[-_MAX_HISTORY:]

                _pending_action_sessions.pop(session_id, None)

                log.info(
                    "image_data_received",
                    session_id=session_id,
                    s3_key=s3_key,
                    animal_type=animal_type,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

                # Resume agent for disease classification (serialised per session)
                async with _get_session_lock(session_id):
                    assistant_response = await process_message(
                        session_id, image_message, language, ws, history,
                        farmer_phone=_session_farmer_phones.get(session_id, ""),
                    )
                    if assistant_response:
                        history.append({"role": "assistant", "content": assistant_response})
                        if len(history) > _MAX_HISTORY:
                            _session_histories[session_id] = history[-_MAX_HISTORY:]

            elif msg_type == "gps_data":
                # Farmer shared GPS — inject coordinates into history and resume agent
                lat = data.get("lat")
                lon = data.get("lon")
                if lat is None or lon is None:
                    continue

                history = _session_histories.setdefault(session_id, [])
                language = _session_languages.get(session_id, "en")

                gps_message = (
                    f"GPS coordinates received. lat={lat}, lon={lon}. "
                    "Please find the nearest vet."
                )
                history.append({"role": "user", "content": gps_message})
                if len(history) > _MAX_HISTORY:
                    _session_histories[session_id] = history[-_MAX_HISTORY:]

                log.info(
                    "gps_data_received",
                    session_id=session_id,
                    lat=lat,
                    lon=lon,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

                async with _get_session_lock(session_id):
                    assistant_response = await process_message(
                        session_id, gps_message, language, ws, history,
                        farmer_phone=_session_farmer_phones.get(session_id, ""),
                    )
                    if assistant_response:
                        history.append({"role": "assistant", "content": assistant_response})
                        if len(history) > _MAX_HISTORY:
                            _session_histories[session_id] = history[-_MAX_HISTORY:]

            elif msg_type == "vet_preference":
                # Farmer responded to vet-preference card (yes/no)
                choice = str(data.get("choice", "")).strip().lower()
                if choice not in ("yes", "no"):
                    continue

                history = _session_histories.setdefault(session_id, [])
                language = _session_languages.get(session_id, "en")

                if choice == "yes":
                    pref_message = "Farmer confirmed: yes, please contact a vet."
                else:
                    pref_message = "Farmer declined vet contact. Please provide self-care guidance only."

                history.append({"role": "user", "content": pref_message})
                if len(history) > _MAX_HISTORY:
                    _session_histories[session_id] = history[-_MAX_HISTORY:]

                log.info(
                    "vet_preference_received",
                    session_id=session_id,
                    choice=choice,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

                async with _get_session_lock(session_id):
                    assistant_response = await process_message(
                        session_id, pref_message, language, ws, history,
                        farmer_phone=_session_farmer_phones.get(session_id, ""),
                    )
                    if assistant_response:
                        history.append({"role": "assistant", "content": assistant_response})
                        if len(history) > _MAX_HISTORY:
                            _session_histories[session_id] = history[-_MAX_HISTORY:]

            elif msg_type == "voice_start":
                language_code = data.get("language", "hi-IN")
                # Cancel any existing transcription for this session
                existing = active_transcriptions.pop(session_id, None)
                if existing and not existing.done():
                    existing.cancel()
                transcribe_service.start_session(session_id)
                task = asyncio.create_task(
                    transcribe_service.run_transcription(
                        session_id=session_id,
                        language_code=language_code,
                        region=config.aws_region,
                        send_fn=locked_send,
                    )
                )
                active_transcriptions[session_id] = task
                log.info(
                    "voice_start",
                    session_id=session_id,
                    language_code=language_code,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

            elif msg_type == "voice_audio":
                b64 = data.get("data", "")
                if b64:
                    transcribe_service.push_audio(session_id, b64)

            elif msg_type == "voice_stop":
                transcribe_service.stop_session(session_id)
                log.info(
                    "voice_stop",
                    session_id=session_id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

            else:
                log.warning(
                    "ws_unknown_message_type",
                    msg_type=msg_type,
                    session_id=session_id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

    except WebSocketDisconnect:
        # Cancel all in-progress transcription tasks for this connection
        for task in active_transcriptions.values():
            if not task.done():
                task.cancel()
        active_transcriptions.clear()
        log.info(
            "ws_disconnected",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )


@app.post("/api/upload-url")
async def upload_url(
    session_id: str = "",
    authorization: Optional[str] = Header(default=None),
):
    """Generate a pre-signed S3 PUT URL for image upload."""
    # Extract session_id from Authorization header (JWT sub claim) if not provided
    if not session_id and authorization:
        try:
            token = authorization.removeprefix("Bearer ").strip()
            claims = await _validate_jwt(token)
            session_id = claims.get("sub", str(uuid4()))
        except Exception:
            session_id = str(uuid4())

    if not session_id:
        session_id = str(uuid4())

    s3_key = f"uploads/{session_id}/{uuid4()}.jpg"

    try:
        upload_presigned_url = _s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": config.s3_image_bucket,
                "Key": s3_key,
                "ContentType": "image/jpeg",
            },
            ExpiresIn=900,  # 15 minutes
        )
        log.info(
            "presigned_url_generated",
            session_id=session_id,
            s3_key=s3_key,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        return {
            "success": True,
            "data": {"upload_url": upload_presigned_url, "s3_key": s3_key},
            "error": None,
        }
    except ClientError as exc:
        log.error(
            "presigned_url_error",
            session_id=session_id,
            error=str(exc),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "UPLOAD_URL_ERROR",
                    "message": "Could not generate upload URL. Please try again.",
                    "message_hi": "अपलोड URL उत्पन्न नहीं हो सका। कृपया पुनः प्रयास करें।",
                },
            },
        )


@app.get("/api/history")
async def history(authorization: Optional[str] = Header(default=None)):
    token = (authorization or "").replace("Bearer ", "").strip()
    if not token:
        return JSONResponse(status_code=401, content={
            "success": False, "data": None,
            "error": {"message": "Unauthorized", "message_hi": "अनधिकृत"},
        })
    try:
        claims = await _validate_jwt(token)
        farmer_phone = claims.get("phone_number", "")
    except Exception:
        return JSONResponse(status_code=401, content={
            "success": False, "data": None,
            "error": {"message": "Invalid token", "message_hi": "अमान्य टोकन"},
        })

    if not farmer_phone:
        return JSONResponse(status_code=400, content={
            "success": False, "data": None,
            "error": {"message": "Phone number not found in token", "message_hi": "टोकन में फोन नंबर नहीं मिला"},
        })

    try:
        response = _dynamodb.query(
            TableName=config.consultations_table,
            IndexName="gsi-farmer-phone",
            KeyConditionExpression="farmer_phone = :phone",
            ExpressionAttributeValues={":phone": {"S": farmer_phone}},
            ScanIndexForward=False,  # no-op (GSI has no sort key); app sort below
        )
        items = response.get("Items", [])
        consultations = []
        for item in items:
            consultations.append({
                "consultation_id": item.get("session_id", {}).get("S", ""),
                "animal_type": item.get("animal_type", {}).get("S", ""),
                "disease_name": item.get("disease_name", {}).get("S", ""),
                "confidence_score": float(item.get("confidence_score", {}).get("N", "0")),
                "severity": item.get("severity", {}).get("S", ""),
                "vet_assigned": item.get("vet_assigned", {}).get("S", ""),
                "treatment_summary": item.get("treatment_summary", {}).get("S", ""),
                "kb_citations": item.get("kb_citations", {}).get("S", "[]"),
                "timestamp": item.get("timestamp", {}).get("S", ""),
            })
        consultations.sort(key=lambda c: c["timestamp"], reverse=True)
        return {"success": True, "data": consultations, "error": None}
    except Exception as e:
        log.error(
            "history_dynamo_error",
            error=str(e),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        return JSONResponse(status_code=500, content={
            "success": False, "data": None,
            "error": {"message": "Internal server error", "message_hi": "इतिहास लोड करने में त्रुटि"},
        })
