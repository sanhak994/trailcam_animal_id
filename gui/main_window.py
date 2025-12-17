"""Main window for the TrailCam Animal ID GUI application."""

import customtkinter as ctk
from gui.pipeline_tab import PipelineTab
from gui.cleanup_tab import CleanupTab
from gui.review_tab import ReviewTab


class TrailCamApp(ctk.CTk):
    """Main application window with tabbed interface."""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("TrailCam Animal ID Pipeline")
        self.geometry("1000x800")

        # Set modern dark appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Create tab view
        self.tabview = ctk.CTkTabview(self, width=980, height=750)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        # Add tabs
        self.tabview.add("Pipeline")
        self.tabview.add("Cleanup")
        self.tabview.add("Review")

        # Initialize tab content
        self.pipeline_tab = PipelineTab(self.tabview.tab("Pipeline"))
        self.cleanup_tab = CleanupTab(
            self.tabview.tab("Cleanup"),
            clips_dir_callback=lambda: self.pipeline_tab.clips_dir_var.get()
        )
        self.review_tab = ReviewTab(
            self.tabview.tab("Review"),
            clips_dir_callback=lambda: self.pipeline_tab.clips_dir_var.get()
        )

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
