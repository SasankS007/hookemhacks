"""
Compose all game layers: background, court, net, sprites, ball, HUD.
"""
from __future__ import annotations

import math
import pygame
import numpy as np

from game.game_state import (
    GameState, COURT_W, COURT_H, MARGIN_X, MARGIN_TOP, MARGIN_BOT,
    PADDLE_W, PADDLE_H, BALL_R, POINT_PAUSE_FRAMES,
)
from game.court import (
    draw_background, draw_court_shadow, draw_court_surface, draw_net,
    court_point, row_xs, BOT_LEFT, BOT_RIGHT, TOP_LEFT, TOP_RIGHT,
)
from game.ai_opponent import draw_ai_sprite

# Colours
C_LINE = (255, 255, 255)
C_SKIN = (253, 188, 180)   # #FDBCB4
C_SHIRT = (240, 240, 245)
C_SHORTS = (40, 40, 50)
C_PLAYER_ARM = (253, 188, 180)
C_BALL_CENTER = (255, 255, 255)
C_BALL_EDGE = (200, 255, 0)   # #C8FF00
C_SHADOW_BALL = (15, 20, 30, 90)
C_HIT_GLOW = (0, 255, 80)
C_NET_TEXT = (255, 60, 60)

C_PADDLE_FACE = (50, 200, 90)
C_PADDLE_EDGE = (20, 100, 40)
C_SCORE_PAUSE = (80, 220, 255)


def _lerp(a, b, t):
    return a + (b - a) * t


def _ball_perspective_radius(by: float) -> int:
    """Scale ball smaller near the net (middle), larger near edges."""
    # by range: ~60 (top) .. ~460 (bottom)
    mid = (TOP_LEFT[1] + BOT_LEFT[1]) / 2.0
    dist_from_mid = abs(by - mid) / (BOT_LEFT[1] - mid)
    return max(3, int(BALL_R * (0.6 + 0.4 * dist_from_mid)))


class GameRenderer:
    def __init__(self):
        self.surface = pygame.Surface((COURT_W, COURT_H))
        self.font_score = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 12)
        self.font_big = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_net = pygame.font.SysFont("Arial", 36, bold=True)
        # Smoothed on-screen ball (sim position can step; this interpolates for video)
        self._ball_vis: list[float] | None = None
        self._ball_trail: list[tuple[float, float]] = []

    def render(self, gs: GameState) -> np.ndarray:
        s = self.surface

        # 1. Background
        draw_background(s)

        # 2. Court shadow + surface + net
        draw_court_shadow(s)
        draw_court_surface(s)
        draw_net(s)

        # 3. Hit window glow
        if gs.hit_window:
            self._draw_hit_window(s)

        # 4. Ball shadow + smoothed trail + ball
        vx, vy = self._smooth_ball_pos(gs)
        self._draw_ball_trail(s, gs)
        self._draw_ball_shadow(s, gs, vx, vy)

        # 5. AI sprite (top of court)
        ai_cx = int(gs.ai_x + PADDLE_W / 2)
        ai_cy = TOP_LEFT[1] + 30
        draw_ai_sprite(s, ai_cx, ai_cy, swinging=gs.ai_swinging, scale=0.65)
        self._draw_paddle_graphic(s, ai_cx, ai_cy + int(22 * 0.65), "up", gs.ai_swinging)

        # 6. Player sprite (bottom of court)
        player_cx = int(gs.player_x + PADDLE_W / 2)
        player_cy = BOT_LEFT[1] - 30
        self._draw_player_sprite(
            s, player_cx, player_cy, gs.stroke_phase, gs.player_swinging
        )
        self._draw_paddle_graphic(s, player_cx, player_cy + 18, "down", gs.player_swinging)

        # 7. Ball with gradient (uses smoothed vx, vy)
        self._draw_ball(s, gs, vx, vy)

        # 8. HUD
        self._draw_hud(s, gs)

        # 9. NET flash (skip during point pause — overlay handles NET)
        if getattr(gs, "_point_pause_remaining", 0) <= 0:
            if gs.net_flash_frames > 0:
                self._draw_net_flash(s, gs.net_flash_frames)

        # 9b. Point pause: first 1s reason, second 1s score
        if getattr(gs, "_point_pause_remaining", 0) > 0:
            self._draw_point_pause_overlay(s, gs)

        # 10. Game over
        if gs.game_over:
            self._draw_game_over(s, gs)

        arr = pygame.surfarray.array3d(s)
        return arr.transpose(1, 0, 2)

    # ── Player sprite ───────────────────────────────────────────────────

    def _draw_player_sprite(
        self,
        surf: pygame.Surface,
        cx: int,
        cy: int,
        phase: str,
        swinging: bool = False,
    ):
        s = 0.85  # slightly larger than AI (perspective)

        head_r = int(8 * s)
        # Head
        pygame.draw.circle(surf, C_SKIN, (cx, cy - int(26 * s)), head_r)

        # Torso
        torso_w = int(20 * s)
        torso_h = int(22 * s)
        torso_x = cx - torso_w // 2
        torso_y = cy - int(18 * s)
        pygame.draw.rect(surf, C_SHIRT, (torso_x, torso_y, torso_w, torso_h), border_radius=3)

        # Shorts
        shorts_h = int(10 * s)
        pygame.draw.rect(
            surf, C_SHORTS,
            (torso_x + 2, torso_y + torso_h, torso_w - 4, shorts_h),
            border_radius=2,
        )

        # Legs
        leg_w = max(4, int(5 * s))
        leg_h = int(14 * s)
        leg_y = torso_y + torso_h + shorts_h
        pygame.draw.rect(surf, C_SKIN, (cx - int(7 * s), leg_y, leg_w, leg_h), border_radius=2)
        pygame.draw.rect(surf, C_SKIN, (cx + int(2 * s), leg_y, leg_w, leg_h), border_radius=2)

        # Arms
        arm_w = max(3, int(5 * s))
        arm_len = int(18 * s)

        # Left arm (static)
        la_x = torso_x - arm_w - 1
        la_y = torso_y + 3
        pygame.draw.rect(surf, C_PLAYER_ARM, (la_x, la_y, arm_w, arm_len), border_radius=2)

        # Right arm (animated by phase; swing mirrors CONTACT)
        eff_phase = "CONTACT" if swinging else phase
        ra_x = torso_x + torso_w + 1
        ra_y = torso_y + 3
        if eff_phase == "BACKSWING":
            # Arm raised
            ra_y -= int(10 * s)
            pygame.draw.rect(surf, C_PLAYER_ARM, (ra_x, ra_y, arm_w, arm_len + int(4 * s)), border_radius=2)
        elif eff_phase == "CONTACT":
            # Arm extended forward
            ra_y -= int(6 * s)
            ext_len = arm_len + int(8 * s)
            pygame.draw.rect(surf, C_PLAYER_ARM, (ra_x, ra_y, arm_w, ext_len), border_radius=2)
        elif eff_phase == "LOAD":
            ra_y -= int(4 * s)
            pygame.draw.rect(surf, C_PLAYER_ARM, (ra_x, ra_y, arm_w, arm_len + int(2 * s)), border_radius=2)
        else:
            pygame.draw.rect(surf, C_PLAYER_ARM, (ra_x, ra_y, arm_w, arm_len), border_radius=2)


    def _draw_paddle_graphic(
        self,
        surf: pygame.Surface,
        cx: int,
        cy: int,
        facing: str,
        swinging: bool,
    ):
        """Pickleball paddle beside the body; animates on swing."""
        pw, ph = 28, 8
        tilt = -18 if swinging else 0
        if facing == "up":
            tilt = 18 if swinging else 0
        paddle = pygame.Surface((pw + 4, ph + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(paddle, C_PADDLE_EDGE, (2, 2, pw, ph))
        pygame.draw.ellipse(paddle, C_PADDLE_FACE, (4, 3, pw - 4, ph - 4))
        if tilt:
            rotated = pygame.transform.rotate(paddle, tilt)
            surf.blit(rotated, (cx - rotated.get_width() // 2, cy - rotated.get_height() // 2))
        else:
            surf.blit(paddle, (cx - pw // 2, cy - ph // 2))

    def _draw_point_pause_overlay(self, surf: pygame.Surface, gs: GameState):
        rem = gs._point_pause_remaining
        half = POINT_PAUSE_FRAMES // 2
        y = COURT_H // 2 - 20
        if rem > half:
            reason = getattr(gs, "pause_overlay_reason", None)
            if reason == "NET":
                alpha = min(255, int(255 * (rem - half) / half))
                ovl = pygame.Surface((COURT_W, COURT_H), pygame.SRCALPHA)
                txt = self.font_net.render("NET", True, (*C_NET_TEXT, alpha))
                ovl.blit(txt, (COURT_W // 2 - txt.get_width() // 2, y))
                surf.blit(ovl, (0, 0))
        else:
            alpha = min(255, int(255 * rem / half))
            score_str = f"{gs.player_score} \u2014 {gs.ai_score}"
            ovl = pygame.Surface((COURT_W, COURT_H), pygame.SRCALPHA)
            txt = self.font_net.render(score_str, True, (*C_SCORE_PAUSE, alpha))
            ovl.blit(txt, (COURT_W // 2 - txt.get_width() // 2, y))
            surf.blit(ovl, (0, 0))

    # ── Ball ────────────────────────────────────────────────────────────

    def _smooth_ball_pos(self, gs: GameState) -> tuple[float, float]:
        """Interpolate toward sim ball; snap on large jumps (serve / point reset)."""
        if self._ball_vis is None:
            self._ball_vis = [float(gs.bx), float(gs.by)]
            self._ball_trail = []
        else:
            dx = gs.bx - self._ball_vis[0]
            dy = gs.by - self._ball_vis[1]
            if dx * dx + dy * dy > 160 * 160:
                self._ball_vis[0] = float(gs.bx)
                self._ball_vis[1] = float(gs.by)
                self._ball_trail = []
            else:
                tau = 0.36
                self._ball_vis[0] += dx * tau
                self._ball_vis[1] += dy * tau
        self._ball_trail.append((self._ball_vis[0], self._ball_vis[1]))
        if len(self._ball_trail) > 16:
            self._ball_trail.pop(0)
        return self._ball_vis[0], self._ball_vis[1]

    def _draw_ball_trail(self, surf: pygame.Surface, gs: GameState):
        if len(self._ball_trail) < 2:
            return
        n = len(self._ball_trail)
        for i, (tx, ty) in enumerate(self._ball_trail[:-1]):
            age = (i + 1) / max(n, 1)
            alpha = int(35 + 55 * age)
            rr = max(2, int(_ball_perspective_radius(ty) * 0.35))
            spot = pygame.Surface((rr * 2 + 2, rr * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(spot, (220, 255, 120, alpha), (rr + 1, rr + 1), rr)
            surf.blit(spot, (int(tx) - rr - 1, int(ty) - rr - 1))

    def _draw_ball_shadow(self, surf: pygame.Surface, gs: GameState, vx: float, vy: float):
        """Shadow on court surface below ball, scaled by y position."""
        r = _ball_perspective_radius(gs.by)
        shadow_r = max(2, int(r * 0.8))
        # Shadow offset scales with distance from bottom
        t = (gs.by - TOP_LEFT[1]) / (BOT_LEFT[1] - TOP_LEFT[1])
        t = max(0.0, min(1.0, t))
        shadow_y = int(vy + 4 + (1 - t) * 6)

        shadow_surf = pygame.Surface((shadow_r * 2, shadow_r * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, C_SHADOW_BALL, (0, 0, shadow_r * 2, shadow_r))
        surf.blit(shadow_surf, (int(vx) - shadow_r, shadow_y - shadow_r // 2))

    def _draw_ball(self, surf: pygame.Surface, gs: GameState, vx: float, vy: float):
        r = _ball_perspective_radius(gs.by)
        bx, by = int(vx), int(vy)

        # Radial gradient: white centre → yellow-green edge
        ball_surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        for i in range(r, 0, -1):
            t = i / r
            cr = int(_lerp(C_BALL_CENTER[0], C_BALL_EDGE[0], t))
            cg = int(_lerp(C_BALL_CENTER[1], C_BALL_EDGE[1], t))
            cb = int(_lerp(C_BALL_CENTER[2], C_BALL_EDGE[2], t))
            pygame.draw.circle(ball_surf, (cr, cg, cb), (r + 1, r + 1), i)

        surf.blit(ball_surf, (bx - r - 1, by - r - 1))

    # ── Hit window ──────────────────────────────────────────────────────

    def _draw_hit_window(self, surf: pygame.Surface):
        # Pulsing green bar at bottom of court (aligned with game_state hit_zone_y = 0.72)
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 0.5 + 0.5
        alpha = int(40 * pulse)
        bar_y = int(COURT_H * 0.72)
        bar_h = COURT_H - bar_y
        hw = pygame.Surface((COURT_W, bar_h), pygame.SRCALPHA)
        hw.fill((0, 255, 80, alpha))
        surf.blit(hw, (0, bar_y))

        # Glowing text
        txt = self.font_small.render("SWING NOW", True, C_HIT_GLOW)
        surf.blit(txt, (COURT_W // 2 - txt.get_width() // 2, bar_y + bar_h // 2 - 6))

    # ── NET flash ───────────────────────────────────────────────────────

    def _draw_net_flash(self, surf: pygame.Surface, frames_left: int):
        alpha = min(255, int(255 * (frames_left / 15.0)))
        net_surf = pygame.Surface((COURT_W, COURT_H), pygame.SRCALPHA)
        txt = self.font_net.render("NET", True, (*C_NET_TEXT, alpha))
        net_surf.blit(txt, (COURT_W // 2 - txt.get_width() // 2, COURT_H // 2 - 20))
        surf.blit(net_surf, (0, 0))

    # ── OUT flash ──────────────────────────────────────────────────────

    def _draw_out_flash(self, surf: pygame.Surface, frames_left: int):
        alpha = min(255, int(255 * (frames_left / 12.0)))
        out_surf = pygame.Surface((COURT_W, COURT_H), pygame.SRCALPHA)
        txt = self.font_net.render("OUT", True, (255, 180, 40, alpha))
        out_surf.blit(txt, (COURT_W // 2 - txt.get_width() // 2, COURT_H // 2 - 20))
        surf.blit(out_surf, (0, 0))

    # ── HUD ─────────────────────────────────────────────────────────────

    def _draw_hud(self, surf: pygame.Surface, gs: GameState):
        # Score top centre
        score_txt = self.font_score.render(
            f"PLAYER {gs.player_score}  \u2014  AI {gs.ai_score}",
            True, C_LINE,
        )
        surf.blit(score_txt, (COURT_W // 2 - score_txt.get_width() // 2, 8))

        # Rally + difficulty
        diff_label = gs.difficulty.upper() if hasattr(gs, "difficulty") else "HARD"
        rally_txt = self.font_small.render(
            f"Rally {gs.rally}   [{diff_label}]", True, (140, 140, 140)
        )
        surf.blit(rally_txt, (COURT_W // 2 - rally_txt.get_width() // 2, 28))

    # ── Game over ───────────────────────────────────────────────────────

    def _draw_game_over(self, surf: pygame.Surface, gs: GameState):
        overlay = pygame.Surface((COURT_W, COURT_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))
        w_text = self.font_big.render(f"{gs.winner} Wins!", True, (255, 220, 50))
        surf.blit(w_text, (COURT_W // 2 - w_text.get_width() // 2, COURT_H // 2 - 24))
        sub = self.font_small.render(
            f"{gs.player_score} \u2014 {gs.ai_score}", True, (200, 200, 200)
        )
        surf.blit(sub, (COURT_W // 2 - sub.get_width() // 2, COURT_H // 2 + 14))
