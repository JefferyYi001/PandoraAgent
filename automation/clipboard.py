"""
Clipboard operations - safe read/write system clipboard
"""

import pyperclip
import time


class ClipboardHelper:
    """Clipboard helper class"""

    @staticmethod
    def get_text(max_attempts: int = 3, delay: float = 0.1) -> str:
        """Get plain text from clipboard, returns empty string on failure"""
        for attempt in range(max_attempts):
            try:
                text = pyperclip.paste()
                if text and isinstance(text, str):
                    return text.strip()
            except Exception:
                time.sleep(delay)
        return ""

    @staticmethod
    def set_text(text: str, max_attempts: int = 3, delay: float = 0.1) -> bool:
        """Set clipboard text with verification, returns True on success"""
        if not isinstance(text, str):
            text = str(text)
        for attempt in range(max_attempts):
            try:
                pyperclip.copy(text)
                time.sleep(delay)
                verify = pyperclip.paste()
                if verify == text:
                    return True
            except Exception:
                time.sleep(delay)
        return False

    @staticmethod
    def clear() -> bool:
        """Clear clipboard"""
        try:
            pyperclip.copy("")
            return True
        except Exception:
            return False
