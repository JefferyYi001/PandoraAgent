"""
CalibrationTool - Capture screen region, preview template matching, assist with visual calibration
Supports: screenshot capture, template matching preview, red dot analysis
"""

import base64
import os
import cv2
import time

from agent.tools.base_tool import BaseTool, ToolResult
from automation.vision import VisionUtils
from utils.logger import logger


class CalibrationTool(BaseTool):
    name = "calibration"
    description = "Capture screen region, preview template matching, analyze red dot parameters. Used for visual calibration and debugging."
    params = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["screenshot", "match_template", "analyze_red_dot"],
                "description": "Calibration action to perform",
            },
            "region": {
                "type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4,
                "description": "Screen region as [left, top, width, height]",
            },
            "template_path": {
                "type": "string",
                "description": "Path to template image (for match_template action)",
            },
            "threshold": {
                "type": "number",
                "description": "Matching threshold (0.0-1.0)",
            },
        },
        "required": ["action"],
    }

    def execute(self, params: dict | None = None) -> ToolResult:
        p = params or {}
        action = p.get("action", "screenshot")

        if action == "screenshot":
            return self._screenshot(p)
        elif action == "match_template":
            return self._match_template(p)
        elif action == "analyze_red_dot":
            return self._analyze_red_dot(p)
        return ToolResult.fail(f"Unknown action: {action}")

    def _screenshot(self, params: dict) -> ToolResult:
        region = tuple(params.get("region", []))
        if len(region) == 4:
            screenshot = VisionUtils.capture_region(region)
        else:
            screenshot = VisionUtils.capture_full_screen()
        if screenshot is None:
            return ToolResult.fail("Screenshot capture failed")

        include_base64 = params.get("include_base64", False)
        output_path = params.get("output_path")

        data = {"width": screenshot.shape[1], "height": screenshot.shape[0]}

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            cv2.imwrite(output_path, screenshot)
            logger.info(f"Screenshot saved to {output_path}")
            data["path"] = output_path

        if include_base64:
            _, buffer = cv2.imencode(".png", screenshot)
            data["image_base64"] = base64.b64encode(buffer).decode("utf-8")

        return ToolResult.ok(f"Screenshot captured: {screenshot.shape[1]}x{screenshot.shape[0]}", data=data)

    def _match_template(self, params: dict) -> ToolResult:
        region = tuple(params.get("region", []))
        if len(region) != 4:
            return ToolResult.fail("region is required for match_template")

        template_path = params.get("template_path", "")
        if not os.path.exists(template_path):
            return ToolResult.fail(f"Template not found: {template_path}")

        threshold = params.get("threshold", 0.8)
        pos = VisionUtils.find_template(region, template_path, threshold)

        if pos:
            return ToolResult.ok(f"Template matched at ({pos[0]}, {pos[1]})",
                                 data={"position": pos, "template": os.path.basename(template_path)})
        return ToolResult.fail("No template match found",
                               data={"template": os.path.basename(template_path), "threshold": threshold})

    def _analyze_red_dot(self, params: dict) -> ToolResult:
        template_path = params.get("template_path", "")
        if not template_path or not os.path.exists(template_path):
            return ToolResult.fail("Valid template_path is required")

        config = VisionUtils.analyze_red_dot_template(template_path)
        if config is None:
            return ToolResult.fail("Red dot analysis failed")

        return ToolResult.ok(f"Red dot analyzed: HSV=({config['h_min']}-{config['h_max']}, "
                             f"S>{config['s_min']}, V>{config['v_min']})", data=config)
