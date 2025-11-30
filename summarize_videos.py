#!/usr/bin/env python3
"""Summarize per-video animals from frame-level predictions.

Reads a frame-level CSV (animal_predictions.csv) and writes animals_in_videos.csv
with unique animals per video and a multiple_animals flag.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set


def parse_args():
    parser = argparse.ArgumentParser(
        description="Aggregate frame predictions into per-video animal lists.")
    parser.add_argument(
        "--input_csv",
        default=None,
        help="Path to animal_predictions.csv (defaults to detection_csvs/animal_predictions.csv).",
    )
    parser.add_argument(
        "--output_csv",
        default=None,
        help="Path to write animals_in_videos.csv (defaults to detection_csvs/animals_in_videos.csv).",
    )
    return parser.parse_args()


def video_name_from_frame(frame_filename: str) -> str:
    stem = Path(frame_filename).stem  # drop extension
    if "_frame_" in stem:
        return stem.split("_frame_", 1)[0]
    return stem


def normalize_animal(name: str) -> str:
    return name.replace(" ", "_")


def load_predictions(csv_path: Path) -> Dict[str, List[str]]:
    per_video: Dict[str, List[str]] = defaultdict(list)
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            frame_file = row.get("filename", "")
            animal = row.get("animal", "")
            video = video_name_from_frame(frame_file)
            per_video[video].append(animal)
    return per_video


def aggregate(per_video: Dict[str, List[str]]):
    rows = []
    for video, animals in per_video.items():
        uniq: Set[str] = set(a for a in animals if a)
        unique_animals_str = "&".join(sorted(normalize_animal(a) for a in uniq)) if uniq else ""
        rows.append(
            {
                "video_title": video,
                "unique_animals": unique_animals_str,
                "multiple_animals": str(len(uniq) > 1).lower(),
            }
        )
    return rows


def write_output(rows: Iterable[Dict[str, str]], out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["video_title", "unique_animals", "multiple_animals"]
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    default_dir = Path("detection_csvs")
    input_csv = Path(args.input_csv) if args.input_csv else default_dir / "animal_predictions.csv"
    output_csv = Path(args.output_csv) if args.output_csv else default_dir / "animals_in_videos.csv"

    if not input_csv.exists():
        raise SystemExit(f"Input CSV not found: {input_csv}")

    per_video = load_predictions(input_csv)
    rows = aggregate(per_video)
    write_output(rows, output_csv)
    print(f"Wrote {len(rows)} rows to {output_csv}")


if __name__ == "__main__":
    main()
