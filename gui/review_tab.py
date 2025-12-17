"""Review tab for viewing clips with animal predictions."""

import csv
from pathlib import Path
from typing import List, Dict, Optional
import customtkinter as ctk
from tkinter import messagebox
from send2trash import send2trash
from gui.video_player import VideoPlayer
from gui.config import TITLE_FONT, HEADING_FONT, BODY_FONT, PLAY_RATE_RANGE, DEFAULT_CONFIG, PAUSE_DURATION_RANGE, COLORS, SUBHEADING_FONT, SMALL_FONT


class ReviewTab:
    """Tab for reviewing video clips with animal prediction overlays."""

    def __init__(self, parent, clips_dir_callback):
        self.parent = parent
        self.clips_dir_callback = clips_dir_callback

        self.clips: List[Dict] = []
        self.current_index: Optional[int] = None
        self.player: Optional[VideoPlayer] = None
        self.current_button: Optional[ctk.CTkButton] = None  # Track current clip button

        # Keyboard shortcut state
        self.shortcuts_enabled_globally = True  # Toggle from settings
        self.search_has_focus = False  # Track search box focus

        # Settings variables
        self.shortcuts_enabled_var = ctk.BooleanVar(value=True)
        self.auto_play_enabled_var = ctk.BooleanVar(value=True)
        self.pause_duration_var = ctk.DoubleVar(value=DEFAULT_CONFIG['clip_pause_seconds'])

        # Variables for UI state
        self.speed_var = ctk.DoubleVar(value=DEFAULT_CONFIG['play_rate'])
        self.progress_var = ctk.DoubleVar(value=0.0)

        self._create_widgets()

    def _create_widgets(self):
        """Create all UI widgets for the review tab."""
        # Main container with two-column layout
        main_frame = ctk.CTkFrame(self.parent)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure grid weights for video-first layout (25:75 split)
        main_frame.grid_columnconfigure(0, weight=25, minsize=220)  # Clip list (25%)
        main_frame.grid_columnconfigure(1, weight=75, minsize=700)  # Video area (75%)
        main_frame.grid_rowconfigure(0, weight=1)

        # === LEFT SIDE: Clip List ===
        left_frame = ctk.CTkFrame(main_frame, fg_color=COLORS['bg_secondary'])
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 3))

        ctk.CTkLabel(
            left_frame,
            text="Clips",
            font=ctk.CTkFont(**HEADING_FONT)
        ).pack(padx=10, pady=(10, 5))

        # Search entry
        search_container = ctk.CTkFrame(left_frame, fg_color=COLORS['bg_primary'])
        search_container.pack(padx=10, pady=(5, 10), fill="x")

        # Top row: search box and clear button
        search_frame = ctk.CTkFrame(search_container, fg_color=COLORS['bg_primary'])
        search_frame.pack(fill="x")

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search clips...",
            textvariable=self.search_var,
            width=170,
            fg_color=COLORS['ui_input'],
            border_color=COLORS['ui_frame']
        )
        self.search_entry.pack(side="left", fill="x", expand=True)

        # Clear button
        clear_btn = ctk.CTkButton(
            search_frame,
            text="×",
            width=30,
            command=self._clear_search,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        clear_btn.pack(side="left", padx=(5, 0))

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
        self.search_entry.bind("<Return>", self._jump_to_first_match)
        self.search_entry.bind("<Escape>", lambda e: self._clear_search())

        # Track focus to disable shortcuts during search
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)

        # Scrollable clip list
        self.clip_list_frame = ctk.CTkScrollableFrame(left_frame, width=220, fg_color=COLORS['bg_secondary'])
        self.clip_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Bind mouse wheel events for trackpad scrolling
        self._bind_mousewheel(self.clip_list_frame)

        # Load button
        ctk.CTkButton(
            left_frame,
            text="Load Clips",
            command=self._load_clips,
            width=200
        ).pack(padx=10, pady=(0, 10))

        # === RIGHT SIDE: Video Display and Controls ===
        right_frame = ctk.CTkFrame(main_frame, fg_color=COLORS['bg_primary'])
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 0))

        # Title
        ctk.CTkLabel(
            right_frame,
            text="Review Clips with Animal Predictions",
            font=ctk.CTkFont(**TITLE_FONT)
        ).pack(padx=10, pady=(10, 5))

        # Video display area - responsive sizing
        self.video_frame = ctk.CTkFrame(
            right_frame,
            fg_color=COLORS['video_bg']
        )
        self.video_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Configure grid to center video
        self.video_frame.grid_rowconfigure(0, weight=1)
        self.video_frame.grid_columnconfigure(0, weight=1)

        self.video_label = ctk.CTkLabel(
            self.video_frame,
            text="Load clips to start reviewing",
            fg_color=COLORS['video_bg']
        )
        self.video_label.grid(row=0, column=0, sticky="")

        # Bind resize events
        self.video_frame.bind("<Configure>", self._on_video_frame_resize)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(right_frame, variable=self.progress_var)
        self.progress_bar.pack(padx=10, pady=(0, 10), fill="x")
        self.progress_bar.set(0)

        # Overlay label for end-of-clip message (not packed initially)
        self.overlay_label = ctk.CTkLabel(
            right_frame,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=COLORS['bg_tertiary'],
            corner_radius=10,
            width=600,
            height=120
        )

        # Info section
        self.info_label = ctk.CTkLabel(
            right_frame,
            text="",
            font=ctk.CTkFont(**BODY_FONT),
            justify="left"
        )
        self.info_label.pack(padx=10, pady=(0, 10), anchor="w")

        # Control buttons frame
        controls_frame = ctk.CTkFrame(right_frame, fg_color=COLORS['bg_primary'])
        controls_frame.pack(padx=10, pady=5)

        ctk.CTkButton(
            controls_frame,
            text="< Previous",
            command=self._previous_clip,
            width=120
        ).pack(side="left", padx=5)

        # Play/Pause button
        self.play_pause_button = ctk.CTkButton(
            controls_frame,
            text="Pause",
            command=self._toggle_pause,
            width=120
        )
        self.play_pause_button.pack(side="left", padx=5)

        ctk.CTkButton(
            controls_frame,
            text="Delete",
            command=self._delete_clip,
            width=120,
            fg_color=COLORS['accent_danger'],
            hover_color=COLORS['accent_danger_hover']
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            controls_frame,
            text="Next >",
            command=self._next_clip,
            width=120
        ).pack(side="left", padx=5)

        # Playback speed slider
        speed_frame = ctk.CTkFrame(right_frame, fg_color=COLORS['bg_primary'])
        speed_frame.pack(padx=10, pady=10, fill="x")

        ctk.CTkLabel(
            speed_frame,
            text="Playback Speed:",
            font=ctk.CTkFont(**BODY_FONT)
        ).pack(side="left", padx=(0, 10))

        self.speed_value_label = ctk.CTkLabel(
            speed_frame,
            text=f"{self.speed_var.get():.1f}x",
            font=ctk.CTkFont(**HEADING_FONT),
            width=50
        )
        self.speed_value_label.pack(side="left", padx=5)

        speed_slider = ctk.CTkSlider(
            speed_frame,
            from_=PLAY_RATE_RANGE[0],
            to=PLAY_RATE_RANGE[1],
            variable=self.speed_var,
            number_of_steps=int((PLAY_RATE_RANGE[1] - PLAY_RATE_RANGE[0]) * 2),
            width=300,
            command=self._update_speed
        )
        speed_slider.pack(side="left", padx=10)

        # Playback Settings Panel
        settings_frame = ctk.CTkFrame(right_frame, fg_color=COLORS['bg_primary'])
        settings_frame.pack(padx=10, pady=(10, 0), fill="x")

        ctk.CTkLabel(
            settings_frame,
            text="Playback Settings:",
            font=ctk.CTkFont(**BODY_FONT)
        ).pack(side="left", padx=(0, 10))

        # Keyboard shortcuts toggle
        self.shortcuts_checkbox = ctk.CTkCheckBox(
            settings_frame,
            text="Keyboard Shortcuts",
            variable=self.shortcuts_enabled_var,
            command=self._on_shortcuts_toggle,
            font=ctk.CTkFont(**BODY_FONT)
        )
        self.shortcuts_checkbox.pack(side="left", padx=10)

        # Auto-play toggle
        self.auto_play_checkbox = ctk.CTkCheckBox(
            settings_frame,
            text="Auto-Play Next",
            variable=self.auto_play_enabled_var,
            font=ctk.CTkFont(**BODY_FONT)
        )
        self.auto_play_checkbox.pack(side="left", padx=10)

        # Pause duration slider
        pause_frame = ctk.CTkFrame(right_frame, fg_color=COLORS['bg_primary'])
        pause_frame.pack(padx=10, pady=(10, 0), fill="x")

        ctk.CTkLabel(
            pause_frame,
            text="Pause Between Clips:",
            font=ctk.CTkFont(**BODY_FONT)
        ).pack(side="left", padx=(0, 10))

        self.pause_value_label = ctk.CTkLabel(
            pause_frame,
            text=f"{self.pause_duration_var.get():.1f}s",
            font=ctk.CTkFont(**HEADING_FONT),
            width=50
        )
        self.pause_value_label.pack(side="left", padx=5)

        pause_slider = ctk.CTkSlider(
            pause_frame,
            from_=PAUSE_DURATION_RANGE[0],
            to=PAUSE_DURATION_RANGE[1],
            variable=self.pause_duration_var,
            number_of_steps=20,  # 0.5s increments
            width=200,
            command=self._update_pause_duration
        )
        pause_slider.pack(side="left", padx=10)

        # Keyboard shortcuts help
        shortcuts_text = "Keyboard: n=Next  p=Previous  d=Delete  space=Pause/Resume  q=Stop"
        ctk.CTkLabel(
            right_frame,
            text=shortcuts_text,
            font=ctk.CTkFont(**SMALL_FONT),
            text_color=COLORS['text_secondary']
        ).pack(padx=10, pady=(5, 10))

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

    def _update_speed(self, value):
        """Update playback speed label and video player."""
        speed = float(value)
        self.speed_value_label.configure(text=f"{speed:.1f}x")
        if self.player:
            self.player.set_speed(speed)

    def _on_video_frame_resize(self, event):
        """Handle video frame resize to update player dimensions."""
        if self.player and event.width > 1 and event.height > 1:
            available_width = max(400, event.width - 20)
            available_height = max(300, event.height - 20)
            self.player.set_target_container_size(available_width, available_height)

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

            # Auto-play first clip
            self._play_clip(0)

    def _create_clip_button(self, idx: int, clip: Dict):
        """Create a clip item with consistent formatting."""
        # Create container frame for clip item
        clip_frame = ctk.CTkFrame(
            self.clip_list_frame,
            width=200,
            height=65,
            fg_color=COLORS['ui_button']
        )
        clip_frame.pack(pady=2, padx=5, fill="x")
        clip_frame.pack_propagate(False)  # Maintain fixed size

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
        animals = clip['animals'].replace('&', ', ').replace('_', ', ')
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

        # Stop current playback
        if self.player:
            self.player.stop()

        clip = self.clips[index]
        self.current_index = index

        # Update info label with nicely formatted animals
        animals_display = clip['animals'].replace('&', ', ').replace('_', ', ')
        multiple_text = "Yes" if clip['multiple'] else "No"
        info_text = (
            f"Current: {clip['title']}\n"
            f"Animals: {animals_display}\n"
            f"Multiple: {multiple_text}"
        )
        self.info_label.configure(text=info_text)

        # Highlight current clip frame
        for i, c in enumerate(self.clips):
            if 'frame_widget' in c and c['frame_widget'].winfo_exists():
                if i == index:
                    c['frame_widget'].configure(fg_color=COLORS['accent_active'])
                else:
                    c['frame_widget'].configure(fg_color=COLORS['ui_button'])

        # Reset progress bar
        self.progress_var.set(0.0)

        # Reset play/pause button to "Pause"
        self.play_pause_button.configure(text="Pause")

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
        except Exception as e:
            messagebox.showerror(
                "Playback Error",
                f"Failed to play video:\n{e}"
            )

    def _update_frame(self, ctk_image):
        """Thread-safe callback to update video frame."""
        # Schedule GUI update on main thread
        self.video_label.after(0, lambda: self.video_label.configure(image=ctk_image, text=""))

    def _update_progress(self, progress: float):
        """Thread-safe callback to update progress bar."""
        # Schedule GUI update on main thread
        self.progress_bar.after(0, lambda: self.progress_var.set(progress))

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

        # Confirm with user
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Move {clip['title']} to Trash?\n\nAnimals: {clip['animals']}",
            icon='warning'
        )

        if result:
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

    def _toggle_pause(self):
        """Toggle pause/resume on current video."""
        if self.player:
            self.player.toggle_pause()
            # Update button text based on paused state
            if self.player.paused:
                self.play_pause_button.configure(text="Play")
            else:
                self.play_pause_button.configure(text="Pause")

    def _stop_playback(self):
        """Stop current playback."""
        if self.player:
            self.player.stop()
            self.video_label.configure(text="Playback stopped\nSelect a clip to resume")

    def _bind_mousewheel(self, widget):
        """Bind mouse wheel events for scrolling."""
        # macOS and Windows
        widget.bind("<MouseWheel>", self._on_mousewheel)
        # Linux
        widget.bind("<Button-4>", lambda e: self._on_mousewheel_linux(e, -1))
        widget.bind("<Button-5>", lambda e: self._on_mousewheel_linux(e, 1))

        # Also bind to children for better event capture
        for child in widget.winfo_children():
            child.bind("<MouseWheel>", self._on_mousewheel)
            child.bind("<Button-4>", lambda e: self._on_mousewheel_linux(e, -1))
            child.bind("<Button-5>", lambda e: self._on_mousewheel_linux(e, 1))

    def _on_mousewheel(self, event):
        """Handle mouse wheel scroll event."""
        # Get the canvas from CTkScrollableFrame
        canvas = self.clip_list_frame._parent_canvas
        canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    def _on_mousewheel_linux(self, event, direction):
        """Handle Linux mouse wheel events."""
        canvas = self.clip_list_frame._parent_canvas
        canvas.yview_scroll(direction, "units")

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
        # Restore all clips
        for clip in self.clips:
            if 'frame_widget' in clip and clip['frame_widget'].winfo_exists():
                clip['frame_widget'].pack(pady=2, padx=5, fill="x")

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

    def _update_pause_duration(self, value):
        """Update pause duration label."""
        duration = float(value)
        self.pause_value_label.configure(text=f"{duration:.1f}s")
