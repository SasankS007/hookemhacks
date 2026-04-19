"""
Sweet spot crosshair renderer — draws only when an explicit bounding box
is supplied.  No box = nothing rendered.
"""

from typing import Optional, Tuple

import cv2
import numpy as np

Box = Tuple[int, int, int, int]

_CROSS_HALF = 10  # half-length of each crosshair arm (20px total)
_DOT_RADIUS = 6
_LABEL = "SWEET SPOT"


def draw_sweet_spot(
    frame: np.ndarray,
    box: Optional[Box],
) -> None:
    """
    Draw a crosshair + label at the sweet spot of `box`.

    Position: 55 % down from top, centred horizontally.
    If `box` is None the function returns immediately.
    """
    if box is None:
        return

    x1, y1, x2, y2 = box
    cx = (x1 + x2) // 2
    cy = y1 + int((y2 - y1) * 0.55)

    # Crosshair lines (white, 2px)
    cv2.line(frame, (cx - _CROSS_HALF, cy), (cx + _CROSS_HALF, cy), (255, 255, 255), 2)
    cv2.line(frame, (cx, cy - _CROSS_HALF), (cx, cy + _CROSS_HALF), (255, 255, 255), 2)

    # Filled yellow dot at centre
    cv2.circle(frame, (cx, cy), _DOT_RADIUS, (0, 255, 255), -1)

    # Label above
    cv2.putText(
        frame,
        _LABEL,
        (cx - 32, cy - _CROSS_HALF - 6),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.32,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
