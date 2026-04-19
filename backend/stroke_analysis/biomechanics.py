"""
Biomechanical math engine for pickleball swing analysis.

Body-proportion normalization, joint angle computation, kinetic chain
velocity estimation, and adaptive target generation — all from MediaPipe
33-landmark pose data in normalised (0-1) coordinate space.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

# ── MediaPipe landmark indices ──────────────────────────────────────────
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_HEEL, R_HEEL = 29, 30


def _pt(lm):
    return np.array([lm.x, lm.y])


def _pt3(lm):
    return np.array([lm.x, lm.y, lm.z])


def dist(a, b) -> float:
    return float(np.linalg.norm(_pt(a) - _pt(b)))


def dist3(a, b) -> float:
    return float(np.linalg.norm(_pt3(a) - _pt3(b)))


def joint_angle(a, b, c) -> float:
    """Angle in degrees at vertex b formed by segments b→a and b→c."""
    ba = _pt(a) - _pt(b)
    bc = _pt(c) - _pt(b)
    cos = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return math.degrees(math.acos(np.clip(cos, -1.0, 1.0)))


def rotation_angle(p1_a, p1_b, p2_a, p2_b) -> float:
    """
    Relative rotation between two body lines (e.g. shoulder line vs hip line).
    Returns signed angle in degrees (positive = open rotation toward camera-left).
    """
    v1 = _pt(p1_b) - _pt(p1_a)
    v2 = _pt(p2_b) - _pt(p2_a)
    cross = float(np.cross(v1, v2))
    dot = float(np.dot(v1, v2))
    return math.degrees(math.atan2(cross, dot))


def midpoint(a, b):
    return np.array([(a.x + b.x) / 2, (a.y + b.y) / 2])


# ── Body Proportions ────────────────────────────────────────────────────

@dataclass
class BodyProportions:
    """Extracted once during calibration, used to normalise all targets."""
    shoulder_width: float = 0.0
    hip_width: float = 0.0
    torso_length: float = 0.0
    leg_length: float = 0.0
    upper_arm: float = 0.0
    forearm: float = 0.0
    arm_span_est: float = 0.0
    height_est: float = 0.0

    # Derived ratios
    shoulder_hip_ratio: float = 0.0
    torso_leg_ratio: float = 0.0
    upper_forearm_ratio: float = 0.0
    arm_height_ratio: float = 0.0
    speed_multiplier: float = 0.0  # hip-to-paddle lever ratio

    calibrated: bool = False

    def calibrate(self, landmarks) -> None:
        lm = landmarks
        self.shoulder_width = dist(lm[L_SHOULDER], lm[R_SHOULDER])
        self.hip_width = dist(lm[L_HIP], lm[R_HIP])

        self.torso_length = (
            dist(lm[L_SHOULDER], lm[L_HIP]) + dist(lm[R_SHOULDER], lm[R_HIP])
        ) / 2.0

        self.leg_length = (
            dist(lm[L_HIP], lm[L_ANKLE]) + dist(lm[R_HIP], lm[R_ANKLE])
        ) / 2.0

        self.upper_arm = (
            dist(lm[L_SHOULDER], lm[L_ELBOW]) + dist(lm[R_SHOULDER], lm[R_ELBOW])
        ) / 2.0

        self.forearm = (
            dist(lm[L_ELBOW], lm[L_WRIST]) + dist(lm[R_ELBOW], lm[R_WRIST])
        ) / 2.0

        # Arm span ≈ shoulder width + 2*(upper_arm + forearm)
        self.arm_span_est = self.shoulder_width + 2 * (self.upper_arm + self.forearm)

        # Height ≈ distance from mid-ankle to nose + a bit for top of head
        mid_ankle_y = (lm[L_ANKLE].y + lm[R_ANKLE].y) / 2.0
        self.height_est = abs(mid_ankle_y - lm[NOSE].y) * 1.08

        # Ratios
        self.shoulder_hip_ratio = self.shoulder_width / (self.hip_width + 1e-8)
        self.torso_leg_ratio = self.torso_length / (self.leg_length + 1e-8)
        self.upper_forearm_ratio = self.upper_arm / (self.forearm + 1e-8)
        self.arm_height_ratio = self.arm_span_est / (self.height_est + 1e-8)

        # Speed multiplier: how much paddle moves per unit of hip displacement
        spine_hip = self.torso_length / 2.0
        spine_paddle = self.torso_length / 2.0 + self.upper_arm + self.forearm
        self.speed_multiplier = spine_paddle / (spine_hip + 1e-8)

        self.calibrated = True

    def to_dict(self) -> dict:
        return {
            "calibrated": self.calibrated,
            "shoulderWidth": round(self.shoulder_width, 4),
            "hipWidth": round(self.hip_width, 4),
            "torsoLength": round(self.torso_length, 4),
            "legLength": round(self.leg_length, 4),
            "upperArm": round(self.upper_arm, 4),
            "forearm": round(self.forearm, 4),
            "shoulderHipRatio": round(self.shoulder_hip_ratio, 3),
            "torsoLegRatio": round(self.torso_leg_ratio, 3),
            "upperForearmRatio": round(self.upper_forearm_ratio, 3),
            "armHeightRatio": round(self.arm_height_ratio, 3),
            "speedMultiplier": round(self.speed_multiplier, 2),
        }


# ── Kinetic Chain Velocity ──────────────────────────────────────────────

class VelocityTracker:
    """Rolling-window velocity tracker for any landmark point."""

    def __init__(self, window: int = 5):
        self._buf: deque = deque(maxlen=window)

    def push(self, pt: np.ndarray) -> None:
        self._buf.append(pt.copy())

    @property
    def velocity(self) -> float:
        if len(self._buf) < 2:
            return 0.0
        return float(np.linalg.norm(self._buf[-1] - self._buf[-2]))

    @property
    def direction(self) -> np.ndarray:
        if len(self._buf) < 2:
            return np.zeros(2)
        d = self._buf[-1] - self._buf[-2]
        n = np.linalg.norm(d)
        return d / n if n > 1e-8 else np.zeros(2)

    @property
    def acceleration(self) -> float:
        if len(self._buf) < 3:
            return 0.0
        v1 = np.linalg.norm(self._buf[-1] - self._buf[-2])
        v0 = np.linalg.norm(self._buf[-2] - self._buf[-3])
        return v1 - v0

    @property
    def avg_velocity(self) -> float:
        if len(self._buf) < 2:
            return 0.0
        total = sum(
            np.linalg.norm(self._buf[i + 1] - self._buf[i])
            for i in range(len(self._buf) - 1)
        )
        return total / (len(self._buf) - 1)


class KineticChain:
    """
    Tracks the kinetic chain: shoulder → elbow → wrist → paddle-tip.
    v_paddle = v_shoulder + v_elbow + v_wrist + v_paddle_rotation
    """

    def __init__(self):
        self.shoulder = VelocityTracker()
        self.elbow = VelocityTracker()
        self.wrist = VelocityTracker()
        self.hip = VelocityTracker()

    def update(self, landmarks) -> None:
        self.shoulder.push(_pt(landmarks[R_SHOULDER]))
        self.elbow.push(_pt(landmarks[R_ELBOW]))
        self.wrist.push(_pt(landmarks[R_WRIST]))
        self.hip.push(midpoint(landmarks[L_HIP], landmarks[R_HIP]))

    @property
    def paddle_velocity(self) -> float:
        return (
            self.shoulder.velocity
            + self.elbow.velocity
            + self.wrist.velocity
        )

    @property
    def chain_sequence_correct(self) -> bool:
        """True if energy flows proximal→distal (hip before shoulder before wrist)."""
        return self.hip.velocity <= self.shoulder.velocity <= self.wrist.velocity

    def to_dict(self) -> dict:
        return {
            "hipVel": round(self.hip.velocity, 4),
            "shoulderVel": round(self.shoulder.velocity, 4),
            "elbowVel": round(self.elbow.velocity, 4),
            "wristVel": round(self.wrist.velocity, 4),
            "paddleVel": round(self.paddle_velocity, 4),
            "chainCorrect": self.chain_sequence_correct,
        }


# ── Adaptive Target Generator ──────────────────────────────────────────

def get_ideal_contact_point(lm, props: BodyProportions):
    """Contact should be ~1 forearm-length in front of lead hip."""
    hip = _pt(lm[R_HIP])
    offset_x = props.forearm * 0.8
    offset_y = props.forearm * 0.2
    return hip[0] + offset_x, hip[1] - offset_y


def hip_rotation_score(lm, props: BodyProportions) -> float:
    """Hip displacement normalised by shoulder width. Target: >0.4."""
    shoulder_line = rotation_angle(
        lm[L_SHOULDER], lm[R_SHOULDER], lm[L_HIP], lm[R_HIP]
    )
    return abs(shoulder_line) / 90.0  # normalise to 0-1


def scale_angle_target(base_angle: float, props: BodyProportions) -> float:
    """Scale ideal joint angle by upper/forearm ratio (double-pendulum timing)."""
    ratio_deviation = props.upper_forearm_ratio - 1.0
    return base_angle + ratio_deviation * 5.0  # ±5° per unit ratio difference
