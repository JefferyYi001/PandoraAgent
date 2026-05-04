"""
Calibration API - screenshot capture, template matching, red dot analysis
"""

import os
import time
from fastapi import APIRouter
from pydantic import BaseModel

from agent.tools.calibration_tool import CalibrationTool
from config.settings import get_settings

router = APIRouter(prefix="/calibration")


class ScreenshotRequest(BaseModel):
    region: list[int] | None = None
    output_path: str | None = None


class TemplateMatchRequest(BaseModel):
    region: list[int]
    template_path: str
    threshold: float = 0.8


class RedDotAnalyzeRequest(BaseModel):
    template_path: str


@router.post("/screenshot")
async def capture_screenshot(req: ScreenshotRequest):
    tool = CalibrationTool()
    params = {"include_base64": True}
    if req.region:
        params["region"] = req.region

    # Auto-save to data/uploads/ if no output_path specified
    if not req.output_path:
        settings = get_settings()
        upload_dir = os.path.join(settings.data_dir, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        params["output_path"] = os.path.join(upload_dir, f"screenshot_{int(time.time())}.png")

    result = tool.execute({"action": "screenshot", **params})
    return {"success": result.success, "output": result.output, "data": result.data}


@router.post("/match_template")
async def match_template(req: TemplateMatchRequest):
    tool = CalibrationTool()
    result = tool.execute({
        "action": "match_template",
        "region": req.region,
        "template_path": req.template_path,
        "threshold": req.threshold,
    })
    return {"success": result.success, "output": result.output, "data": result.data}


@router.post("/analyze_red_dot")
async def analyze_red_dot(req: RedDotAnalyzeRequest):
    tool = CalibrationTool()
    result = tool.execute({
        "action": "analyze_red_dot",
        "template_path": req.template_path,
    })
    return {"success": result.success, "output": result.output, "data": result.data}


@router.get("/mouse_position")
async def get_mouse_position():
    """Get current global mouse position"""
    import pyautogui
    pos = pyautogui.position()
    return {"x": pos.x, "y": pos.y}
