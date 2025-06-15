"""
BrowserBot: A robust browser automation agent powered by AI.
"""

__version__ = "0.1.0"
__author__ = "BrowserBot Team"

from .core.config import settings
from .core.logger import get_logger

__all__ = ["settings", "get_logger"]