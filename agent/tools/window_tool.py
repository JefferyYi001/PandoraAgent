"""
WindowTool - WeChat window detection, restore, and minimize
Uses win32gui API with template-matching fallback
"""

from agent.tools.base_tool import BaseTool, ToolResult
from automation import window
from automation.vision import VisionUtils
from utils.logger import logger


class WindowTool(BaseTool):
    name = "window"
    description = "Find, restore, or minimize the WeChat window"
    params = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["restore", "minimize", "check_visible"],
                       "description": "Action to perform on WeChat window"},
        },
        "required": ["action"],
    }

    def execute(self, params: dict | None = None) -> ToolResult:
        action = (params or {}).get("action", "check_visible")
        if action == "check_visible":
            return self._check_visible()
        elif action == "restore":
            return self._restore()
        elif action == "minimize":
            return self._minimize()
        return ToolResult.fail(f"Unknown action: {action}")

    def _check_visible(self) -> ToolResult:
        from config.defaults import get_defaults
        defaults = get_defaults()
        visible_threshold = defaults.get("vision", {}).get("thresholds", {}).get("window_visible", 0.6)

        hwnd = window.find_window(window_name="WeChat")
        if hwnd and window.is_window_visible(hwnd):
            return ToolResult.ok("WeChat window is visible", data={"hwnd": hwnd, "visible": True})

        hwnd = window.find_window(window_name="微信")
        if hwnd and window.is_window_visible(hwnd):
            return ToolResult.ok("WeChat window is visible", data={"hwnd": hwnd, "visible": True})

        return ToolResult.ok("WeChat window is not visible", data={"visible": False})

    def _restore(self) -> ToolResult:
        hwnd = window.find_window(window_name="WeChat") or window.find_window(window_name="微信")
        if not hwnd:
            return ToolResult.fail("WeChat window not found")
        if window.is_window_visible(hwnd) and not window.is_window_minimized(hwnd):
            return ToolResult.ok("WeChat window already visible")
        if window.restore_window(hwnd):
            return ToolResult.ok("WeChat window restored")
        return ToolResult.fail("Failed to restore WeChat window")

    def _minimize(self) -> ToolResult:
        hwnd = window.find_window(window_name="WeChat") or window.find_window(window_name="微信")
        if not hwnd:
            return ToolResult.fail("WeChat window not found")
        if window.minimize_window(hwnd):
            return ToolResult.ok("WeChat window minimized")
        return ToolResult.fail("Failed to minimize WeChat window")
