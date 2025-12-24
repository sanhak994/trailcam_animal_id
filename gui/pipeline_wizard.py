"""Pipeline wizard - full modal wizard for new analysis setup."""

import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox
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


class PipelineWizard(ctk.CTkToplevel):
    """Full-featured wizard for pipeline setup and execution."""

    def __init__(self, parent, session_manager, completion_callback):
        """Initialize pipeline wizard.

        Args:
            parent: Parent window
            session_manager: SessionManager instance
            completion_callback: Called with skip_pipeline=True/False when done
        """
        super().__init__(parent)

        self.session_manager = session_manager
        self.completion_callback = completion_callback
        self.runner = None
        self.current_step = 1

        # Form variables
        self.clips_dir_var = ctk.StringVar(value=DEFAULT_CONFIG['clips_dir'])
        self.frames_dir_var = ctk.StringVar()
        self.detection_dir_var = ctk.StringVar()
        self.extensions_var = ctk.StringVar(value=DEFAULT_CONFIG['extensions'])
        self.frames_per_clip_var = ctk.IntVar(value=DEFAULT_CONFIG['frames_per_clip'])
        self.frame_workers_var = ctk.IntVar(value=DEFAULT_CONFIG['frame_workers'])
        self.classify_workers_var = ctk.IntVar(value=DEFAULT_CONFIG['classify_workers'])
        self.force_var = ctk.BooleanVar(value=DEFAULT_CONFIG['force'])

        # Window configuration
        self.title("New Analysis Wizard")
        self.geometry("900x700")
        self.configure(fg_color=COLORS['bg_primary'])

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        # Create main container
        self.container = ctk.CTkFrame(self, fg_color=COLORS['bg_primary'])
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        # Show first step
        self._show_step1_directory()

    def _show_step1_directory(self):
        """Step 1: Select clips directory and detect existing outputs."""
        self._clear_container()
        self.current_step = 1

        # Title
        ctk.CTkLabel(
            self.container,
            text="Step 1: Select Clips Directory",
            font=ctk.CTkFont(**TITLE_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(0, 10))

        # Description
        ctk.CTkLabel(
            self.container,
            text="Choose the folder containing your trail camera video clips",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(0, 20))

        # Directory selection
        dir_frame = ctk.CTkFrame(self.container, fg_color=COLORS['bg_secondary'])
        dir_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            dir_frame,
            text="Clips Directory:",
            font=ctk.CTkFont(**BODY_FONT)
        ).grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.clips_entry = ctk.CTkEntry(
            dir_frame,
            textvariable=self.clips_dir_var,
            width=600
        )
        self.clips_entry.grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkButton(
            dir_frame,
            text="Browse...",
            command=self._browse_clips,
            width=100,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['ui_button_hover']
        ).grid(row=0, column=2, padx=10, pady=10)

        # Status area
        self.step1_status = ctk.CTkLabel(
            self.container,
            text="Select a directory to continue",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_primary'],
            wraplength=800,
            justify="left"
        )
        self.step1_status.pack(pady=20)

        # Navigation buttons
        nav_frame = ctk.CTkFrame(self.container, fg_color=COLORS['bg_primary'])
        nav_frame.pack(side="bottom", pady=20)

        ctk.CTkButton(
            nav_frame,
            text="Cancel",
            command=self.destroy,
            width=150,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['ui_button_hover']
        ).pack(side="left", padx=5)

        self.step1_continue_btn = ctk.CTkButton(
            nav_frame,
            text="Continue",
            command=self._step1_continue,
            width=150,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['accent_active_hover'],
            state="disabled"
        )
        self.step1_continue_btn.pack(side="left", padx=5)

        # If default directory exists, validate it
        if Path(DEFAULT_CONFIG['clips_dir']).exists():
            self._validate_step1()

    def _browse_clips(self):
        """Browse for clips directory."""
        path = filedialog.askdirectory(title="Select Clips Directory")
        if path:
            self.clips_dir_var.set(path)
            self._validate_step1()

    def _validate_step1(self):
        """Validate clips directory and update status."""
        clips_path = Path(self.clips_dir_var.get())

        if not clips_path.exists():
            self.step1_status.configure(
                text="Directory does not exist",
                text_color="#ff5555"  # Bright red for visibility
            )
            self.step1_continue_btn.configure(state="disabled")
            return

        # Update session manager
        self.session_manager.set_clips_directory(clips_path)

        # Count video files
        video_exts = ['.mp4', '.MP4', '.mov', '.MOV', '.avi', '.AVI']
        video_files = []
        for ext in video_exts:
            video_files.extend(list(clips_path.glob(f"*{ext}")))

        if not video_files:
            self.step1_status.configure(
                text=f"No video files found in: {clips_path}",
                text_color="#ff5555"  # Bright red for visibility
            )
            self.step1_continue_btn.configure(state="disabled")
            return

        # Check for existing pipeline outputs
        if self.session_manager.has_existing_outputs():
            self.step1_status.configure(
                text=f"✓ Found {len(video_files)} video clips\n"
                     f"✓ Pipeline outputs detected!\n\n"
                     f"You can skip analysis and start reviewing immediately,\n"
                     f"or re-run the pipeline with new settings.",
                text_color=COLORS['text_primary']
            )
            self.step1_continue_btn.configure(
                text="Skip to Review",
                state="normal"
            )
        else:
            self.step1_status.configure(
                text=f"✓ Found {len(video_files)} video clips\n\n"
                     f"No pipeline outputs detected.\n"
                     f"Continue to configure and run analysis.",
                text_color=COLORS['text_primary']
            )
            self.step1_continue_btn.configure(
                text="Continue to Settings",
                state="normal"
            )

    def _step1_continue(self):
        """Continue from step 1 based on whether outputs exist."""
        # Update default paths
        clips_path = Path(self.clips_dir_var.get())
        self.frames_dir_var.set(str(clips_path / ".pipeline_output" / "frames"))
        self.detection_dir_var.set(str(clips_path / ".pipeline_output" / "detection_csvs"))

        # Check if we can skip pipeline
        if self.session_manager.has_existing_outputs():
            # Outputs exist - offer to skip to review
            result = messagebox.askyesno(
                "Pipeline Outputs Found",
                "Pipeline outputs already exist for this directory.\n\n"
                "Would you like to start reviewing immediately?",
                parent=self
            )
            if result:
                # Skip to review
                self.destroy()
                self.completion_callback(skip_pipeline=True)
                return

        # Continue to settings
        self._show_step2_settings()

    def _show_step2_settings(self):
        """Step 2: Configure pipeline settings."""
        self._clear_container()
        self.current_step = 2

        # Title
        ctk.CTkLabel(
            self.container,
            text="Step 2: Pipeline Settings",
            font=ctk.CTkFont(**TITLE_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(0, 10))

        # Settings frame with scroll
        settings_scroll = ctk.CTkScrollableFrame(
            self.container,
            fg_color=COLORS['bg_secondary'],
            height=400
        )
        settings_scroll.pack(fill="both", expand=True, pady=10)

        # Add all pipeline settings (simplified from pipeline_tab.py)
        self._create_pipeline_settings(settings_scroll)

        # Navigation buttons
        nav_frame = ctk.CTkFrame(self.container, fg_color=COLORS['bg_primary'])
        nav_frame.pack(side="bottom", pady=20)

        ctk.CTkButton(
            nav_frame,
            text="< Back",
            command=self._show_step1_directory,
            width=150,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['ui_button_hover']
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            nav_frame,
            text="Use Defaults",
            command=self._show_step3_run,
            width=150,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['accent_active_hover']
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            nav_frame,
            text="Run Analysis",
            command=self._show_step3_run,
            width=150,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['accent_active_hover']
        ).pack(side="left", padx=5)

    def _create_pipeline_settings(self, parent):
        """Create pipeline settings widgets.

        Args:
            parent: Parent frame for settings
        """
        # This is a condensed version of pipeline_tab settings
        # Frames per clip
        frame_frame = ctk.CTkFrame(parent, fg_color=COLORS['bg_primary'])
        frame_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            frame_frame,
            text="Frames per Clip:",
            font=ctk.CTkFont(**BODY_FONT)
        ).pack(side="left", padx=10)

        frames_value = ctk.CTkLabel(
            frame_frame,
            text=str(self.frames_per_clip_var.get()),
            font=ctk.CTkFont(**HEADING_FONT),
            width=30
        )
        frames_value.pack(side="left", padx=5)

        slider = ctk.CTkSlider(
            frame_frame,
            from_=FRAMES_PER_CLIP_RANGE[0],
            to=FRAMES_PER_CLIP_RANGE[1],
            variable=self.frames_per_clip_var,
            number_of_steps=FRAMES_PER_CLIP_RANGE[1] - FRAMES_PER_CLIP_RANGE[0],
            width=300,
            command=lambda v: frames_value.configure(text=str(int(float(v)))),
            fg_color=COLORS['bg_tertiary'],
            progress_color=COLORS['text_secondary'],
            button_color=COLORS['text_primary'],
            button_hover_color=COLORS['text_primary']
        )
        slider.pack(side="left", padx=10)

        # Workers
        worker_frame = ctk.CTkFrame(parent, fg_color=COLORS['bg_primary'])
        worker_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            worker_frame,
            text="Frame Workers:",
            font=ctk.CTkFont(**BODY_FONT)
        ).pack(side="left", padx=10)

        worker_options = get_worker_options()
        ctk.CTkOptionMenu(
            worker_frame,
            variable=self.frame_workers_var,
            values=[str(w) for w in worker_options],
            width=100
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            worker_frame,
            text="Classify Workers:",
            font=ctk.CTkFont(**BODY_FONT)
        ).pack(side="left", padx=20)

        ctk.CTkOptionMenu(
            worker_frame,
            variable=self.classify_workers_var,
            values=[str(w) for w in worker_options],
            width=100
        ).pack(side="left", padx=10)

        # Force checkbox
        ctk.CTkCheckBox(
            parent,
            text="Force re-run even if outputs exist",
            variable=self.force_var,
            font=ctk.CTkFont(**BODY_FONT),
            fg_color=COLORS['text_secondary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            checkmark_color=COLORS['bg_primary']
        ).pack(padx=10, pady=10, anchor="w")

    def _show_step3_run(self):
        """Step 3: Run pipeline."""
        self._clear_container()
        self.current_step = 3

        # Title
        ctk.CTkLabel(
            self.container,
            text="Step 3: Running Analysis",
            font=ctk.CTkFont(**TITLE_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(0, 10))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.container, width=800)
        self.progress_bar.pack(padx=10, pady=10)
        self.progress_bar.set(0)

        # Status label
        self.run_status_label = ctk.CTkLabel(
            self.container,
            text="Ready to start",
            font=ctk.CTkFont(**BODY_FONT)
        )
        self.run_status_label.pack(padx=10, pady=10)

        # Log output
        self.log_text = ctk.CTkTextbox(
            self.container,
            width=800,
            height=400,
            font=ctk.CTkFont(**MONO_FONT),
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['ui_frame'],
            border_width=1
        )
        self.log_text.pack(padx=10, pady=10, fill="both", expand=True)

        # Buttons
        button_frame = ctk.CTkFrame(self.container, fg_color=COLORS['bg_primary'])
        button_frame.pack(side="bottom", pady=20)

        self.cancel_run_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel_pipeline,
            width=150,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['accent_danger'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['accent_danger'],
            state="disabled"
        )
        self.cancel_run_btn.pack(side="left", padx=5)

        # Start pipeline immediately
        self._run_pipeline()

    def _run_pipeline(self):
        """Execute the pipeline."""
        clips_path = Path(self.clips_dir_var.get())
        if not clips_path.exists():
            messagebox.showerror("Error", "Clips directory does not exist", parent=self)
            return

        # Create output directories
        frames_path = Path(self.frames_dir_var.get())
        detection_path = Path(self.detection_dir_var.get())

        try:
            frames_path.mkdir(parents=True, exist_ok=True)
            detection_path.mkdir(parents=True, exist_ok=True)
            self._append_log(f"Created output directories:\n  - {frames_path}\n  - {detection_path}\n")
        except Exception as e:
            self._append_log(f"Error creating directories: {e}")
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

        self._append_log(f"Running: {' '.join(cmd)}\n\n")
        self.run_status_label.configure(text="Running pipeline...")
        self.cancel_run_btn.configure(state="normal")

        # Run pipeline
        self.runner = ProcessRunner(
            log_callback=self._append_log,
            progress_callback=lambda x: None,
            completion_callback=self._on_pipeline_complete
        )
        self.runner.run(cmd)

    def _append_log(self, text: str):
        """Append text to log."""
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _cancel_pipeline(self):
        """Cancel running pipeline."""
        if self.runner:
            self.runner.cancel()
            self.run_status_label.configure(text="Cancelled")
            self.cancel_run_btn.configure(state="disabled")

    def _on_pipeline_complete(self, return_code: int):
        """Handle pipeline completion.

        Args:
            return_code: Process return code
        """
        self.cancel_run_btn.configure(state="disabled")

        if return_code == 0:
            self.progress_bar.set(1.0)
            self.run_status_label.configure(text="Pipeline completed successfully!")
            self._append_log("\n=== Pipeline completed ===")

            # Wait 1 second then transition to review
            self.after(1000, self._transition_to_review)
        else:
            self.run_status_label.configure(text=f"Pipeline failed (exit code {return_code})")
            self._append_log(f"\n=== Pipeline failed (exit code {return_code}) ===")
            messagebox.showerror(
                "Pipeline Failed",
                f"Pipeline failed with exit code {return_code}.\n\nCheck the log for details.",
                parent=self
            )

    def _transition_to_review(self):
        """Transition to review screen after successful pipeline."""
        self.destroy()
        self.completion_callback(skip_pipeline=False)

    def _clear_container(self):
        """Clear all widgets from container."""
        for widget in self.container.winfo_children():
            widget.destroy()
