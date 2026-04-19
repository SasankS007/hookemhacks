"""
HSV color-mask paddle fallback when YOLO weights are unavailable.

Filters by contour area and aspect ratio (height:width must be 1.8–3.5).
Returns the bounding box of the single largest qualifying contour,
or None if nothing passes all filters.

A debug variant is also provided for HSV tuning.
"""

from typing import List, Optional, Tuple

import cv2
import numpy as np

from cv.config import (
    PADDLE_HSV_LOWER,
    PADDLE_HSV_UPPER,
    PADDLE_MIN_CONTOUR_AREA,
    PADDLE_ASPECT_MIN,
    PADDLE_ASPECT_MAX,
)

Box = Tuple[int, int, int, int]


def _hsv_mask(frame_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv,
        np.array(PADDLE_HSV_LOWER, dtype=np.uint8),
        np.array(PADDLE_HSV_UPPER, dtype=np.uint8),
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return mask


def _valid_contour(contour) -> bool:
    area = cv2.contourArea(contour)
    if area < PADDLE_MIN_CONTOUR_AREA:
        return False
    _, _, w, h = cv2.boundingRect(contour)
    if w == 0:
        return False
    ratio = h / w
    return PADDLE_ASPECT_MIN <= ratio <= PADDLE_ASPECT_MAX


def detect_paddle_hsv(frame_bgr: np.ndarray) -> Optional[Box]:
    """
    Returns (x1, y1, x2, y2) of the largest qualifying contour,
    or None if nothing passes area + aspect ratio filters.
    """
    mask = _hsv_mask(frame_bgr)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    valid = [c for c in contours if _valid_contour(c)]
    if not valid:
        return None

    biggest = max(valid, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(biggest)
    return (x, y, x + w, y + h)


def detect_paddle_hsv_debug(
    frame_bgr: np.ndarray,
) -> Tuple[Optional[Box], List, Tuple[int, int, int]]:
    """
    Debug variant: returns (box, all_contours, center_hsv).

    all_contours — every contour found by HSV mask (for blue overlay).
    center_hsv   — HSV value at the frame centre (for terminal printout).
    """
    mask = _hsv_mask(frame_bgr)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    hsv_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    h_px, w_px = frame_bgr.shape[:2]
    center_hsv = tuple(int(v) for v in hsv_frame[h_px // 2, w_px // 2])

    if not contours:
        return None, [], center_hsv

    valid = [c for c in contours if _valid_contour(c)]
    if not valid:
        return None, list(contours), center_hsv

    biggest = max(valid, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(biggest)
    return (x, y, x + w, y + h), list(contours), center_hsv
