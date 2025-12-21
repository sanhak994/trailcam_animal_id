"""Keyboard shortcuts help overlay modal."""

import customtkinter as ctk
from gui.config import TITLE_FONT, HEADING_FONT, BODY_FONT, COLORS


class ShortcutsHelpModal(ctk.CTkToplevel):
    """Modal overlay displaying keyboard shortcuts reference."""

    def __init__(self, parent):
        super().__init__(parent)

        # Window configuration
        self.title("Keyboard Shortcuts")
        self.geometry("600x500")
        self.resizable(False, False)

        # Center on parent window
        self.transient(parent)
        self.grab_set()

        # Set appearance
        self.configure(fg_color=COLORS['bg_secondary'])

        # Create content
        self._create_widgets()

        # Bind Esc and h to close
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<h>", lambda e: self.destroy())
        self.bind("<H>", lambda e: self.destroy())

    def _create_widgets(self):
        """Create modal content."""
        # Title
        ctk.CTkLabel(
            self,
            text="Keyboard Shortcuts",
            font=ctk.CTkFont(**TITLE_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 30))

        # Two-column layout frame
        columns_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_secondary'])
        columns_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # Configure grid for two columns
        columns_frame.grid_columnconfigure(0, weight=1)
        columns_frame.grid_columnconfigure(1, weight=1)

        # Left Column - Navigation and Playback
        left_column = ctk.CTkFrame(columns_frame, fg_color=COLORS['bg_primary'])
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Navigation section
        ctk.CTkLabel(
            left_column,
            text="Navigation",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", padx=15, pady=(15, 10))

        navigation_shortcuts = [
            ("n", "Next clip"),
            ("p", "Previous clip"),
            ("d", "Delete clip"),
            ("q", "Stop playback"),
        ]

        for key, description in navigation_shortcuts:
            self._create_shortcut_row(left_column, key, description)

        # Playback section
        ctk.CTkLabel(
            left_column,
            text="Playback",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", padx=15, pady=(20, 10))

        playback_shortcuts = [
            ("space", "Pause/Resume"),
            ("+ or =", "Speed up"),
            ("-", "Slow down"),
            ("0", "Reset speed (1x)"),
        ]

        for key, description in playback_shortcuts:
            self._create_shortcut_row(left_column, key, description)

        # Right Column - Settings and View
        right_column = ctk.CTkFrame(columns_frame, fg_color=COLORS['bg_primary'])
        right_column.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Settings section
        ctk.CTkLabel(
            right_column,
            text="Settings",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", padx=15, pady=(15, 10))

        settings_shortcuts = [
            ("a", "Toggle auto-play"),
            ("h", "Show/hide help"),
        ]

        for key, description in settings_shortcuts:
            self._create_shortcut_row(right_column, key, description)

        # Speed steps info
        ctk.CTkLabel(
            right_column,
            text="Speed Steps",
            font=ctk.CTkFont(**HEADING_FONT),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", padx=15, pady=(20, 10))

        speed_info = ctk.CTkLabel(
            right_column,
            text="1x → 1.5x → 2x → 4x → 8x",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_secondary'],
            justify="left"
        )
        speed_info.pack(anchor="w", padx=15, pady=(0, 5))

        # Close instruction
        ctk.CTkLabel(
            self,
            text="Press 'h' or 'Esc' to close",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 15))

    def _create_shortcut_row(self, parent, key: str, description: str):
        """Create a row displaying a keyboard shortcut and its description."""
        row_frame = ctk.CTkFrame(parent, fg_color=COLORS['bg_primary'])
        row_frame.pack(fill="x", padx=15, pady=3)

        # Key label (monospace, highlighted)
        ctk.CTkLabel(
            row_frame,
            text=key,
            font=ctk.CTkFont(family="SF Mono", size=12, weight="bold"),
            text_color=COLORS['text_primary'],
            width=80,
            anchor="w"
        ).pack(side="left")

        # Description label
        ctk.CTkLabel(
            row_frame,
            text=description,
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_secondary'],
            anchor="w"
        ).pack(side="left", fill="x", expand=True)
