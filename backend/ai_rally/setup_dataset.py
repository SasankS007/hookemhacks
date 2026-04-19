"""
Pull the Roboflow pickleball-paddle-detection dataset, validate it
contains a 'paddle' class, and train YOLOv8n → models/paddle.pt.

Usage:
    python3 setup_dataset.py

Reads ROBOFLOW_API_KEY from the project-root .env.local.
"""

import os
import shutil
import sys
import yaml
from pathlib import Path


_DIR = Path(__file__).resolve().parent
_MODELS_DIR = _DIR / "models"
_DATASET_DIR = _DIR / "dataset"
_OUTPUT_PT = _MODELS_DIR / "paddle.pt"

_RF_WORKSPACE = "roboflow-universe-projects"
_RF_PROJECT = "pickleball-paddle-detection"
_RF_VERSION = 1


def _load_dotenv() -> None:
    env_path = _DIR.parent.parent / ".env.local"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    _load_dotenv()

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        print("ERROR: ROBOFLOW_API_KEY not found.")
        print("  Add it to .env.local at the project root,")
        print("  or export it:  export ROBOFLOW_API_KEY=your_key")
        sys.exit(1)

    from roboflow import Roboflow
    from ultralytics import YOLO

    # ── 1. Pull dataset ─────────────────────────────────────────────────
    print(f"Connecting to Roboflow → {_RF_WORKSPACE}/{_RF_PROJECT} v{_RF_VERSION}")
    rf = Roboflow(api_key=api_key)
    project = rf.workspace(_RF_WORKSPACE).project(_RF_PROJECT)
    dataset = project.version(_RF_VERSION).download(
        "yolov8", location=str(_DATASET_DIR)
    )
    print(f"Dataset saved to {dataset.location}")

    # ── 2. Validate data.yaml contains 'paddle' ─────────────────────────
    data_yaml = Path(dataset.location) / "data.yaml"
    if not data_yaml.is_file():
        raise RuntimeError(
            f"data.yaml not found at {data_yaml}. "
            "Check Roboflow API key and dataset slug"
        )

    with open(data_yaml) as f:
        cfg = yaml.safe_load(f)

    names = cfg.get("names", [])
    if isinstance(names, dict):
        names = list(names.values())
    names_lower = [n.lower() for n in names]

    if "paddle" not in names_lower:
        raise RuntimeError(
            f"data.yaml classes are {names} — no 'paddle' found. "
            "Check Roboflow API key and dataset slug"
        )

    print(f"Validated: data.yaml contains classes {names}")

    # ── 3. Train ─────────────────────────────────────────────────────────
    print("Training YOLOv8n on paddle dataset (50 epochs, imgsz=640)…")
    model = YOLO("yolov8n.pt")
    model.train(
        data=str(data_yaml),
        epochs=50,
        imgsz=640,
        batch=16,
        project=str(_DIR / "runs"),
        name="paddle_train",
    )

    best = _DIR / "runs" / "paddle_train" / "weights" / "best.pt"
    if not best.is_file():
        print("ERROR: best.pt not produced — training failed.")
        sys.exit(1)

    _MODELS_DIR.mkdir(exist_ok=True)
    shutil.copy2(best, _OUTPUT_PT)
    print(f"Trained model saved → {_OUTPUT_PT}")


if __name__ == "__main__":
    main()
