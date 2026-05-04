"""
Image recognition utilities - template matching using OpenCV
"""

import cv2
import numpy as np
import pyautogui
import os

from utils.logger import logger


class VisionUtils:
    """Image recognition utility class"""

    @staticmethod
    def find_template(screen_region: tuple, template_path: str, threshold: float = 0.8) -> tuple | None:
        """Find a template image in a screen region"""
        try:
            if not os.path.exists(template_path):
                logger.warning(f"Template not found: {template_path}")
                return None

            screenshot = VisionUtils.capture_region(screen_region)
            if screenshot is None:
                return None

            template = cv2.imread(template_path)
            if template is None:
                logger.warning(f"Cannot load template: {template_path}")
                return None

            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            logger.debug(f"Template '{os.path.basename(template_path)}' score: {max_val:.3f} (threshold: {threshold})")

            if max_val < threshold:
                return None

            template_height, template_width = template.shape[:2]
            center_x = max_loc[0] + template_width // 2 + screen_region[0]
            center_y = max_loc[1] + template_height // 2 + screen_region[1]
            return (center_x, center_y)
        except Exception as e:
            logger.error(f"find_template error: {e}")
            return None

    @staticmethod
    def find_all_matches(screen_region: tuple, template_path: str, threshold: float = 0.75) -> list:
        """Find all matching positions for multi-target scenarios"""
        try:
            if not os.path.exists(template_path):
                return []
            screenshot = VisionUtils.capture_region(screen_region)
            if screenshot is None:
                return []
            template = cv2.imread(template_path)
            if template is None:
                return []

            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            template_height, template_width = template.shape[:2]
            locations = np.where(result >= threshold)
            matches = []
            for pt in zip(*locations[::-1]):
                center_x = pt[0] + template_width // 2 + screen_region[0]
                center_y = pt[1] + template_height // 2 + screen_region[1]
                matches.append((center_x, center_y))
            return VisionUtils._filter_overlapping_matches(matches, min(template_width, template_height) // 2)
        except Exception as e:
            logger.error(f"find_all_matches error: {e}")
            return []

    @staticmethod
    def _filter_overlapping_matches(matches: list, min_distance: int) -> list:
        """Filter overlapping match points"""
        if not matches:
            return []
        filtered = []
        for match in matches:
            is_duplicate = False
            for existing in filtered:
                distance = np.sqrt((match[0] - existing[0])**2 + (match[1] - existing[1])**2)
                if distance < min_distance:
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered.append(match)
        return filtered

    @staticmethod
    def capture_region(screen_region: tuple) -> np.ndarray | None:
        """Capture a screen region and convert to OpenCV BGR format"""
        try:
            pil_image = pyautogui.screenshot(region=screen_region)
            rgb_array = np.array(pil_image)
            return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"capture_region error: {e}")
            return None

    @staticmethod
    def capture_full_screen() -> np.ndarray | None:
        """Capture full screen"""
        try:
            pil_image = pyautogui.screenshot()
            rgb_array = np.array(pil_image)
            return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"capture_full_screen error: {e}")
            return None

    @staticmethod
    def analyze_red_dot_template(template_path: str) -> dict:
        """Analyze red dot template to extract HSV color ranges and shape params"""
        try:
            template = cv2.imread(template_path)
            if template is None:
                return None
            hsv = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)
            h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
            red_mask = (s > 50) & (v > 50)
            red_h, red_s, red_v = h[red_mask], s[red_mask], v[red_mask]
            if len(red_h) == 0:
                return None
            h_min, h_max = int(np.percentile(red_h, 5)), int(np.percentile(red_h, 95))
            s_min, v_min = int(np.percentile(red_s, 5)), int(np.percentile(red_v, 5))
            if h_max > 150:
                color_mask = cv2.inRange(hsv, (h_min, s_min, v_min), (180, 255, 255))
            elif h_min < 15:
                color_mask = cv2.inRange(hsv, (0, s_min, v_min), (h_max, 255, 255))
                color_mask2 = cv2.inRange(hsv, (170, s_min, v_min), (180, 255, 255))
                color_mask = cv2.bitwise_or(color_mask, color_mask2)
            else:
                color_mask = cv2.inRange(hsv, (h_min, s_min, v_min), (h_max, 255, 255))
            contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                max_contour = max(contours, key=cv2.contourArea)
                actual_area = cv2.contourArea(max_contour)
                x, y, w, h_rect = cv2.boundingRect(max_contour)
                aspect_ratio = w / h_rect if h_rect > 0 else 1.0
                min_area, max_area = actual_area * 0.5, actual_area * 2.0
            else:
                height, width = template.shape[:2]
                aspect_ratio = width / height
                min_area, max_area = width * height * 0.3, width * height * 1.5
            height, width = template.shape[:2]
            return {'h_min': h_min, 'h_max': h_max, 's_min': s_min, 'v_min': v_min,
                    'min_area': min_area, 'max_area': max_area,
                    'aspect_ratio': aspect_ratio, 'template_size': (width, height)}
        except Exception as e:
            logger.error(f"analyze_red_dot_template error: {e}")
            return None

    @staticmethod
    def find_red_dots(screen_region: tuple, template_configs: list) -> list:
        """Find red dots using color + shape detection"""
        try:
            screenshot = VisionUtils.capture_region(screen_region)
            if screenshot is None:
                return []
            hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
            red_dots = []
            for config in template_configs:
                h_min, h_max = config['h_min'], config['h_max']
                s_min, v_min = config['s_min'], config['v_min']
                min_area, max_area = config['min_area'], config['max_area']
                aspect_ratio = config['aspect_ratio']
                if h_max > 150:
                    red_mask = cv2.inRange(hsv, (h_min, s_min, v_min), (180, 255, 255))
                elif h_min < 15:
                    red_mask = cv2.inRange(hsv, (0, s_min, v_min), (h_max, 255, 255))
                    red_mask2 = cv2.inRange(hsv, (170, s_min, v_min), (180, 255, 255))
                    red_mask = cv2.bitwise_or(red_mask, red_mask2)
                else:
                    red_mask = cv2.inRange(hsv, (h_min, s_min, v_min), (h_max, 255, 255))
                contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area < min_area or area > max_area:
                        continue
                    x, y, w, h = cv2.boundingRect(contour)
                    current_aspect = w / h if h > 0 else 0
                    aspect_tolerance = 0.35
                    if abs(current_aspect - aspect_ratio) > aspect_tolerance:
                        if aspect_ratio < 1.5 and abs(current_aspect - 1.0) > aspect_tolerance:
                            continue
                    roi = screenshot[y:y+h, x:x+w]
                    if VisionUtils._has_white_number(roi):
                        red_dots.append((x + w // 2 + screen_region[0], y + h // 2 + screen_region[1]))
            return red_dots
        except Exception as e:
            logger.error(f"find_red_dots error: {e}")
            return []

    @staticmethod
    def _has_white_number(roi: np.ndarray, white_threshold: float = 0.02) -> bool:
        """Detect if ROI contains white number characters"""
        try:
            if roi is None or roi.size == 0:
                return False
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            white_mask = cv2.inRange(gray, 180, 255)
            white_ratio = cv2.countNonZero(white_mask) / gray.size
            dynamic_threshold = 0.015 if gray.size < 600 else white_threshold
            return white_ratio >= dynamic_threshold
        except Exception:
            return False
