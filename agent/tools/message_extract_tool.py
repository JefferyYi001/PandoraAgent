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
            x, y = sender_positions[0]
            result = self._copy_single_message(x, y, templates_dir, defaults)
            if result and result.success:
                messages.append(result.data.get("text", ""))
        else:
            result = self._copy_multiple_messages(sender_positions, templates_dir, defaults)
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
            defaults.get("vision", {}).get("bubble_threshold", 0.75)
        )
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
            defaults.get("vision", {}).get("bubble_threshold", 0.75)
        )
        left_matches = [m for m in matches if region[0] + 50 < m[0] < region[0] + 100]
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

        positions = []
        for cluster in clusters:
            avg_x = int(sum(m[0] for m in cluster) / len(cluster))
            avg_y = int(sum(m[1] for m in cluster) / len(cluster))
            positions.append((avg_x, avg_y))

        return [(x, y) for x, y in positions if y > my_last_y - 50]

    def _is_cursor_over_text(self, templates_dir, defaults) -> bool:
        """Check if mouse cursor has changed from arrow to I-beam (text selection)"""
        cursor_path = os.path.join(templates_dir, "cursor_arrow.png")
        if not os.path.exists(cursor_path):
            return True

        threshold = defaults.get("vision", {}).get("cursor_arrow_threshold", 0.5)
        mx, my = pyautogui.position()
        region = (mx - 15, my - 15, 30, 30)
        score = VisionUtils.get_template_score(region, cursor_path)
        logger.info(f"Cursor arrow score: {score:.3f}")
        return score < threshold

    def _copy_single_message(self, x, y, templates_dir, defaults):
        """Right-click single message and copy — no text selection, no deselect needed"""
        from agent.tools.copy_tool import CopyTool
        copy_x = x + 15 + random.randint(-3, 3)
        copy_y = y + random.randint(-3, 3)
        copy_tool = CopyTool()
        return copy_tool.execute({"x": copy_x, "y": copy_y})

    def _copy_multiple_messages(self, positions, templates_dir, defaults):
        """Drag-select multiple messages, with cursor detection + retry + fallback"""
        first = positions[0]
        last = positions[-1]
        start_x = first[0] + 16
        start_y = first[1] + 3
        end_y = last[1] + random.randint(80, 150)

        logger.info(f"Drag select: ({start_x}, {start_y}) -> ({start_x}, {end_y})")

        pyautogui.moveTo(start_x, start_y)
        human_sleep(0.15, 0.25)

        # Cursor detection with retry (max 2 attempts)
        is_i_beam = False
        for attempt in range(2):
            if self._is_cursor_over_text(templates_dir, defaults):
                is_i_beam = True
                logger.info("I-beam cursor detected, proceeding to drag")
                break
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)
            logger.info(f"Still arrow cursor, offset ({offset_x}, {offset_y}) retry")
            start_x += offset_x
            start_y += offset_y
            pyautogui.moveTo(start_x, start_y)
            human_sleep(0.1, 0.2)

        if not is_i_beam:
            logger.warning("Cursor never changed to I-beam, fallback to single copy")
            return self._copy_single_message(first[0], first[1], templates_dir, defaults)

        # Clear stale clipboard content before copy
        ClipboardHelper.clear()

        # Drag to select all messages
        duration = random.uniform(0.4, 0.6)
        pyautogui.dragTo(start_x, end_y, duration=duration, button='left')
        human_sleep(0.1, 0.2)

        # Right-click to open context menu on selected text
        human_right_click(start_x, start_y)
        human_sleep(0.2, 0.4)

        # Find and click "复制" in the already-open context menu
        if self._find_and_click_copy(templates_dir, defaults):
            human_sleep(0.1, 0.2)
            text = ClipboardHelper.get_text() or ""
            self._deselect()
            return ToolResult.ok(f"Copied: {text[:50]}...", data={"text": text})

        from automation.humanize import human_press_key
        human_press_key('esc')
        return ToolResult.fail("Could not find copy button in context menu")

    def _find_and_click_copy(self, templates_dir, defaults) -> bool:
        """Find and click copy button in an already-open context menu"""
        copy_btn_path = os.path.join(templates_dir, "copy_btn.png")
        if not os.path.exists(copy_btn_path):
            logger.warning(f"Copy button template not found: {copy_btn_path}")
            return False

        threshold = defaults.get("vision", {}).get("copy_button_threshold", 0.75)
        mx, my = pyautogui.position()
        search_region = (mx - 80, my - 10, 200, 300)

        for attempt in range(10):
            pos = VisionUtils.find_template(search_region, copy_btn_path, threshold)
            if pos:
                human_click(pos[0], pos[1])
                return True
            human_sleep(0.1, 0.15)

        logger.warning("Could not find copy button after 10 attempts")
        return False

    def _deselect(self):
        """Click at random offset to deselect text"""
        x, y = pyautogui.position()
        offset_x = random.randint(50, 100)
        offset_y = random.randint(-100, -50)
        human_click(x + offset_x, y + offset_y)