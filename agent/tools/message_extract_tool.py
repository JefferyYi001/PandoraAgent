"""
MessageExtractTool - Extract sender messages from chat content area
Flow: scroll to bottom → find my last avatar → locate sender bubbles → copy text
"""

import os
import random
import pyautogui

from agent.tools.base_tool import BaseTool, ToolResult
from automation.humanize import human_sleep, human_right_click, human_click
from automation.vision import VisionUtils
from automation.clipboard import ClipboardHelper
from utils.logger import logger


class MessageExtractTool(BaseTool):
    name = "message_extract"
    description = "Extract messages from the chat area. Scrolls to bottom, finds sender bubbles, copies text. Returns list of messages."
    params = {
        "type": "object",
        "properties": {
            "chat_content_region": {
                "type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4,
                "description": "Chat content region as [left, top, width, height] in screen coords",
            },
        },
        "required": ["chat_content_region"],
    }

    def execute(self, params: dict | None = None) -> ToolResult:
        p = params or {}
        region = tuple(p.get("chat_content_region", []))
        if len(region) != 4:
            return ToolResult.fail("chat_content_region must be [left, top, width, height]")

        from config.settings import get_settings
        from config.defaults import get_defaults
        settings = get_settings()
        defaults = get_defaults()

        templates_dir = settings.templates_dir
        avatar_path = os.path.join(templates_dir, "my_avatar.png")
        bubble_path = os.path.join(templates_dir, "bubble_left.png")

        # Step 1: Find my last message avatar (right side)
        my_last_y = self._find_my_last_message_y(region, avatar_path, defaults)
        if my_last_y is None:
            return ToolResult.fail("Could not find my last message avatar")

        logger.info(f"My last message Y: {my_last_y}")

        # Step 2: Find sender bubbles (left side, newer than my last message)
        sender_positions = self._find_sender_bubbles(region, bubble_path, my_last_y, defaults)
        if not sender_positions:
            return ToolResult.ok("No new sender messages found", data={"messages": []})

        logger.info(f"Found {len(sender_positions)} sender message(s)")

        # Step 3: Copy messages
        messages = []
        if len(sender_positions) == 1:
            # Single message: right-click + copy
            x, y = sender_positions[0]
            result = self._copy_single_message(x, y, templates_dir, defaults)
            if result and result.success:
                messages.append(result.data.get("text", ""))
        else:
            # Multiple messages: drag select + copy
            result = self._copy_multiple_messages(sender_positions, region, templates_dir, defaults)
            if result and result.success:
                messages.append(result.data.get("text", ""))

        if messages:
            return ToolResult.ok(f"Extracted {len(messages)} message(s)", data={"messages": messages})
        return ToolResult.fail("Failed to extract messages")

    def _find_my_last_message_y(self, region, avatar_path, defaults):
        if not os.path.exists(avatar_path):
            return None
        matches = VisionUtils.find_all_matches(
            region, avatar_path,
            defaults.get("vision", {}).get("thresholds", {}).get("bubble", 0.75)
        )
        # Filter to right side of chat area
        right_threshold = region[0] + region[2] - 100
        right_matches = [m for m in matches if m[0] > right_threshold]
        if not right_matches:
            return None
        return max(m[1] for m in right_matches)

    def _find_sender_bubbles(self, region, bubble_path, my_last_y, defaults):
        if not os.path.exists(bubble_path):
            return []
        matches = VisionUtils.find_all_matches(
            region, bubble_path,
            defaults.get("vision", {}).get("thresholds", {}).get("bubble", 0.75)
        )
        # Filter: left side (x between 50-100 relative to region)
        left_matches = [m for m in matches if region[0] + 50 < m[0] < region[0] + 100]
        # Y-clustering to group overlapping bubbles
        left_matches.sort(key=lambda m: m[1])
        clusters = []
        current_cluster = [left_matches[0]]
        for m in left_matches[1:]:
            if m[1] - current_cluster[-1][1] < 20:
                current_cluster.append(m)
            else:
                clusters.append(current_cluster)
                current_cluster = [m]
        clusters.append(current_cluster)

        # Take centroid of each cluster
        positions = []
        for cluster in clusters:
            avg_x = int(sum(m[0] for m in cluster) / len(cluster))
            avg_y = int(sum(m[1] for m in cluster) / len(cluster))
            positions.append((avg_x, avg_y))

        # Filter: only messages newer than my last message
        return [(x, y) for x, y in positions if y > my_last_y - 50]

    def _copy_single_message(self, x, y, templates_dir, defaults):
        from agent.tools.copy_tool import CopyTool
        copy_x = x + 15 + random.randint(-3, 3)
        copy_y = y + random.randint(-3, 3)
        copy_tool = CopyTool()
        return copy_tool.execute({"x": copy_x, "y": copy_y})

    def _copy_multiple_messages(self, positions, region, templates_dir, defaults):
        """Drag-select multiple messages and copy"""
        start_x, start_y = positions[0]
        last_y = positions[-1][1]

        pyautogui.moveTo(start_x, start_y)
        human_sleep(0.1, 0.2)

        # Drag down to select all messages
        drag_end_y = last_y + random.randint(80, 150)
        pyautogui.dragTo(start_x, drag_end_y, duration=0.3)
        human_sleep(0.2, 0.4)

        # Right-click and copy
        from agent.tools.copy_tool import CopyTool
        copy_tool = CopyTool()
        return copy_tool.execute({"x": start_x, "y": start_y})
