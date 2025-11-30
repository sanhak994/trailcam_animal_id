#!/usr/bin/env python3
"""Review clips with overlayed animal predictions and simple controls.

- Loads per-video predictions from detection_csvs/animals_in_videos.csv (configurable).
- Plays clips from a clips directory (default ./clips), overlaying unique_animals and multiple_animals.
- Key controls: n=next, p=previous, space=pause/resume, d=delete clip, q=quit.
"""

import argparse
import csv
import math
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from send2trash import send2trash


def parse_args():
    parser = argparse.ArgumentParser(description="Review clips with animal overlays.")
    parser.add_argument(
        "--csv_path",
        default="./detection_csvs/animals_in_videos.csv",
        help="Path to animals_in_videos.csv.",
    )
    parser.add_argument(
        "--animal_predictions_csv",
        default="./detection_csvs/animal_predictions.csv",
        help="Path to frame-level animal_predictions.csv (to list available animals).",
    )
    parser.add_argument(
        "--clips_dir",
        default="clips",
        help="Directory containing video clips.",
    )
    parser.add_argument(
        "--exts",
        default=".mp4,.MP4,.mov,.MOV",
        help="Comma-separated video extensions to search for.",
    )
    parser.add_argument(
        "--play_rate",
        type=float,
        default=4.0,
        help="Playback speed multiplier (e.g., 4.0 plays at 4x).",
    )
    parser.add_argument(
        "--clip_pause_seconds",
        type=float,
        default=2.0,
        help="Pause after each clip ends to decide on delete/next (seconds).",
    )
    parser.add_argument(
        "--include_animals",
        default="",
        help="Comma-separated animals to include; others are skipped. Empty means include all.",
    )
    parser.add_argument(
        "--auto_delete_animals",
        default="",
        help="Comma-separated animals to auto-delete clips for (match against unique_animals).",
    )
    return parser.parse_args()


def load_annotations(csv_path: Path) -> Dict[str, Tuple[str, bool]]:
    ann: Dict[str, Tuple[str, bool]] = {}
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("video_title", "").strip()
            unique_animals = row.get("unique_animals", "").strip()
            multiple_animals = row.get("multiple_animals", "false").strip().lower() == "true"
            if title:
                ann[title] = (unique_animals, multiple_animals)
    return ann


def find_clip(title: str, clips_dir: Path, exts: List[str]) -> Optional[Path]:
    for ext in exts:
        candidate = clips_dir / f"{title}{ext}"
        if candidate.exists():
            return candidate
    return None


def overlay_frame(
    frame,
    lines: List[str],
    start_y: int = 30,
    line_step: int = 32,
    font_scale: float = 0.8,
    thickness: int = 2,
):
    y = start_y
    for line in lines:
        cv2.putText(frame, line, (20, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
        y += line_step


def play_clip(path: Path, unique_animals: str, multiple: bool, play_rate: float, pause_seconds: float) -> str:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        print(f"Could not open {path}")
        return "next"

    cv2.namedWindow("clip", cv2.WINDOW_NORMAL)
    paused = False
    action = "next"
    user_input = False
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    # Show frames at base FPS, but drop/skips frames proportional to play_rate.
    delay = max(1, int(1000 / fps))
    frame_step = max(1, int(math.ceil(play_rate)))  # e.g., 2x -> show every other frame
    last_raw_frame = None

    overlay_lines = [
        f"file: {path.name}",
        f"unique_animals: {unique_animals or 'none'}",
        f"multiple_animals: {multiple}",
        "n=next p=prev space=pause d=delete q=quit",
    ]

    while True:
        if not paused:
            ok, frame = cap.read()
            if not ok:
                break
            # Skip extra frames to accelerate playback.
            for _ in range(frame_step - 1):
                cap.grab()
            last_raw_frame = frame.copy()
        elif last_raw_frame is None:
            ok, frame = cap.read()
            if not ok:
                break
            last_raw_frame = frame.copy()

        if last_raw_frame is None:
            break

        frame_copy = last_raw_frame.copy()
        overlay_frame(frame_copy, overlay_lines)
        cv2.imshow("clip", frame_copy)
        key = cv2.waitKey(delay if not paused else 100) & 0xFF

        if key == ord("q"):
            action = "quit"
            user_input = True
            break
        if key == ord("n"):
            action = "next"
            user_input = True
            break
        if key == ord("p"):
            action = "prev"
            user_input = True
            break
        if key == ord("d"):
            action = "delete"
            user_input = True
            break
        if key == ord(" "):
            paused = not paused

    cap.release()

    # If user already chose an action, return immediately.
    if user_input:
        return action

    # Post-clip pause to let user choose next action.
    end_overlay = (
        np.zeros_like(last_raw_frame) if last_raw_frame is not None else np.zeros((360, 640, 3), dtype=np.uint8)
    )
    end_lines = [
        f"file: {path.name}",
        f"unique_animals: {unique_animals or 'none'}",
        f"multiple_animals: {multiple}",
        f"clip ended - waiting {pause_seconds:.1f}s",
        "n=next  p=prev  d=delete  q=quit",
    ]
    overlay_frame(
        end_overlay,
        end_lines,
        start_y=50,
        line_step=42,
        font_scale=1.1,
        thickness=2,
    )
    cv2.imshow("clip", end_overlay)
    action_after = None
    deadline = time.monotonic() + max(0.0, pause_seconds)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        wait_ms = int(min(100, max(1, remaining * 1000)))
        key = cv2.waitKey(wait_ms) & 0xFF
        if key == ord("q"):
            action_after = "quit"
            break
        if key == ord("n"):
            action_after = "next"
            break
        if key == ord("p"):
            action_after = "prev"
            break
        if key == ord("d"):
            action_after = "delete"
            break

    if action_after:
        action = action_after

    return action


def load_available_animals(pred_csv: Path) -> List[str]:
    animals: List[str] = []
    if not pred_csv.exists():
        return animals
    with pred_csv.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            a = row.get("animal", "").strip()
            if a and a not in animals:
                animals.append(a)
    return animals


def parse_filter_list(val: str) -> List[str]:
    return [x.strip() for x in val.split(",") if x.strip()]


def main():
    args = parse_args()
    csv_path = Path(args.csv_path)
    animal_pred_csv = Path(args.animal_predictions_csv)
    clips_dir = Path(args.clips_dir)
    exts = [e for e in args.exts.split(",") if e]
    include_animals = set(parse_filter_list(args.include_animals))
    auto_delete_animals = set(parse_filter_list(args.auto_delete_animals))

    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")
    if not clips_dir.exists():
        raise SystemExit(f"Clips dir not found: {clips_dir}")

    annotations = load_annotations(csv_path)
    ordered_titles = sorted(annotations.keys())
    available_animals = load_available_animals(animal_pred_csv)
    if available_animals:
        print("Available animals from predictions:", ", ".join(available_animals))

    clips: List[Tuple[Path, str, bool]] = []
    for title in ordered_titles:
        clip_path = find_clip(title, clips_dir, exts)
        if clip_path:
            unique_animals, multiple = annotations[title]
            animal_list = [a for a in unique_animals.split("_") if a]
            animal_set = set(animal_list)
            if include_animals and not (animal_set & include_animals):
                continue
            if auto_delete_animals and len(animal_set) == 1 and (animal_set & auto_delete_animals):
                try:
                    send2trash(clip_path)
                    print(f"Auto-trashed {clip_path} (matched auto-delete animals and single-species clip)")
                except OSError as e:
                    print(f"Failed auto-delete {clip_path}: {e}")
                continue
            clips.append((clip_path, unique_animals, multiple))
        else:
            print(f"Warning: no clip found for {title}")

    if not clips:
        raise SystemExit("No matching clips found.")

    idx = 0
    while 0 <= idx < len(clips):
        clip_path, unique_animals, multiple = clips[idx]
        action = play_clip(clip_path, unique_animals, multiple, args.play_rate, args.clip_pause_seconds)

        if action == "quit":
            break
        if action == "delete":
            try:
                send2trash(clip_path)
                print(f"Trashed {clip_path}")
                clips.pop(idx)
                if idx >= len(clips):
                    idx = len(clips) - 1
            except OSError as e:
                print(f"Failed to delete {clip_path}: {e}")
                idx += 1
            continue
        if action == "prev":
            idx = max(0, idx - 1)
            continue
        # default next
        idx += 1

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
