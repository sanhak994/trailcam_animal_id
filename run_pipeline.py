#!/usr/bin/env python3
"""Run the full pipeline: extract frames -> classify -> summarize.

Skips steps if outputs already exist unless --force is set.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


def run_cmd(cmd: List[str]):
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        sys.exit(res.returncode)


def any_frames_exist(frames_dir: Path) -> bool:
    patterns = ["*.jpg", "*.jpeg", "*.png"]
    return any(frames_dir.glob(p) for p in patterns)


def parse_args():
    parser = argparse.ArgumentParser(description="Top-to-bottom pipeline runner.")
    parser.add_argument("--clips_dir", default="clips", help="Directory of input MP4/MOV clips.")
    parser.add_argument("--frames_dir", default=None, help="Directory to store extracted frames (defaults to sibling 'frames').")
    parser.add_argument("--detection_dir", default=None, help="Directory for CSV outputs (defaults to sibling 'detection_csvs').")
    parser.add_argument("--frames_per_clip", type=int, default=4, help="Frames to sample per clip.")
    parser.add_argument("--frames_workers", type=int, default=4, help="Workers for frame extraction.")
    parser.add_argument("--classify_workers", type=int, default=4, help="Workers for classification.")
    parser.add_argument("--exts", default=".mp4,.MP4", help="Comma-separated glob patterns for video files.")
    parser.add_argument("--force", action="store_true", help="Re-run all steps even if outputs exist.")
    return parser.parse_args()


def main():
    args = parse_args()
    clips_dir = Path(args.clips_dir)
    frames_dir = Path(args.frames_dir) if args.frames_dir else clips_dir.parent / "frames"
    detection_dir = Path(args.detection_dir) if args.detection_dir else frames_dir.parent / "detection_csvs"

    animal_csv = detection_dir / "animal_predictions.csv"
    summary_csv = detection_dir / "animals_in_videos.csv"

    # Step 1: extract frames
    if args.force or not any_frames_exist(frames_dir):
        run_cmd(
            [
                sys.executable,
                "extract_frames.py",
                "--input_dir",
                str(clips_dir),
                "--output_dir",
                str(frames_dir),
                "--frames_per_clip",
                str(args.frames_per_clip),
                "--workers",
                str(args.frames_workers),
                "--exts",
                args.exts,
            ]
        )
    else:
        print(f"Skipping frame extraction; frames already exist in {frames_dir}")

    # Step 2: classify frames
    if args.force or not animal_csv.exists():
        run_cmd(
            [
                sys.executable,
                "classify_frames.py",
                "--frames_dir",
                str(frames_dir),
                "--csv_output_dir",
                str(detection_dir),
                "--workers",
                str(args.classify_workers),
            ]
        )
    else:
        print(f"Skipping classification; found {animal_csv}")

    # Step 3: summarize videos
    if args.force or not summary_csv.exists():
        run_cmd(
            [
                sys.executable,
                "summarize_videos.py",
                "--input_csv",
                str(animal_csv),
                "--output_csv",
                str(summary_csv),
            ]
        )
    else:
        print(f"Skipping summary; found {summary_csv}")

    print("Pipeline complete.")


if __name__ == "__main__":
    main()
