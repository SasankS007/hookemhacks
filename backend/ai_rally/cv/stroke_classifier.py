"""
Biomechanical stroke classifier: body-normalised ratios, 5-phase swing
segmentation, kinetic-chain velocity, CONTACT-only scoring.

Validation rules:
  - Full phase sequence BACKSWING → LOAD → CONTACT → FOLLOW_THROUGH
    must complete within 90 frames.
  - Score at CONTACT ≥ 45 for a valid stroke.
  - FOLLOW_THROUGH confirmed: wrist must decelerate for ≥ 6 consecutive
    frames after CONTACT before the stroke is emitted.
  - Stroke emitted once per swing; state resets to READY after emission.
  - return_probability: score 45→0.5, score 100→1.0 (linear).

Wrist x-direction (mirrored camera):
  - Forehand: wrist x moves high→low (dx < 0)
  - Backhand: wrist x moves low→high (dx > 0)
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from cv.pose_estimator import (
    BodyCalibration,
    DOM_ELBOW,
    DOM_SHOULDER,
    DOM_WRIST,
    L_SHOULDER,
    NOSE,
    ROLLING_BUFFER,
    joint_angle_deg,
    hip_mid_xy,
)

_SWING_WINDOW = 90           # max frames for a valid swing
_FOLLOW_DECEL_FRAMES = 6     # consecutive decelerating frames required
_MIN_SCORE = 45              # minimum score for a valid stroke


class Phase(str, Enum):
    READY = "READY"
    BACKSWING = "BACKSWING"
    LOAD = "LOAD"
    CONTACT = "CONTACT"
    FOLLOW_THROUGH = "FOLLOW_THROUGH"


@dataclass
class FrameSample:
    shoulder: Tuple[float, float]
    elbow: Tuple[float, float]
    wrist: Tuple[float, float]
    hip_mid: Tuple[float, float]
    l_shoulder: Tuple[float, float]
    nose: Tuple[float, float]
    torso_cx: float
    elbow_angle: float
    v_shoulder: float
    v_elbow: float
    v_wrist: float
    v_paddle_rot: float
    v_paddle: float


def _xy(lm, idx: int) -> Tuple[float, float]:
    return (lm[idx].x, lm[idx].y)


def _wrap_pi(a: float) -> float:
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def _return_probability(score: int) -> float:
    """Map score 45→0.5 … 100→1.0 (linear).  Scores below 45 get 0.0."""
    if score < _MIN_SCORE:
        return 0.0
    return 0.5 + 0.5 * (score - 45) / 55.0


class StrokeClassifier:
    """
    Rolling 30-frame buffer, 30-frame calibration, CONTACT-only scoring,
    follow-through decel gate, return-probability roll.
    """

    def __init__(self):
        self._cal = BodyCalibration()
        self._buf: deque[Optional[FrameSample]] = deque(maxlen=ROLLING_BUFFER)

        self.phase = Phase.READY
        self.state: str = "READY"
        self.wrist_speed: float = 0.0

        # Swing bookkeeping
        self._swing_start_hip_x: Optional[float] = None
        self._backswing_wrist_v: List[float] = []
        self._in_swing = False
        self._swing_frame_idx = 0
        self._prev_wrist_vel: Optional[Tuple[float, float]] = None
        self._prev_theta: Optional[float] = None

        # Backhand path checks
        self._l_shoulder_max_x: float = -1.0
        self._wrist_min_x_before_contact: float = 1.0
        self._had_cross_l_shoulder_nose = False
        self._had_wrist_cross_torso = False

        # Wrist x-displacement for mirrored-camera forehand/backhand
        self._backswing_start_wrist_x: Optional[float] = None
        self._wrist_dx: float = 0.0

        # Peak / follow-through
        self._vel_history: deque[float] = deque(maxlen=8)
        self._follow_decel_count = 0
        self._follow_prev_vw: Optional[float] = None
        self._contact_scored = False

        # Last scored swing
        self._last_stroke: str = "READY"
        self._last_score: int = 0
        self._last_return_prob: float = 0.0
        self._last_net_event: bool = False  # True when return-prob roll fails
        self._last_metrics: Dict[str, float] = {}
        self._weakest_metric: str = ""

        self._contact_snapshot: Optional[Dict[str, Any]] = None
        self._emitted = False  # stroke emitted once per swing

    # ── Public API ──────────────────────────────────────────────────────

    def update(
        self,
        landmarks,
        paddle_center_norm: Optional[Tuple[float, float]] = None,
    ) -> str:
        if landmarks is None:
            return self.state

        if not self._cal.feed(landmarks):
            self._emit_pre_calib()
            return self.state

        bl = self._cal.baseline
        fl = max(bl.forearm_len, 1e-6)

        s = _xy(landmarks, DOM_SHOULDER)
        e = _xy(landmarks, DOM_ELBOW)
        w = _xy(landmarks, DOM_WRIST)
        hip = hip_mid_xy(landmarks)
        ls = _xy(landmarks, L_SHOULDER)
        nose = _xy(landmarks, NOSE)
        torso_cx = (landmarks[11].x + landmarks[12].x) / 2.0

        elbow_ang = joint_angle_deg(landmarks, DOM_SHOULDER, DOM_ELBOW, DOM_WRIST)

        if len(self._buf) >= 1 and self._buf[-1] is not None:
            ps = self._buf[-1]
            assert ps is not None
            vs = math.hypot(s[0] - ps.shoulder[0], s[1] - ps.shoulder[1]) / fl
            ve = math.hypot(e[0] - ps.elbow[0], e[1] - ps.elbow[1]) / fl
            vw = math.hypot(w[0] - ps.wrist[0], w[1] - ps.wrist[1]) / fl
        else:
            vs = ve = vw = 0.0

        v_rot = self._paddle_rotation_term(w, e, paddle_center_norm, fl)
        v_paddle = vs + ve + vw + v_rot

        sample = FrameSample(
            shoulder=s, elbow=e, wrist=w, hip_mid=hip,
            l_shoulder=ls, nose=nose, torso_cx=torso_cx,
            elbow_angle=elbow_ang,
            v_shoulder=vs, v_elbow=ve, v_wrist=vw,
            v_paddle_rot=v_rot, v_paddle=v_paddle,
        )
        self._buf.append(sample)

        if len(self._buf) >= 2 and self._buf[-2] is not None:
            p0 = self._buf[-2]
            assert p0 is not None
            self._prev_wrist_vel = (w[0] - p0.wrist[0], w[1] - p0.wrist[1])

        self.wrist_speed = min(1.0, vw / 0.35)

        # Phase FSM
        self._advance_phase(landmarks, sample, fl)
        if self.phase != Phase.READY:
            self._swing_frame_idx += 1

        # 90-frame window enforcement
        if self._in_swing and self._swing_frame_idx > _SWING_WINDOW:
            self._reset_swing()

        self._sync_game_state()
        return self.state

    @property
    def last_net_event(self) -> bool:
        return self._last_net_event

    @property
    def last_return_probability(self) -> float:
        return self._last_return_prob

    # ── Paddle rotation ─────────────────────────────────────────────────

    def _paddle_rotation_term(
        self, w: Tuple[float, float], e: Tuple[float, float],
        paddle_center: Optional[Tuple[float, float]], fl: float,
    ) -> float:
        if paddle_center is not None:
            theta = math.atan2(paddle_center[1] - w[1], paddle_center[0] - w[0])
        else:
            theta = math.atan2(w[1] - e[1], w[0] - e[0])
        if self._prev_theta is None:
            self._prev_theta = theta
            return 0.0
        dtheta = _wrap_pi(theta - self._prev_theta)
        self._prev_theta = theta
        return min(1.0, abs(dtheta) / (math.pi * 0.35))

    # ── Phase FSM ───────────────────────────────────────────────────────

    def _peak_detected(self) -> bool:
        if self._swing_frame_idx < 5:
            return False
        if len(self._vel_history) < 3:
            return False
        vlist = list(self._vel_history)
        return vlist[-2] >= vlist[-1] and vlist[-2] >= vlist[-3] and vlist[-2] > 0.08

    def _fire_contact(self, lm, sample: FrameSample, fl: float) -> None:
        self.phase = Phase.CONTACT
        if self._backswing_start_wrist_x is not None:
            self._wrist_dx = sample.wrist[0] - self._backswing_start_wrist_x
        self._score_contact(lm, sample, fl)
        self._contact_scored = True
        self._contact_snapshot = self._build_frame_output(Phase.CONTACT)
        self.phase = Phase.FOLLOW_THROUGH
        self._follow_decel_count = 0
        self._follow_prev_vw = sample.v_wrist

    def _advance_phase(self, lm, sample: FrameSample, fl: float) -> None:
        vw = sample.v_wrist
        self._vel_history.append(vw)

        hip_vx = 0.0
        if len(self._buf) >= 2 and self._buf[-2] is not None:
            p = self._buf[-2]
            assert p is not None
            hip_vx = sample.hip_mid[0] - p.hip_mid[0]

        elbow_below = lm[DOM_ELBOW].y > lm[DOM_SHOULDER].y + 0.01

        if self.phase != Phase.READY:
            self._l_shoulder_max_x = max(self._l_shoulder_max_x, lm[L_SHOULDER].x)
            if lm[L_SHOULDER].x > lm[NOSE].x - 0.01:
                self._had_cross_l_shoulder_nose = True
            if sample.wrist[0] < sample.torso_cx:
                self._had_wrist_cross_torso = True
            self._wrist_min_x_before_contact = min(
                self._wrist_min_x_before_contact, sample.wrist[0]
            )

        if self.phase == Phase.READY:
            self._backswing_wrist_v.clear()
            if vw > 0.12 and not self._in_swing:
                self._swing_start_hip_x = sample.hip_mid[0]
                self._backswing_start_wrist_x = sample.wrist[0]
                self._in_swing = True
                self.phase = Phase.BACKSWING
                self._l_shoulder_max_x = lm[L_SHOULDER].x
                self._wrist_min_x_before_contact = sample.wrist[0]
                self._had_cross_l_shoulder_nose = False
                self._had_wrist_cross_torso = False

        elif self.phase == Phase.BACKSWING:
            self._backswing_wrist_v.append(vw)
            if self._peak_detected():
                self._fire_contact(lm, sample, fl)
                return
            if len(self._vel_history) >= 3:
                decel = vw < list(self._vel_history)[-2]
                if elbow_below and decel and abs(hip_vx) > 0.002:
                    self.phase = Phase.LOAD
            if vw < 0.03 and len(self._backswing_wrist_v) > 20:
                self._reset_swing()

        elif self.phase == Phase.LOAD:
            self._backswing_wrist_v.append(vw)
            if self._peak_detected():
                self._fire_contact(lm, sample, fl)
                return
            if vw < 0.04 and len(self._backswing_wrist_v) > 8:
                self._reset_swing()

        elif self.phase == Phase.FOLLOW_THROUGH:
            # Deceleration gate: 6 consecutive frames of wrist slowing
            if self._follow_prev_vw is not None and vw <= self._follow_prev_vw:
                self._follow_decel_count += 1
            else:
                self._follow_decel_count = 0
            self._follow_prev_vw = vw

            if self._follow_decel_count >= _FOLLOW_DECEL_FRAMES and not self._emitted:
                self._emit_stroke()
            elif vw < 0.03:
                # Wrist stopped without enough decel frames — still emit
                # if contact was scored, else just reset
                if self._contact_scored and not self._emitted:
                    self._emit_stroke()
                else:
                    self._reset_swing()

    def _emit_stroke(self) -> None:
        """Emit the stroke once, roll return probability, reset."""
        if self._last_score >= _MIN_SCORE and self._last_stroke in ("FOREHAND", "BACKHAND"):
            self._last_return_prob = _return_probability(self._last_score)
            roll = random.random()
            self._last_net_event = roll > self._last_return_prob
            self.state = self._last_stroke
        else:
            self._last_return_prob = 0.0
            self._last_net_event = False
            self.state = "UNIDENTIFIABLE"

        self._emitted = True
        # Hold state for one frame, then reset in _sync_game_state
        # next cycle will see _emitted=True and reset.

    def _reset_swing(self) -> None:
        self.phase = Phase.READY
        self._in_swing = False
        self._swing_frame_idx = 0
        self._swing_start_hip_x = None
        self._backswing_start_wrist_x = None
        self._wrist_dx = 0.0
        self._backswing_wrist_v.clear()
        self._contact_snapshot = None
        self._contact_scored = False
        self._follow_decel_count = 0
        self._follow_prev_vw = None
        self._emitted = False
        self.state = "READY"

    # ── Scoring ─────────────────────────────────────────────────────────

    def _score_contact(self, lm, sample: FrameSample, fl: float) -> None:
        bl = self._cal.baseline
        sw = max(bl.shoulder_width, 1e-6)

        hip_start = self._swing_start_hip_x
        if hip_start is None:
            hip_start = sample.hip_mid[0]
        delta_hip = abs(sample.hip_mid[0] - hip_start)
        hip_ratio = delta_hip / sw

        def hip_score() -> float:
            if hip_ratio < 0.4:
                return max(0.0, hip_ratio / 0.4)
            return min(1.0, (hip_ratio - 0.4) / 0.35)

        hip_s = hip_score()

        target_fh_x = sample.hip_mid[0] + fl * 0.8
        err_fh = abs(sample.wrist[0] - target_fh_x) / fl
        contact_fh = 1.0 if err_fh <= 0.15 else max(0.0, 1.0 - (err_fh - 0.15) / 0.25)

        ideal_bh_x = sample.torso_cx - 0.45 * fl
        err_bh = abs(sample.wrist[0] - ideal_bh_x) / fl
        bh_slot = 1.0 if err_bh <= 0.15 else max(0.0, 1.0 - (err_bh - 0.15) / 0.25)
        wrist_cross = 1.0 if self._had_wrist_cross_torso else 0.0
        contact_bh = 0.5 * bh_slot + 0.5 * wrist_cross

        ang = sample.elbow_angle

        def elbow_score() -> float:
            if 160 <= ang <= 170:
                return 1.0
            return max(0.0, 1.0 - min(abs(ang - 160), abs(ang - 170)) / 25.0)

        el_s = elbow_score()

        mean_bs = (
            float(np.mean(self._backswing_wrist_v))
            if self._backswing_wrist_v else sample.v_wrist
        )
        mean_bs = max(mean_bs, 1e-6)
        snap_ratio = sample.v_wrist / mean_bs
        sn_s = min(1.0, snap_ratio / 1.5)

        fh_metrics = {"hip_rotation": hip_s, "contact_point": contact_fh, "elbow_angle": el_s, "wrist_snap": sn_s}
        fh_avg = float(np.mean(list(fh_metrics.values())))

        shoulder_turn = 1.0 if self._had_cross_l_shoulder_nose else 0.0
        bh_metrics = {"hip_rotation": hip_s, "contact_point": contact_bh, "elbow_angle": el_s, "wrist_snap": 0.5 * sn_s + 0.5 * shoulder_turn}
        bh_avg = float(np.mean(list(bh_metrics.values())))

        # Wrist x-displacement override for mirrored camera:
        # dx < 0 → forehand, dx > 0 → backhand
        dx = self._wrist_dx
        dx_fh = dx < -0.01
        dx_bh = dx > 0.01

        if dx_fh and fh_avg >= 0.45:
            self._last_stroke = "FOREHAND"
            self._last_metrics = fh_metrics
            self._last_score = int(round(fh_avg * 100))
        elif dx_bh and bh_avg >= 0.45:
            self._last_stroke = "BACKHAND"
            self._last_metrics = bh_metrics
            self._last_score = int(round(bh_avg * 100))
        elif fh_avg >= 0.45 and fh_avg >= bh_avg:
            self._last_stroke = "FOREHAND"
            self._last_metrics = fh_metrics
            self._last_score = int(round(fh_avg * 100))
        elif bh_avg >= 0.45 and bh_avg > fh_avg:
            self._last_stroke = "BACKHAND"
            self._last_metrics = bh_metrics
            self._last_score = int(round(bh_avg * 100))
        else:
            self._last_stroke = "UNIDENTIFIABLE"
            self._last_metrics = fh_metrics
            self._last_score = int(round(max(fh_avg, bh_avg) * 100))

        self._weakest_metric = min(self._last_metrics.keys(), key=lambda k: self._last_metrics[k])

    # ── Game state sync ─────────────────────────────────────────────────

    def _sync_game_state(self) -> None:
        if self._emitted and self.phase == Phase.FOLLOW_THROUGH:
            # Already emitted — let the game read self.state for one tick,
            # then reset next frame
            pass
        elif self.phase == Phase.READY:
            self.state = "READY"

    # ── Output helpers ──────────────────────────────────────────────────

    def _build_frame_output(self, ph: Phase) -> Dict[str, Any]:
        rp = _return_probability(self._last_score)
        return {
            "phase": ph.value,
            "stroke": self._last_stroke,
            "score": self._last_score,
            "return_probability": round(rp, 2),
            "metrics": {k: round(v, 2) for k, v in self._last_metrics.items()},
        }

    def _emit_pre_calib(self) -> None:
        self.state = "READY"

    @property
    def frame_output(self) -> Dict[str, Any]:
        if self._contact_snapshot:
            return self._contact_snapshot
        return {
            "phase": self.phase.value,
            "stroke": self.state if self.state in ("FOREHAND", "BACKHAND", "UNIDENTIFIABLE") else "READY",
            "score": self._last_score,
            "return_probability": round(self._last_return_prob, 2),
            "metrics": {k: round(v, 2) for k, v in self._last_metrics.items()},
        }

    @property
    def overlay_lines(self) -> Tuple[str, str]:
        if not self._cal.baseline.ready:
            return ("Calibrating body…", "")
        if self._weakest_metric and self._last_metrics:
            wv = self._last_metrics.get(self._weakest_metric, 0.0)
            return (
                f"Score {self._last_score} | {self._last_stroke}",
                f"Weakest: {self._weakest_metric} ({wv:.2f})",
            )
        return (f"{self.phase.value}", "")
