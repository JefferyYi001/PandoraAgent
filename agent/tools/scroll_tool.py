"""
ScrollTool - Scroll chat content area to bottom, detect completion via screenshot diff
"""

import time
import random
import pyautogui
import cv2
import numpy as np

from agent.tools.base_tool import BaseTool, ToolResult
from automation.humanize import human_sleep
from automation.vision import VisionUtils
from utils.logger import logger


class ScrollTool(BaseTool):
    name = "scroll"
    description = "Scroll the chat content area to the bottom. Scrolls until no new content appears."
    params = {
        "type": "object",
        "properties": {
            "screen_region": {
                "type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4,
                "description": "Chat content region as [left, top, width, height] in screen coords",
            },
            "max_scrolls": {
                "type": "integer", "description": "Maximum scroll iterations before giving up",
            },
        },
        "required": ["screen_region"],
    }

    def execute(self, params: dict | None = None) -> ToolResult:
        p = params or {}
        screen_region = tuple(p.get("screen_region", []))
        if len(screen_region) != 4:
            return ToolResult.fail("screen_region must be [left, top, width, height]")

        from config.defaults import get_defaults
        defaults = get_defaults()
        max_scrolls = p.get("max_scrolls", defaults.get("polling", {}).get("max_scroll_attempts", 20))
        change_threshold = defaults.get("vision", {}).get("scroll_change_threshold", 0.01)

        # Move cursor into chat area before scrolling
        pyautogui.moveTo(screen_region[0] + 50, screen_region[1] + 50)

        prev_screenshot = None
        scroll_count = 0

        for i in range(max_scrolls):
            current = VisionUtils.capture_region(screen_region)
            if current is None:
                return ToolResult.fail("Failed to capture screen region")

            if prev_screenshot is not None:
                diff = cv2.absdiff(prev_screenshot, current)
                gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                total_pixels = gray.shape[0] * gray.shape[1]
                non_zero = cv2.countNonZero(gray)
                change_ratio = non_zero / total_pixels if total_pixels > 0 else 0

                logger.debug(f"Scroll iteration {i}: change_ratio={change_ratio:.4f}")
                if change_ratio < change_threshold:
                    return ToolResult.ok(f"Reached bottom after {scroll_count} scrolls",
                                         data={"scrolls": scroll_count, "iterations": i + 1})

            prev_screenshot = current.copy()
            scroll_amount = random.randint(-600, -300)
            pyautogui.scroll(scroll_amount)
            human_sleep(0.15, 0.3)
            scroll_count += 1

        return ToolResult.ok(f"Max scrolls ({max_scrolls}) reached", data={"scrolls": scroll_count})
