import os
import sys
import subprocess

from fastapi import APIRouter

router = APIRouter()

_cv_process: subprocess.Popen | None = None


def _kill_port(port: int):
    """Best-effort cleanup of anything occupying the given port."""
    try:
        pids = subprocess.check_output(
            ["lsof", "-ti", f":{port}"], text=True
        ).strip()
        for pid in pids.split("\n"):
            pid = pid.strip()
            if pid:
                os.kill(int(pid), 9)
    except (subprocess.CalledProcessError, ProcessLookupError, ValueError):
        pass


@router.post("/launch-cv")
async def launch_cv_game():
    """Spawn the AI Rally CV WebSocket server as a subprocess."""
    global _cv_process

    if _cv_process is not None and _cv_process.poll() is None:
        return {"status": "already_running", "ws_url": "ws://localhost:8765"}

    _kill_port(8765)

    server_script = os.path.join(
        os.path.dirname(__file__), "..", "ai_rally", "server.py"
    )
    _cv_process = subprocess.Popen(
        [sys.executable, server_script],
        cwd=os.path.join(os.path.dirname(__file__), "..", "ai_rally"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {
        "status": "launched",
        "pid": _cv_process.pid,
        "ws_url": "ws://localhost:8765",
    }


@router.post("/stop-cv")
async def stop_cv_game():
    """Terminate the running CV server subprocess."""
    global _cv_process

    if _cv_process is not None and _cv_process.poll() is None:
        _cv_process.terminate()
        _cv_process.wait(timeout=5)
        _cv_process = None
        return {"status": "stopped"}

    _cv_process = None
    return {"status": "not_running"}


@router.get("/cv-status")
async def cv_status():
    """Check whether the CV server subprocess is alive."""
    running = _cv_process is not None and _cv_process.poll() is None
    return {"running": running}


@router.get("/leaderboard")
async def get_leaderboard():
    return {
        "leaderboard": [
            {"rank": 1, "player": "Player1", "wins": 42, "losses": 12},
            {"rank": 2, "player": "Player2", "wins": 38, "losses": 15},
            {"rank": 3, "player": "Player3", "wins": 31, "losses": 20},
        ]
    }


@router.post("/result")
async def submit_result():
    return {
        "status": "recorded",
        "message": "Game result saved successfully.",
    }


@router.get("/stats")
async def get_rally_stats():
    return {
        "total_games": 24,
        "wins": 16,
        "losses": 8,
        "win_rate": 66.7,
        "avg_score": 9.2,
        "best_streak": 5,
    }
