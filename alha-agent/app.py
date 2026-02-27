import json
from datetime import datetime
from typing import Optional

import boto3
import httpx
import structlog
from botocore.exceptions import ClientError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from pydantic import BaseModel

from agent import process_message
from config import config
from hooks.logging_hook import LoggingHook

log = structlog.get_logger()
_hook = LoggingHook()

app = FastAPI(title="ALHA Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Module-level Cognito client — created once, reused per request
_cognito = boto3.client("cognito-idp", region_name=config.aws_region)

# JWKS cache — refreshed on validation failure
_jwks: Optional[dict] = None

# In-memory conversation history keyed by session_id.
# Each value is a list of {"role": "user"|"assistant", "content": str} dicts.
# Capped at _MAX_HISTORY entries to avoid unbounded growth.
_session_histories: dict[str, list[dict]] = {}
_MAX_HISTORY = 40


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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


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

    await ws.accept()
    log.info(
        "ws_connected",
        username=claims.get("cognito:username", "unknown"),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

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
                await ws.send_json(
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
                    await ws.send_json(
                        {
                            "type": "error",
                            "session_id": session_id,
                            "message": "Message too long (max 2000 characters)",
                            "message_hi": "संदेश बहुत लंबा है (अधिकतम 2000 अक्षर)",
                        }
                    )
                    continue
                language = data.get("language", "en")

                start_time = datetime.utcnow()
                await _hook.pre_tool_use(session_id, "chat", {"language": language})

                history = _session_histories.setdefault(session_id, [])
                assistant_response = await process_message(
                    session_id, message, language, ws, history
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
            else:
                log.warning(
                    "ws_unknown_message_type",
                    msg_type=msg_type,
                    session_id=session_id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

    except WebSocketDisconnect:
        log.info(
            "ws_disconnected",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )


@app.post("/api/upload-url")
async def upload_url():
    return {"success": True, "data": {}, "error": None}


@app.get("/api/history")
async def history():
    return {"success": True, "data": [], "error": None}
