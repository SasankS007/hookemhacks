import os
import sys
import subprocess

from fastapi import APIRouter

router = APIRouter()

_cv_process: subprocess.Popen | None = None


def _kill_port(port: int):
    try:
        pids = subprocess.check_output(
            ["lsof", "-ti", f":{port}"], text=True
        ).strip()
        for pid in pids.split("\n"):
            pid = pid.strip()
            if pid:
                os.kill(int(pid), 9)
        import time; time.sleep(0.5)
    except (subprocess.CalledProcessError, ProcessLookupError, ValueError):
        pass


@router.post("/launch-cv")
async def launch_stroke_cv():
    """Spawn the Stroke Analysis CV WebSocket server as a subprocess."""
    global _cv_process

    if _cv_process is not None and _cv_process.poll() is None:
        return {"status": "already_running", "ws_url": "ws://localhost:8766"}

    _kill_port(8766)

    server_script = os.path.join(
        os.path.dirname(__file__), "..", "stroke_analysis", "server.py"
    )
    _cv_process = subprocess.Popen(
        [sys.executable, server_script],
        cwd=os.path.join(os.path.dirname(__file__), "..", "stroke_analysis"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {
        "status": "launched",
        "pid": _cv_process.pid,
        "ws_url": "ws://localhost:8766",
    }


@router.post("/stop-cv")
async def stop_stroke_cv():
    """Terminate the running stroke analysis CV server."""
    global _cv_process

    if _cv_process is not None and _cv_process.poll() is None:
        _cv_process.terminate()
        _cv_process.wait(timeout=5)
        _cv_process = None
        return {"status": "stopped"}

    _cv_process = None
    return {"status": "not_running"}


@router.get("/cv-status")
async def stroke_cv_status():
    running = _cv_process is not None and _cv_process.poll() is None
    return {"running": running}


@router.get("/tips/{stroke_type}")
async def get_stroke_tips(stroke_type: str):
    return {"stroke_type": stroke_type, "tips": []}


@router.get("/scores/{stroke_type}")
async def get_stroke_scores(stroke_type: str):
    return {"stroke_type": stroke_type, "scores": {}}


@router.post("/analyze")
async def analyze_stroke():
    return {"status": "use_cv_mode"}
