"""
Windows window management using win32gui API
"""

import ctypes
from utils.logger import logger

try:
    import win32gui
    import win32con
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False
    logger.warning("win32gui not available, window operations will be limited")


def get_screen_size() -> tuple:
    """Get screen resolution (width, height)"""
    return (ctypes.windll.user32.GetSystemMetrics(0),
            ctypes.windll.user32.GetSystemMetrics(1))


def find_window(class_name: str = None, window_name: str = None) -> int | None:
    """Find window handle by class name or title"""
    if not _HAS_WIN32:
        return None
    try:
        hwnd = win32gui.FindWindow(class_name, window_name)
        return hwnd if hwnd else None
    except Exception as e:
        logger.error(f"find_window error: {e}")
        return None


def is_window_visible(hwnd: int) -> bool:
    """Check if window is visible"""
    if not _HAS_WIN32:
        return False
    try:
        return bool(win32gui.IsWindowVisible(hwnd))
    except Exception:
        return False


def is_window_minimized(hwnd: int) -> bool:
    """Check if window is minimized"""
    if not _HAS_WIN32:
        return False
    try:
        return bool(win32gui.IsIconic(hwnd))
    except Exception:
        return False


def restore_window(hwnd: int) -> bool:
    """Restore a minimized window"""
    if not _HAS_WIN32:
        return False
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        logger.error(f"restore_window error: {e}")
        return False


def minimize_window(hwnd: int) -> bool:
    """Minimize a window"""
    if not _HAS_WIN32:
        return False
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return True
    except Exception as e:
        logger.error(f"minimize_window error: {e}")
        return False


def get_window_dpi() -> int:
    """Get current system DPI"""
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi
    except Exception:
        return 96
