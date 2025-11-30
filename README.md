# Trailcam Animal ID Pipeline

A way to quickly id animals on trailcam footage and review clips with annotations. I am using [Trapper AI](https://huggingface.co/OSCF/TrapperAI-v02.2024), which is trained on European wildlife, but I find the model still works to roughly id some North American animals. I find the model to be effective for my primary purpose of filtering out footage of Deer from the thousands of clips collected by my trailcam. 

## Setup
- Python 3.9+ (tested on Apple Silicon). Example setup:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  python3 -m pip install -r requirements.txt
  ```

## Running the pipeline
Use `run_pipeline.py` to execute all steps (extract frames → classify → summarize). Defaults expect clips in `./clips`, frames in a sibling `./frames`, and CSVs in `./detection_csvs`.

Example (copy/paste):
```bash
python3 run_pipeline.py \
  --clips_dir clips \
  --frames_per_clip 4 \
  --frames_workers 4 \
  --classify_workers 4 \
  --exts .mp4,.MP4 \
  --force
```
- Add `--force` to regenerate frames/CSVs even if they already exist.

## Script breakdown (intended order)
1) `extract_frames.py` – samples evenly spaced frames from each MP4/MOV into a frames directory. 
  - Args: 
    - `--input_dir` (clips)
    - `--output_dir` (default sibling `frames`)
    - `--frames_per_clip` (default 4)
    - `--workers` (parallel extraction)
    - `--exts` (comma-separated patterns, default `.mp4,.MP4`)
2) `classify_frames.py` – runs the TrapperAI YOLOv8 model on frames; writes `animal_predictions.csv` in `detection_csvs` (sibling to frames) by default. 
  - Args: 
    - `--frames_dir` (where extracted frames live)
    - `--csv_output_dir` (default sibling `detection_csvs`)
    - `--workers` (parallel frame inference)
3) `summarize_videos.py` – aggregates frame predictions into `animals_in_videos.csv` (per-clip unique animals and multi-animal flag). 
  - Args: 
    - `--input_csv` (frame-level)
    - `--output_csv` (summary)
4) `review_clips.py` – interactive reviewer; overlays labels, supports filtering, auto-delete (single-species only), play-rate control, and Trash-safe deletions. 
  - Args: 
    - `--csv_path` (per-video summary)
    - `--animal_predictions_csv` (frame-level, to show available animals)
    - `--clips_dir`
    - `--exts` (video extensions)
    - `--play_rate` (frame-skipping speedup; higher = faster playback)
    - `--clip_pause_seconds` (pause at end of clip only if no key was pressed)
    - `--include_animals` (comma list; only show clips containing at least one)
    - `--auto_delete_animals` (comma list; auto-trash clips when single-species and matching one of these)
5) `run_pipeline.py` – orchestrates steps 1–3 and skips completed steps unless `--force` is set.

## Notes and sources
- Model: TrapperAI v02.2024 YOLOv8 from OSCF on [Hugging Face](https://huggingface.co/OSCF/TrapperAI-v02.2024) (`OSCF/TrapperAI-v02.2024`).
