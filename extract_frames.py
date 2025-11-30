#!/usr/bin/env python3
"""Extract evenly spaced frames from MP4 clips."""

import argparse
import concurrent.futures as futures
import os
from pathlib import Path
from typing import List

import cv2
from tqdm import tqdm


def extract_even_frames(video_path: Path, frames_per_clip: int, output_dir: Path) -> List[Path]:
    """Grab evenly spaced frames from a video and write them to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return saved

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total_frames <= 0 or frames_per_clip <= 0:
        cap.release()
        return saved

    step = max(1, total_frames // frames_per_clip)
    positions = [min(total_frames - 1, i * step) for i in range(frames_per_clip)]

    for idx, pos in enumerate(positions, start=1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ok, frame = cap.read()
        if not ok:
            continue
        out_path = output_dir/f"{video_path.stem}_frame_{idx}.jpg"
        cv2.imwrite(str(out_path), frame)
        saved.append(out_path)

    cap.release()
    return saved


def find_videos(input_dir: Path, patterns: List[str]) -> List[Path]:
    videos: List[Path] = []
    for pattern in patterns:
        videos.extend(sorted(input_dir.glob(pattern)))
    return videos


def parse_args():
    parser = argparse.ArgumentParser(description="Extract evenly spaced frames from MP4 clips.")
    parser.add_argument("--input_dir", required=True, help="Directory containing MP4 clips.")
    parser.add_argument(
        "--output_dir",
        default=None,
        help="Directory to write extracted frames (defaults to <input_dir>/../frames).",
    )
    parser.add_argument(
        "--frames_per_clip",
        type=int,
        default=4,
        help="Number of frames to sample per clip.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(4, os.cpu_count() or 1)),
        help="Number of clips to process in parallel.",
    )
    parser.add_argument(
        "--exts",
        default=".mp4,.MP4",
        help="Comma-separated glob patterns for videos (default .mp4,.MP4).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    default_out = input_dir.parent / "frames"
    output_dir = Path(args.output_dir or default_out)
    output_dir.mkdir(parents=True, exist_ok=True)

    patterns = [f"*{ext.strip()}" if not ext.strip().startswith("*") else ext.strip() for ext in args.exts.split(",") if ext.strip()]
    if not patterns:
        patterns = ["*.mp4", "*.MP4"]

    videos = find_videos(input_dir, patterns)
    if not videos:
        raise SystemExit(f"No video files matching {patterns} found in {input_dir}")

    with futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures_list = [
            executor.submit(extract_even_frames, video, args.frames_per_clip, output_dir)
            for video in videos
        ]
        for _ in tqdm(futures.as_completed(futures_list), total=len(futures_list), desc="Extracting frames"):
            pass

    print(f"Extracted frames for {len(videos)} clips into {output_dir}")


if __name__ == "__main__":
    main()
