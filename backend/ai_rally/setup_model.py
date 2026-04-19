"""
Download YOLOv8n and optionally fine-tune on a Roboflow paddle dataset.

Usage:
    python3 setup_model.py              # downloads base YOLOv8n (works immediately)
    python3 setup_model.py --finetune   # also pulls Roboflow dataset + trains

Reads ROBOFLOW_API_KEY from the project-root .env.local (gitignored).

The base model detects COCO objects. For paddle-specific detection, add annotated
images to your Roboflow project ("hookemhacks" in sasanks-workspace), generate a
version, then re-run with --finetune.
"""

import os
import shutil
import sys
from pathlib import Path


def _load_dotenv():
    """Load keys from the project-root .env.local so they never need exporting."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env.local"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def download_base_model():
    """Download the base YOLOv8n weights (COCO pre-trained)."""
    from ultralytics import YOLO

    print("Downloading YOLOv8n base model...")
    model = YOLO("yolov8n.pt")
    print(f"Base model ready: {model.ckpt_path}")
    return model


def finetune():
    """Pull dataset from Roboflow and fine-tune YOLOv8n."""
    _load_dotenv()

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        print("ERROR: ROBOFLOW_API_KEY not found.\n")
        print("  Either add it to .env.local at the project root,")
        print("  or export it:  export ROBOFLOW_API_KEY=your_key")
        sys.exit(1)

    project_name = os.environ.get("ROBOFLOW_PROJECT", "hookemhacks")
    version_num = int(os.environ.get("ROBOFLOW_VERSION", "1"))

    from roboflow import Roboflow
    from ultralytics import YOLO

    print(f"Connecting to Roboflow (project={project_name}, v{version_num})...")
    rf = Roboflow(api_key=api_key)
    workspace = rf.workspace()
    project = workspace.project(project_name)

    versions = list(project.versions())
    if not versions:
        print("\nNo dataset versions found in your Roboflow project.")
        print("To fine-tune:")
        print("  1. Upload & annotate paddle images at https://app.roboflow.com")
        print("  2. Generate a dataset version")
        print("  3. Re-run: python3 setup_model.py --finetune")
        print("\nThe base YOLOv8n model + MediaPipe wrist fallback will work in the meantime.")
        sys.exit(0)

    dataset = project.version(version_num).download("yolov8", location="./dataset")
    print(f"Dataset downloaded to {dataset.location}")

    print("Starting fine-tuning YOLOv8n...")
    model = YOLO("yolov8n.pt")
    model.train(
        data=os.path.join(dataset.location, "data.yaml"),
        epochs=50,
        imgsz=640,
        batch=16,
        project="./runs",
        name="paddle_detector",
    )

    best = os.path.join("runs", "paddle_detector", "weights", "best.pt")
    if os.path.isfile(best):
        dest = os.path.join(os.path.dirname(__file__), "paddle_model.pt")
        shutil.copy2(best, dest)
        print(f"Trained model saved → {dest}")
    else:
        print("WARNING: best.pt not found — training may have failed.")
        sys.exit(1)


def main():
    _load_dotenv()

    if "--finetune" in sys.argv:
        finetune()
    else:
        download_base_model()
        print("\nBase model downloaded. The CV game will use MediaPipe wrist")
        print("tracking as a fallback for paddle position until you fine-tune.")
        print("\nTo fine-tune on your own dataset:")
        print("  python3 setup_model.py --finetune")


if __name__ == "__main__":
    main()
