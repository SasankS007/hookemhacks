"""
CV pipeline configuration — tuneable constants in one place.
"""

# HSV range for the fallback paddle color detector.
# Default targets mid-green paddles.
PADDLE_HSV_LOWER = (35, 50, 50)
PADDLE_HSV_UPPER = (85, 255, 255)

# Minimum contour area (pixels) to accept as a paddle hit
PADDLE_MIN_CONTOUR_AREA = 800

# Valid paddle bounding-box aspect ratio (height / width)
PADDLE_ASPECT_MIN = 1.8
PADDLE_ASPECT_MAX = 3.5
