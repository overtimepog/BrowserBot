"""
Browser instance management with connection pooling and lifecycle control.
"""

import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import uuid

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Error as PlaywrightError
)

from ..core.config import settings
from ..core.logger import get_logger
from ..core.errors import BrowserError, ConfigurationError
from ..core.retry import with_retry, CircuitBreaker, CircuitBreakerConfig
from .stealth import StealthConfig, apply_stealth_settings, create_browser_args, get_random_viewport

logger = get_logger(__name__)


class BrowserInstance:
    """Represents a single browser instance with its metadata."""
    
    def __init__(self, browser: Browser, instance_id: str):
        self.browser = browser
        self.instance_id = instance_id
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.usage_count = 0
        self.contexts: Dict[str, BrowserContext] = {}
    
    def is_stale(self, max_age_minutes: int = 30) -> bool:
        """Check if browser instance is stale."""
        age = datetime.utcnow() - self.created_at
        return age > timedelta(minutes=max_age_minutes)
    
    def is_idle(self, idle_minutes: int = 5) -> bool:
        """Check if browser instance is idle."""
        idle_time = datetime.utcnow() - self.last_used
        return idle_time > timedelta(minutes=idle_minutes)
    
    def update_usage(self) -> None:
        """Update usage statistics."""
        self.last_used = datetime.utcnow()
        self.usage_count += 1


class BrowserManager:
    """
    Manages browser instances with pooling and lifecycle control.
    """
    
    def __init__(
        self,
        max_browsers: int = None,
        stealth_config: Optional[StealthConfig] = None
    ):
        self.max_browsers = max_browsers or settings.max_concurrent_browsers
        self.stealth_config = stealth_config or StealthConfig()
        self.playwright: Optional[Playwright] = None
        self.browsers: Dict[str, BrowserInstance] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=BrowserError
            )
        )
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the browser manager."""
        if self._initialized:
            return
            
        logger.info("Initializing browser manager", max_browsers=self.max_browsers)
        
        try:
            self.playwright = await async_playwright().start()
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._initialized = True
            logger.info("Browser manager initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize browser manager", error=str(e))
            raise ConfigurationError(f"Failed to initialize Playwright: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the browser manager and cleanup resources."""
        logger.info("Shutting down browser manager")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all browsers
        async with self._lock:
            for instance_id, instance in list(self.browsers.items()):
                await self._close_browser(instance_id)
        
        # Stop playwright
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        self._initialized = False
        logger.info("Browser manager shutdown complete")
    
    @asynccontextmanager
    async def get_browser(self, context_options: Optional[Dict[str, Any]] = None):
        """
        Get a browser instance from the pool or create a new one.
        
        Args:
            context_options: Additional options for browser context
            
        Yields:
            Browser context ready for use
        """
        if not self._initialized:
            await self.initialize()
        
        instance = await self._get_or_create_browser()
        
        try:
            # Create a new context with stealth settings
            context = await self._create_context(instance, context_options)
            
            yield context
            
        finally:
            # Cleanup context
            try:
                await context.close()
            except Exception as e:
                logger.warning("Error closing context", error=str(e))
            
            # Update instance usage
            instance.update_usage()
    
    @asynccontextmanager
    async def get_page(
        self,
        url: Optional[str] = None,
        context_options: Optional[Dict[str, Any]] = None
    ):
        """
        Get a new page with browser context.
        
        Args:
            url: Optional URL to navigate to
            context_options: Additional options for browser context
            
        Yields:
            Page instance ready for use
        """
        async with self.get_browser(context_options) as context:
            page = await context.new_page()
            
            # Apply page-level stealth settings
            from .stealth import apply_page_stealth
            await apply_page_stealth(page, self.stealth_config)
            
            # Navigate to URL if provided
            if url:
                await self._navigate_with_retry(page, url)
            
            yield page
    
    async def _get_or_create_browser(self) -> BrowserInstance:
        """Get an existing browser or create a new one."""
        async with self._lock:
            # Try to reuse an existing browser
            for instance in self.browsers.values():
                if not instance.is_stale() and instance.browser.is_connected():
                    logger.debug(
                        "Reusing browser instance",
                        instance_id=instance.instance_id,
                        usage_count=instance.usage_count
                    )
                    return instance
            
            # Check if we can create a new browser
            if len(self.browsers) >= self.max_browsers:
                # Try to close idle browsers
                await self._close_idle_browsers()
                
                # If still at limit, wait or raise error
                if len(self.browsers) >= self.max_browsers:
                    raise BrowserError(
                        f"Maximum browser limit reached: {self.max_browsers}"
                    )
            
            # Create new browser
            return await self._create_browser()
    
    async def _create_browser(self) -> BrowserInstance:
        """Create a new browser instance."""
        instance_id = str(uuid.uuid4())
        
        try:
            logger.info("Creating new browser instance", instance_id=instance_id)
            
            # Launch browser with stealth arguments
            browser = await self._circuit_breaker.async_call(
                self._launch_browser
            )
            
            instance = BrowserInstance(browser, instance_id)
            self.browsers[instance_id] = instance
            
            logger.info(
                "Browser instance created",
                instance_id=instance_id,
                total_browsers=len(self.browsers)
            )
            
            return instance
            
        except Exception as e:
            logger.error(
                "Failed to create browser",
                instance_id=instance_id,
                error=str(e)
            )
            raise BrowserError(f"Failed to create browser: {e}")
    
    async def _launch_browser(self) -> Browser:
        """Launch a new browser with configuration."""
        if not self.playwright:
            raise ConfigurationError("Playwright not initialized")
        
        browser_config = settings.get_browser_config()
        browser_config["args"] = create_browser_args(stealth=True)
        
        # Remove viewport from browser config (set at context level)
        browser_config.pop("viewport", None)
        
        return await self.playwright.chromium.launch(**browser_config)
    
    async def _create_context(
        self,
        instance: BrowserInstance,
        options: Optional[Dict[str, Any]] = None
    ) -> BrowserContext:
        """Create a new browser context with stealth settings."""
        context_options = {
            "viewport": get_random_viewport(self.stealth_config),
            "locale": self.stealth_config.locale,
            "timezone_id": self.stealth_config.timezone,
            "permissions": [],  # Deny all permissions by default
            "color_scheme": "light",
            "reduced_motion": "no-preference",
            "forced_colors": "none",
        }
        
        # Merge with provided options
        if options:
            context_options.update(options)
        
        # Create context
        context = await instance.browser.new_context(**context_options)
        
        # Apply stealth settings
        await apply_stealth_settings(context, self.stealth_config)
        
        # Store context reference
        context_id = str(uuid.uuid4())
        instance.contexts[context_id] = context
        
        # Cleanup context reference when closed
        async def cleanup():
            instance.contexts.pop(context_id, None)
        
        context.on("close", lambda: asyncio.create_task(cleanup()))
        
        return context
    
    @with_retry(max_attempts=3, exceptions=(PlaywrightError, BrowserError))
    async def _navigate_with_retry(self, page: Page, url: str) -> None:
        """Navigate to URL with retry logic."""
        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.browser_timeout
            )
        except PlaywrightError as e:
            if "timeout" in str(e).lower():
                raise BrowserError(f"Navigation timeout for {url}")
            raise BrowserError(f"Navigation failed: {e}")
    
    async def _close_browser(self, instance_id: str) -> None:
        """Close a browser instance."""
        instance = self.browsers.pop(instance_id, None)
        if not instance:
            return
        
        try:
            # Close all contexts
            for context in list(instance.contexts.values()):
                await context.close()
            
            # Close browser
            if instance.browser.is_connected():
                await instance.browser.close()
            
            logger.info(
                "Browser instance closed",
                instance_id=instance_id,
                usage_count=instance.usage_count
            )
        except Exception as e:
            logger.error(
                "Error closing browser",
                instance_id=instance_id,
                error=str(e)
            )
    
    async def _close_idle_browsers(self) -> None:
        """Close browsers that have been idle."""
        for instance_id, instance in list(self.browsers.items()):
            if instance.is_idle() or instance.is_stale():
                await self._close_browser(instance_id)
    
    async def _cleanup_loop(self) -> None:
        """Background task to cleanup stale browsers."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                async with self._lock:
                    await self._close_idle_browsers()
                    
                    # Log current state
                    active_browsers = len(self.browsers)
                    if active_browsers > 0:
                        logger.debug(
                            "Browser pool status",
                            active_browsers=active_browsers,
                            max_browsers=self.max_browsers
                        )
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup loop", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get browser manager statistics."""
        return {
            "active_browsers": len(self.browsers),
            "max_browsers": self.max_browsers,
            "browser_stats": [
                {
                    "instance_id": instance.instance_id,
                    "created_at": instance.created_at.isoformat(),
                    "last_used": instance.last_used.isoformat(),
                    "usage_count": instance.usage_count,
                    "active_contexts": len(instance.contexts),
                    "is_connected": instance.browser.is_connected(),
                }
                for instance in self.browsers.values()
            ]
        }