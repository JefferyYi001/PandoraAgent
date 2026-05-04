"""
RedDotTool - Detect unread red dots in chat list using HSV color + shape analysis
"""

import os

from agent.tools.base_tool import BaseTool, ToolResult
from automation.vision import VisionUtils
from utils.logger import logger


class RedDotTool(BaseTool):
    name = "red_dot"
    description = "Detect unread red dots in the chat list area. Returns coordinates of detected red dots."
    params = {
        "type": "object",
        "properties": {
            "chat_list_region": {
                "type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4,
                "description": "Chat list area as [left, top, width, height] in screen coords",
            },
        },
        "required": ["chat_list_region"],
    }

    def execute(self, params: dict | None = None) -> ToolResult:
        p = params or {}
        screen_region = tuple(p.get("chat_list_region", []))
        if len(screen_region) != 4:
            return ToolResult.fail("chat_list_region must be [left, top, width, height]")

        from config.settings import get_settings
        settings = get_settings()
        templates_dir = settings.templates_dir

        # Load red dot template configs
        template_configs = []
        for filename in ("red_dot.png", "red_dot_2.png"):
            path = os.path.join(templates_dir, filename)
            if os.path.exists(path):
                config = VisionUtils.analyze_red_dot_template(path)
                if config:
                    template_configs.append(config)
                    logger.debug(f"Loaded red dot template: {filename}")

        if not template_configs:
            return ToolResult.fail("No red dot template files found")

        dots = VisionUtils.find_red_dots(screen_region, template_configs)
        if dots:
            return ToolResult.ok(f"Found {len(dots)} red dot(s)", data={"dots": dots, "count": len(dots)})

        return ToolResult.ok("No red dots found", data={"dots": [], "count": 0})
