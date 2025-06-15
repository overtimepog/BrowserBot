"""Browser automation module with Playwright."""

from .browser_manager import BrowserManager
from .page_controller import PageController
from .stealth import StealthConfig, apply_stealth_settings

__all__ = [
    "BrowserManager",
    "PageController", 
    "StealthConfig",
    "apply_stealth_settings"
]