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

### For macOS Users (Recommended)
- Tested with MacOS Tahoe 26.1 and Python 3.14.2

**Quick Install (choose one):**

**Option A: DMG File**
1. Download `TrailCam_Animal_ID_v1.0.0.dmg` from [Releases](https://github.com/MoonMayne/trailcam_animal_id/releases)
2. Double-click to mount the DMG
3. Drag "TrailCam Animal ID" to your Applications folder
4. Eject the DMG
5. Launch from Applications or Spotlight search
6. **First launch:** Right-click → Open (to bypass Gatekeeper warning)

**Option B: ZIP File**
1. Download `TrailCam_Animal_ID_v1.0.0.zip` from [Releases](https://github.com/MoonMayne/trailcam_animal_id/releases)
2. Double-click to unzip
3. Drag "TrailCam Animal ID.app" to your Applications folder
4. Launch from Applications or Spotlight search
5. **First launch:** Right-click → Open (to bypass Gatekeeper warning)

The app will download the AI model (>50MB) on first run.

### For Developers

**Installation:**
```bash
# Clone the repository
git clone https://github.com/MoonMayne/trailcam_animal_id.git
cd trailcam_animal_id

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch the app
python3 gui_app.py
```

**Building from Source:**
```bash
# Install build dependencies
pip install py2app

# Run build script
./build.sh

# Find your app in dist/ folder
open dist/
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
├── gui/                    # GUI modules
├── assets/                 # Icons and resources
├── extract_frames.py       # Frame extraction
├── classify_frames.py      # AI inference
├── summarize_videos.py     # CSV aggregation
├── review_clips.py         # CLI reviewer
├── run_pipeline.py         # Orchestrator
├── requirements.txt        # Python dependencies
├── setup.py               # Packaging configuration
└── build.sh               # Build script
```

### Building the App
See **Getting Started → For Developers → Building from Source** above.
