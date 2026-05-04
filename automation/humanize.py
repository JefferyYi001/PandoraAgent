"""
Anti-detection module - humanized delay and click behavior
All actions must go through this module to avoid detection as automation
"""

import random
import time
import pyautogui


def _get_humanize_params() -> dict:
    """Lazy-load humanize params from defaults to avoid circular imports"""
    from config.defaults import get_defaults
    return get_defaults()


# =============================================================================
# Delay
# =============================================================================

def human_sleep(min_sec: float, max_sec: float) -> None:
    """Gaussian random delay, simulating human operation interval"""
    if min_sec >= max_sec:
        time.sleep(min_sec)
        return
    mean = (min_sec + max_sec) / 2
    std = (max_sec - min_sec) / 4
    delay = random.gauss(mean, std)
    delay = max(min_sec, min(max_sec, delay))
    time.sleep(delay)


# =============================================================================
# Bezier Curve
# =============================================================================

def _generate_bezier_points(start: tuple, end: tuple, num_points: int = 20) -> list:
    """Generate Bezier curve trajectory points"""
    params = _get_humanize_params()
    offset_range = params.get("humanize", {}).get("bezier", {}).get("control_offset_range", 30)

    mid_x = (start[0] + end[0]) / 2 + random.randint(-offset_range, offset_range)
    mid_y = (start[1] + end[1]) / 2 + random.randint(-offset_range, offset_range)

    control1 = (start[0] + random.randint(-offset_range, offset_range),
                start[1] + random.randint(-offset_range, offset_range))
    control2 = (mid_x, mid_y)
    control3 = (end[0] + random.randint(-offset_range, offset_range),
                end[1] + random.randint(-offset_range, offset_range))

    points = []
    for i in range(num_points + 1):
        t = i / num_points
        x = (1-t)**3 * start[0] + 3*(1-t)**2*t * control1[0] + 3*(1-t)*t**2 * control2[0] + t**3 * control3[0]
        y = (1-t)**3 * start[1] + 3*(1-t)**2*t * control1[1] + 3*(1-t)*t**2 * control2[1] + t**3 * control3[1]
        points.append((int(x), int(y)))
    return points


# =============================================================================
# Click
# =============================================================================

def _get_click_offset_range(fallback: int) -> int:
    """Get click offset range from config with fallback"""
    return _get_humanize_params().get("humanize", {}).get("click", {}).get("offset_range", fallback)


def _get_delay(key: str, fallback: list) -> list:
    """Get delay range from config with fallback"""
    return _get_humanize_params().get("humanize", {}).get("delays", {}).get(key, fallback)


def human_click(target_x: int, target_y: int, offset_range: int = None) -> None:
    """Humanized click with random offset and Bezier curve trajectory"""
    if offset_range is None:
        offset_range = _get_click_offset_range(5)

    actual_x = target_x + random.randint(-offset_range, offset_range)
    actual_y = target_y + random.randint(-offset_range, offset_range)
    current_pos = pyautogui.position()
    trajectory = _generate_bezier_points(current_pos, (actual_x, actual_y))

    bezier_delays = _get_delay("before_click", [0.003, 0.008])
    for i, (px, py) in enumerate(trajectory):
        if i == len(trajectory) - 1:
            break
        px += random.randint(-1, 1)
        py += random.randint(-1, 1)
        pyautogui.moveTo(px, py)
        human_sleep(*bezier_delays)

    duration = random.uniform(0.05, 0.15)
    pyautogui.moveTo(actual_x, actual_y, duration=duration)
    human_sleep(*_get_delay("before_click", [0.03, 0.08]))
    pyautogui.click()


def human_right_click(target_x: int, target_y: int, offset_range: int = None) -> None:
    """Humanized right-click with random offset"""
    if offset_range is None:
        offset_range = _get_click_offset_range(3)

    actual_x = target_x + random.randint(-offset_range, offset_range)
    actual_y = target_y + random.randint(-offset_range, offset_range)
    current_pos = pyautogui.position()
    trajectory = _generate_bezier_points(current_pos, (actual_x, actual_y))

    bezier_delays = _get_delay("before_click", [0.003, 0.008])
    for i, (px, py) in enumerate(trajectory):
        if i == len(trajectory) - 1:
            break
        px += random.randint(-1, 1)
        py += random.randint(-1, 1)
        pyautogui.moveTo(px, py)
        human_sleep(*bezier_delays)

    duration = random.uniform(0.05, 0.12)
    pyautogui.moveTo(actual_x, actual_y, duration=duration)
    human_sleep(*_get_delay("before_click", [0.03, 0.08]))
    pyautogui.rightClick()


# =============================================================================
# Keyboard
# =============================================================================

def human_type_text(text: str) -> None:
    """
    Humanized keyboard input (ASCII only).
    Note: Chinese requires clipboard method instead.
    """
    char_delays = _get_delay("between_chars", [0.05, 0.15])
    for char in text:
        pyautogui.press(char)
        human_sleep(*char_delays)


def human_press_key(key: str) -> None:
    """Humanized key press"""
    human_sleep(*_get_delay("before_press_key", [0.05, 0.12]))
    pyautogui.press(key)


def human_hotkey(*keys: str) -> None:
    """Humanized hotkey combination"""
    human_sleep(*_get_delay("before_hotkey", [0.05, 0.15]))
    pyautogui.hotkey(*keys)


# =============================================================================
# Scroll
# =============================================================================

def human_scroll(clicks: int) -> None:
    """Humanized scroll wheel operation"""
    human_sleep(*_get_delay("before_scroll", [0.05, 0.15]))
    variance = _get_humanize_params().get("humanize", {}).get("scroll", {}).get("random_variance", 1)
    actual_clicks = clicks + random.randint(-variance, variance)
    pyautogui.scroll(actual_clicks)
