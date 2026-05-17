"""
SentryTool - Detect taskbar icon flashing to identify new messages
Uses dual-template diff-based comparison (normal vs alert state)
"""

import os
import cv2

from agent.tools.base_tool import BaseTool, ToolResult
from automation.vision import VisionUtils
from utils.logger import logger


class SentryTool(BaseTool):
    name = "sentry"
    description = "Detect if the WeChat taskbar icon is flashing, indicating a new message. Returns 'alert' if flashing, 'normal' otherwise."
    params = {
        "type": "object",
        "properties": {
            "taskbar_region": {
                "type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4,
                "description": "Taskbar region as [left, top, width, height] in screen coords",
            },
        },
        "required": ["taskbar_region"],
    }

    def execute(self, params: dict | None = None) -> ToolResult:
        p = params or {}
        region = tuple(p.get("taskbar_region", []))
        if len(region) != 4:
            return ToolResult.fail("taskbar_region must be [left, top, width, height]")

        from config.defaults import get_defaults
        from config.settings import get_settings
        defaults = get_defaults()
        settings = get_settings()

        diff_threshold = defaults.get("vision", {}).get("sentry_diff_threshold", 0.05)

        templates_dir = settings.templates_dir
        normal_path = os.path.join(templates_dir, "taskbar_normal.png")
        alert_path = os.path.join(templates_dir, "taskbar_alert.png")

        if not os.path.exists(normal_path) or not os.path.exists(alert_path):
            return ToolResult.fail(f"Missing template files: {normal_path} or {alert_path}")

        screenshot = VisionUtils.capture_region(region)
        if screenshot is None:
            return ToolResult.fail("Failed to capture taskbar region")

        normal_score, _ = self._match_template(screenshot, normal_path)
        alert_score, alert_loc = self._match_template(screenshot, alert_path)

        logger.debug(f"Sentry: normal={normal_score:.3f}, alert={alert_score:.3f}, threshold={diff_threshold}")

        if alert_score > normal_score + diff_threshold:
            alert_position = None
            if alert_loc is not None:
                alert_template = cv2.imread(alert_path)
                th, tw = alert_template.shape[:2]
                alert_position = [
                    alert_loc[0] + tw // 2 + region[0],
                    alert_loc[1] + th // 2 + region[1],
                ]
            return ToolResult.ok("alert", data={
                "normal_score": normal_score,
                "alert_score": alert_score,
                "state": "alert",
                "alert_position": alert_position,
            })

        return ToolResult.ok("normal", data={
            "normal_score": normal_score,
            "alert_score": alert_score,
            "state": "normal",
        })

    def _match_template(self, screenshot, template_path: str) -> tuple[float, tuple[int, int] | None]:
        template = cv2.imread(template_path)
        if template is None:
            return (0.0, None)
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return (max_val, max_loc)
