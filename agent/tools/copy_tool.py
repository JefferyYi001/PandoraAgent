"""
CopyTool - Right-click to open context menu and click the copy button
Uses template matching to find "复制" (Copy) menu item
"""

import os
import pyautogui

from agent.tools.base_tool import BaseTool, ToolResult
from automation.humanize import human_right_click, human_sleep
from automation.vision import VisionUtils
from automation.clipboard import ClipboardHelper
from utils.logger import logger


class CopyTool(BaseTool):
    name = "copy"
    description = "Right-click at the given position and click the copy button in the context menu. Returns the copied text."
    params = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "Screen X coordinate to right-click"},
            "y": {"type": "integer", "description": "Screen Y coordinate to right-click"},
        },
        "required": ["x", "y"],
    }

    def execute(self, params: dict | None = None) -> ToolResult:
        p = params or {}
        if "x" not in p or "y" not in p:
            return ToolResult.fail("x and y are required")

        from config.settings import get_settings
        from config.defaults import get_defaults
        settings = get_settings()
        defaults = get_defaults()

        copy_btn_path = os.path.join(settings.templates_dir, "copy_btn.png")
        if not os.path.exists(copy_btn_path):
            return ToolResult.fail(f"Copy button template not found: {copy_btn_path}")

        threshold = defaults.get("vision", {}).get("thresholds", {}).get("copy_button", 0.75)

        ClipboardHelper.clear()
        human_right_click(p["x"], p["y"])
        human_sleep(0.3, 0.5)

        # Search for copy button in context menu region (near cursor)
        mx, my = pyautogui.position()
        search_region = (mx - 80, my - 10, 200, 300)

        for attempt in range(10):
            pos = VisionUtils.find_template(search_region, copy_btn_path, threshold)
            if pos:
                pyautogui.moveTo(pos[0], pos[1])
                human_sleep(0.05, 0.1)
                pyautogui.click()
                human_sleep(0.2, 0.4)

                text = ClipboardHelper.get_text()
                if text:
                    return ToolResult.ok(f"Copied text: {text[:50]}...",
                                         data={"text": text, "attempts": attempt + 1})
                return ToolResult.ok("Clicked copy button", data={"attempts": attempt + 1})

            human_sleep(0.1, 0.15)

        return ToolResult.fail("Could not find copy button after 10 attempts")
