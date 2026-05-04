"""
WechatAssistantAgent - FastAPI entry point + Agent background dispatch
"""

import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config.settings import get_settings
from utils.logger import logger
from db.connection import init_db
from agent.core import WechatAgent

# Global agent instance
agent = WechatAgent()
_agent_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events (startup/shutdown)"""
    settings = get_settings()
    logger.info("WechatAssistantAgent starting up")
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.logs_dir).mkdir(parents=True, exist_ok=True)
    yield
    logger.info("WechatAssistantAgent shutting down")
    await agent.stop()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="WechatAssistantAgent",
        description="WeChat customer service automation with LLM-powered replies",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Initialize database
    init_db()

    # Initialize agent
    agent.initialize()

    # Mount static files
    static_dir = Path(__file__).parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Register API routes
    register_routes(app)

    return app


def register_routes(app: FastAPI):
    """Register all API routes"""
    from api import agent_api, config_api, calibration_api, sse_api

    app.include_router(agent_api.router, prefix="/api")
    app.include_router(config_api.router, prefix="/api")
    app.include_router(calibration_api.router, prefix="/api")
    app.include_router(sse_api.router, prefix="/api")

    # Static page routes
    pages_dir = Path(__file__).parent / "web" / "pages"

    @app.get("/")
    async def index():
        return FileResponse(str(pages_dir / "index.html"))

    @app.get("/config")
    async def config_page():
        return FileResponse(str(pages_dir / "config.html"))

    @app.get("/wechat-config")
    async def wechat_config_page():
        return FileResponse(str(pages_dir / "wechat-config.html"))

    @app.get("/templates")
    async def templates_page():
        return FileResponse(str(pages_dir / "templates.html"))

    @app.get("/calibration")
    async def calibration_page():
        return FileResponse(str(pages_dir / "calibration.html"))

    @app.get("/monitor")
    async def monitor_page():
        return FileResponse(str(pages_dir / "monitor.html"))


app = create_app()


def start_agent():
    """Start the agent background task (called from main)"""
    global _agent_task
    loop = asyncio.get_event_loop()
    _agent_task = loop.create_task(agent.run())


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "access": {
                    "format": "%(asctime)s %(levelname)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "access": {
                    "class": "logging.StreamHandler",
                    "formatter": "access",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
            },
        },
    )
