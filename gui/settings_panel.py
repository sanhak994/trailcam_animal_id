"""Settings panel modal overlay."""

import customtkinter as ctk
from gui.config import TITLE_FONT, HEADING_FONT, BODY_FONT, PLAY_RATE_RANGE, PAUSE_DURATION_RANGE, COLORS


class SettingsPanelModal(ctk.CTkToplevel):
    """Modal overlay for playback settings."""

    def __init__(self, parent, speed_var, auto_play_var, pause_duration_var, shortcuts_enabled_var,
                 on_speed_change, on_pause_duration_change, on_shortcuts_toggle, on_close):
        super().__init__(parent)

        # Store callbacks and variables
        self.speed_var = speed_var
        self.auto_play_var = auto_play_var
        self.pause_duration_var = pause_duration_var
        self.shortcuts_enabled_var = shortcuts_enabled_var
        self.on_speed_change = on_speed_change
        self.on_pause_duration_change = on_pause_duration_change
        self.on_shortcuts_toggle = on_shortcuts_toggle
        self.on_close_callback = on_close

        # Window configuration
        self.title("Playback Settings")
        self.geometry("500x400")
        self.resizable(False, False)

        # Center on parent window
        self.transient(parent)
        self.grab_set()

        # Set appearance
        self.configure(fg_color=COLORS['bg_secondary'])

        # Create content
        self._create_widgets()

        # Bind close events
        self.bind("<Escape>", lambda e: self._close())
        self.bind("<s>", lambda e: self._close())
        self.bind("<S>", lambda e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _create_widgets(self):
        """Create modal content."""
        # Title
        ctk.CTkLabel(
            self,
            text="Playback Settings",
            font=ctk.CTkFont(**TITLE_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 30))

        # Content frame
        content_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_primary'])
        content_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # Playback Speed
        speed_frame = ctk.CTkFrame(content_frame, fg_color=COLORS['bg_primary'])
        speed_frame.pack(padx=20, pady=(20, 15), fill="x")

        ctk.CTkLabel(
            speed_frame,
            text="Playback Speed:",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary']
        ).pack(side="left", padx=(0, 10))

        self.speed_value_label = ctk.CTkLabel(
            speed_frame,
            text=f"{self.speed_var.get():.1f}x",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary'],
            width=50
        )
        self.speed_value_label.pack(side="left", padx=5)

        speed_slider = ctk.CTkSlider(
            speed_frame,
            from_=PLAY_RATE_RANGE[0],
            to=PLAY_RATE_RANGE[1],
            variable=self.speed_var,
            number_of_steps=int((PLAY_RATE_RANGE[1] - PLAY_RATE_RANGE[0]) * 2),
            width=250,
            command=self._update_speed,
            fg_color=COLORS['bg_tertiary'],
            progress_color=COLORS['text_secondary'],
            button_color=COLORS['text_primary'],
            button_hover_color=COLORS['text_primary']
        )
        speed_slider.pack(side="left", padx=10)

        # Auto-Play Toggle
        auto_play_frame = ctk.CTkFrame(content_frame, fg_color=COLORS['bg_primary'])
        auto_play_frame.pack(padx=20, pady=15, fill="x")

        ctk.CTkLabel(
            auto_play_frame,
            text="Auto-Play Next Clip:",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary']
        ).pack(side="left", padx=(0, 10))

        auto_play_checkbox = ctk.CTkCheckBox(
            auto_play_frame,
            text="Enabled",
            variable=self.auto_play_var,
            command=self._on_auto_play_toggle,
            font=ctk.CTkFont(**BODY_FONT),
            fg_color=COLORS['text_secondary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            checkmark_color=COLORS['bg_primary']
        )
        auto_play_checkbox.pack(side="left", padx=10)

        # Pause Duration (only visible if auto-play is enabled)
        self.pause_frame = ctk.CTkFrame(content_frame, fg_color=COLORS['bg_primary'])
        self._update_pause_frame_visibility()  # Show/hide based on current auto-play state

        ctk.CTkLabel(
            self.pause_frame,
            text="Pause Between Clips:",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary']
        ).pack(side="left", padx=(0, 10))

        self.pause_value_label = ctk.CTkLabel(
            self.pause_frame,
            text=f"{self.pause_duration_var.get():.1f}s",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary'],
            width=50
        )
        self.pause_value_label.pack(side="left", padx=5)

        pause_slider = ctk.CTkSlider(
            self.pause_frame,
            from_=PAUSE_DURATION_RANGE[0],
            to=PAUSE_DURATION_RANGE[1],
            variable=self.pause_duration_var,
            number_of_steps=20,
            width=200,
            command=self._update_pause_duration,
            fg_color=COLORS['bg_tertiary'],
            progress_color=COLORS['text_secondary'],
            button_color=COLORS['text_primary'],
            button_hover_color=COLORS['text_primary']
        )
        pause_slider.pack(side="left", padx=10)

        # Keyboard Shortcuts Toggle
        shortcuts_frame = ctk.CTkFrame(content_frame, fg_color=COLORS['bg_primary'])
        shortcuts_frame.pack(padx=20, pady=15, fill="x")

        ctk.CTkLabel(
            shortcuts_frame,
            text="Keyboard Shortcuts:",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary']
        ).pack(side="left", padx=(0, 10))

        shortcuts_checkbox = ctk.CTkCheckBox(
            shortcuts_frame,
            text="Enabled",
            variable=self.shortcuts_enabled_var,
            command=self.on_shortcuts_toggle,
            font=ctk.CTkFont(**BODY_FONT),
            fg_color=COLORS['text_secondary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            checkmark_color=COLORS['bg_primary']
        )
        shortcuts_checkbox.pack(side="left", padx=10)

        # Close instruction
        ctk.CTkLabel(
            self,
            text="Press 's' or 'Esc' to close",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 15))

    def _update_speed(self, value):
        """Update speed label and notify parent."""
        speed = float(value)
        self.speed_value_label.configure(text=f"{speed:.1f}x")
        self.on_speed_change(speed)

    def _update_pause_duration(self, value):
        """Update pause duration label and notify parent."""
        duration = float(value)
        self.pause_value_label.configure(text=f"{duration:.1f}s")
        self.on_pause_duration_change(duration)

    def _on_auto_play_toggle(self):
        """Handle auto-play toggle and show/hide pause duration."""
        self._update_pause_frame_visibility()

    def _update_pause_frame_visibility(self):
        """Show or hide pause duration based on auto-play state."""
        if self.auto_play_var.get():
            self.pause_frame.pack(padx=20, pady=15, fill="x")
        else:
            self.pause_frame.pack_forget()

    def _close(self):
        """Close modal and trigger callback."""
        self.on_close_callback()
        self.destroy()
