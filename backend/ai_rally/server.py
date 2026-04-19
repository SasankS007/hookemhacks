"""
WebSocket server for the AI Rally CV game.

Streams combined JPEG frames (webcam left + Pygame court right) and
interleaved JSON game-state messages to connected browser clients.

Start:  python server.py
"""

import asyncio
import json
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np
import websockets

from cv_engine import CVEngine
from game import GameEngine

WS_HOST = "0.0.0.0"
WS_PORT = 8765
TARGET_FPS = 30

# Match CVEngine webcam frame (640×480) so camera + court panes are equal in the JPEG
PANEL_W, PANEL_H = 640, 480


async def _stream(ws, game: GameEngine):
    loop = asyncio.get_event_loop()
    cv_engine = CVEngine()

    test_frame, _, _ = await loop.run_in_executor(None, cv_engine.process_frame)
    if test_frame is None:
        await ws.send(json.dumps({
            "error": "Camera not available. On macOS, open System Settings -> Privacy & Security -> Camera and grant access to Terminal (or the app running Python). Then restart the CV server.",
        }))
        cv_engine.release()
        return

    try:
        while True:
            t0 = time.monotonic()

            frame, stroke, velocity = await loop.run_in_executor(
                None, cv_engine.process_frame
            )
            if frame is None:
                await asyncio.sleep(0.033)
                continue

            stroke = stroke or "READY"

            clf = cv_engine.classifier
            net_event = clf.last_net_event if stroke in ("FOREHAND", "BACKHAND") else False
            fo = clf.frame_output

            game.update(
                stroke,
                net_event=net_event,
                stroke_score=fo.get("score", 0),
                weakest_metric=min(fo.get("metrics", {"": 0}), key=lambda k: fo["metrics"].get(k, 1), default="") if fo.get("metrics") else "",
                stroke_phase=fo.get("phase", "READY"),
                wrist_dx=fo.get("wrist_dx", 0.0),
            )

            if stroke in ("FOREHAND", "BACKHAND") and clf._emitted:
                clf._reset_swing()

            court_rgb = await loop.run_in_executor(None, game.render)
            court_bgr = cv2.cvtColor(court_rgb, cv2.COLOR_RGB2BGR)

            court_panel = cv2.resize(court_bgr, (PANEL_W, PANEL_H))
            combined = np.hstack([frame, court_panel])

            _, buf = cv2.imencode(".jpg", combined, [cv2.IMWRITE_JPEG_QUALITY, 80])
            await ws.send(buf.tobytes())

            await ws.send(
                json.dumps({
                    "stroke": stroke,
                    "velocity": round(velocity or 0, 3),
                    "playerScore": game.player_score,
                    "aiScore": game.ai_score,
                    "gameOver": game.game_over,
                    "winner": game.winner,
                    "hitWindow": game.hit_window,
                    "rally": game.rally,
                    "netEvent": game.net_flash_active,
                    "strokeScore": fo.get("score", 0),
                    "returnProbability": fo.get("return_probability", 0),
                    "difficulty": game.difficulty,
                })
            )

            elapsed = time.monotonic() - t0
            await asyncio.sleep(max(0, 1 / TARGET_FPS - elapsed))

    finally:
        cv_engine.release()


async def _handler(ws):
    game = GameEngine()
    game_task: asyncio.Task | None = None

    async def _listen():
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            action = msg.get("action")
            if action == "reset" and game_task:
                game.reset()
                game_task.cancel()
            elif action == "set_difficulty":
                level = msg.get("level", "easy")
                game.set_difficulty(level)

    listener = asyncio.create_task(_listen())

    while True:
        game_task = asyncio.create_task(_stream(ws, game))
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
    import subprocess
    try:
        pids = subprocess.check_output(
            ["lsof", "-ti", f":{port}"], text=True
        ).strip()
        if pids:
            for pid in pids.split("\n"):
                pid = pid.strip()
                if pid and pid != str(os.getpid()):
                    os.kill(int(pid), 9)
                    print(f"Killed stale process {pid} on port {port}")
            import time; time.sleep(0.5)
    except (subprocess.CalledProcessError, ProcessLookupError):
        pass


async def main():
    _kill_stale(WS_PORT)
    print(f"AI Rally CV server -> ws://{WS_HOST}:{WS_PORT}")
    async with websockets.serve(
        _handler,
        WS_HOST,
        WS_PORT,
        max_size=2**22,
        ping_interval=20,
        ping_timeout=60,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
