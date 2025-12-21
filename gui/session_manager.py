"""Session state management for TrailCam Animal ID GUI."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from appdirs import user_config_dir


class SessionManager:
    """Manages session state (clip index, directory path) in memory only."""

    def __init__(self):
        """Initialize session manager with default state."""
        self.current_clip_index: int = 0
        self.clips_directory: Optional[Path] = None
        self.csv_path: Optional[Path] = None

    def set_clips_directory(self, directory: Path):
        """Set the clips directory and derive CSV path.

        Args:
            directory: Path to clips directory
        """
        self.clips_directory = Path(directory)
        self.csv_path = self.clips_directory / ".pipeline_output" / "detection_csvs" / "animals_in_videos.csv"

    def save_clip_index(self, index: int):
        """Update current clip index.

        Args:
            index: Current clip index (0-based)
        """
        self.current_clip_index = index

    def get_last_state(self) -> dict:
        """Return last session state.

        Returns:
            Dictionary with session state (index, directory, csv_path)
        """
        return {
            'index': self.current_clip_index,
            'directory': self.clips_directory,
            'csv_path': self.csv_path
        }

    def has_existing_outputs(self) -> bool:
        """Check if pipeline outputs exist for current directory.

        Returns:
            True if CSV file exists, False otherwise
        """
        if self.csv_path and self.csv_path.exists():
            return True
        return False

    def reset(self):
        """Reset session state to defaults."""
        self.current_clip_index = 0
        self.clips_directory = None
        self.csv_path = None

    def _get_config_path(self) -> Path:
        """Get platform-appropriate config file path.

        Returns:
            Path to session.json config file
        """
        config_dir = Path(user_config_dir("TrailCamAnimalID", "TrailCamAnimalID"))
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "session.json"

    def load_state(self) -> Optional[dict]:
        """Load state from disk.

        Returns:
            State dictionary if valid file exists, None otherwise
        """
        config_path = self._get_config_path()
        if not config_path.exists():
            return None

        try:
            with open(config_path, 'r') as f:
                state = json.load(f)

            # Validate version
            if state.get('version') != '1.0':
                return None

            return state
        except (json.JSONDecodeError, OSError):
            return None  # Corrupt file, treat as fresh install

    def validate_state(self, state: dict) -> bool:
        """Validate that saved state is still valid.

        Args:
            state: State dictionary from load_state()

        Returns:
            True if state is valid and usable, False otherwise
        """
        if not state or 'session' not in state:
            return False

        session = state['session']

        # Check clips_directory exists
        clips_dir = session.get('clips_directory')
        if not clips_dir or not Path(clips_dir).exists():
            return False

        # Check CSV file exists
        csv_path = session.get('csv_path')
        if not csv_path or not Path(csv_path).exists():
            return False

        return True

    def save_state(self, preferences: dict):
        """Save current state to disk.

        Args:
            preferences: Dictionary of user preferences to persist
        """
        config_path = self._get_config_path()

        state = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'session': {
                'clips_directory': str(self.clips_directory) if self.clips_directory else None,
                'current_clip_index': self.current_clip_index,
                'csv_path': str(self.csv_path) if self.csv_path else None
            },
            'preferences': preferences
        }

        try:
            with open(config_path, 'w') as f:
                json.dump(state, f, indent=2)
        except OSError:
            pass  # Silent fail if can't write

    def restore_from_state(self, state: dict) -> dict:
        """Restore session from loaded state.

        Args:
            state: State dictionary from load_state()

        Returns:
            Preferences dictionary
        """
        session = state.get('session', {})

        clips_dir = session.get('clips_directory')
        if clips_dir:
            self.clips_directory = Path(clips_dir)

        self.current_clip_index = session.get('current_clip_index', 0)

        csv_path = session.get('csv_path')
        if csv_path:
            self.csv_path = Path(csv_path)

        return state.get('preferences', {})
