"""Process runner for executing subprocesses in the background without blocking the GUI."""

import os
import subprocess
import threading
from typing import List, Callable, Optional


class ProcessRunner:
    """Manages subprocess execution with real-time output capture and cancellation."""

    def __init__(self, log_callback: Callable[[str], None],
                 progress_callback: Optional[Callable[[dict], None]] = None,
                 completion_callback: Optional[Callable[[int], None]] = None):
        """
        Initialize the process runner.

        Args:
            log_callback: Function to call with each line of output
            progress_callback: Optional function to call with progress updates
            completion_callback: Optional function to call when process completes (with exit code)
        """
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.process: Optional[subprocess.Popen] = None
        self.thread: Optional[threading.Thread] = None
        self.cancelled = False

    def run(self, command: List[str]):
        """
        Run command in background thread.

        Args:
            command: List of command arguments (e.g., ['python3', 'script.py', '--arg', 'value'])
        """
        self.cancelled = False
        self.thread = threading.Thread(target=self._run_process, args=(command,), daemon=True)
        self.thread.start()

    def _run_process(self, command: List[str]):
        """
        Thread worker that runs subprocess.

        Args:
            command: Command to execute
        """
        # Create environment with unbuffered Python output
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                bufsize=1,
                universal_newlines=True,
                env=env
            )

            # Read line by line
            for line in iter(self.process.stdout.readline, ''):
                if self.cancelled:
                    break

                if line:
                    # Update GUI log (callback should handle thread-safety)
                    self.log_callback(line.rstrip())

                    # Parse progress if callback provided
                    if self.progress_callback:
                        # Progress callback can parse tqdm or other progress formats
                        self.progress_callback(line.rstrip())

            # Wait for process to complete
            return_code = self.process.wait()

            # Notify completion
            if self.completion_callback and not self.cancelled:
                self.completion_callback(return_code)

        except Exception as e:
            self.log_callback(f"Error running process: {e}")
            if self.completion_callback:
                self.completion_callback(-1)

    def cancel(self):
        """Gracefully stop running process."""
        self.cancelled = True
        if self.process:
            try:
                # Try graceful termination first
                self.process.terminate()

                # Wait up to 5 seconds for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                    self.log_callback("Process terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    self.process.kill()
                    self.log_callback("Process forcefully killed")

            except Exception as e:
                self.log_callback(f"Error cancelling process: {e}")

    def is_running(self) -> bool:
        """Check if process is currently running."""
        return self.process is not None and self.process.poll() is None
