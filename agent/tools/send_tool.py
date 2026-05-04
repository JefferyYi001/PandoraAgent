"""
SendTool - Paste reply from clipboard and press Enter to send
"""

import pyautogui

from agent.tools.base_tool import BaseTool, ToolResult
from automation.humanize import human_sleep, human_click, human_hotkey
from automation.clipboard import ClipboardHelper
from utils.logger import logger


class SendTool(BaseTool):
    name = "send"
    description = "Paste text from clipboard into the WeChat input box and press Enter to send."
    params = {
        "type": "object",
        "properties": {
            "input_box_center": {
                "type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2,
                "description": "Center coordinates of WeChat input box as [x, y]",
            },
            "text": {"type": "string", "description": "Text to send (will be placed on clipboard)"},
        },
        "required": ["input_box_center", "text"],
    }

    def execute(self, params: dict | None = None) -> ToolResult:
        p = params or {}
        if "input_box_center" not in p or "text" not in p:
            return ToolResult.fail("input_box_center and text are required")

        center = p["input_box_center"]
        if len(center) != 2:
            return ToolResult.fail("input_box_center must be [x, y]")

        # Set clipboard with reply text
        if not ClipboardHelper.set_text(p["text"]):
            return ToolResult.fail("Failed to set clipboard text")

        # Click input box to focus
        human_click(center[0], center[1])
        human_sleep(0.1, 0.2)

        # Paste
        human_hotkey("ctrl", "v")
        human_sleep(0.3, 0.5)

        # Send
        pyautogui.press("enter")
        human_sleep(0.2, 0.4)

        logger.info(f"Sent reply: {p['text'][:50]}...")
        return ToolResult.ok("Reply sent successfully", data={"text_length": len(p["text"])})
