"""Review tab for viewing clips with animal predictions."""

import csv
import platform
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import customtkinter as ctk
from tkinter import messagebox
from send2trash import send2trash
from gui.video_player import VideoPlayer
from gui.shortcuts_help import ShortcutsHelpModal
from gui.settings_panel import SettingsPanelModal
from gui.cleanup_modal import CleanupModal
from gui.config import TITLE_FONT, HEADING_FONT, BODY_FONT, PLAY_RATE_RANGE, DEFAULT_CONFIG, PAUSE_DURATION_RANGE, COLORS, SUBHEADING_FONT, SMALL_FONT


class ReviewTab:
    """Tab for reviewing video clips with animal prediction overlays."""

    def __init__(self, parent, clips_dir_callback, session_manager=None, preferences=None):
        self.parent = parent
        self.clips_dir_callback = clips_dir_callback
        self.session_manager = session_manager  # Optional session manager for progress tracking

        self.clips: List[Dict] = []
        self.current_index: Optional[int] = None
        self.player: Optional[VideoPlayer] = None
        self.current_button: Optional[ctk.CTkButton] = None  # Track current clip button

        # Keyboard shortcut state
        self.shortcuts_enabled_globally = True  # Toggle from settings
        self.search_has_focus = False  # Track search box focus

        # Deletion confirmation state (session-only, not persisted)
        self.skip_delete_confirmation = False  # Reset on app restart for safety

        # Apply preferences if provided, otherwise use defaults
        if preferences:
            play_rate = preferences.get('play_rate', DEFAULT_CONFIG['play_rate'])
            clip_pause_seconds = preferences.get('clip_pause_seconds', DEFAULT_CONFIG['clip_pause_seconds'])
        else:
            play_rate = DEFAULT_CONFIG['play_rate']
            clip_pause_seconds = DEFAULT_CONFIG['clip_pause_seconds']

        # Settings variables
        self.shortcuts_enabled_var = ctk.BooleanVar(value=True)
        self.auto_play_enabled_var = ctk.BooleanVar(value=True)
        self.pause_duration_var = ctk.DoubleVar(value=clip_pause_seconds)

        # Variables for UI state
        self.speed_var = ctk.DoubleVar(value=play_rate)
        self.progress_var = ctk.DoubleVar(value=0.0)
        self.was_playing_before_settings = False  # Track video state before settings open

        # Auto-hide controls state
        self.controls_visible = True
        self.auto_hide_timer = None
        self.auto_hide_delay_ms = 3000  # 3 seconds
        self.controls_placeholder = None  # Placeholder to prevent video jump
        self.was_playing_before_menu = False  # Track video state before advanced menu open
        self.main_frame = None  # Will be set in _create_widgets

        # Mouse motion debouncing
        self.mouse_motion_debounce_timer = None
        self.layout_in_progress = False  # Block events during layout changes

        # Resize debounce
        self.resize_debounce_timer = None

        self._create_widgets()

    def _create_widgets(self):
        """Create all UI widgets for the review tab."""
        # Main container with two-column layout
        main_frame = ctk.CTkFrame(self.parent)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.main_frame = main_frame  # Store reference for sidebar collapse

        # Configure grid weights for stable layout (fixed sidebar, expanding video)
        main_frame.grid_columnconfigure(0, weight=0, minsize=220)  # Clip list (fixed 220px)
        main_frame.grid_columnconfigure(1, weight=1, minsize=700)  # Video area (expands)
        main_frame.grid_rowconfigure(0, weight=1)

        # === LEFT SIDE: Clip List ===
        left_frame = ctk.CTkFrame(main_frame, fg_color=COLORS['bg_primary'])
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        self.left_frame = left_frame  # Store reference for sidebar collapse

        # Configure grid layout for sidebar (fixed rows, no weight changes)
        left_frame.grid_rowconfigure(0, weight=0)  # clips_label
        left_frame.grid_rowconfigure(1, weight=0)  # search_container
        left_frame.grid_rowconfigure(2, weight=1)  # clip_list_frame (expandable)
        left_frame.grid_columnconfigure(0, weight=1)

        # Clips label
        self.clips_label = ctk.CTkLabel(
            left_frame,
            text="Clips",
            font=ctk.CTkFont(**HEADING_FONT)
        )
        self.clips_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # Search entry
        search_container = ctk.CTkFrame(left_frame, fg_color=COLORS['bg_primary'])
        search_container.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.search_container = search_container  # Store reference for collapse

        # Top row: search box and clear button
        search_frame = ctk.CTkFrame(search_container, fg_color=COLORS['bg_primary'])
        search_frame.pack(fill="x")

        self.search_var = ctk.StringVar()
        # Search now triggered by button/Enter, not on every keystroke

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search clips...",
            textvariable=self.search_var,
            width=170,
            fg_color=COLORS['ui_input'],
            border_color=COLORS['ui_border'],
            border_width=1
        )
        self.search_entry.pack(side="left", fill="x", expand=True)

        # Search button
        search_btn = ctk.CTkButton(
            search_frame,
            text="Search",
            width=70,
            command=self._on_search_changed,
            font=ctk.CTkFont(**BODY_FONT),
            fg_color=COLORS['ui_button'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        search_btn.pack(side="left", padx=(5, 0))

        # Hover effects - only border glows
        search_btn.bind("<Enter>", lambda e: search_btn.configure(border_color=COLORS['ui_border_hover']))
        search_btn.bind("<Leave>", lambda e: search_btn.configure(border_color=COLORS['ui_border']))

        # Clear button
        clear_btn = ctk.CTkButton(
            search_frame,
            text="Clear",
            width=60,
            command=self._clear_search,
            font=ctk.CTkFont(**BODY_FONT),
            fg_color=COLORS['ui_button'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        clear_btn.pack(side="left", padx=(5, 0))

        # Hover effects - only border glows
        clear_btn.bind("<Enter>", lambda e: clear_btn.configure(border_color=COLORS['ui_border_hover']))
        clear_btn.bind("<Leave>", lambda e: clear_btn.configure(border_color=COLORS['ui_border']))

        # Bottom row: match count
        self.match_count_label = ctk.CTkLabel(
            search_container,
            text="",
            font=ctk.CTkFont(**SMALL_FONT),
            text_color=COLORS['text_secondary'],
            anchor="w"
        )
        self.match_count_label.pack(fill="x", pady=(2, 0))

        # Bind keys
        self.search_entry.bind("<Return>", lambda e: self._on_search_and_jump())
        self.search_entry.bind("<Escape>", lambda e: self._clear_search())

        # Track focus to disable shortcuts during search
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)

        # Scrollable clip list
        self.clip_list_frame = ctk.CTkScrollableFrame(left_frame, width=220, fg_color=COLORS['bg_primary'])
        self.clip_list_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # Setup macOS trackpad scrolling
        self._setup_macos_scrolling()

        # === RIGHT SIDE: Video Display and Controls ===
        right_frame = ctk.CTkFrame(main_frame, fg_color=COLORS['bg_primary'])
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 0))

        # Configure right_frame grid (fixed regions for stability)
        right_frame.grid_rowconfigure(0, weight=0, minsize=60)   # Title bar (fixed)
        right_frame.grid_rowconfigure(1, weight=1)                # Video container (expands)
        right_frame.grid_rowconfigure(2, weight=0, minsize=30)   # Progress bar (fixed)
        right_frame.grid_rowconfigure(3, weight=0, minsize=40)   # Info strip (fixed)
        right_frame.grid_columnconfigure(0, weight=1)

        # Title bar with settings gear icon and menu
        title_frame = ctk.CTkFrame(right_frame, fg_color=COLORS['bg_primary'])
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(
            title_frame,
            text="Review Clips with Animal Predictions",
            font=ctk.CTkFont(**TITLE_FONT)
        ).pack(side="left")

        # Settings gear icon button
        settings_btn = ctk.CTkButton(
            title_frame,
            text="⚙",
            width=40,
            height=30,
            command=self._show_settings_panel,
            font=ctk.CTkFont(size=18),
            fg_color=COLORS['ui_button'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        settings_btn.pack(side="right", padx=(5, 0))

        # Hover effects - only border glows
        settings_btn.bind("<Enter>", lambda e: settings_btn.configure(border_color=COLORS['ui_border_hover']))
        settings_btn.bind("<Leave>", lambda e: settings_btn.configure(border_color=COLORS['ui_border']))

        # Advanced menu button
        adv_btn = ctk.CTkButton(
            title_frame,
            text="≡",
            width=40,
            height=30,
            command=self._show_advanced_menu,
            font=ctk.CTkFont(size=20),
            fg_color=COLORS['ui_button'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        adv_btn.pack(side="right")

        # Hover effects - only border glows
        adv_btn.bind("<Enter>", lambda e: adv_btn.configure(border_color=COLORS['ui_border_hover']))
        adv_btn.bind("<Leave>", lambda e: adv_btn.configure(border_color=COLORS['ui_border']))

        # Video container (holds video and overlay controls)
        video_container = ctk.CTkFrame(right_frame, fg_color=COLORS['video_bg'])
        video_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.video_container = video_container  # Store reference

        # Configure grid: 2 rows (video + controls)
        video_container.grid_rowconfigure(0, weight=1)    # Video expands
        video_container.grid_rowconfigure(1, weight=0)    # Controls fixed height
        video_container.grid_columnconfigure(0, weight=1)

        # Video frame (fills container)
        self.video_frame = ctk.CTkFrame(video_container, fg_color=COLORS['video_bg'])
        self.video_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        # Configure grid to center video label
        self.video_frame.grid_rowconfigure(0, weight=1)
        self.video_frame.grid_columnconfigure(0, weight=1)

        # Video label (expands to fill available space)
        self.video_label = ctk.CTkLabel(
            self.video_frame,
            text="Load clips to start reviewing",
            fg_color=COLORS['video_bg']
        )
        self.video_label.grid(row=0, column=0, sticky="nsew")

        # Bind resize events
        self.video_frame.bind("<Configure>", self._on_video_frame_resize)

        # Bind mouse movement for overlay controls (on container, not just video)
        video_container.bind("<Enter>", lambda e: self._show_controls())
        video_container.bind("<Leave>", lambda e: self._reset_auto_hide_timer())
        video_container.bind("<Motion>", self._on_mouse_movement)
        self.video_label.bind("<Motion>", self._on_mouse_movement)

        # Controls overlay (bottom of video container)
        controls_overlay = ctk.CTkFrame(
            video_container,
            fg_color=COLORS['bg_primary'],  # Pure black background
            height=80
        )
        controls_overlay.grid(row=1, column=0, sticky="ew")
        self.controls_overlay = controls_overlay  # Store reference

        # Control buttons inside overlay (circular icon buttons)
        controls_inner = ctk.CTkFrame(controls_overlay, fg_color=COLORS['bg_primary'])
        controls_inner.pack(expand=True)

        # Previous button
        prev_button = ctk.CTkButton(
            controls_inner,
            text="◀",
            command=self._previous_clip,
            width=50,
            height=50,
            corner_radius=25,
            font=ctk.CTkFont(size=20),
            fg_color=COLORS['ui_button'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        prev_button.pack(side="left", padx=10)

        # Hover effects - only border glows
        prev_button.bind("<Enter>", lambda e: prev_button.configure(border_color=COLORS['ui_border_hover']))
        prev_button.bind("<Leave>", lambda e: prev_button.configure(border_color=COLORS['ui_border']))

        # Play/Pause button (larger, more prominent)
        self.play_pause_button = ctk.CTkButton(
            controls_inner,
            text="⏸",
            command=self._toggle_pause,
            width=60,
            height=60,
            corner_radius=30,
            font=ctk.CTkFont(size=24),
            fg_color=COLORS['ui_button'],
            border_color=COLORS['ui_border'],
            border_width=2,
            text_color=COLORS['text_primary']
        )
        self.play_pause_button.pack(side="left", padx=10)

        # Hover effects - only border glows
        self.play_pause_button.bind("<Enter>", lambda e: self.play_pause_button.configure(border_color=COLORS['ui_border_hover']))
        self.play_pause_button.bind("<Leave>", lambda e: self.play_pause_button.configure(border_color=COLORS['ui_border']))

        # Next button
        next_button = ctk.CTkButton(
            controls_inner,
            text="▶",
            command=self._next_clip,
            width=50,
            height=50,
            corner_radius=25,
            font=ctk.CTkFont(size=20),
            fg_color=COLORS['ui_button'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        next_button.pack(side="left", padx=10)

        # Hover effects - only border glows
        next_button.bind("<Enter>", lambda e: next_button.configure(border_color=COLORS['ui_border_hover']))
        next_button.bind("<Leave>", lambda e: next_button.configure(border_color=COLORS['ui_border']))

        # Delete button (danger accent border)
        delete_button = ctk.CTkButton(
            controls_inner,
            text="🗑",
            command=self._delete_clip,
            width=50,
            height=50,
            corner_radius=25,
            font=ctk.CTkFont(size=18),
            fg_color=COLORS['ui_button'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        delete_button.pack(side="left", padx=10)

        # Hover effects - border glows red to signal danger (destructive action)
        delete_button.bind("<Enter>", lambda e: delete_button.configure(border_color=COLORS['accent_danger']))
        delete_button.bind("<Leave>", lambda e: delete_button.configure(border_color=COLORS['ui_border']))

        # Progress bar (thin, elegant timeline scrubber)
        self.progress_bar = ctk.CTkProgressBar(
            right_frame,
            variable=self.progress_var,
            height=6,
            corner_radius=3,
            progress_color=COLORS['text_primary'],
            fg_color=COLORS['bg_tertiary']
        )
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        self.progress_bar.set(0)

        # Overlay label for end-of-clip message (not placed initially)
        self.overlay_label = ctk.CTkLabel(
            right_frame,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=COLORS['bg_tertiary'],
            corner_radius=10,
            width=600,
            height=120
        )

        # Compact info strip (single line with left/center/right sections)
        info_strip = ctk.CTkFrame(right_frame, height=40, fg_color=COLORS['bg_primary'])
        info_strip.grid(row=3, column=0, sticky="ew")
        info_strip.grid_propagate(False)  # Maintain fixed height

        # Left: Clip filename
        self.info_filename_label = ctk.CTkLabel(
            info_strip,
            text="",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_primary'],
            anchor="w"
        )
        self.info_filename_label.pack(side="left", padx=10, fill="x", expand=False)

        # Center: Animals detected
        self.info_animals_label = ctk.CTkLabel(
            info_strip,
            text="",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_secondary'],
            anchor="center"
        )
        self.info_animals_label.pack(side="left", padx=10, fill="x", expand=True)

        # Right: Clip count
        self.info_count_label = ctk.CTkLabel(
            info_strip,
            text="",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_primary'],
            anchor="e"
        )
        self.info_count_label.pack(side="right", padx=10, fill="x", expand=False)

        # Bind keyboard shortcuts to main window with focus checks
        root = self.parent.winfo_toplevel()
        root.bind("<n>", lambda e: self._next_clip() if self._should_execute_shortcut() else None)
        root.bind("<N>", lambda e: self._next_clip() if self._should_execute_shortcut() else None)
        root.bind("<p>", lambda e: self._previous_clip() if self._should_execute_shortcut() else None)
        root.bind("<P>", lambda e: self._previous_clip() if self._should_execute_shortcut() else None)
        root.bind("<d>", lambda e: self._delete_clip() if self._should_execute_shortcut() else None)
        root.bind("<D>", lambda e: self._delete_clip() if self._should_execute_shortcut() else None)
        root.bind("<space>", lambda e: self._toggle_pause() if self._should_execute_shortcut() else None)
        root.bind("<q>", lambda e: self._stop_playback() if self._should_execute_shortcut() else None)
        root.bind("<Q>", lambda e: self._stop_playback() if self._should_execute_shortcut() else None)

        # Speed control shortcuts
        root.bind("<plus>", lambda e: self._increase_speed() if self._should_execute_shortcut() else None)
        root.bind("<equal>", lambda e: self._increase_speed() if self._should_execute_shortcut() else None)
        root.bind("<minus>", lambda e: self._decrease_speed() if self._should_execute_shortcut() else None)
        root.bind("<0>", lambda e: self._reset_speed() if self._should_execute_shortcut() else None)

        # Settings shortcuts
        root.bind("<a>", lambda e: self._toggle_auto_play() if self._should_execute_shortcut() else None)
        root.bind("<A>", lambda e: self._toggle_auto_play() if self._should_execute_shortcut() else None)
        root.bind("<s>", lambda e: self._show_settings_panel() if self._should_execute_shortcut() else None)
        root.bind("<S>", lambda e: self._show_settings_panel() if self._should_execute_shortcut() else None)
        root.bind("<h>", lambda e: self._show_shortcuts_help() if self._should_execute_shortcut() else None)
        root.bind("<H>", lambda e: self._show_shortcuts_help() if self._should_execute_shortcut() else None)

    def _setup_macos_scrolling(self):
        """Setup macOS trackpad scrolling with bind_all."""
        import platform
        if platform.system() != "Darwin":
            return

        try:
            canvas = self.clip_list_frame._parent_canvas

            def on_scroll(event):
                # Check if mouse is over the clip list area
                try:
                    x, y = event.x_root, event.y_root
                    widget = event.widget.winfo_containing(x, y)

                    # Only scroll if mouse is over clip list frame or its children
                    if widget and (widget == self.clip_list_frame or
                                   str(widget).startswith(str(self.clip_list_frame))):
                        canvas.yview_scroll(int(-1 * (event.delta)), "units")
                        return "break"
                except:
                    pass

            # Use bind_all to capture scroll events globally
            root = self.parent.winfo_toplevel()
            root.bind_all("<MouseWheel>", on_scroll, add="+")

        except Exception as e:
            print(f"macOS scrolling setup failed: {e}")

    def _update_speed(self, value):
        """Update playback speed from settings panel."""
        speed = float(value)
        # Speed label is in settings panel, not review tab - no label to update here
        if self.player:
            self.player.set_speed(speed)

    def _on_video_frame_resize(self, event):
        """Handle video frame resize with debouncing to prevent glitches."""
        # Cancel previous timer if exists
        if self.resize_debounce_timer:
            self.video_frame.after_cancel(self.resize_debounce_timer)

        # Schedule resize after 300ms of no resize events (user stopped dragging)
        self.resize_debounce_timer = self.video_frame.after(
            300,
            lambda: self._apply_resize(event.width, event.height)
        )

    def _apply_resize(self, width: int, height: int):
        """Apply the resize after debounce delay."""
        if self.player and width > 1 and height > 1:
            available_width = max(400, width - 20)
            available_height = max(300, height - 20)
            self.player.set_target_container_size(available_width, available_height)
        self.resize_debounce_timer = None

    def _load_clips(self):
        """Load clips from CSV and populate clip list."""
        clips_dir = Path(self.clips_dir_callback())
        csv_path = clips_dir / ".pipeline_output" / "detection_csvs" / "animals_in_videos.csv"

        # Check if clips directory exists
        if not clips_dir.exists():
            messagebox.showerror(
                "Invalid Clips Directory",
                f"Clips directory does not exist:\n{clips_dir}\n\nPlease select a valid clips directory in the Pipeline tab."
            )
            return

        # Check if CSV exists
        if not csv_path.exists():
            messagebox.showwarning(
                "No Data",
                f"CSV file not found:\n{csv_path}\n\nRun the pipeline first to generate predictions."
            )
            return

        # Clear existing clips
        self.clips = []
        for widget in self.clip_list_frame.winfo_children():
            widget.destroy()

        # Parse CSV and build clip list
        exts = [".mp4", ".MP4", ".mov", ".MOV"]
        with csv_path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row['video_title']
                unique_animals = row['unique_animals']
                multiple = row['multiple_animals'] == 'true'

                # Find clip file
                clip_path = self._find_clip(title, clips_dir, exts)
                if clip_path:
                    # Keep original for display formatting in button
                    self.clips.append({
                        'path': clip_path,
                        'title': title,
                        'animals': unique_animals if unique_animals else 'none',
                        'unique_animals': unique_animals,
                        'multiple': multiple
                    })

        # Create clip list UI elements
        if not self.clips:
            ctk.CTkLabel(
                self.clip_list_frame,
                text="No clips found",
                text_color=COLORS['text_secondary']
            ).pack(pady=20)
        else:
            for idx, clip in enumerate(self.clips):
                self._create_clip_button(idx, clip)

            # CTkScrollableFrame handles scrolling automatically
            # Custom mousewheel bindings removed

            # Auto-play first clip
            self._play_clip(0)

    def _format_animal_names(self, animals_raw: str) -> str:
        """Format animal names for display.

        Args:
            animals_raw: Raw animal string like "deer&european_badger" or "cat"

        Returns:
            Formatted string like "Deer, European Badger" or "Cat"
        """
        if not animals_raw or animals_raw == 'none':
            return "No animals"

        # Split by ampersand (multiple animals)
        animal_list = animals_raw.split('&')

        # Format each animal name
        formatted_animals = []
        for animal in animal_list:
            # Replace underscores with spaces and convert to Title Case
            formatted = animal.replace('_', ' ').title()
            formatted_animals.append(formatted)

        # Join with comma-space
        return ', '.join(formatted_animals)

    def _create_clip_button(self, idx: int, clip: Dict):
        """Create a clip item with consistent formatting."""
        # Create container frame for clip item
        clip_frame = ctk.CTkFrame(
            self.clip_list_frame,
            width=200,
            height=65,
            fg_color=COLORS['ui_button'],
            border_width=1,
            border_color=COLORS['ui_border']
        )
        clip_frame.pack(pady=2, padx=5, fill="x")
        clip_frame.pack_propagate(False)  # Maintain fixed size

        # Hover effects (only change border, not background)
        def on_enter(event):
            if self.current_index != idx:  # Don't override active state
                clip_frame.configure(border_color=COLORS['ui_border_hover'])

        def on_leave(event):
            if self.current_index != idx:  # Don't override active state
                clip_frame.configure(border_color=COLORS['ui_border'])

        clip_frame.bind("<Enter>", on_enter)
        clip_frame.bind("<Leave>", on_leave)

        # Make frame clickable
        clip_frame.bind("<Button-1>", lambda e, i=idx: self._play_clip(i))

        # Title label (fixed font size)
        title_label = ctk.CTkLabel(
            clip_frame,
            text=clip['title'],
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        title_label.pack(anchor="w", padx=8, pady=(5, 0))
        title_label.bind("<Button-1>", lambda e, i=idx: self._play_clip(i))

        # Animals label (fixed font size, truncated consistently)
        animals = self._format_animal_names(clip['animals'])
        if len(animals) > 28:
            animals = animals[:25] + "..."

        animals_label = ctk.CTkLabel(
            clip_frame,
            text=animals,
            font=ctk.CTkFont(**SMALL_FONT),
            anchor="w",
            text_color=COLORS['text_secondary']
        )
        animals_label.pack(anchor="w", padx=8, pady=(0, 5))
        animals_label.bind("<Button-1>", lambda e, i=idx: self._play_clip(i))

        # Store frame reference for highlighting
        clip['frame_widget'] = clip_frame

    def _find_clip(self, title: str, clips_dir: Path, exts: List[str]) -> Optional[Path]:
        """Find clip file by title and extension."""
        for ext in exts:
            candidate = clips_dir / f"{title}{ext}"
            if candidate.exists():
                return candidate
        return None

    def _play_clip(self, index: int):
        """Start playing clip at given index."""
        if index < 0 or index >= len(self.clips):
            return

        # Set flag to block mouse events during layout changes
        self.layout_in_progress = True

        # Stop current playback
        if self.player:
            self.player.stop()

        clip = self.clips[index]
        self.current_index = index

        # Save progress and state to session manager
        if self.session_manager:
            self.session_manager.save_clip_index(index)
            self.session_manager.save_state(self._get_preferences())

        # Update compact info strip (left/center/right sections)
        animals_display = self._format_animal_names(clip['animals']).replace(',', ' •')

        self.info_filename_label.configure(text=f"🎬 {clip['title']}")
        self.info_animals_label.configure(text=animals_display if animals_display else "No animals detected")
        self.info_count_label.configure(text=f"{index + 1} / {len(self.clips)}")

        # Highlight current clip frame
        for i, c in enumerate(self.clips):
            if 'frame_widget' in c and c['frame_widget'].winfo_exists():
                if i == index:
                    # Active state: neon teal border, black background
                    c['frame_widget'].configure(
                        fg_color=COLORS['ui_button'],
                        border_color=COLORS['accent_active']
                    )
                    # Scroll the highlighted clip into view
                    self._scroll_clip_into_view(c['frame_widget'])
                else:
                    # Inactive state: grey border, black background
                    c['frame_widget'].configure(
                        fg_color=COLORS['ui_button'],
                        border_color=COLORS['ui_border']
                    )

        # Reset progress bar
        self.progress_var.set(0.0)

        # Reset play/pause button to pause icon
        self.play_pause_button.configure(text="⏸")

        # Create and start video player
        try:
            self.player = VideoPlayer(
                frame_callback=self._update_frame,
                completion_callback=self._on_video_complete,
                progress_callback=self._update_progress
            )
            self.player.load_video(clip['path'])

            # Set target size from current frame dimensions
            if self.video_frame.winfo_width() > 1:
                available_width = max(400, self.video_frame.winfo_width() - 20)
                available_height = max(300, self.video_frame.winfo_height() - 20)
                self.player.set_target_container_size(available_width, available_height)

            self.player.set_speed(self.speed_var.get())
            self.player.start()

            # Start auto-hide timer for controls
            self._reset_auto_hide_timer()
        except Exception as e:
            messagebox.showerror(
                "Playback Error",
                f"Failed to play video:\n{e}"
            )
        finally:
            # Clear layout flag immediately (blocking operations already done)
            self.layout_in_progress = False

    def _scroll_clip_into_view(self, clip_widget):
        """Scroll the clips list to make the given clip widget visible."""
        try:
            # Get the scrollable frame's canvas
            canvas = self.clip_list_frame._parent_canvas

            # Get widget's position relative to the scrollable frame
            widget_y = clip_widget.winfo_y()
            widget_height = clip_widget.winfo_height()

            # Get visible area bounds
            canvas_height = canvas.winfo_height()
            scroll_region = canvas.cget("scrollregion").split()
            if len(scroll_region) == 4:
                total_height = float(scroll_region[3])
            else:
                return

            # Calculate current viewport
            yview = canvas.yview()
            visible_top = yview[0] * total_height
            visible_bottom = yview[1] * total_height

            # Check if widget is outside visible area
            if widget_y < visible_top:
                # Scroll up to show widget at top
                canvas.yview_moveto(widget_y / total_height)
            elif widget_y + widget_height > visible_bottom:
                # Scroll down to show widget at bottom
                target = (widget_y + widget_height - canvas_height) / total_height
                canvas.yview_moveto(max(0, target))
        except (AttributeError, ValueError, ZeroDivisionError):
            # If scroll fails, it's not critical - clip is highlighted anyway
            pass

    def _update_frame(self, ctk_image):
        """Thread-safe callback to update video frame."""
        # Schedule GUI update on main thread, with safety check
        def safe_update():
            try:
                if self.video_label.winfo_exists():
                    self.video_label.configure(image=ctk_image, text="")
            except:
                pass  # Widget destroyed, ignore
        self.video_label.after(0, safe_update)

    def _update_progress(self, progress: float):
        """Thread-safe callback to update progress bar."""
        # Schedule GUI update on main thread, with safety check
        def safe_update():
            try:
                if self.progress_bar.winfo_exists():
                    self.progress_var.set(progress)
            except:
                pass  # Widget destroyed, ignore
        self.progress_bar.after(0, safe_update)

    def _on_video_complete(self):
        """Called when video playback completes."""
        pause_seconds = self.pause_duration_var.get()

        # Check if auto-play is enabled
        if self.auto_play_enabled_var.get():
            # Auto-play ON: show countdown and schedule advance
            message = (
                f"Clip Ended\n\n"
                f"Advancing to next clip in {pause_seconds:.1f} seconds\n"
                f"Press 'n' for next, 'p' for previous, 'd' to delete"
            )
            self.overlay_label.configure(text=message)
            self.overlay_label.place(relx=0.5, rely=0.4, anchor="center")

            # Schedule hide and advance after pause
            self.video_label.after(int(pause_seconds * 1000), self._advance_after_pause)
        else:
            # Auto-play OFF: show static message, no auto-advance
            message = (
                f"Clip Ended\n\n"
                f"Auto-play disabled\n"
                f"Press 'n' for next, 'p' for previous, 'd' to delete"
            )
            self.overlay_label.configure(text=message)
            self.overlay_label.place(relx=0.5, rely=0.4, anchor="center")

            # Schedule hide after pause (but no advance)
            self.video_label.after(int(pause_seconds * 1000), lambda: self.overlay_label.place_forget())

    def _advance_after_pause(self):
        """Hide overlay and advance to next clip."""
        self.overlay_label.place_forget()  # Hide overlay
        self._next_clip()

    def _next_clip(self):
        """Go to next clip in list."""
        # Hide overlay if visible (user manually advancing)
        self.overlay_label.place_forget()

        if self.current_index is None or not self.clips:
            return

        next_index = self.current_index + 1
        if next_index < len(self.clips):
            self._play_clip(next_index)
        else:
            # At end of list, stop playback
            if self.player:
                self.player.stop()
            self.video_label.configure(text="End of clip list")

    def _previous_clip(self):
        """Go to previous clip in list."""
        # Hide overlay if visible (user manually advancing)
        self.overlay_label.place_forget()

        if self.current_index is None or not self.clips:
            return

        prev_index = self.current_index - 1
        if prev_index >= 0:
            self._play_clip(prev_index)

    def _delete_clip(self):
        """Delete current clip and advance to next."""
        if self.current_index is None or not self.clips:
            return

        clip = self.clips[self.current_index]

        # Check if user disabled confirmations this session
        if not self.skip_delete_confirmation:
            # Show custom confirmation dialog with checkbox
            result, dont_ask_again = self._show_delete_confirmation(clip)

            if dont_ask_again:
                self.skip_delete_confirmation = True

            if not result:
                return  # User clicked "No"

        # Proceed with deletion (confirmations either disabled or user clicked "Yes")
        try:
            # Stop playback
            if self.player:
                self.player.stop()

            # Move to trash
            send2trash(str(clip['path']))

            # Remove from list
            deleted_index = self.current_index
            self.clips.pop(deleted_index)

            # Rebuild clip list UI
            for widget in self.clip_list_frame.winfo_children():
                widget.destroy()

            if not self.clips:
                ctk.CTkLabel(
                    self.clip_list_frame,
                    text="No clips remaining",
                    text_color=COLORS['text_secondary']
                ).pack(pady=20)
                self.video_label.configure(text="No more clips to review")
                self.current_index = None
            else:
                # Recreate buttons
                for idx, c in enumerate(self.clips):
                    self._create_clip_button(idx, c)

                # Play next clip (or previous if at end)
                next_index = min(deleted_index, len(self.clips) - 1)
                self._play_clip(next_index)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete clip:\n{e}")

    def _show_delete_confirmation(self, clip):
        """Show custom delete confirmation with 'skip confirmation' checkbox.

        Returns:
            tuple: (confirmed: bool, dont_ask_again: bool)
        """
        # Create modal dialog
        dialog = ctk.CTkToplevel(self.parent.winfo_toplevel())
        dialog.title("Confirm Delete")
        dialog.geometry("400x220")
        dialog.resizable(False, False)
        dialog.transient(self.parent.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(fg_color=COLORS['bg_secondary'])

        # Center on parent
        dialog.update_idletasks()
        parent = self.parent.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (220 // 2)
        dialog.geometry(f"+{x}+{y}")

        # Result variables
        confirmed = False
        dont_ask = False

        # Message
        ctk.CTkLabel(
            dialog,
            text="Move clip to Trash?",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            dialog,
            text=f"{clip['title']}\n\nAnimals: {clip['animals']}",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_secondary'],
            justify="center"
        ).pack(pady=(0, 15))

        # Checkbox
        dont_ask_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            dialog,
            text="Skip confirmation this session",
            variable=dont_ask_var,
            font=ctk.CTkFont(**BODY_FONT),
            fg_color=COLORS['text_secondary'],
            border_color=COLORS['text_secondary'],
            text_color=COLORS['text_primary'],
            checkmark_color=COLORS['bg_primary']
        ).pack(pady=(0, 20))

        # Buttons
        def on_yes():
            nonlocal confirmed, dont_ask
            confirmed = True
            dont_ask = dont_ask_var.get()  # Only applies checkbox if clicking Yes
            dialog.destroy()

        def on_no():
            nonlocal confirmed
            confirmed = False
            # NOTE: Checkbox is IGNORED when clicking No (matches macOS behavior)
            # User must click Yes to confirm they don't want prompts
            dialog.destroy()

        button_frame = ctk.CTkFrame(dialog, fg_color=COLORS['bg_secondary'])
        button_frame.pack(pady=(0, 20))

        ctk.CTkButton(
            button_frame,
            text="No",
            command=on_no,
            width=100,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['ui_button_hover']
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Yes",
            command=on_yes,
            width=100,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['accent_danger'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['accent_danger']
        ).pack(side="left", padx=5)

        # Keyboard shortcuts
        dialog.bind("<Return>", lambda e: on_yes())
        dialog.bind("<Escape>", lambda e: on_no())

        # Wait for dialog to close
        dialog.wait_window()

        return confirmed, dont_ask

    def _toggle_pause(self):
        """Toggle pause/resume on current video."""
        if self.player:
            self.player.toggle_pause()
            # Update button text based on paused state
            if self.player.paused:
                self.play_pause_button.configure(text="▶")
                # Cancel auto-hide timer when paused (show controls)
                self._cancel_auto_hide_timer()
            else:
                self.play_pause_button.configure(text="⏸")
                # Restart auto-hide timer when resumed
                self._reset_auto_hide_timer()

    def _stop_playback(self):
        """Stop current playback."""
        if self.player:
            self.player.stop()
            self.video_label.configure(text="Playback stopped\nSelect a clip to resume")
            # Cancel auto-hide timer and show controls
            self._cancel_auto_hide_timer()

    # Custom mousewheel bindings removed - CTkScrollableFrame handles scrolling automatically
    # The following methods are commented out as they interfered with native scrolling:
    # - _bind_mousewheel()
    # - _on_mousewheel()
    # - _on_mousewheel_mac()
    # - _on_mousewheel_linux()

    def _on_search_changed(self, *args):
        """Filter clip list based on search text."""
        search_text = self.search_var.get().lower()
        match_count = 0

        for clip in self.clips:
            if 'frame_widget' in clip and clip['frame_widget'].winfo_exists():
                # Show/hide based on match
                if not search_text or search_text in clip['title'].lower() or search_text in clip['animals'].lower():
                    clip['frame_widget'].pack(pady=2, padx=5, fill="x")
                    match_count += 1
                else:
                    clip['frame_widget'].pack_forget()

        # Update match count label
        if search_text:
            total_clips = len(self.clips)
            self.match_count_label.configure(
                text=f"{match_count} of {total_clips} clips"
            )
        else:
            self.match_count_label.configure(text="")

    def _clear_search(self):
        """Clear search and show all clips."""
        self.search_var.set("")
        self.match_count_label.configure(text="")
        # Remove focus from search entry to restore keyboard shortcuts
        self.parent.winfo_toplevel().focus()
        # Restore all clips
        for clip in self.clips:
            if 'frame_widget' in clip and clip['frame_widget'].winfo_exists():
                clip['frame_widget'].pack(pady=2, padx=5, fill="x")

    def _on_search_and_jump(self):
        """Trigger search and jump to first match (called on Enter key)."""
        self._on_search_changed()  # Apply search filter first
        self._jump_to_first_match()  # Then jump to first match
        # Remove focus from search entry to restore keyboard shortcuts
        self.parent.winfo_toplevel().focus()

    def _jump_to_first_match(self, event=None):
        """Jump to and play first matching clip."""
        search_text = self.search_var.get().lower()

        for i, clip in enumerate(self.clips):
            if search_text in clip['title'].lower():
                self._play_clip(i)
                return

    def _on_search_focus_in(self, event=None):
        """Disable shortcuts when search box has focus."""
        self.search_has_focus = True

    def _on_search_focus_out(self, event=None):
        """Re-enable shortcuts when search box loses focus."""
        self.search_has_focus = False

    def _should_execute_shortcut(self) -> bool:
        """Check if shortcuts should execute (not in search box)."""
        return self.shortcuts_enabled_globally and not self.search_has_focus

    def _on_shortcuts_toggle(self):
        """Update global shortcuts enabled state."""
        self.shortcuts_enabled_globally = self.shortcuts_enabled_var.get()

    def _increase_speed(self):
        """Increase playback speed through discrete steps: 1x → 1.5x → 2x → 4x → 8x."""
        speed_steps = [1.0, 1.5, 2.0, 4.0, 8.0]
        current_speed = self.speed_var.get()

        # Find next higher step
        for speed in speed_steps:
            if speed > current_speed + 0.01:  # Small tolerance for float comparison
                self.speed_var.set(speed)
                self._update_speed(speed)
                return

        # Already at max, stay at 8x
        self.speed_var.set(8.0)
        self._update_speed(8.0)

    def _decrease_speed(self):
        """Decrease playback speed through discrete steps: 8x → 4x → 2x → 1.5x → 1x."""
        speed_steps = [8.0, 4.0, 2.0, 1.5, 1.0]
        current_speed = self.speed_var.get()

        # Find next lower step
        for speed in speed_steps:
            if speed < current_speed - 0.01:  # Small tolerance for float comparison
                self.speed_var.set(speed)
                self._update_speed(speed)
                return

        # Already at min, stay at 1x
        self.speed_var.set(1.0)
        self._update_speed(1.0)

    def _reset_speed(self):
        """Reset playback speed to 1x."""
        self.speed_var.set(1.0)
        self._update_speed(1.0)

    def _toggle_auto_play(self):
        """Toggle auto-play on/off."""
        current = self.auto_play_enabled_var.get()
        self.auto_play_enabled_var.set(not current)

    def _show_shortcuts_help(self):
        """Show keyboard shortcuts help overlay."""
        modal = ShortcutsHelpModal(self.parent.winfo_toplevel())
        modal.focus()

    def _show_settings_panel(self):
        """Show settings panel modal and pause video."""
        # Remember if video was playing before opening settings
        self.was_playing_before_settings = False
        if self.player and not self.player.paused:
            self.was_playing_before_settings = True
            self.player.toggle_pause()
            self.play_pause_button.configure(text="▶")

        # Show settings modal
        modal = SettingsPanelModal(
            parent=self.parent.winfo_toplevel(),
            speed_var=self.speed_var,
            auto_play_var=self.auto_play_enabled_var,
            pause_duration_var=self.pause_duration_var,
            shortcuts_enabled_var=self.shortcuts_enabled_var,
            on_speed_change=self._update_speed,
            on_pause_duration_change=lambda v: None,  # No-op, value is already updated via variable
            on_shortcuts_toggle=self._on_shortcuts_toggle,
            on_close=self._on_settings_close,
            clips_dir_callback=self.clips_dir_callback
        )
        modal.focus()

    def _on_settings_close(self):
        """Resume video when settings panel closes if it was playing."""
        if self.was_playing_before_settings and self.player:
            self.player.toggle_pause()
            self.play_pause_button.configure(text="⏸")

    def _on_mouse_movement(self, event=None):
        """Handle mouse movement with debouncing."""
        # Block events during layout changes
        if self.layout_in_progress:
            return

        # Cancel existing timer
        if self.mouse_motion_debounce_timer:
            self.video_frame.after_cancel(self.mouse_motion_debounce_timer)

        # Debounce: wait 100ms before acting
        self.mouse_motion_debounce_timer = self.video_frame.after(
            100,
            self._handle_mouse_movement_debounced
        )

    def _handle_mouse_movement_debounced(self):
        """Actually handle mouse movement after debounce."""
        if not self.controls_visible:
            self._show_controls()

        if self.player and not self.player.paused:
            self._reset_auto_hide_timer()

    def _show_controls(self):
        """Show the playback controls (now always visible as overlay)."""
        # Controls are now always-visible overlay - no-op
        pass

    def _hide_controls(self):
        """Hide the playback controls (now always visible as overlay)."""
        # Controls are now always-visible overlay - no-op
        pass

    def _reset_auto_hide_timer(self):
        """Reset the auto-hide timer (controls now always visible)."""
        # Controls are now always-visible overlay - no auto-hide needed
        pass

    def _cancel_auto_hide_timer(self):
        """Cancel the auto-hide timer and ensure controls are visible."""
        if self.auto_hide_timer:
            self.video_frame.after_cancel(self.auto_hide_timer)
            self.auto_hide_timer = None
        self._show_controls()

    def _show_advanced_menu(self):
        """Show advanced options menu and pause video."""
        # Save playing state and pause video if playing
        self.was_playing_before_menu = False
        if self.player and not self.player.paused:
            self.was_playing_before_menu = True
            self.player.toggle_pause()
            self.play_pause_button.configure(text="▶")

        # Create a simple menu modal
        menu_modal = ctk.CTkToplevel(self.parent.winfo_toplevel())
        menu_modal.title("Advanced Options")
        menu_modal.geometry("300x280")
        menu_modal.resizable(False, False)
        menu_modal.transient(self.parent.winfo_toplevel())
        menu_modal.grab_set()
        menu_modal.configure(fg_color=COLORS['bg_secondary'])

        # Title
        ctk.CTkLabel(
            menu_modal,
            text="Advanced Options",
            font=ctk.CTkFont(**TITLE_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 20))

        # Menu buttons
        button_frame = ctk.CTkFrame(menu_modal, fg_color=COLORS['bg_secondary'])
        button_frame.pack(fill="both", expand=True, padx=30)

        # Start Over
        start_over_btn = ctk.CTkButton(
            button_frame,
            text="Start Over",
            command=lambda: self._start_over(menu_modal),
            width=240,
            height=40,
            font=ctk.CTkFont(**HEADING_FONT),
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        start_over_btn.pack(pady=5)

        # Hover effects - border glows red to signal danger (destructive action)
        start_over_btn.bind("<Enter>", lambda e: start_over_btn.configure(border_color=COLORS['accent_danger']))
        start_over_btn.bind("<Leave>", lambda e: start_over_btn.configure(border_color=COLORS['ui_border']))

        # Open Output Folder
        output_btn = ctk.CTkButton(
            button_frame,
            text="Open Output Folder",
            command=lambda: self._open_output_folder(menu_modal),
            width=240,
            height=40,
            font=ctk.CTkFont(**HEADING_FONT),
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        output_btn.pack(pady=5)

        # Hover effects - border glows neon teal
        output_btn.bind("<Enter>", lambda e: output_btn.configure(border_color=COLORS['ui_border_hover']))
        output_btn.bind("<Leave>", lambda e: output_btn.configure(border_color=COLORS['ui_border']))

        # About
        about_btn = ctk.CTkButton(
            button_frame,
            text="About",
            command=lambda: self._show_about(menu_modal),
            width=240,
            height=40,
            font=ctk.CTkFont(**HEADING_FONT),
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['ui_border'],
            border_width=1,
            text_color=COLORS['text_primary']
        )
        about_btn.pack(pady=5)

        # Hover effects - border glows neon teal
        about_btn.bind("<Enter>", lambda e: about_btn.configure(border_color=COLORS['ui_border_hover']))
        about_btn.bind("<Leave>", lambda e: about_btn.configure(border_color=COLORS['ui_border']))

        # Close instruction
        ctk.CTkLabel(
            menu_modal,
            text="Press 'Esc' to close",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_secondary']
        ).pack(pady=(10, 15))

        # Bind Esc and window close to resume video
        menu_modal.bind("<Escape>", lambda e: self._close_advanced_menu(menu_modal))
        menu_modal.protocol("WM_DELETE_WINDOW", lambda: self._close_advanced_menu(menu_modal))
        menu_modal.focus()

    def _close_advanced_menu(self, menu_modal):
        """Close advanced menu and resume video if it was playing."""
        menu_modal.destroy()
        # Resume video if it was playing before menu opened
        if self.was_playing_before_menu and self.player:
            self.player.toggle_pause()
            self.play_pause_button.configure(text="⏸")

    def _open_cleanup_modal(self, parent_modal):
        """Open cleanup modal and close menu."""
        self._close_advanced_menu(parent_modal)
        clips_dir = self.clips_dir_callback()
        modal = CleanupModal(self.parent.winfo_toplevel(), clips_dir)
        modal.focus()

    def _start_over(self, parent_modal):
        """Delete pipeline outputs and return to startup screen."""
        # Close the advanced menu first
        self._close_advanced_menu(parent_modal)

        # Get clips directory and output path
        clips_dir = Path(self.clips_dir_callback())
        output_dir = clips_dir / ".pipeline_output"

        # Check if outputs exist
        if not output_dir.exists():
            messagebox.showinfo(
                "Nothing to Delete",
                "No pipeline outputs found.\n\n"
                "Click 'Start New Analysis' to run the pipeline."
            )
            return

        # Confirmation dialog
        result = messagebox.askyesno(
            "Start Over",
            "This will:\n\n"
            "• Delete all pipeline outputs\n"
            "• Return to the startup screen\n"
            "• Let you start fresh with the wizard\n\n"
            "The outputs will be moved to Trash and can be recovered.\n\n"
            "Continue?",
            icon='warning'
        )

        if not result:
            return

        try:
            # 1. Cancel all pending timers to prevent callbacks on destroyed widgets
            if self.auto_hide_timer:
                self.video_frame.after_cancel(self.auto_hide_timer)
                self.auto_hide_timer = None
            if self.mouse_motion_debounce_timer:
                self.video_frame.after_cancel(self.mouse_motion_debounce_timer)
                self.mouse_motion_debounce_timer = None
            if self.resize_debounce_timer:
                self.video_frame.after_cancel(self.resize_debounce_timer)
                self.resize_debounce_timer = None

            # 2. Stop video player to prevent frame update callbacks
            if self.player:
                self.player.stop()

            # 3. Delete .pipeline_output folder (sends to Trash)
            send2trash(str(output_dir))

            # 4. Reset session state
            if self.session_manager:
                self.session_manager.reset()
                self.session_manager.save_state(self._get_preferences())

            # 5. Navigate back to startup screen
            root = self.parent.winfo_toplevel()
            root._show_startup_screen()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to reset pipeline:\n\n{str(e)}"
            )

    def _open_output_folder(self, parent_modal):
        """Open output folder in Finder and close menu."""
        clips_dir = Path(self.clips_dir_callback())
        output_dir = clips_dir / ".pipeline_output"

        if not output_dir.exists():
            messagebox.showwarning(
                "Directory Not Found",
                f"Output directory does not exist:\n{output_dir}\n\nRun the pipeline first."
            )
        else:
            subprocess.run(["open", str(output_dir)])

        self._close_advanced_menu(parent_modal)

    def _show_about(self, parent_modal):
        """Show about dialog and close menu."""
        self._close_advanced_menu(parent_modal)
        messagebox.showinfo(
            "About TrailCam Animal ID",
            "TrailCam Animal ID\n\n"
            "A professional video review tool for analyzing trail camera footage.\n\n"
            "Features:\n"
            "• Automated animal detection\n"
            "• Fast video playback (up to 8x speed)\n"
            "• Keyboard shortcuts for efficient review\n"
            "• Session-based progress tracking"
        )

    def _get_preferences(self) -> dict:
        """Get current user preferences for state persistence.

        Returns:
            Dictionary of current preferences
        """
        return {
            'play_rate': self.speed_var.get(),
            'clip_pause_seconds': self.pause_duration_var.get()
        }
