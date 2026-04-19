"""
Pure game state — no rendering.  Ball physics, scoring, NET events,
difficulty modes, sideline OOB, and shot-side enforcement.

Ball stays within the perspective court trapezoid.  If it crosses a
sideline the last hitter is faulted.  Forehand is required when the ball
is right of the player icon; backhand when left.
"""

import random

from game.court import row_xs, TOP_LEFT, BOT_LEFT

COURT_W = 426
COURT_H = 480
BALL_R = 6
WIN_SCORE = 11

BALL_SPEED_INIT = 6.0
BALL_SPEED_INC = 0.3
BALL_SPEED_CAP = 12.0

# AI miss probability (Hard baseline)
AI_MISS_BASE = 0.15
AI_MISS_PER_RALLY = 0.015
AI_MISS_SCORE_MAX = 0.12
AI_SPEED = 5.0

MARGIN_X = 16
MARGIN_TOP = 44
MARGIN_BOT = 16
PADDLE_W = 60
PADDLE_H = 10

NET_FLASH_DURATION = 30
OUT_FLASH_DURATION = 25

# Difficulty multipliers applied to AI miss probability
DIFFICULTY_MULT = {
    "easy":   1.55,
    "medium": 1.25,
    "hard":   1.00,
}
MISS_CAP = {"easy": 0.60, "medium": 0.55, "hard": 0.50}

# Dead-zone (pixels) around player centre where either FH or BH is accepted
_SIDE_DEAD_ZONE = 12


def _court_x_bounds(by: float) -> tuple[float, float]:
    """Playable left/right x at a given ball y, using the trapezoid."""
    cy = max(TOP_LEFT[1], min(BOT_LEFT[1], by))
    lx, rx = row_xs(cy)
    return lx + BALL_R, rx - BALL_R


class GameState:
    def __init__(self, difficulty: str = "hard"):
        self.difficulty = difficulty if difficulty in DIFFICULTY_MULT else "hard"

        self.player_score = 0
        self.ai_score = 0
        self.game_over = False
        self.winner: str | None = None
        self.rally = 0
        self.hit_window = False

        self.ball_speed = BALL_SPEED_INIT
        self.bx = float(COURT_W // 2)
        self.by = float(COURT_H // 2)
        self.bdx = 0.0
        self.bdy = 0.0

        self.player_x = COURT_W / 2 - PADDLE_W / 2
        self.ai_x = COURT_W / 2 - PADDLE_W / 2

        self.net_flash_frames = 0
        self.out_flash_frames = 0
        self.stroke_score = 0
        self.weakest_metric = ""
        self.stroke_phase = "READY"

        self.last_hit_by: str = "ai"  # "player" | "ai"

        # AI arm animation state
        self.ai_swinging = False
        self._ai_swing_frames = 0

        self._serve(toward_player=True)

    # ── helpers ──────────────────────────────────────────────────────────

    @property
    def player_cx(self) -> float:
        return self.player_x + PADDLE_W / 2

    def _expected_shot(self) -> str | None:
        """Which stroke the game requires for the current ball position."""
        diff = self.bx - self.player_cx
        if diff > _SIDE_DEAD_ZONE:
            return "FOREHAND"
        if diff < -_SIDE_DEAD_ZONE:
            return "BACKHAND"
        return None  # dead zone — either is fine

    def _score_point(self, scorer: str):
        if scorer == "ai":
            self.ai_score += 1
            if self.ai_score >= WIN_SCORE:
                self.game_over = True
                self.winner = "AI"
            else:
                self.rally = 0
                self.ball_speed = BALL_SPEED_INIT
                self._serve(toward_player=True)
        else:
            self.player_score += 1
            if self.player_score >= WIN_SCORE:
                self.game_over = True
                self.winner = "Player"
            else:
                self.rally = 0
                self.ball_speed = BALL_SPEED_INIT
                self._serve(toward_player=True)

    def _clamp_bdx(self):
        """Tighten bdx so the ball won't immediately exit the sideline."""
        lx, rx = _court_x_bounds(self.by)
        margin = 8.0
        if self.bdx > 0:
            room = rx - self.bx - margin
            if room < 20 and self.bdx > 1.5:
                self.bdx = min(self.bdx, max(1.0, room * 0.15))
        elif self.bdx < 0:
            room = self.bx - lx - margin
            if room < 20 and self.bdx < -1.5:
                self.bdx = max(self.bdx, min(-1.0, -room * 0.15))

    # ── main update ──────────────────────────────────────────────────────

    def update(self, stroke_state: str, *, net_event: bool = False):
        if self.game_over:
            return

        if self.net_flash_frames > 0:
            self.net_flash_frames -= 1
        if self.out_flash_frames > 0:
            self.out_flash_frames -= 1

        if self.ai_swinging:
            self._ai_swing_frames -= 1
            if self._ai_swing_frames <= 0:
                self.ai_swinging = False

        # Ball motion
        self.bx += self.bdx
        self.by += self.bdy

        # ── Sideline OOB check (no wall bounces) ────────────────────────
        lx, rx = _court_x_bounds(self.by)
        if self.bx < lx or self.bx > rx:
            self.out_flash_frames = OUT_FLASH_DURATION
            fault_on = self.last_hit_by
            self._score_point("player" if fault_on == "ai" else "ai")
            return

        # Hit window (bottom 20%)
        hit_zone_y = COURT_H * 0.80
        self.hit_window = self.bdy > 0 and self.by >= hit_zone_y

        if self.hit_window and stroke_state in ("FOREHAND", "BACKHAND"):
            # Shot-side enforcement
            expected = self._expected_shot()
            if expected is not None and stroke_state != expected:
                pass  # wrong side — don't count the hit; ball continues
            elif net_event:
                self.net_flash_frames = NET_FLASH_DURATION
                self._score_point("ai")
            else:
                self.last_hit_by = "player"
                self.rally += 1
                self.ball_speed = min(
                    BALL_SPEED_INIT + BALL_SPEED_INC * self.rally, BALL_SPEED_CAP
                )
                self.bdy = -self.ball_speed
                if stroke_state == "FOREHAND":
                    self.bdx = random.uniform(1.0, 3.0)
                else:
                    self.bdx = random.uniform(-3.0, -1.0)
                self._clamp_bdx()
                self.by = hit_zone_y - 4
                self.hit_window = False

        # Ball past player baseline → AI scores
        if self.by >= COURT_H + BALL_R:
            self._score_point("ai")

        # ── AI paddle tracking ───────────────────────────────────────────
        ai_cx = self.ai_x + PADDLE_W / 2
        if ai_cx < self.bx - 4:
            self.ai_x = min(self.ai_x + AI_SPEED, COURT_W - MARGIN_X - PADDLE_W)
        elif ai_cx > self.bx + 4:
            self.ai_x = max(self.ai_x - AI_SPEED, MARGIN_X)

        # ── AI return ────────────────────────────────────────────────────
        ai_paddle_y = MARGIN_TOP
        if self.bdy < 0 and self.by <= ai_paddle_y + PADDLE_H + BALL_R:
            if self.ai_x <= self.bx <= self.ai_x + PADDLE_W:
                miss = AI_MISS_BASE + AI_MISS_PER_RALLY * min(self.rally, 10)
                if self.stroke_score > 50:
                    miss += AI_MISS_SCORE_MAX * (self.stroke_score - 50) / 50.0
                mult = DIFFICULTY_MULT.get(self.difficulty, 1.0)
                cap = MISS_CAP.get(self.difficulty, 0.50)
                miss = min(miss * mult, cap)
                if random.random() > miss:
                    self.last_hit_by = "ai"
                    self.bdy = self.ball_speed
                    self.bdx = random.uniform(-2.5, 2.5)
                    self._clamp_bdx()
                    self.by = ai_paddle_y + PADDLE_H + BALL_R + 2
                    self.ai_swinging = True
                    self._ai_swing_frames = 8

        # Ball past AI → player scores
        if self.by <= -BALL_R:
            self._score_point("player")

    def _serve(self, toward_player: bool = True):
        self.bx = float(COURT_W // 2)
        self.by = float(COURT_H // 2)
        self.bdx = random.choice([-1.5, -1.0, 1.0, 1.5])
        self.bdy = self.ball_speed if toward_player else -self.ball_speed
        self.last_hit_by = "ai"
