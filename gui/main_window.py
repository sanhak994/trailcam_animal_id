"""Main window for the TrailCam Animal ID GUI application."""

import customtkinter as ctk
from pathlib import Path
from gui.session_manager import SessionManager
from gui.review_tab import ReviewTab
from gui.pipeline_wizard import PipelineWizard
from gui.config import TITLE_FONT, HEADING_FONT, BODY_FONT, COLORS, DEFAULT_CONFIG


class TrailCamApp(ctk.CTk):
    """Main application window with Netflix-style single-screen interface."""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("TrailCam Animal ID")
        self.geometry("1200x900")

        # Set pure black appearance
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=COLORS['bg_primary'])

        # Bind window close event to save state
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Session manager for state tracking
        self.session = SessionManager()

        # Set default clips directory if exists
        default_clips_dir = Path(DEFAULT_CONFIG['clips_dir'])
        if default_clips_dir.exists():
            self.session.set_clips_directory(default_clips_dir)

        # Main content frame (will hold startup screen or review screen)
        self.content_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_primary'])
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Status bar
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            anchor="w",
            height=30,
            fg_color=COLORS['bg_secondary'],
            text_color=COLORS['text_secondary']
        )
        self.status_label.pack(side="bottom", fill="x", padx=10, pady=(0, 5))

        # Load saved state and auto-resume if valid
        saved_state = self.session.load_state()

        if saved_state and self.session.validate_state(saved_state):
            # Valid saved session - auto-resume directly to review
            preferences = self.session.restore_from_state(saved_state)
            self._auto_resume_review(preferences)
        else:
            # No valid session - show startup screen
            self._show_startup_screen()

    def _show_startup_screen(self):
        """Show startup screen with Resume or New Analysis options."""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Detect if we have existing outputs
        has_outputs = self.session.has_existing_outputs()

        # Create startup container (centered)
        startup_container = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS['bg_primary']
        )
        startup_container.place(relx=0.5, rely=0.5, anchor="center")

        # App title
        ctk.CTkLabel(
            startup_container,
            text="TrailCam Animal ID",
            font=ctk.CTkFont(**TITLE_FONT),
            text_color=COLORS['text_primary']
        ).pack(pady=(0, 40))

        if has_outputs:
            # Show Resume option (primary)
            state = self.session.get_last_state()

            # Session info
            info_text = f"Last session: {state['directory'].name if state['directory'] else 'Unknown'}"
            ctk.CTkLabel(
                startup_container,
                text=info_text,
                font=ctk.CTkFont(**BODY_FONT),
                text_color=COLORS['text_secondary']
            ).pack(pady=(0, 20))

            # Resume button (large, primary)
            ctk.CTkButton(
                startup_container,
                text="Resume Review",
                command=self._resume_review,
                width=300,
                height=60,
                font=ctk.CTkFont(**HEADING_FONT),
                fg_color=COLORS['bg_primary'],
                border_color=COLORS['text_secondary'],
                border_width=2,
                text_color=COLORS['text_primary'],
                hover_color=COLORS['accent_active_hover']
            ).pack(pady=10)

            # New Analysis button (smaller, secondary)
            ctk.CTkButton(
                startup_container,
                text="Start New Analysis",
                command=self._start_new_analysis,
                width=300,
                height=40,
                font=ctk.CTkFont(**BODY_FONT),
                fg_color=COLORS['bg_primary'],
                border_color=COLORS['text_secondary'],
                border_width=1,
                text_color=COLORS['text_primary'],
                hover_color=COLORS['ui_button_hover']
            ).pack(pady=10)

        else:
            # Show New Analysis option (primary)
            ctk.CTkLabel(
                startup_container,
                text="Analyze your trail camera videos",
                font=ctk.CTkFont(**BODY_FONT),
                text_color=COLORS['text_secondary']
            ).pack(pady=(0, 20))

            # New Analysis button (large, primary)
            ctk.CTkButton(
                startup_container,
                text="Start New Analysis",
                command=self._start_new_analysis,
                width=300,
                height=60,
                font=ctk.CTkFont(**HEADING_FONT),
                fg_color=COLORS['bg_primary'],
                border_color=COLORS['text_secondary'],
                border_width=2,
                text_color=COLORS['text_primary'],
                hover_color=COLORS['accent_active_hover']
            ).pack(pady=10)

    def _start_new_analysis(self):
        """Show pipeline wizard for new analysis."""
        wizard = PipelineWizard(
            self,
            self.session,
            completion_callback=self._on_wizard_complete
        )
        wizard.focus()

    def _resume_review(self):
        """Resume review from last session."""
        self._show_review_screen(resume=True)

    def _on_wizard_complete(self, skip_pipeline):
        """Handle wizard completion.

        Args:
            skip_pipeline: True if pipeline was skipped (outputs exist)
        """
        # Wizard completed - show review screen
        self._show_review_screen(resume=True)

    def _show_review_screen(self, resume=False):
        """Show main review screen.

        Args:
            resume: If True, load from last session index
        """
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create review screen using existing ReviewTab component
        # (Will be refactored to ReviewScreen in later iterations)
        self.review_screen = ReviewTab(
            self.content_frame,
            clips_dir_callback=lambda: str(self.session.clips_directory) if self.session.clips_directory else DEFAULT_CONFIG['clips_dir'],
            session_manager=self.session
        )

        # Auto-load clips if resuming
        if resume and self.session.has_existing_outputs():
            self.review_screen._load_clips()
            # Jump to last clip index if available
            if self.session.current_clip_index > 0 and self.session.current_clip_index < len(self.review_screen.clips):
                self.review_screen._play_clip(self.session.current_clip_index)

        self.update_status("Review mode active")

    def _auto_resume_review(self, preferences: dict):
        """Auto-resume review screen from saved state.

        Args:
            preferences: Dictionary of user preferences from saved state
        """
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create review tab with saved preferences
        self.review_screen = ReviewTab(
            self.content_frame,
            clips_dir_callback=lambda: str(self.session.clips_directory) if self.session.clips_directory else DEFAULT_CONFIG['clips_dir'],
            session_manager=self.session,
            preferences=preferences
        )

        # Auto-load clips from saved session
        if self.session.has_existing_outputs():
            self.review_screen._load_clips()
            # Jump to last clip index if available
            if self.session.current_clip_index >= 0 and self.session.current_clip_index < len(self.review_screen.clips):
                self.review_screen._play_clip(self.session.current_clip_index)

        # Show brief toast notification
        self.status_label.configure(
            text=f"Resumed at clip {self.session.current_clip_index + 1}",
            text_color=COLORS['text_primary']
        )

        # Clear toast after 3 seconds
        self.after(3000, lambda: self.status_label.configure(
            text="Ready",
            text_color=COLORS['text_secondary']
        ))

    def _show_pipeline_wizard(self):
        """Show pipeline wizard modal.

        Modal wizard with steps:
        1. Select directory
        2. Configure settings
        3. Run pipeline
        4. Auto-transition to review
        """
        # TODO: Implement in Phase 2
        pass

    def _show_cleanup_modal(self):
        """Show cleanup modal for pipeline outputs."""
        # TODO: Implement in Phase 4
        pass

    def _show_advanced_menu(self):
        """Show dropdown menu with advanced options."""
        # TODO: Implement in Phase 6
        # Menu items:
        # - Start New Analysis
        # - Pipeline Cleanup
        # - Open Output Folder
        # - About
        pass

    def update_status(self, message: str):
        """Update the status bar message.

        Args:
            message: Status message to display
        """
        self.status_label.configure(text=message)

    def _on_closing(self):
        """Handle window close event - save state before quitting."""
        # Save state if review screen exists
        if hasattr(self, 'review_screen') and self.review_screen:
            try:
                preferences = self.review_screen._get_preferences()
                self.session.save_state(preferences)
            except:
                pass  # Silent fail if save fails

        # Destroy window
        self.destroy()
