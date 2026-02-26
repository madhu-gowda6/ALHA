import structlog
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

log = structlog.get_logger()

app = FastAPI(title="ALHA Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    log.info("ws_connected")
    # stub — implemented in Epic 2
    await ws.close()


@app.post("/api/upload-url")
async def upload_url():
    return {"success": True, "data": {}, "error": None}


@app.get("/api/history")
async def history():
    return {"success": True, "data": [], "error": None}


@app.post("/api/auth/login")
async def auth_login():
    return {"success": True, "data": {}, "error": None}
