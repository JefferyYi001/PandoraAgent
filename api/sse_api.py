"""
SSE API - Server-Sent Events for real-time monitoring
"""

import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/sse")


def _get_agent():
    """Lazy import to avoid circular dependency"""
    from main import agent
    return agent


async def event_generator():
    """Generate SSE events with agent status updates"""
    agent = _get_agent()
    while True:
        status = agent.get_status()
        yield f"data: {status}\n\n"
        await asyncio.sleep(2)


@router.get("/events")
async def sse_events():
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
