"""
WebSocket server for the Stroke Analysis CV pipeline.

Streams JPEG frames with pose overlays + JSON analysis state (shot type,
phase, metrics, coaching tips) to the browser.

Start:  python3 server.py          (port 8766)
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)
import websockets

from swing_analyzer import SwingAnalyzer, Phase, ShotType

WS_HOST = "0.0.0.0"
WS_PORT = 8766
TARGET_FPS = 30
FRAME_W, FRAME_H = 640, 480

# ── Pose connections for skeleton drawing ───────────────────────────────
_POSE_CONNS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
    (25, 27), (26, 28), (15, 17), (15, 19), (16, 18), (16, 20),
]
_ARM_IDS = {12, 14, 16}
_ARM_COLOR = (0, 165, 255)
_SKEL_COLOR = (200, 200, 200)

_PHASE_COLORS = {
    "ready": (255, 255, 255),
    "backswing": (255, 200, 0),
    "load": (0, 200, 255),
    "contact": (0, 255, 0),
    "follow_through": (200, 100, 255),
}

_SHOT_COLORS = {
    "forehand": (0, 255, 0),
    "backhand": (255, 180, 0),
    "dink": (0, 200, 255),
    "serve": (255, 100, 255),
    "volley": (255, 255, 0),
    "none": (120, 120, 120),
}


class _LandmarkProxy:
    __slots__ = ("x", "y", "z", "visibility")

    def __init__(self, lm):
        self.x = lm.x
        self.y = lm.y
        self.z = lm.z
        self.visibility = lm.visibility


def _draw_overlays(frame, landmarks, analyzer: SwingAnalyzer):
    h, w = frame.shape[:2]
    if landmarks is None:
        cv2.putText(frame, "No pose detected", (14, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        return

    pts = {}
    for i, lm in enumerate(landmarks):
        if lm.visibility > 0.3:
            pts[i] = (int(lm.x * w), int(lm.y * h))

    # Skeleton
    for a, b in _POSE_CONNS:
        if a in pts and b in pts:
            is_arm = a in _ARM_IDS and b in _ARM_IDS
            cv2.line(frame, pts[a], pts[b],
                     _ARM_COLOR if is_arm else _SKEL_COLOR,
                     3 if is_arm else 1)
    for i, pt in pts.items():
        cv2.circle(frame, pt, 6 if i in _ARM_IDS else 2,
                   _ARM_COLOR if i in _ARM_IDS else _SKEL_COLOR, -1)

    # Calibration progress bar
    if not analyzer.is_calibrated:
        prog = analyzer._calibration_frames / analyzer._calibration_target
        bx, by, bw, bh = 20, h - 40, w - 40, 20
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (50, 50, 50), -1)
        cv2.rectangle(frame, (bx, by), (bx + int(bw * prog), by + bh), (0, 255, 200), -1)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (100, 100, 100), 1)
        cv2.putText(frame, f"Calibrating body proportions... {int(prog * 100)}%",
                    (bx + 8, by + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "Stand naturally, arms relaxed",
                    (bx + 8, by - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        return

    # Shot type label
    shot = analyzer.classifier.current.value
    shot_color = _SHOT_COLORS.get(shot, (120, 120, 120))
    cv2.putText(frame, shot.upper(), (14, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, shot_color, 2, cv2.LINE_AA)

    # Phase label
    phase = analyzer.phase_detector.phase.value
    phase_color = _PHASE_COLORS.get(phase, (255, 255, 255))
    phase_label = phase.replace("_", " ").upper()
    cv2.putText(frame, phase_label, (14, 62),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, phase_color, 1, cv2.LINE_AA)

    # Elbow angle arc visualization
    if 12 in pts and 14 in pts and 16 in pts:
        from biomechanics import joint_angle
        angle = joint_angle(landmarks[12], landmarks[14], landmarks[16])
        cv2.putText(frame, f"{int(angle)}°", (pts[14][0] + 10, pts[14][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)

    # Wrist velocity meter
    vel = min(analyzer.chain.wrist.velocity / 0.08, 1.0)
    bx, by, bw_bar, bh_bar = w - 130, 14, 110, 14
    cv2.rectangle(frame, (bx, by), (bx + bw_bar, by + bh_bar), (50, 50, 50), -1)
    fill = int(bw_bar * vel)
    cv2.rectangle(frame, (bx, by), (bx + fill, by + bh_bar), (0, 255, 200), -1)
    cv2.rectangle(frame, (bx, by), (bx + bw_bar, by + bh_bar), (100, 100, 100), 1)
    cv2.putText(frame, "Velocity", (bx, by - 3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (170, 170, 170), 1, cv2.LINE_AA)

    # Kinetic chain indicator
    chain = analyzer.chain
    if chain.chain_sequence_correct:
        cv2.putText(frame, "CHAIN OK", (w - 130, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1, cv2.LINE_AA)
    else:
        cv2.putText(frame, "CHAIN BREAK", (w - 130, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)


# ── WebSocket streaming ────────────────────────────────────────────────

async def _stream(ws):
    loop = asyncio.get_event_loop()

    # MediaPipe
    model_path = os.path.join(os.path.dirname(__file__), "..", "ai_rally", "models", "pose_landmarker_lite.task")
    if not os.path.isfile(model_path):
        model_path = os.path.join(os.path.dirname(__file__), "models", "pose_landmarker_lite.task")
    pose = PoseLandmarker.create_from_options(PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ))

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    analyzer = SwingAnalyzer()
    frame_ts = 0

    # Camera check
    ok, test = cap.read()
    if not ok:
        await ws.send(json.dumps({
            "error": "Camera not available. Grant camera access in System Settings → Privacy & Security → Camera, then restart."
        }))
        cap.release()
        pose.close()
        return

    try:
        while True:
            t0 = time.monotonic()

            def _process():
                nonlocal frame_ts
                ret, frame = cap.read()
                if not ret:
                    return None, None, None
                frame = cv2.resize(frame, (FRAME_W, FRAME_H))
                frame = cv2.flip(frame, 1)

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                frame_ts += 33
                result = pose.detect_for_video(mp_img, frame_ts)

                landmarks = None
                if result.pose_landmarks and len(result.pose_landmarks) > 0:
                    landmarks = [_LandmarkProxy(lm) for lm in result.pose_landmarks[0]]

                state = {}
                if landmarks:
                    state = analyzer.update(landmarks)

                _draw_overlays(frame, landmarks, analyzer)
                return frame, landmarks, state

            frame, landmarks, state = await loop.run_in_executor(None, _process)

            if frame is None:
                await asyncio.sleep(0.033)
                continue

            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            await ws.send(buf.tobytes())
            await ws.send(json.dumps(state or {"calibrated": False, "calibrationProgress": 0}))

            elapsed = time.monotonic() - t0
            await asyncio.sleep(max(0, 1 / TARGET_FPS - elapsed))

    finally:
        cap.release()
        pose.close()


async def _handler(ws):
    game_task = None

    async def _listen():
        async for raw in ws:
            try:
                msg = json.loads(raw)
                if msg.get("action") == "reset" and game_task:
                    game_task.cancel()
            except (json.JSONDecodeError, TypeError):
                pass

    listener = asyncio.create_task(_listen())

    while True:
        game_task = asyncio.create_task(_stream(ws))
        try:
            await game_task
        except asyncio.CancelledError:
            continue
        except websockets.exceptions.ConnectionClosed:
            break
        else:
            break

    listener.cancel()


def _kill_stale(port: int):
    try:
        pids = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
        for pid in pids.split("\n"):
            pid = pid.strip()
            if pid and pid != str(os.getpid()):
                os.kill(int(pid), 9)
        time.sleep(0.5)
    except (subprocess.CalledProcessError, ProcessLookupError):
        pass


async def main():
    _kill_stale(WS_PORT)
    print(f"Stroke Analysis CV server → ws://{WS_HOST}:{WS_PORT}")
    async with websockets.serve(_handler, WS_HOST, WS_PORT, max_size=2**22, ping_interval=20, ping_timeout=60):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
