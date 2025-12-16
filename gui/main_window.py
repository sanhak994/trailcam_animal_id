"""Main window for the TrailCam Animal ID GUI application."""

import customtkinter as ctk
from gui.pipeline_tab import PipelineTab


class TrailCamApp(ctk.CTk):
    """Main application window with tabbed interface."""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("TrailCam Animal ID Pipeline")
        self.geometry("1000x800")

        # Set appearance mode - use "dark" directly to bypass darkdetect macOS 26 bug
        # TODO: Switch back to "system" when darkdetect supports macOS 26+
        try:
            ctk.set_appearance_mode("system")
        except Exception:
            # Fallback if darkdetect fails on newer macOS
            ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create tab view
        self.tabview = ctk.CTkTabview(self, width=980, height=750)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        # Add tabs
        self.tabview.add("Pipeline")
        # self.tabview.add("Review")  # TODO: Add in Phase 3
        # self.tabview.add("Cleanup")  # TODO: Add in Phase 3

        # Initialize tab content
        self.pipeline_tab = PipelineTab(self.tabview.tab("Pipeline"))

        # Status bar
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            anchor="w",
            height=30
        )
        self.status_label.pack(side="bottom", fill="x", padx=10, pady=(0, 5))

    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.configure(text=message)
