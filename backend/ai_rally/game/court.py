"""
Perspective-projected pickleball court renderer.

Trapezoid: wide at bottom (player), narrow at top (AI).
Gradient sky above, darker floor below, net mesh at midpoint.
"""

import pygame
import numpy as np

COURT_W = 426
COURT_H = 480

# Perspective trapezoid corners (px)
_BOT_LEFT = (30, 460)
_BOT_RIGHT = (396, 460)
_TOP_LEFT = (100, 60)
_TOP_RIGHT = (326, 60)

# Colours
C_COURT = (74, 124, 89)        # #4A7C59
C_LINE = (255, 255, 255)
C_SHADOW = (10, 15, 25, 80)
C_SKY_TOP = (25, 30, 50)
C_SKY_BOT = (50, 65, 95)
C_FLOOR = (20, 28, 42)
C_NET_MESH = (60, 60, 60)
C_NET_EDGE = (220, 220, 220)


def _lerp(a, b, t):
    return a + (b - a) * t


def _row_xs(y: float) -> tuple[float, float]:
    """Left and right x of the trapezoid at a given y."""
    if _TOP_LEFT[1] == _BOT_LEFT[1]:
        return float(_BOT_LEFT[0]), float(_BOT_RIGHT[0])
    t = (y - _TOP_LEFT[1]) / (_BOT_LEFT[1] - _TOP_LEFT[1])
    t = max(0.0, min(1.0, t))
    lx = _lerp(_TOP_LEFT[0], _BOT_LEFT[0], t)
    rx = _lerp(_TOP_RIGHT[0], _BOT_RIGHT[0], t)
    return lx, rx


def _court_point(nx: float, ny: float) -> tuple[int, int]:
    """Convert normalised court coords (0–1, 0–1) to pixel position."""
    y = _lerp(_TOP_LEFT[1], _BOT_LEFT[1], ny)
    lx, rx = _row_xs(y)
    x = _lerp(lx, rx, nx)
    return int(x), int(y)


def draw_background(surf: pygame.Surface):
    """Sky gradient top half, dark floor bottom half."""
    for y in range(COURT_H):
        t = y / COURT_H
        if t < 0.12:
            # Sky gradient
            st = t / 0.12
            r = int(_lerp(C_SKY_TOP[0], C_SKY_BOT[0], st))
            g = int(_lerp(C_SKY_TOP[1], C_SKY_BOT[1], st))
            b = int(_lerp(C_SKY_TOP[2], C_SKY_BOT[2], st))
            pygame.draw.line(surf, (r, g, b), (0, y), (COURT_W, y))
        else:
            pygame.draw.line(surf, C_FLOOR, (0, y), (COURT_W, y))


def draw_court_shadow(surf: pygame.Surface):
    """Drop shadow behind the court trapezoid."""
    shadow = pygame.Surface((COURT_W, COURT_H), pygame.SRCALPHA)
    offset = 6
    pts = [
        (_BOT_LEFT[0] + offset, _BOT_LEFT[1] + offset),
        (_BOT_RIGHT[0] + offset, _BOT_RIGHT[1] + offset),
        (_TOP_RIGHT[0] + offset // 2, _TOP_RIGHT[1] + offset // 2),
        (_TOP_LEFT[0] + offset // 2, _TOP_LEFT[1] + offset // 2),
    ]
    pygame.draw.polygon(shadow, C_SHADOW, pts)
    surf.blit(shadow, (0, 0))


def draw_court_surface(surf: pygame.Surface):
    """Green court trapezoid + white lines."""
    pts = [_BOT_LEFT, _BOT_RIGHT, _TOP_RIGHT, _TOP_LEFT]
    pygame.draw.polygon(surf, C_COURT, pts)
    pygame.draw.polygon(surf, C_LINE, pts, 2)

    # Baseline (bottom edge is the trapezoid itself)
    # Kitchen lines at 25% and 75% of court depth
    for ny in (0.25, 0.75):
        p1 = _court_point(0.0, ny)
        p2 = _court_point(1.0, ny)
        pygame.draw.line(surf, C_LINE, p1, p2, 1)

    # Centre line (vertical)
    p1 = _court_point(0.5, 0.0)
    p2 = _court_point(0.5, 1.0)
    pygame.draw.line(surf, C_LINE, p1, p2, 1)

    # Centreline horizontal at 50% (midcourt)
    p1 = _court_point(0.0, 0.5)
    p2 = _court_point(1.0, 0.5)
    pygame.draw.line(surf, C_LINE, p1, p2, 1)


def draw_net(surf: pygame.Surface):
    """Net mesh: horizontal band at ~50% depth with vertical mesh lines."""
    net_ny = 0.50
    net_y = int(_lerp(_TOP_LEFT[1], _BOT_LEFT[1], net_ny))
    lx, rx = _row_xs(net_y)
    net_h = 10

    # Dark mesh fill
    mesh = pygame.Surface((int(rx - lx), net_h), pygame.SRCALPHA)
    mesh.fill((40, 40, 40, 200))
    surf.blit(mesh, (int(lx), net_y - net_h // 2))

    # Vertical mesh lines
    for i in range(0, int(rx - lx), 8):
        x = int(lx) + i
        pygame.draw.line(surf, C_NET_MESH, (x, net_y - net_h // 2), (x, net_y + net_h // 2), 1)

    # White top edge
    pygame.draw.line(surf, C_NET_EDGE, (int(lx), net_y - net_h // 2), (int(rx), net_y - net_h // 2), 2)


def court_point(nx: float, ny: float) -> tuple[int, int]:
    """Public accessor for perspective projection."""
    return _court_point(nx, ny)


def row_xs(y: float) -> tuple[float, float]:
    return _row_xs(y)


# Export corners for sprite positioning
BOT_LEFT = _BOT_LEFT
BOT_RIGHT = _BOT_RIGHT
TOP_LEFT = _TOP_LEFT
TOP_RIGHT = _TOP_RIGHT
