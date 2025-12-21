"""Cleanup tab for managing pipeline outputs."""

import subprocess
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox
from send2trash import send2trash
from gui.config import HEADING_FONT, BODY_FONT, COLORS


class CleanupTab:
    """Simple cleanup tab for managing pipeline outputs."""

    def __init__(self, parent, clips_dir_callback):
        self.parent = parent
        self.clips_dir_callback = clips_dir_callback  # Function to get clips dir
        self._create_widgets()

    def _create_widgets(self):
        # Info section
        info_frame = ctk.CTkFrame(self.parent, fg_color=COLORS['bg_secondary'])
        info_frame.pack(padx=25, pady=15, fill="both", expand=True)

        ctk.CTkLabel(
            info_frame,
            text="Pipeline Output Management",
            font=ctk.CTkFont(**HEADING_FONT)
        ).pack(padx=15, pady=(15, 10), anchor="w")

        self.info_label = ctk.CTkLabel(
            info_frame,
            text="Select a clips directory in the Pipeline tab to see output info",
            font=ctk.CTkFont(**BODY_FONT),
            justify="left"
        )
        self.info_label.pack(padx=15, pady=10, anchor="w")

        # Buttons frame
        button_frame = ctk.CTkFrame(info_frame, fg_color=COLORS['bg_primary'])
        button_frame.pack(padx=15, pady=10, anchor="w")

        ctk.CTkButton(
            button_frame,
            text="Refresh Info",
            command=self._refresh_info,
            width=150,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['ui_button_hover']
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Open in Finder",
            command=self._open_in_finder,
            width=150,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['text_secondary'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['ui_button_hover']
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Delete All Outputs",
            command=self._delete_outputs,
            width=150,
            fg_color=COLORS['bg_primary'],
            border_color=COLORS['accent_danger'],
            border_width=1,
            text_color=COLORS['text_primary'],
            hover_color=COLORS['accent_danger']
        ).pack(side="left", padx=5)

    def _get_output_dir(self) -> Path:
        clips_dir = self.clips_dir_callback()
        return Path(clips_dir) / ".pipeline_output"

    def _refresh_info(self):
        output_dir = self._get_output_dir()

        if not output_dir.exists():
            self.info_label.configure(
                text=f"Output directory does not exist:\n{output_dir}\n\n"
                     "Run the pipeline first to generate outputs."
            )
            return

        # Calculate directory info
        total_size = 0
        total_files = 0

        for item in output_dir.rglob("*"):
            if item.is_file():
                total_files += 1
                total_size += item.stat().st_size

        # Format size
        if total_size < 1024:
            size_str = f"{total_size} B"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        elif total_size < 1024 * 1024 * 1024:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"

        info_text = (
            f"Output Directory: {output_dir}\n\n"
            f"Total Files: {total_files:,}\n"
            f"Total Size: {size_str}\n\n"
            f"Subdirectories:\n"
            f"  • frames/\n"
            f"  • detection_csvs/"
        )

        self.info_label.configure(text=info_text)

    def _open_in_finder(self):
        output_dir = self._get_output_dir()

        if not output_dir.exists():
            messagebox.showwarning(
                "Directory Not Found",
                f"Output directory does not exist:\n{output_dir}"
            )
            return

        subprocess.run(["open", str(output_dir)])

    def _delete_outputs(self):
        output_dir = self._get_output_dir()

        if not output_dir.exists():
            messagebox.showinfo(
                "Nothing to Delete",
                "Output directory does not exist."
            )
            return

        # Confirmation dialog
        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete all pipeline outputs?\n\n"
            f"This will move the following to Trash:\n{output_dir}\n\n"
            f"This action can be undone by restoring from Trash.",
            icon='warning'
        )

        if result:
            try:
                send2trash(str(output_dir))
                messagebox.showinfo(
                    "Success",
                    "Pipeline outputs moved to Trash successfully."
                )
                self._refresh_info()
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to delete outputs:\n{e}"
                )
