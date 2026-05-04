"""
Agent API - start/stop/status endpoints
"""

from fastapi import APIRouter

router = APIRouter(prefix="/agent")


def _get_agent():
    """Lazy import to avoid circular dependency"""
    from main import agent
    return agent


@router.get("/status")
async def get_agent_status():
    return _get_agent().get_status()


@router.post("/start")
async def start_agent():
    agent = _get_agent()
    if agent._running:
        return {"status": "already_running"}
    from main import start_agent
    start_agent()
    return {"status": "started"}


@router.post("/stop")
async def stop_agent():
    await _get_agent().stop()
    return {"status": "stopped"}
