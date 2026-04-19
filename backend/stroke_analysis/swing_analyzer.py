"""
Complete swing analysis pipeline: shot classification, 5-phase detection,
per-shot metric scoring with body-proportional targets, and coaching
feedback generation.
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import numpy as np

from biomechanics import (
    BodyProportions,
    KineticChain,
    VelocityTracker,
    joint_angle,
    rotation_angle,
    dist,
    get_ideal_contact_point,
    hip_rotation_score,
    scale_angle_target,
    midpoint,
    _pt,
    L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW,
    L_WRIST, R_WRIST, L_HIP, R_HIP,
    L_KNEE, R_KNEE, L_ANKLE, R_ANKLE, NOSE,
)


# ── Shot Types ──────────────────────────────────────────────────────────

class ShotType(str, Enum):
    NONE = "none"
    FOREHAND = "forehand"
    BACKHAND = "backhand"
    DINK = "dink"
    SERVE = "serve"
    VOLLEY = "volley"


# ── Swing Phases ────────────────────────────────────────────────────────

class Phase(str, Enum):
    READY = "ready"
    BACKSWING = "backswing"
    LOAD = "load"
    CONTACT = "contact"
    FOLLOW_THROUGH = "follow_through"


# ── Shot Classifier (rule-based FSM) ────────────────────────────────────

_VELOCITY_THRESHOLD = 0.015
_DINK_VEL_CEILING = 0.04
_SERVE_WRIST_BELOW_WAIST_MARGIN = 0.03


class ShotClassifier:
    """
    Classifies the current swing into a shot type using wrist trajectory,
    elbow angle, body position, and velocity magnitude.
    """

    def __init__(self):
        self._wrist_buf: deque = deque(maxlen=30)
        self._shot = ShotType.NONE
        self._confidence = 0.0
        self._consec = 0
        self._pending: ShotType = ShotType.NONE

    def update(self, lm, chain: KineticChain) -> ShotType:
        rw = _pt(lm[R_WRIST])
        self._wrist_buf.append(rw)
        if len(self._wrist_buf) < 5:
            return self._shot

        wrist_vel = chain.wrist.velocity
        elbow_angle = joint_angle(lm[R_SHOULDER], lm[R_ELBOW], lm[R_WRIST])
        wrist_y = lm[R_WRIST].y
        hip_y = (lm[L_HIP].y + lm[R_HIP].y) / 2.0
        shoulder_y = (lm[L_SHOULDER].y + lm[R_SHOULDER].y) / 2.0
        torso_cx = (lm[L_SHOULDER].x + lm[R_SHOULDER].x) / 2.0

        dx = self._wrist_buf[-1][0] - self._wrist_buf[-3][0]

        candidate = ShotType.NONE

        if wrist_vel < _VELOCITY_THRESHOLD:
            candidate = ShotType.NONE
        elif wrist_vel < _DINK_VEL_CEILING and elbow_angle < 140:
            # Low velocity, compact swing → dink
            candidate = ShotType.DINK
        elif wrist_y > hip_y + _SERVE_WRIST_BELOW_WAIST_MARGIN and wrist_vel > _VELOCITY_THRESHOLD:
            # Wrist below waist, upward trajectory → serve
            if len(self._wrist_buf) >= 3:
                dy = self._wrist_buf[-1][1] - self._wrist_buf[-3][1]
                if dy < 0:  # moving upward (y decreases)
                    candidate = ShotType.SERVE
        elif 85 <= elbow_angle <= 100 and wrist_vel < 0.035:
            # Elbow bent ~90°, minimal backswing → volley/punch
            candidate = ShotType.VOLLEY

        # Forehand vs backhand (if not already classified)
        if candidate == ShotType.NONE and wrist_vel > _VELOCITY_THRESHOLD:
            if dx > 0.005:
                candidate = ShotType.FOREHAND
            elif dx < -0.005:
                candidate = ShotType.BACKHAND

        # Require consecutive confirmation
        if candidate == self._pending and candidate != ShotType.NONE:
            self._consec += 1
        elif candidate != ShotType.NONE:
            self._pending = candidate
            self._consec = 1
        else:
            self._consec = max(0, self._consec - 1)

        if self._consec >= 5:
            self._shot = self._pending
            self._confidence = min(1.0, self._consec / 10.0)
        elif self._consec == 0 and wrist_vel < _VELOCITY_THRESHOLD * 0.5:
            self._shot = ShotType.NONE
            self._confidence = 0.0

        return self._shot

    @property
    def current(self) -> ShotType:
        return self._shot

    @property
    def confidence(self) -> float:
        return self._confidence


# ── Phase Detector ──────────────────────────────────────────────────────

_ANGULAR_VEL_THRESHOLD = 0.8  # degrees/frame

class PhaseDetector:
    """
    Detects the 5 swing phases using joint angular velocities:
    READY → BACKSWING → LOAD → CONTACT → FOLLOW_THROUGH → READY
    """

    def __init__(self):
        self.phase = Phase.READY
        self._elbow_angles: deque = deque(maxlen=10)
        self._wrist_vels: deque = deque(maxlen=10)
        self._hip_rotations: deque = deque(maxlen=10)
        self._phase_start_time = time.time()
        self._min_phase_duration = 0.08  # seconds

    def update(self, lm, chain: KineticChain) -> Phase:
        elbow_ang = joint_angle(lm[R_SHOULDER], lm[R_ELBOW], lm[R_WRIST])
        hip_rot = rotation_angle(lm[L_SHOULDER], lm[R_SHOULDER], lm[L_HIP], lm[R_HIP])
        wrist_vel = chain.wrist.velocity
        wrist_accel = chain.wrist.acceleration

        self._elbow_angles.append(elbow_ang)
        self._wrist_vels.append(wrist_vel)
        self._hip_rotations.append(hip_rot)

        elapsed = time.time() - self._phase_start_time
        if elapsed < self._min_phase_duration:
            return self.phase

        elbow_delta = 0.0
        if len(self._elbow_angles) >= 2:
            elbow_delta = self._elbow_angles[-1] - self._elbow_angles[-2]

        hip_delta = 0.0
        if len(self._hip_rotations) >= 2:
            hip_delta = abs(self._hip_rotations[-1] - self._hip_rotations[-2])

        prev = self.phase

        if self.phase == Phase.READY:
            # Transition to BACKSWING: hip/torso starts rotating, wrist pulls back
            if (hip_delta > _ANGULAR_VEL_THRESHOLD or wrist_vel > _VELOCITY_THRESHOLD) and elbow_delta < 0:
                self.phase = Phase.BACKSWING

        elif self.phase == Phase.BACKSWING:
            # Transition to LOAD: backswing decelerates, weight shifts
            if wrist_vel < _VELOCITY_THRESHOLD and len(self._wrist_vels) >= 3:
                if self._wrist_vels[-1] < self._wrist_vels[-2]:
                    self.phase = Phase.LOAD
            # Direct to contact if fast swing
            if wrist_accel > 0.005:
                self.phase = Phase.LOAD

        elif self.phase == Phase.LOAD:
            # Transition to CONTACT: acceleration spike, arm extending
            if wrist_accel > 0.003 and elbow_delta > 0:
                self.phase = Phase.CONTACT

        elif self.phase == Phase.CONTACT:
            # Transition to FOLLOW_THROUGH: deceleration begins
            if wrist_accel < -0.001 or elapsed > 0.3:
                self.phase = Phase.FOLLOW_THROUGH

        elif self.phase == Phase.FOLLOW_THROUGH:
            # Back to READY: velocity drops to near zero
            if wrist_vel < _VELOCITY_THRESHOLD * 0.5 and elapsed > 0.2:
                self.phase = Phase.READY

        if self.phase != prev:
            self._phase_start_time = time.time()

        return self.phase


# ── Metric Scorer ───────────────────────────────────────────────────────

@dataclass
class ShotMetrics:
    hip_rotation: float = 0.0       # 0-100
    contact_point: float = 0.0      # 0-100
    elbow_extension: float = 0.0    # 0-100
    wrist_snap: float = 0.0         # 0-100
    kinetic_chain: float = 0.0      # 0-100
    knee_bend: float = 0.0          # 0-100
    follow_through: float = 0.0     # 0-100

    @property
    def overall(self) -> float:
        vals = [
            self.hip_rotation, self.contact_point,
            self.elbow_extension, self.wrist_snap,
            self.kinetic_chain, self.knee_bend, self.follow_through,
        ]
        return round(sum(vals) / len(vals), 1)

    def to_dict(self) -> dict:
        return {
            "hipRotation": round(self.hip_rotation, 1),
            "contactPoint": round(self.contact_point, 1),
            "elbowExtension": round(self.elbow_extension, 1),
            "wristSnap": round(self.wrist_snap, 1),
            "kineticChain": round(self.kinetic_chain, 1),
            "kneeBend": round(self.knee_bend, 1),
            "followThrough": round(self.follow_through, 1),
            "overall": self.overall,
        }


def _score(value: float, target: float, tolerance: float = 15.0) -> float:
    """Score 0-100 based on how close value is to target within tolerance."""
    diff = abs(value - target)
    return max(0.0, min(100.0, 100.0 * (1.0 - diff / tolerance)))


class MetricScorer:
    """Scores each swing metric using body-proportional targets."""

    def __init__(self, props: BodyProportions):
        self.props = props
        self._peak_wrist_vel = 0.0
        self._contact_elbow = 0.0
        self._contact_hip_rot = 0.0
        self._follow_wrist_vel_sum = 0.0
        self._follow_frames = 0

    def update_realtime(self, lm, chain: KineticChain, phase: Phase) -> None:
        """Accumulate data during the swing for final scoring."""
        if phase == Phase.CONTACT:
            self._contact_elbow = joint_angle(lm[R_SHOULDER], lm[R_ELBOW], lm[R_WRIST])
            self._contact_hip_rot = abs(rotation_angle(
                lm[L_SHOULDER], lm[R_SHOULDER], lm[L_HIP], lm[R_HIP]
            ))
            self._peak_wrist_vel = max(self._peak_wrist_vel, chain.wrist.velocity)

        if phase == Phase.FOLLOW_THROUGH:
            self._follow_wrist_vel_sum += chain.wrist.velocity
            self._follow_frames += 1

    def score(self, shot: ShotType, lm, chain: KineticChain) -> ShotMetrics:
        """Produce final scores for a completed swing."""
        m = ShotMetrics()

        if shot == ShotType.FOREHAND:
            m.hip_rotation = _score(self._contact_hip_rot, scale_angle_target(65.0, self.props), 25.0)
            m.elbow_extension = _score(self._contact_elbow, scale_angle_target(165.0, self.props), 15.0)

        elif shot == ShotType.BACKHAND:
            m.hip_rotation = _score(self._contact_hip_rot, scale_angle_target(55.0, self.props), 25.0)
            m.elbow_extension = _score(self._contact_elbow, scale_angle_target(155.0, self.props), 15.0)

        elif shot == ShotType.DINK:
            # Dinks: compact swing, continuous wrist motion post-contact
            m.elbow_extension = _score(self._contact_elbow, scale_angle_target(120.0, self.props), 20.0)
            m.hip_rotation = _score(self._contact_hip_rot, 15.0, 15.0)

        elif shot == ShotType.SERVE:
            m.hip_rotation = _score(self._contact_hip_rot, 15.0, 10.0)
            m.elbow_extension = _score(self._contact_elbow, scale_angle_target(160.0, self.props), 15.0)

        elif shot == ShotType.VOLLEY:
            m.elbow_extension = _score(self._contact_elbow, scale_angle_target(90.0, self.props), 15.0)
            m.hip_rotation = _score(self._contact_hip_rot, 5.0, 10.0)

        # Contact point: wrist should be in front of lead hip
        ideal_x, ideal_y = get_ideal_contact_point(lm, self.props)
        actual_x, actual_y = lm[R_WRIST].x, lm[R_WRIST].y
        cp_dist = math.hypot(actual_x - ideal_x, actual_y - ideal_y)
        m.contact_point = max(0, 100.0 - cp_dist * 500.0)

        # Wrist snap: peak velocity during contact phase
        m.wrist_snap = min(100.0, self._peak_wrist_vel * 1200.0)

        # Kinetic chain: correct proximal→distal sequence
        m.kinetic_chain = 100.0 if chain.chain_sequence_correct else 40.0

        # Knee bend: target ~140° (not locked out at 180°)
        knee_angle = joint_angle(lm[R_HIP], lm[R_KNEE], lm[R_ANKLE])
        m.knee_bend = _score(knee_angle, 140.0, 30.0)

        # Follow-through: continuous wrist motion (not stopping dead)
        if self._follow_frames > 0:
            avg_follow_vel = self._follow_wrist_vel_sum / self._follow_frames
            m.follow_through = min(100.0, avg_follow_vel * 2000.0)

        return m

    def reset(self) -> None:
        self._peak_wrist_vel = 0.0
        self._contact_elbow = 0.0
        self._contact_hip_rot = 0.0
        self._follow_wrist_vel_sum = 0.0
        self._follow_frames = 0


# ── Feedback Generator ──────────────────────────────────────────────────

@dataclass
class CoachingTip:
    metric: str
    score: float
    tip: str
    priority: int  # 1 = most urgent

    def to_dict(self) -> dict:
        return {"metric": self.metric, "score": round(self.score, 1), "tip": self.tip, "priority": self.priority}


_FEEDBACK_MAP = {
    ShotType.FOREHAND: {
        "hipRotation": (50, "Rotate your hips more — drive power from your core, not just your arm."),
        "contactPoint": (50, "Make contact further in front of your body — reach out toward the net."),
        "elbowExtension": (50, "Extend your elbow more at contact — aim for nearly straight (~165°)."),
        "wristSnap": (40, "Add more wrist snap at contact for extra pace and spin."),
        "kineticChain": (60, "Initiate from hips first, then shoulder, then wrist — build the whip effect."),
        "kneeBend": (50, "Bend your knees more — staying low gives you better balance and power."),
        "followThrough": (40, "Follow through across your body — don't stop your swing at contact."),
    },
    ShotType.BACKHAND: {
        "hipRotation": (50, "Turn your shoulders more — your non-dominant shoulder should point at the net during backswing."),
        "contactPoint": (50, "Contact the ball out in front — don't let it get beside your body."),
        "elbowExtension": (50, "Keep your elbow slightly bent at contact for control."),
        "wristSnap": (40, "Lead with your knuckles through contact for a cleaner hit."),
        "kineticChain": (60, "Let the rotation unwind naturally — hips lead, arms follow."),
        "kneeBend": (50, "Stay low through the shot — bend those knees."),
        "followThrough": (40, "Extend your follow-through toward the target."),
    },
    ShotType.DINK: {
        "hipRotation": (60, "Keep hip rotation minimal for dinks — this is an arm-and-wrist shot."),
        "contactPoint": (50, "Soft hands, contact out front with a gentle push motion."),
        "elbowExtension": (50, "Keep your elbow bent and the swing compact — no big backswing."),
        "wristSnap": (60, "Maintain continuous wrist motion after contact — don't freeze your wrist."),
        "kneeBend": (40, "Bend your knees deeply — advanced players show significantly more femur flexion on dinks."),
        "followThrough": (40, "Keep a smooth, pendulum-like follow-through."),
    },
    ShotType.SERVE: {
        "hipRotation": (50, "Use 10-20° of hip rotation with knee bend to load your quads and glutes."),
        "contactPoint": (60, "Contact must be below waist height — keep it underhand and legal."),
        "elbowExtension": (50, "Extend your arm through the serve for depth."),
        "kneeBend": (40, "Bend your knees to load power from the ground up."),
        "followThrough": (40, "Follow through across the midline of your body."),
    },
    ShotType.VOLLEY: {
        "hipRotation": (60, "Minimal hip rotation — this is a punch, not a swing."),
        "contactPoint": (50, "Keep the paddle out in front of your body at all times."),
        "elbowExtension": (60, "Keep elbow bent at ~90° — no arm extension on volleys."),
        "wristSnap": (60, "Firm wrist — punch forward, don't snap."),
        "followThrough": (50, "Short, decisive forward push — no long follow-through."),
    },
}


def generate_feedback(shot: ShotType, metrics: ShotMetrics) -> List[CoachingTip]:
    tips: List[CoachingTip] = []
    rules = _FEEDBACK_MAP.get(shot, _FEEDBACK_MAP[ShotType.FOREHAND])

    metric_values = metrics.to_dict()
    priority = 1

    scored = []
    for key, (threshold, tip_text) in rules.items():
        val = metric_values.get(key, 100.0)
        if val < threshold:
            scored.append((val, key, tip_text))

    # Sort worst first
    scored.sort(key=lambda x: x[0])

    for val, key, tip_text in scored[:4]:
        tips.append(CoachingTip(metric=key, score=val, tip=tip_text, priority=priority))
        priority += 1

    if not tips:
        tips.append(CoachingTip(
            metric="overall",
            score=metrics.overall,
            tip="Great form! Keep up the consistent technique.",
            priority=1,
        ))

    return tips


# ── Main Swing Analyzer (orchestrator) ──────────────────────────────────

@dataclass
class ShotRecord:
    shot_type: str
    overall_score: float
    metrics: dict
    tips: list
    timestamp: float


class SwingAnalyzer:
    """
    Top-level orchestrator: takes raw landmarks each frame and produces
    calibration state, shot classification, phase, live metrics, and
    coaching feedback.
    """

    def __init__(self):
        self.props = BodyProportions()
        self.chain = KineticChain()
        self.classifier = ShotClassifier()
        self.phase_detector = PhaseDetector()
        self.scorer: Optional[MetricScorer] = None
        self.shot_history: List[ShotRecord] = []

        self._calibration_frames = 0
        self._calibration_target = 60  # ~2 seconds at 30fps
        self._calibration_buf: list = []

        self._current_metrics = ShotMetrics()
        self._current_tips: List[CoachingTip] = []
        self._prev_phase = Phase.READY
        self._active_shot = ShotType.NONE

    @property
    def is_calibrated(self) -> bool:
        return self.props.calibrated

    def update(self, landmarks) -> dict:
        """
        Process one frame of landmarks. Returns the full analysis state dict.
        """
        # ── Calibration phase ───────────────────────────────────────────
        if not self.props.calibrated:
            self._calibration_frames += 1
            self._calibration_buf.append(landmarks)

            if self._calibration_frames >= self._calibration_target:
                # Use the median frame for calibration (most stable pose)
                mid = self._calibration_buf[len(self._calibration_buf) // 2]
                self.props.calibrate(mid)
                self.scorer = MetricScorer(self.props)

            return self._state_dict()

        # ── Live analysis ───────────────────────────────────────────────
        self.chain.update(landmarks)

        shot = self.classifier.update(landmarks, self.chain)
        phase = self.phase_detector.update(landmarks, self.chain)

        # Track active shot for scoring
        if shot != ShotType.NONE and self._active_shot == ShotType.NONE:
            self._active_shot = shot
            self.scorer.reset()

        # Accumulate scoring data during swing
        if self._active_shot != ShotType.NONE and self.scorer:
            self.scorer.update_realtime(landmarks, self.chain, phase)

        # Shot completed: FOLLOW_THROUGH → READY transition
        if self._prev_phase == Phase.FOLLOW_THROUGH and phase == Phase.READY:
            if self._active_shot != ShotType.NONE and self.scorer:
                self._current_metrics = self.scorer.score(
                    self._active_shot, landmarks, self.chain
                )
                self._current_tips = generate_feedback(
                    self._active_shot, self._current_metrics
                )
                self.shot_history.append(ShotRecord(
                    shot_type=self._active_shot.value,
                    overall_score=self._current_metrics.overall,
                    metrics=self._current_metrics.to_dict(),
                    tips=[t.to_dict() for t in self._current_tips],
                    timestamp=time.time(),
                ))
                if len(self.shot_history) > 20:
                    self.shot_history.pop(0)

            self._active_shot = ShotType.NONE

        self._prev_phase = phase

        # ── Real-time metrics (during swing) ────────────────────────────
        live = {}
        live["elbowAngle"] = round(joint_angle(
            landmarks[R_SHOULDER], landmarks[R_ELBOW], landmarks[R_WRIST]
        ), 1)
        live["hipRotation"] = round(abs(rotation_angle(
            landmarks[L_SHOULDER], landmarks[R_SHOULDER],
            landmarks[L_HIP], landmarks[R_HIP],
        )), 1)
        live["kneeAngle"] = round(joint_angle(
            landmarks[R_HIP], landmarks[R_KNEE], landmarks[R_ANKLE]
        ), 1)
        live["wristVelocity"] = round(self.chain.wrist.velocity, 4)

        return self._state_dict(live)

    def _state_dict(self, live_metrics: dict | None = None) -> dict:
        calibration_progress = min(
            1.0, self._calibration_frames / self._calibration_target
        )

        return {
            "calibrated": self.props.calibrated,
            "calibrationProgress": round(calibration_progress, 2),
            "bodyProportions": self.props.to_dict() if self.props.calibrated else None,
            "shotType": self.classifier.current.value if self.props.calibrated else "none",
            "shotConfidence": round(self.classifier.confidence, 2),
            "phase": self.phase_detector.phase.value if self.props.calibrated else "ready",
            "liveMetrics": live_metrics or {},
            "kineticChain": self.chain.to_dict() if self.props.calibrated else None,
            "lastShotMetrics": self._current_metrics.to_dict() if self._current_metrics.overall > 0 else None,
            "coachingTips": [t.to_dict() for t in self._current_tips],
            "shotHistory": [
                {
                    "shotType": s.shot_type,
                    "overall": s.overall_score,
                    "timestamp": s.timestamp,
                }
                for s in self.shot_history[-10:]
            ],
        }
