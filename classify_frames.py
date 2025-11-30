#!/usr/bin/env python3
"""Classify extracted frames with the TrapperAI YOLOv8 model."""

import argparse
import concurrent.futures as futures
import csv
import os
import threading
from pathlib import Path
from typing import List, Sequence, Tuple

import cv2
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from ultralytics import YOLO
from tqdm import tqdm

MODEL_REPO = "OSCF/TrapperAI-v02.2024"
MODEL_FILENAME = "TrapperAI-v02.2024-YOLOv8-m.pt"

# Canonical model labels (normalized). Anything else becomes "other".
LABEL_MAP = {
    "bird": "bird",
    "cat": "cat",
    "chamois": "chamois",
    "dog": "dog",
    "eurasian lynx": "eurasian_lynx",
    "eurasian red squirrel": "eurasian_red_squirrel",
    "european badger": "european_badger",
    "european mouflon": "european_mouflon",
    "fallow deer": "deer",
    "gray wolf": "gray_wolf",
    "hare": "hare",
    "marten": "marten",
    "moose": "moose",
    "red deer": "deer",
    "red fox": "red_fox",
    "reindeer": "reindeer",
    "roe deer": "deer",
    "wild boar": "wild_boar",
}

_MODEL = None
_MODEL_LOCK = threading.Lock()
_PREDICT_LOCK = threading.Lock()  # Ultralytics predictor is not thread-safe for setup/fuse
_WARMED_UP = False


def normalize_label(raw_label: str) -> str:
    return raw_label.replace("_", " ").replace("-", " ").strip().lower()


def ensure_model_path() -> str:
    local_path = Path(MODEL_FILENAME)
    if local_path.exists():
        return str(local_path)
    return hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILENAME)


def load_model(device: str):
    global _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            model_path = ensure_model_path()
            _MODEL = YOLO(model_path).to(device)
    return _MODEL


def map_label(raw_label: str) -> str:
    normalized = normalize_label(raw_label)
    return LABEL_MAP.get(normalized, "other")


def summarize_labels(labels: Sequence[str]) -> Tuple[str, bool]:
    if not labels:
        return "other", False
    unique = set(labels)
    majority = max(unique, key=labels.count)
    return majority, len(unique) > 1


def predict_frame(frame_path: Path, device: str) -> Tuple[str, str, bool]:
    img = cv2.imread(str(frame_path))
    if img is None:
        return frame_path.name, "other", False

    model = load_model(device)
    # Guard predictor setup/fuse with a lock to avoid race conditions in threads.
    with _PREDICT_LOCK:
        results = model.predict(img, device=device, verbose=False)

    labels: List[str] = []
    for res in results:
        names = res.names
        for box in res.boxes:
            cls_idx = int(box.cls.item())
            raw_label = names[cls_idx]
            labels.append(map_label(raw_label))

    animal, multiple = summarize_labels(labels)
    return frame_path.name, animal, multiple


def find_frames(frames_dir: Path) -> List[Path]:
    frames: List[Path] = []
    for pattern in ("*.jpg", "*.jpeg", "*.png"):
        frames.extend(sorted(frames_dir.glob(pattern)))
    return frames


def parse_args():
    parser = argparse.ArgumentParser(description="Classify frames with the TrapperAI model.")
    parser.add_argument("--frames_dir", required=True, help="Directory containing extracted frames.")
    parser.add_argument(
        "--csv_output_dir",
        default=None,
        help="Directory to write animal_predictions.csv (defaults to sibling 'detection_csvs').",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(4, os.cpu_count() or 1)),
        help="Number of frames to process in parallel.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    frames_dir = Path(args.frames_dir)
    default_out = frames_dir.parent / "detection_csvs"
    output_dir = Path(args.csv_output_dir) if args.csv_output_dir else default_out
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = find_frames(frames_dir)
    if not frames:
        raise SystemExit(f"No frames found in {frames_dir}")

    device = "mps" if torch.backends.mps.is_available() else "cpu"

    rows: List[Tuple[str, str, bool]] = []
    with futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {executor.submit(predict_frame, frame, device): frame for frame in frames}
        for future in tqdm(futures.as_completed(future_map), total=len(future_map), desc="Classifying frames"):
            rows.append(future.result())

    out_path = output_dir/"animal_predictions.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "animal", "multiple_animals"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
