"""
Off-screen Pygame 2D pickleball court and game logic.

Renders to a pygame.Surface and exposes the result as a NumPy array
so the WebSocket server can encode it alongside the webcam frame.
"""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import numpy as np  # noqa: E402

pygame.init()

COURT_W = 426
COURT_H = 480
PADDLE_W = 60
PADDLE_H = 10
BALL_R = 6
WIN_SCORE = 11

# Single difficulty — no selection
BALL_SPEED_INIT = 6.0
BALL_SPEED_INC = 0.3
BALL_SPEED_CAP = 12.0
AI_MISS_RATE = 0.05
AI_SPEED = 5.0

# Colours
C_BG = (15, 23, 42)
C_COURT = (30, 70, 30)
C_LINE = (255, 255, 255)
C_BALL = (255, 220, 50)
C_PLAYER = (50, 150, 255)
C_AI = (255, 80, 80)
C_HIT_WINDOW = (255, 255, 0)

# Court margins
MARGIN_X = 16
MARGIN_TOP = 44
MARGIN_BOT = 16


class GameEngine:
    def __init__(self):
        self.surface = pygame.Surface((COURT_W, COURT_H))
        self.font_score = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 13)
        self.font_big = pygame.font.SysFont("Arial", 26, bold=True)
        self.reset()

    # ── public API ──────────────────────────────────────────────────────

    def reset(self):
        self.player_score = 0
        self.ai_score = 0
        self.game_over = False
        self.winner: str | None = None
        self.rally = 0
        self._ball_speed = BALL_SPEED_INIT
        self._player_x = COURT_W / 2 - PADDLE_W / 2
        self._ai_x = COURT_W / 2 - PADDLE_W / 2
        self._serve(toward_player=True)
        self.hit_window = False

    def update(self, stroke_state: str):
        if self.game_over:
            return

        # ── ball motion ─────────────────────────────────────────────────
        self._bx += self._bdx
        self._by += self._bdy

        # wall bounces
        if self._bx - BALL_R <= MARGIN_X:
            self._bdx = abs(self._bdx)
            self._bx = MARGIN_X + BALL_R
        elif self._bx + BALL_R >= COURT_W - MARGIN_X:
            self._bdx = -abs(self._bdx)
            self._bx = COURT_W - MARGIN_X - BALL_R

        # ── hit window (bottom 20 %) ────────────────────────────────────
        hit_zone_y = COURT_H * 0.80
        self.hit_window = self._bdy > 0 and self._by >= hit_zone_y

        if self.hit_window and stroke_state in ("FOREHAND", "BACKHAND"):
            self.rally += 1
            self._ball_speed = min(BALL_SPEED_INIT + BALL_SPEED_INC * self.rally, BALL_SPEED_CAP)
            self._bdy = -self._ball_speed
            if stroke_state == "FOREHAND":
                self._bdx = random.uniform(2.0, 4.0)
            else:
                self._bdx = random.uniform(-4.0, -2.0)
            self._by = hit_zone_y - 4
            self.hit_window = False

        # ── ball past player → point to AI ──────────────────────────────
        if self._by >= COURT_H + BALL_R:
            self.ai_score += 1
            if self.ai_score >= WIN_SCORE:
                self.game_over = True
                self.winner = "AI"
            else:
                self.rally = 0
                self._ball_speed = BALL_SPEED_INIT
                self._serve(toward_player=True)

        # ── AI paddle tracking ──────────────────────────────────────────
        ai_cx = self._ai_x + PADDLE_W / 2
        if ai_cx < self._bx - 4:
            self._ai_x = min(self._ai_x + AI_SPEED, COURT_W - MARGIN_X - PADDLE_W)
        elif ai_cx > self._bx + 4:
            self._ai_x = max(self._ai_x - AI_SPEED, MARGIN_X)

        # ── AI return ───────────────────────────────────────────────────
        ai_paddle_y = MARGIN_TOP
        if self._bdy < 0 and self._by <= ai_paddle_y + PADDLE_H + BALL_R:
            if self._ai_x <= self._bx <= self._ai_x + PADDLE_W:
                if random.random() > AI_MISS_RATE:
                    self._bdy = self._ball_speed
                    self._bdx = random.uniform(-4.0, 4.0)
                    self._by = ai_paddle_y + PADDLE_H + BALL_R + 2

        # ── ball past AI → point to player ──────────────────────────────
        if self._by <= -BALL_R:
            self.player_score += 1
            if self.player_score >= WIN_SCORE:
                self.game_over = True
                self.winner = "Player"
            else:
                self.rally = 0
                self._ball_speed = BALL_SPEED_INIT
                self._serve(toward_player=True)

    def render(self) -> np.ndarray:
        """Draw current state and return an RGB numpy array (H×W×3)."""
        s = self.surface
        s.fill(C_BG)

        # Court rectangle
        court = pygame.Rect(MARGIN_X, MARGIN_TOP, COURT_W - 2 * MARGIN_X, COURT_H - MARGIN_TOP - MARGIN_BOT)
        pygame.draw.rect(s, C_COURT, court)
        pygame.draw.rect(s, C_LINE, court, 2)

        # Centre line
        cy = court.centery
        pygame.draw.line(s, C_LINE, (MARGIN_X, cy), (COURT_W - MARGIN_X, cy), 1)

        # NVZ lines
        nvz_off = int(court.height * 0.25)
        for y in (court.top + nvz_off, court.bottom - nvz_off):
            pygame.draw.line(s, (180, 180, 180), (MARGIN_X, y), (COURT_W - MARGIN_X, y), 1)

        # Centreline (vertical)
        pygame.draw.line(s, (180, 180, 180), (COURT_W // 2, court.top), (COURT_W // 2, court.bottom), 1)

        # Hit window indicator
        if self.hit_window:
            hw_rect = pygame.Surface((court.width, int(COURT_H * 0.20)), pygame.SRCALPHA)
            hw_rect.fill((255, 255, 0, 35))
            s.blit(hw_rect, (MARGIN_X, int(COURT_H * 0.80)))
            txt = self.font_small.render("SWING NOW", True, C_HIT_WINDOW)
            s.blit(txt, (COURT_W // 2 - txt.get_width() // 2, int(COURT_H * 0.88)))

        # AI paddle
        pygame.draw.rect(s, C_AI, (int(self._ai_x), MARGIN_TOP, PADDLE_W, PADDLE_H), border_radius=4)

        # Player paddle
        player_y = COURT_H - MARGIN_BOT - PADDLE_H - 6
        pygame.draw.rect(s, C_PLAYER, (int(self._player_x), player_y, PADDLE_W, PADDLE_H), border_radius=4)

        # Ball
        pygame.draw.circle(s, C_BALL, (int(self._bx), int(self._by)), BALL_R)

        # Score
        score = self.font_score.render(f"Player {self.player_score}  —  AI {self.ai_score}", True, C_LINE)
        s.blit(score, (COURT_W // 2 - score.get_width() // 2, 10))

        # Rally counter
        rally_txt = self.font_small.render(f"Rally {self.rally}", True, (140, 140, 140))
        s.blit(rally_txt, (COURT_W // 2 - rally_txt.get_width() // 2, 30))

        # Game over overlay
        if self.game_over:
            overlay = pygame.Surface((COURT_W, COURT_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            s.blit(overlay, (0, 0))
            w_text = self.font_big.render(f"{self.winner} Wins!", True, C_BALL)
            s.blit(w_text, (COURT_W // 2 - w_text.get_width() // 2, COURT_H // 2 - 24))
            sub = self.font_small.render(
                f"{self.player_score} — {self.ai_score}", True, (200, 200, 200)
            )
            s.blit(sub, (COURT_W // 2 - sub.get_width() // 2, COURT_H // 2 + 12))

        # Surface → numpy (Pygame gives W×H×3 in RGB order via surfarray)
        arr = pygame.surfarray.array3d(s)  # shape (W, H, 3)
        return arr.transpose(1, 0, 2)  # → (H, W, 3) for OpenCV

    # ── internals ───────────────────────────────────────────────────────

    def _serve(self, toward_player: bool = True):
        self._bx = float(COURT_W // 2)
        self._by = float(COURT_H // 2)
        self._bdx = random.choice([-2.5, -1.5, 1.5, 2.5])
        self._bdy = self._ball_speed if toward_player else -self._ball_speed
