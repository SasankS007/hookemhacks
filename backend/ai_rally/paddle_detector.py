"""
YOLO-based paddle detector — loads models/paddle.pt if present.

On startup, prints model.names and checks for a 'paddle' class.
If paddle.pt is missing or contains no paddle class, self.valid is False
and cv_engine.py should fall back to the HSV detector.
"""

import os
import threading
from queue import Queue, Empty
from typing import List, Tuple

_DIR = os.path.dirname(os.path.abspath(__file__))
_PADDLE_PT = os.path.join(_DIR, "models", "paddle.pt")

Box = Tuple[int, int, int, int]


class PaddleDetector:
    def __init__(self) -> None:
        self.valid = False
        self.latest_boxes: List[Box] = []
        self._paddle_ids: set = set()

        if not os.path.isfile(_PADDLE_PT):
            print(f"[PaddleDetector] WARNING: {_PADDLE_PT} not found — falling back to HSV")
            return

        from ultralytics import YOLO
        self._model = YOLO(_PADDLE_PT)

        names = getattr(self._model, "names", {})
        print(f"[PaddleDetector] model.names = {names}")

        self._paddle_ids = {
            cid for cid, name in names.items()
            if "paddle" in name.lower()
        }

        if not self._paddle_ids:
            print("[PaddleDetector] WARNING: no 'paddle' class in model — falling back to HSV")
            return

        self.valid = True
        print(f"[PaddleDetector] paddle class IDs: {self._paddle_ids}")

        self._in_q: Queue = Queue(maxsize=2)
        self._out_q: Queue = Queue(maxsize=2)
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def enqueue(self, frame) -> None:
        if not self.valid:
            return
        if not self._in_q.full():
            self._in_q.put_nowait(frame.copy())

    def drain(self) -> List[Box]:
        if not self.valid:
            return []
        try:
            while True:
                self.latest_boxes = self._out_q.get_nowait()
        except Empty:
            pass
        return self.latest_boxes

    def stop(self) -> None:
        if self.valid:
            self._in_q.put(None)

    def _worker(self) -> None:
        while True:
            item = self._in_q.get()
            if item is None:
                break
            results = self._model(item, verbose=False, conf=0.3)
            boxes: List[Box] = []
            for r in results:
                for b in r.boxes:
                    if int(b.cls[0]) in self._paddle_ids:
                        boxes.append(tuple(map(int, b.xyxy[0].tolist())))
            while not self._out_q.empty():
                try:
                    self._out_q.get_nowait()
                except Empty:
                    break
            self._out_q.put(boxes)
