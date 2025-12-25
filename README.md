# Trailcam Animal ID Pipeline

A way to quickly id animals on trailcam footage and review clips with annotations. I am using [Trapper AI](https://huggingface.co/OSCF/TrapperAI-v02.2024), which is trained on European wildlife, but I find the model still works to roughly id some North American animals. I find the model to be effective for my primary purpose of filtering out footage of Deer from the thousands of clips collected by my trailcam.

**Key Features:**
- Automated animal detection using state-of-the-art YOLOv8 model
- Professional video review interface with playback controls
- Batch processing of video clips with parallel workers
- Trash-safe deletion (recoverable)
- Session-based deletion confirmations for power users
- Dark mode interface optimized for video editing

---

## Getting Started

### Installation

Tested with macOS Sequoia 15.2 and Python 3.9+

```bash
# Clone the repository
git clone https://github.com/MoonMayne/trailcam_animal_id.git
cd trailcam_animal_id

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Launch the GUI application
python3 gui_app.py
```

The AI model (~250MB) will download automatically on first run from HuggingFace.

### Optional: Convenience Launcher

**For macOS/Linux (launch.sh):**
```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 gui_app.py
```
Make it executable: `chmod +x launch.sh`

**For Windows (launch.bat):**
```batch
@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python gui_app.py
```

---

## Individual Scripts

The application consists of 5 core processing scripts and a GUI frontend:

### 1. `extract_frames.py` - Frame Extraction
Samples evenly-spaced frames from video clips using OpenCV.

**Usage:**
```bash
python3 extract_frames.py \
  --input_dir clips \
  --output_dir frames \
  --frames_per_clip 4 \
  --workers 4 \
  --exts .mp4,.MP4
```

**What it does:**
- Processes videos in parallel using ThreadPoolExecutor
- Extracts N evenly-spaced frames per video
- Saves as JPG with naming: `{video_stem}_frame_{idx}.jpg`

---

### 2. `classify_frames.py` - AI Inference
Runs TrapperAI YOLOv8 model inference on extracted frames.

**Usage:**
```bash
python3 classify_frames.py \
  --frames_dir frames \
  --csv_output_dir detection_csvs \
  --workers 4
```

**What it does:**
- Downloads OSCF/TrapperAI-v02.2024 model from HuggingFace (first run)
- Uses Apple Metal Performance Shaders (MPS) on Apple Silicon
- Thread-safe model operations with locks
- Outputs: `detection_csvs/animal_predictions.csv`

**Model Details:**
- YOLOv8-m trained on European wildlife
- Works reasonably well for North American animals
- Label mapping consolidates species

---

### 3. `summarize_videos.py` - CSV Aggregation
Aggregates frame-level predictions into per-video summaries.

**Usage:**
```bash
python3 summarize_videos.py \
  --input_csv detection_csvs/animal_predictions.csv \
  --output_csv detection_csvs/animals_in_videos.csv
```

**What it does:**
- Groups predictions by video filename
- Identifies unique animals per video
- Flags videos with multiple species
- Outputs: `detection_csvs/animals_in_videos.csv`

---

### 4. `review_clips.py` - Terminal Reviewer (Legacy)
OpenCV-based CLI video reviewer with keyboard controls.

**Usage:**
```bash
python3 review_clips.py \
  --csv_path detection_csvs/animals_in_videos.csv \
  --animal_predictions_csv detection_csvs/animal_predictions.csv \
  --clips_dir clips \
  --play_rate 4.0 \
  --include_animals deer,fox
```

**Keyboard Controls:**
- `n` - next clip
- `p` - previous clip
- `space` - pause/resume
- `d` - delete (moves to Trash)
- `q` - quit

**Note:** The GUI app (`gui_app.py`) provides a superior experience and is recommended over this CLI tool.

---

### 5. `run_pipeline.py` - Orchestrator
Runs the full pipeline (extract → classify → summarize) with smart skipping.

**Usage:**
```bash
python3 run_pipeline.py \
  --clips_dir clips \
  --frames_per_clip 4 \
  --frames_workers 4 \
  --classify_workers 4 \
  --exts .mp4,.MP4,.mov,.MOV \
  --force  # Optional: regenerate even if outputs exist
```

**What it does:**
- Orchestrates steps 1-3 sequentially
- Smart skipping: only reprocesses if inputs changed
- Parallel processing with configurable workers
- Progress tracking with tqdm

---

### 6. `gui_app.py` - GUI Application (Main)
Professional desktop application for the complete workflow.

**Usage:**
```bash
python3 gui_app.py
```

**Features:**
- 3-step pipeline wizard
- Video review interface with playback controls
- Configurable playback speed and auto-advance
- Session-based deletion confirmations
- Advanced menu with cleanup and folder management
- Settings persistence across sessions

---

## Credits

### AI Model
- **TrapperAI YOLOv8** by [OSCF (Open Source Conservation Foundation)](https://huggingface.co/OSCF/TrapperAI-v02.2024)
- Trained on European wildlife, adaptable for North American species
- Released under permissive license

### Core Technologies
- **[Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)** - Object detection framework
- **[PyTorch](https://pytorch.org/)** - Deep learning backend with Apple Silicon MPS support
- **[OpenCV](https://opencv.org/)** - Video processing and frame extraction
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern Python GUI framework
- **[HuggingFace Hub](https://huggingface.co/)** - Model distribution and downloading
- **[send2trash](https://github.com/arsenetar/send2trash)** - Cross-platform Trash support

### Utilities
- **appdirs** - Cross-platform config directory management
- **tqdm** - Progress bars for batch processing
- **Pillow** - Image processing
- **NumPy** - Numerical operations

---

## Development

### Project Structure
```
trailcam_animal_id/
├── gui_app.py              # Main entry point
├── video_backend.py        # FastAPI backend for video streaming
├── gui/                    # GUI modules
│   ├── main_window.py      # Main application window
│   ├── pipeline_tab.py     # Pipeline configuration tab
│   ├── pipeline_wizard.py  # New analysis wizard
│   ├── review_tab.py       # Video review interface
│   ├── process_runner.py   # Subprocess management
│   └── config.py           # UI configuration
├── assets/                 # Icons and resources
├── extract_frames.py       # Frame extraction
├── classify_frames.py      # AI inference
├── summarize_videos.py     # CSV aggregation
├── review_clips.py         # CLI reviewer (legacy)
├── run_pipeline.py         # Pipeline orchestrator
└── requirements.txt        # Python dependencies
```
