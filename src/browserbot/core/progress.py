"""
Simplified progress system using only halo spinners.
No configuration needed - all progress uses the same halo style.
"""

import asyncio
from typing import Optional, Any, Callable
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
import sys
from enum import Enum

from halo import Halo

from .logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Status indicators for tasks."""
    PENDING = "⏳"
    RUNNING = "🔄"
    SUCCESS = "✅"
    FAILED = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"


class ProgressManager:
    """
    Simple progress manager using only halo spinners.
    No modes, no configuration - just consistent halo spinners.
    """
    
    def __init__(self):
        self.current_spinner: Optional[Halo] = None
    
    @contextmanager
    def progress_context(self, title: str = "BrowserBot Progress"):
        """Context manager for progress display."""
        if title:
            print(f"\n🤖 {title}\n")
        yield self
    
    @asynccontextmanager
    async def async_progress_context(self, title: str = "BrowserBot Progress"):
        """Async context manager for progress display."""
        if title:
            print(f"\n🤖 {title}\n")
        yield self
    
    def create_task(self, description: str) -> str:
        """Create a progress task."""
        # For compatibility, just return a fake task ID
        return f"task_{id(description)}"
    
    def update_task(self, task_id: str, description: Optional[str] = None, 
                   completed: Optional[int] = None, total: Optional[int] = None):
        """Update task progress - shows spinner with updated text."""
        if description and self.current_spinner:
            self.current_spinner.text = description
    
    def complete_task(self, task_id: str, description: Optional[str] = None):
        """Mark task as complete."""
        if self.current_spinner:
            self.current_spinner.succeed(description or self.current_spinner.text)
            self.current_spinner = None
    
    def fail_task(self, task_id: str, description: Optional[str] = None):
        """Mark task as failed."""
        if self.current_spinner:
            self.current_spinner.fail(description or self.current_spinner.text)
            self.current_spinner = None
    
    @contextmanager
    def task(self, description: str, total: Optional[int] = None):
        """Context manager for a single task with progress."""
        spinner = Halo(text=description, spinner='dots', color='cyan', stream=sys.stderr)
        self.current_spinner = spinner
        spinner.start()
        
        try:
            yield spinner
            spinner.succeed(f"{description} - completed")
        except Exception as e:
            spinner.fail(f"{description} - failed: {str(e)}")
            raise
        finally:
            self.current_spinner = None
            if spinner.enabled:
                spinner.stop()
    
    @asynccontextmanager
    async def async_task(self, description: str, total: Optional[int] = None):
        """Async context manager for a single task."""
        spinner = Halo(text=description, spinner='dots', color='cyan', stream=sys.stderr)
        self.current_spinner = spinner
        spinner.start()
        
        try:
            yield spinner
            spinner.succeed(f"{description} - completed")
        except Exception as e:
            spinner.fail(f"{description} - failed: {str(e)}")
            raise
        finally:
            self.current_spinner = None
            if spinner.enabled:
                spinner.stop()
    
    def show_status(self, message: str, status: str = "info"):
        """Show a status message."""
        spinner = Halo(text=message, spinner='dots', stream=sys.stderr)
        
        if status == "success":
            spinner.succeed()
        elif status == "error":
            spinner.fail()
        elif status == "warning":
            spinner.warn()
        else:
            spinner.info()
    
    def log_progress(self, message: str, level: str = "info"):
        """Log a progress message."""
        self.show_status(message, level)
    
    def status(self, message: str, task_status: Optional[TaskStatus] = None):
        """Show a status message with optional TaskStatus enum."""
        if task_status:
            status_map = {
                TaskStatus.SUCCESS: "success",
                TaskStatus.FAILED: "error",
                TaskStatus.WARNING: "warning",
                TaskStatus.INFO: "info",
                TaskStatus.RUNNING: "info",
                TaskStatus.PENDING: "info"
            }
            self.show_status(message, status_map.get(task_status, "info"))
        else:
            self.show_status(message, "info")


@asynccontextmanager
async def progress_task(description: str):
    """Async context manager for showing progress during a task."""
    progress = get_progress_manager()
    async with progress.async_task(description):
        yield


# Global progress instance
progress_manager = ProgressManager()


def get_progress_manager() -> ProgressManager:
    """Get the global progress manager instance."""
    return progress_manager