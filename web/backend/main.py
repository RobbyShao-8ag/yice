import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.dirname(backend_dir)
project_root = os.path.dirname(web_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import config, history, websocket
from services.agent_bridge import AgentBridgeService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("易策 Web API starting...")
    app.state.agent_bridge = AgentBridgeService()
    logger.info("Agent bridge service initialized")
    yield
    logger.info("易策 Web API shutting down...")


app = FastAPI(
    title="易策 Web API",
    description="Web backend for yice AI decision system",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config.router, prefix="/api/config", tags=["配置管理"])
app.include_router(history.router, prefix="/api/history", tags=["历史记录"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


@app.get("/", tags=["健康检查"])
async def root():
    return {"status": "ok", "message": "易策 Web API 运行中"}


@app.get("/api/health", tags=["健康检查"])
async def health_check():
    return {
        "status": "healthy",
        "service": "yice-web-api",
        "version": "1.2.0",
    }
