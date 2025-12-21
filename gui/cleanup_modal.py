"""Cleanup modal for managing pipeline outputs."""

import subprocess
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox
from send2trash import send2trash
from gui.config import TITLE_FONT, HEADING_FONT, BODY_FONT, COLORS


class CleanupModal(ctk.CTkToplevel):
    """Modal for managing pipeline outputs."""

    def __init__(self, parent, clips_dir):
        super().__init__(parent)

        # Window configuration
        self.title("Pipeline Cleanup")
        self.geometry("600x400")
        self.resizable(False, False)

        # Center on parent window
        self.transient(parent)
        self.grab_set()

        # Set appearance
        self.configure(fg_color=COLORS['bg_secondary'])

        # Store clips directory
        self.clips_dir = Path(clips_dir)

        # Create content
        self._create_widgets()

        # Auto-refresh on open
        self._refresh_info()

        # Bind Esc to close
        self.bind("<Escape>", lambda e: self.destroy())

    def _create_widgets(self):
        """Create modal content."""
        # Title
        ctk.CTkLabel(
            self,
            text="Pipeline Output Management",
            font=ctk.CTkFont(**TITLE_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10))

        # Info section
        info_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_primary'])
        info_frame.pack(padx=30, pady=(10, 20), fill="both", expand=True)

        self.info_label = ctk.CTkLabel(
            info_frame,
            text="Loading output information...",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_primary'],
            justify="left",
            anchor="nw"
        )
        self.info_label.pack(padx=20, pady=20, fill="both", expand=True)

        # Buttons frame
        button_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_secondary'])
        button_frame.pack(padx=30, pady=(0, 20))

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

        # Close instruction
        ctk.CTkLabel(
            self,
            text="Press 'Esc' to close",
            font=ctk.CTkFont(**BODY_FONT),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 15))

    def _get_output_dir(self) -> Path:
        """Get the pipeline output directory."""
        return self.clips_dir / ".pipeline_output"

    def _refresh_info(self):
        """Refresh output directory information."""
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
            f"Output Directory:\n{output_dir}\n\n"
            f"Total Files: {total_files:,}\n"
            f"Total Size: {size_str}\n\n"
            f"Subdirectories:\n"
            f"  • frames/\n"
            f"  • detection_csvs/"
        )

        self.info_label.configure(text=info_text)

    def _open_in_finder(self):
        """Open output directory in Finder."""
        output_dir = self._get_output_dir()

        if not output_dir.exists():
            messagebox.showwarning(
                "Directory Not Found",
                f"Output directory does not exist:\n{output_dir}"
            )
            return

        subprocess.run(["open", str(output_dir)])

    def _delete_outputs(self):
        """Delete all pipeline outputs."""
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
