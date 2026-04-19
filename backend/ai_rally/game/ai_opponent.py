"""
Robot AI opponent sprite — square metallic head, rectangular chassis,
cylindrical arms, cyan visor, glow aura, arm swing animation.
"""

import pygame
import math

C_BODY = (168, 169, 173)         # #A8A9AD silver
C_VISOR = (0, 255, 255)          # #00FFFF cyan
C_DARK = (90, 90, 95)
C_GLOW = (0, 255, 255, 30)


def draw_ai_sprite(
    surf: pygame.Surface,
    cx: int,
    cy: int,
    swinging: bool = False,
    scale: float = 0.7,
):
    """Draw the robot AI at (cx, cy) with optional swing animation."""
    s = scale

    # Glow aura (blurred circle)
    glow = pygame.Surface((int(60 * s), int(60 * s)), pygame.SRCALPHA)
    for r in range(int(30 * s), 0, -2):
        alpha = max(5, 30 - r)
        pygame.draw.circle(glow, (0, 255, 255, alpha), (int(30 * s), int(30 * s)), r)
    surf.blit(glow, (cx - int(30 * s), cy - int(30 * s)))

    head_w = int(18 * s)
    head_h = int(16 * s)
    head_x = cx - head_w // 2
    head_y = cy - int(28 * s)

    # Head (square metallic)
    pygame.draw.rect(surf, C_BODY, (head_x, head_y, head_w, head_h), border_radius=2)
    pygame.draw.rect(surf, C_DARK, (head_x, head_y, head_w, head_h), 1, border_radius=2)

    # Visor strip
    visor_h = max(3, int(4 * s))
    visor_y = head_y + head_h // 2 - visor_h // 2
    pygame.draw.rect(surf, C_VISOR, (head_x + 2, visor_y, head_w - 4, visor_h))

    # Torso (chassis)
    torso_w = int(22 * s)
    torso_h = int(20 * s)
    torso_x = cx - torso_w // 2
    torso_y = head_y + head_h + 1
    pygame.draw.rect(surf, C_BODY, (torso_x, torso_y, torso_w, torso_h), border_radius=2)
    pygame.draw.rect(surf, C_DARK, (torso_x, torso_y, torso_w, torso_h), 1, border_radius=2)

    # Arms
    arm_w = max(4, int(6 * s))
    arm_h = int(18 * s)

    # Left arm
    la_x = torso_x - arm_w - 1
    la_y = torso_y + 2
    pygame.draw.rect(surf, C_BODY, (la_x, la_y, arm_w, arm_h), border_radius=2)

    # Right arm (swinging animation)
    ra_x = torso_x + torso_w + 1
    ra_y = torso_y + 2
    if swinging:
        # Arm raised forward during swing
        ra_y -= int(8 * s)
        arm_h_adj = arm_h + int(4 * s)
        pygame.draw.rect(surf, C_VISOR, (ra_x, ra_y, arm_w, arm_h_adj), border_radius=2)
    else:
        pygame.draw.rect(surf, C_BODY, (ra_x, ra_y, arm_w, arm_h), border_radius=2)

    # Legs (short cylinders)
    leg_w = max(4, int(6 * s))
    leg_h = int(12 * s)
    leg_y = torso_y + torso_h + 1
    # Left leg
    pygame.draw.rect(surf, C_DARK, (cx - int(8 * s), leg_y, leg_w, leg_h), border_radius=2)
    # Right leg
    pygame.draw.rect(surf, C_DARK, (cx + int(2 * s), leg_y, leg_w, leg_h), border_radius=2)
