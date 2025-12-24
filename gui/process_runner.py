"""Process runner for executing subprocesses in the background without blocking the GUI."""

import os
import subprocess
import sys
import threading
from pathlib import Path
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
        # Check if we should use backend executable (frozen mode)
        if getattr(sys, 'frozen', False):
            return self._run_with_backend(command)
        else:
            return self._run_subprocess(command)

    def _run_with_backend(self, command: List[str]):
        """
        Run script using backend executable (has all ML dependencies).

        Args:
            command: Command to execute (script path + args)
        """
        # Find backend executable
        backend_path = Path(sys.executable).parent / 'trailcam_backend'

        if not backend_path.exists():
            self.log_callback(f"Error: Backend not found at {backend_path}")
            if self.completion_callback:
                self.completion_callback(-1)
            return

        # Build command: backend_exe + script + args
        script_path = command[0]
        args = command[1:]
        new_command = [str(backend_path), script_path] + args

        # Create environment with unbuffered Python output
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        # Set working directory to _MEIPASS
        cwd = sys._MEIPASS

        try:
            self.process = subprocess.Popen(
                new_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                bufsize=1,
                universal_newlines=True,
                env=env,
                cwd=cwd
            )

            # Read line by line
            for line in iter(self.process.stdout.readline, ''):
                if self.cancelled:
                    break

                if line:
                    line_stripped = line.rstrip()
                    # Update GUI log (callback should handle thread-safety)
                    self.log_callback(line_stripped)

                    # Parse progress if callback provided
                    if self.progress_callback:
                        # Progress callback can parse tqdm or other progress formats
                        self.progress_callback(line_stripped)

                    # Detect pipeline completion message
                    if "Pipeline complete." in line_stripped:
                        self.log_callback("Detected pipeline completion, cleaning up processes...")

                        # Kill process tree to clean up orphaned children
                        import signal
                        try:
                            # Kill entire process group (parent + all children)
                            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                            # Give it 1 second to terminate gracefully
                            try:
                                self.process.wait(timeout=1)
                            except subprocess.TimeoutExpired:
                                # Force kill if it doesn't terminate
                                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                                self.process.wait()

                            self.log_callback("Process cleanup complete")
                        except Exception as e:
                            self.log_callback(f"Error during process cleanup: {e}")

                        # Notify completion
                        if self.completion_callback:
                            self.completion_callback(0)
                        return

            # Wait for process to complete
            return_code = self.process.wait()

            # Notify completion
            if self.completion_callback and not self.cancelled:
                self.completion_callback(return_code)

        except Exception as e:
            self.log_callback(f"Error running process: {e}")
            if self.completion_callback:
                self.completion_callback(-1)

    def _run_subprocess(self, command: List[str]):
        """
        Original subprocess implementation for development mode.

        Args:
            command: Command to execute
        """
        # Create environment with unbuffered Python output
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        # Set working directory based on execution mode
        if getattr(sys, 'frozen', False):
            # Packaged app - use _MEIPASS as working directory
            cwd = sys._MEIPASS
        else:
            # Development - use project root
            cwd = str(Path(__file__).parent.parent)

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                bufsize=1,
                universal_newlines=True,
                env=env,
                cwd=cwd
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
