"""Pipeline configuration and execution tab."""

import sys
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from gui.process_runner import ProcessRunner
from gui.config import (
    DEFAULT_CONFIG, get_worker_options, FRAMES_PER_CLIP_RANGE,
    TITLE_FONT, HEADING_FONT, BODY_FONT, MONO_FONT, COLORS
)


def get_script_path(script_name):
    """Find script in bundled app or development environment.

    Args:
        script_name: Name of the script file (e.g., 'run_pipeline.py')

    Returns:
        Full path to the script
    """
    if getattr(sys, 'frozen', False):
        # Running in packaged app - scripts are in _MEIPASS temp dir
        base_path = sys._MEIPASS
        script_path = Path(base_path) / script_name
        if script_path.exists():
            return str(script_path)

    # Development mode - scripts are in project root
    return script_name


class PipelineTab:
    """Tab for configuring and running the pipeline."""

    def __init__(self, parent):
        self.parent = parent
        self.runner = None

        # StringVars for form fields
        self.clips_dir_var = ctk.StringVar(value=DEFAULT_CONFIG['clips_dir'])
        self.frames_dir_var = ctk.StringVar()
        self.detection_dir_var = ctk.StringVar()
        self.extensions_var = ctk.StringVar(value=DEFAULT_CONFIG['extensions'])
        self.frames_per_clip_var = ctk.IntVar(value=DEFAULT_CONFIG['frames_per_clip'])
        self.frame_workers_var = ctk.IntVar(value=DEFAULT_CONFIG['frame_workers'])
        self.classify_workers_var = ctk.IntVar(value=DEFAULT_CONFIG['classify_workers'])
        self.force_var = ctk.BooleanVar(value=DEFAULT_CONFIG['force'])

        # UI state
        self.is_running = False

        # Create widgets
        self._create_widgets()
        self._update_default_paths()

    def _create_widgets(self):
        """Create all UI widgets for the pipeline tab."""

        # Input Configuration Frame
        input_frame = ctk.CTkFrame(self.parent, fg_color=COLORS['bg_secondary'])
        input_frame.pack(padx=20, pady=10, fill="x")

        # Title
        ctk.CTkLabel(
            input_frame,
            text="Pipeline Configuration",
            font=ctk.CTkFont(**TITLE_FONT)
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 15))

        # Clips Directory
        ctk.CTkLabel(
            input_frame,
            text="Clips Directory:",
            font=ctk.CTkFont(**BODY_FONT)
        ).grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self.clips_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.clips_dir_var,
            width=500
        )
        self.clips_entry.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkButton(
            input_frame,
            text="Browse...",
            command=self._browse_clips,
            width=100,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['ui_button_hover']
        ).grid(row=1, column=2, padx=10, pady=5)

        # Frames Directory
        ctk.CTkLabel(
            input_frame,
            text="Frames Directory:",
            font=ctk.CTkFont(**BODY_FONT)
        ).grid(row=2, column=0, sticky="w", padx=10, pady=5)

        self.frames_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.frames_dir_var,
            width=500
        )
        self.frames_entry.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkButton(
            input_frame,
            text="Browse...",
            command=self._browse_frames,
            width=100,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['ui_button_hover']
        ).grid(row=2, column=2, padx=10, pady=5)

        # Detection Directory
        ctk.CTkLabel(
            input_frame,
            text="Output Directory:",
            font=ctk.CTkFont(**BODY_FONT)
        ).grid(row=3, column=0, sticky="w", padx=10, pady=5)

        self.detection_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.detection_dir_var,
            width=500
        )
        self.detection_entry.grid(row=3, column=1, padx=10, pady=5)

        ctk.CTkButton(
            input_frame,
            text="Browse...",
            command=self._browse_detection,
            width=100,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['ui_button_hover']
        ).grid(row=3, column=2, padx=10, pady=5)

        # Video Extensions
        ctk.CTkLabel(
            input_frame,
            text="Video Extensions:",
            font=ctk.CTkFont(**BODY_FONT)
        ).grid(row=4, column=0, sticky="w", padx=10, pady=5)

        ctk.CTkEntry(
            input_frame,
            textvariable=self.extensions_var,
            width=500
        ).grid(row=4, column=1, padx=10, pady=5)

        # Frames per Clip
        frames_label_frame = ctk.CTkFrame(input_frame, fg_color=COLORS['bg_primary'])
        frames_label_frame.grid(row=5, column=0, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(
            frames_label_frame,
            text="Frames per Clip:",
            font=ctk.CTkFont(**BODY_FONT)
        ).pack(side="left")

        self.frames_value_label = ctk.CTkLabel(
            frames_label_frame,
            text=str(self.frames_per_clip_var.get()),
            font=ctk.CTkFont(**HEADING_FONT),
            width=30  # Fixed width for up to 2 digits
        )
        self.frames_value_label.pack(side="left", padx=5)

        frames_slider = ctk.CTkSlider(
            input_frame,
            from_=FRAMES_PER_CLIP_RANGE[0],
            to=FRAMES_PER_CLIP_RANGE[1],
            variable=self.frames_per_clip_var,
            number_of_steps=FRAMES_PER_CLIP_RANGE[1] - FRAMES_PER_CLIP_RANGE[0],
            width=500,
            command=self._update_frames_label
        )
        frames_slider.grid(row=5, column=1, padx=10, pady=5)
        frames_slider.set(DEFAULT_CONFIG['frames_per_clip'])

        # Frame Workers
        ctk.CTkLabel(
            input_frame,
            text="Frame Workers:",
            font=ctk.CTkFont(**BODY_FONT)
        ).grid(row=6, column=0, sticky="w", padx=10, pady=5)

        worker_options = get_worker_options()
        ctk.CTkOptionMenu(
            input_frame,
            variable=self.frame_workers_var,
            values=[str(w) for w in worker_options],
            width=200
        ).grid(row=6, column=1, sticky="w", padx=10, pady=5)

        # Classify Workers
        ctk.CTkLabel(
            input_frame,
            text="Classify Workers:",
            font=ctk.CTkFont(**BODY_FONT)
        ).grid(row=7, column=0, sticky="w", padx=10, pady=5)

        ctk.CTkOptionMenu(
            input_frame,
            variable=self.classify_workers_var,
            values=[str(w) for w in worker_options],
            width=200
        ).grid(row=7, column=1, sticky="w", padx=10, pady=5)

        # Force Checkbox
        ctk.CTkCheckBox(
            input_frame,
            text="Force re-run even if outputs exist",
            variable=self.force_var,
            font=ctk.CTkFont(**BODY_FONT)
        ).grid(row=8, column=0, columnspan=2, sticky="w", padx=10, pady=10)

        # Execution Frame
        exec_frame = ctk.CTkFrame(self.parent, fg_color=COLORS['bg_secondary'])
        exec_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # Title
        ctk.CTkLabel(
            exec_frame,
            text="Pipeline Execution",
            font=ctk.CTkFont(**TITLE_FONT)
        ).pack(padx=10, pady=(10, 5), anchor="w")

        # Button Frame
        button_frame = ctk.CTkFrame(exec_frame, fg_color=COLORS['bg_primary'])
        button_frame.pack(padx=10, pady=5, fill="x")

        self.run_button = ctk.CTkButton(
            button_frame,
            text="Run Pipeline",
            command=self._run_pipeline,
            width=150,
            height=40,
            font=ctk.CTkFont(**HEADING_FONT),
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['accent_active_hover']
        )
        self.run_button.pack(side="left", padx=5)

        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel_pipeline,
            width=150,
            height=40,
            state="disabled",
            font=ctk.CTkFont(**HEADING_FONT),
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['accent_danger'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['accent_danger']
        )
        self.cancel_button.pack(side="left", padx=5)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(exec_frame, width=940)
        self.progress_bar.pack(padx=10, pady=10, fill="x")
        self.progress_bar.set(0)

        # Current Step Label
        self.step_label = ctk.CTkLabel(
            exec_frame,
            text="Ready",
            font=ctk.CTkFont(**BODY_FONT)
        )
        self.step_label.pack(padx=10, pady=(0, 10), anchor="w")

        # Log Output
        ctk.CTkLabel(
            exec_frame,
            text="Output Log:",
            font=ctk.CTkFont(**HEADING_FONT)
        ).pack(padx=10, pady=(10, 5), anchor="w")

        self.log_text = ctk.CTkTextbox(
            exec_frame,
            width=940,
            height=300,
            font=ctk.CTkFont(**MONO_FONT),
            fg_color=COLORS['bg_primary'],  # Black background for log
            border_color=COLORS['ui_frame'],  # Dark border
            border_width=1
        )
        self.log_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    def _update_frames_label(self, value):
        """Update the frames per clip label when slider changes."""
        self.frames_value_label.configure(text=str(int(float(value))))

    def _browse_clips(self):
        """Browse for clips directory."""
        path = filedialog.askdirectory(title="Select Clips Directory")
        if path:
            self.clips_dir_var.set(path)
            self._update_default_paths()

    def _browse_frames(self):
        """Browse for frames output directory."""
        path = filedialog.askdirectory(title="Select Frames Output Directory")
        if path:
            self.frames_dir_var.set(path)

    def _browse_detection(self):
        """Browse for detection output directory."""
        path = filedialog.askdirectory(title="Select Detection Output Directory")
        if path:
            self.detection_dir_var.set(path)

    def _update_default_paths(self):
        """Update default frames and detection paths based on clips directory."""
        clips_path = Path(self.clips_dir_var.get())
        self.frames_dir_var.set(str(clips_path / ".pipeline_output" / "frames"))
        self.detection_dir_var.set(str(clips_path / ".pipeline_output" / "detection_csvs"))

    def _append_log(self, text: str):
        """Thread-safe log append."""
        self.log_text.after(0, lambda: self._append_log_sync(text))

    def _append_log_sync(self, text: str):
        """Append text to log (must be called from main thread)."""
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _update_progress(self, line: str):
        """Parse line for progress information (basic implementation)."""
        # TODO: Implement progress parsing in Phase 2
        pass

    def _on_completion(self, return_code: int):
        """Handle pipeline completion."""
        self.is_running = False
        self.run_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

        if return_code == 0:
            self.step_label.configure(text="Pipeline completed successfully!")
            self.progress_bar.set(1.0)
            self._append_log("\n=== Pipeline completed successfully ===")
        else:
            self.step_label.configure(text=f"Pipeline failed with exit code {return_code}")
            self._append_log(f"\n=== Pipeline failed with exit code {return_code} ===")

    def _run_pipeline(self):
        """Execute the pipeline with current configuration."""
        if self.is_running:
            return

        # Validate clips directory exists
        clips_path = Path(self.clips_dir_var.get())
        if not clips_path.exists():
            self._append_log(f"Error: Clips directory does not exist: {clips_path}")
            return

        # Create output directories before running pipeline
        frames_path = Path(self.frames_dir_var.get())
        detection_path = Path(self.detection_dir_var.get())

        try:
            frames_path.mkdir(parents=True, exist_ok=True)
            detection_path.mkdir(parents=True, exist_ok=True)
            self._append_log(f"Created output directories:\n  - {frames_path}\n  - {detection_path}\n")
        except Exception as e:
            self._append_log(f"Error: Failed to create output directories: {e}")
            return

        # Build command - handle frozen vs development mode
        if getattr(sys, 'frozen', False):
            # Packaged app - run script directly (PyInstaller's Python will execute it)
            cmd = [
                get_script_path("run_pipeline.py"),
            ]
        else:
            # Development - use Python interpreter explicitly
            cmd = [
                sys.executable,
                get_script_path("run_pipeline.py"),
            ]

        # Add arguments (same for both modes)
        cmd.extend([
            "--clips_dir", self.clips_dir_var.get(),
            "--frames_dir", self.frames_dir_var.get(),
            "--detection_dir", self.detection_dir_var.get(),
            "--frames_per_clip", str(self.frames_per_clip_var.get()),
            "--frames_workers", str(self.frame_workers_var.get()),
            "--classify_workers", str(self.classify_workers_var.get()),
            "--exts", self.extensions_var.get(),
        ])

        if self.force_var.get():
            cmd.append("--force")

        # Clear log and reset progress
        self.log_text.delete("1.0", "end")
        self.progress_bar.set(0)
        self.step_label.configure(text="Starting pipeline...")

        # Update UI state
        self.is_running = True
        self.run_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        # Log command
        self._append_log(f"Running command: {' '.join(cmd)}\n")

        # Run in background
        self.runner = ProcessRunner(
            log_callback=self._append_log,
            progress_callback=self._update_progress,
            completion_callback=self._on_completion
        )
        self.runner.run(cmd)

    def _cancel_pipeline(self):
        """Cancel running pipeline."""
        if self.runner and self.is_running:
            self.step_label.configure(text="Cancelling pipeline...")
            self._append_log("\n=== Cancelling pipeline ===")
            self.runner.cancel()
            self.is_running = False
            self.run_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
