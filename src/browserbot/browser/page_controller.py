"""
High-level page interactions and element management for browser automation.
"""

import asyncio
import random
from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from playwright.async_api import Page, Locator, ElementHandle, Error as PlaywrightError

from ..core.logger import get_logger
from ..core.errors import BrowserError, ValidationError, TimeoutError
from ..core.retry import with_retry
from ..core.progress import get_progress_manager, TaskStatus, progress_task

logger = get_logger(__name__)


class WaitStrategy(Enum):
    """Different wait strategies for element interactions."""
    VISIBLE = "visible"
    HIDDEN = "hidden" 
    ATTACHED = "attached"
    DETACHED = "detached"
    STABLE = "stable"


@dataclass
class ElementInfo:
    """Information about a web element."""
    tag_name: str
    text: Optional[str] = None
    attributes: Dict[str, str] = None
    bounding_box: Optional[Dict[str, float]] = None
    is_visible: bool = False
    is_enabled: bool = False


@dataclass
class ActionResult:
    """Result of a page action."""
    success: bool
    action: str
    element: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    screenshot: Optional[bytes] = None


class PageController:
    """
    High-level controller for page interactions with intelligent waiting and error handling.
    """
    
    def __init__(self, page: Page, timeout: int = None, enable_caching: bool = True, reduce_delays: bool = True):
        self.page = page
        self.timeout = timeout or 30000  # 30 seconds default
        self.actions_taken: List[ActionResult] = []
        self.enable_caching = enable_caching
        self.reduce_delays = reduce_delays
        
        # Initialize cache manager if enabled
        if self.enable_caching:
            from ..core.cache import cache_manager
            self._cache_manager = cache_manager
    
    # Navigation methods
    
    @with_retry(max_attempts=3, exceptions=(PlaywrightError, BrowserError))
    async def navigate(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: Optional[int] = None
    ) -> ActionResult:
        """
        Navigate to a URL with intelligent waiting.
        
        Args:
            url: URL to navigate to
            wait_until: When to consider navigation complete
            timeout: Navigation timeout in milliseconds
            
        Returns:
            ActionResult with navigation details
        """
        progress = get_progress_manager()
        
        try:
            # Normalize URL - add https:// if no protocol specified
            if not url.startswith(('http://', 'https://', 'file://', 'about:', 'data:')):
                url = f"https://{url}"
            
            logger.info(f"Navigating to {url}")
            
            # Add human-like delay
            await self._human_delay()
            
            progress.status(f"Loading {url}...", TaskStatus.RUNNING)
            
            async with progress_task(f"Navigating to {url}..."):
                await self.page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=timeout or self.timeout
                )
            
            # Wait for page to stabilize
            progress.status("Waiting for page to stabilize...", TaskStatus.RUNNING)
            await self._wait_for_stable_dom()
            
            result = ActionResult(
                success=True,
                action="navigate",
                data={"url": url, "title": await self.page.title()}
            )
            
            self.actions_taken.append(result)
            logger.info(f"Successfully navigated to {url}")
            
            return result
            
        except PlaywrightError as e:
            error_msg = f"Navigation failed: {e}"
            logger.error(error_msg, url=url)
            
            result = ActionResult(
                success=False,
                action="navigate",
                error=error_msg,
                screenshot=await self._safe_screenshot()
            )
            
            self.actions_taken.append(result)
            raise BrowserError(error_msg)
    
    async def go_back(self) -> ActionResult:
        """Go back in browser history."""
        try:
            await self.page.go_back(wait_until="domcontentloaded")
            result = ActionResult(success=True, action="go_back")
            self.actions_taken.append(result)
            return result
        except PlaywrightError as e:
            error_msg = f"Go back failed: {e}"
            result = ActionResult(success=False, action="go_back", error=error_msg)
            self.actions_taken.append(result)
            raise BrowserError(error_msg)
    
    async def refresh(self) -> ActionResult:
        """Refresh the current page."""
        try:
            await self.page.reload(wait_until="domcontentloaded")
            await self._wait_for_stable_dom()
            result = ActionResult(success=True, action="refresh")
            self.actions_taken.append(result)
            return result
        except PlaywrightError as e:
            error_msg = f"Refresh failed: {e}"
            result = ActionResult(success=False, action="refresh", error=error_msg)
            self.actions_taken.append(result)
            raise BrowserError(error_msg)
    
    # Element interaction methods
    
    async def find_element(
        self,
        selector: str,
        wait_strategy: WaitStrategy = WaitStrategy.VISIBLE,
        timeout: Optional[int] = None
    ) -> Optional[Locator]:
        """
        Find an element with intelligent waiting.
        
        Args:
            selector: CSS selector or text to find
            wait_strategy: How to wait for the element
            timeout: Timeout in milliseconds
            
        Returns:
            Locator for the element or None if not found
        """
        progress = get_progress_manager()
        
        try:
            locator = self.page.locator(selector)
            
            # Wait based on strategy
            wait_timeout = timeout or self.timeout
            
            async with progress_task(f"Looking for element: {selector[:50]}..."):
                if wait_strategy == WaitStrategy.VISIBLE:
                    await locator.first.wait_for(state="visible", timeout=wait_timeout)
                elif wait_strategy == WaitStrategy.HIDDEN:
                    await locator.first.wait_for(state="hidden", timeout=wait_timeout)
                elif wait_strategy == WaitStrategy.ATTACHED:
                    await locator.first.wait_for(state="attached", timeout=wait_timeout)
                elif wait_strategy == WaitStrategy.DETACHED:
                    await locator.first.wait_for(state="detached", timeout=wait_timeout)
                elif wait_strategy == WaitStrategy.STABLE:
                    await self._wait_for_element_stable(locator.first)
            
            return locator
            
        except PlaywrightError:
            logger.debug(f"Element not found: {selector}")
            return None
    
    async def click(
        self,
        selector: str,
        button: str = "left",
        modifiers: Optional[List[str]] = None,
        force: bool = False
    ) -> ActionResult:
        """
        Click an element with human-like behavior.
        
        Args:
            selector: Element selector
            button: Mouse button to click
            modifiers: Keyboard modifiers
            force: Force click even if element not visible
            
        Returns:
            ActionResult with click details
        """
        progress = get_progress_manager()
        
        try:
            element = await self.find_element(selector)
            if not element:
                raise BrowserError(f"Element not found: {selector}")
            
            # Human-like pre-click delay
            await self._human_delay(0.1, 0.3)
            
            # Get element info for logging
            element_info = await self._get_element_info(element)
            
            progress.status(f"Clicking on {element_info.get('tag_name', 'element')}: {selector[:50]}...", TaskStatus.RUNNING)
            
            # Perform click
            await element.first.click(
                button=button,
                modifiers=modifiers or [],
                force=force,
                timeout=self.timeout
            )
            
            # Post-click delay
            await self._human_delay(0.2, 0.5)
            
            result = ActionResult(
                success=True,
                action="click",
                element=selector,
                data={"element_info": element_info}
            )
            
            self.actions_taken.append(result)
            logger.info(f"Clicked element: {selector}")
            
            return result
            
        except PlaywrightError as e:
            error_msg = f"Click failed: {e}"
            logger.error(error_msg, selector=selector)
            
            result = ActionResult(
                success=False,
                action="click",
                element=selector,
                error=error_msg,
                screenshot=await self._safe_screenshot()
            )
            
            self.actions_taken.append(result)
            raise BrowserError(error_msg)
    
    async def type_text(
        self,
        selector: str,
        text: str,
        clear_first: bool = True,
        delay: Optional[float] = None
    ) -> ActionResult:
        """
        Type text into an element with human-like typing.
        
        Args:
            selector: Element selector
            text: Text to type
            clear_first: Clear existing text first
            delay: Delay between keystrokes
            
        Returns:
            ActionResult with typing details
        """
        progress = get_progress_manager()
        
        try:
            element = await self.find_element(selector)
            if not element:
                raise BrowserError(f"Element not found: {selector}")
            
            # Clear existing text if requested
            if clear_first:
                await element.first.clear()
            
            # Human-like typing with random delays
            if delay is None:
                delay = random.uniform(0.05, 0.15)
            
            # Show typing progress
            text_preview = text[:30] + "..." if len(text) > 30 else text
            async with progress_task(f"Typing '{text_preview}' ({len(text)} chars)..."):
                await element.first.type(text, delay=delay * 1000)  # Convert to ms
            
            result = ActionResult(
                success=True,
                action="type",
                element=selector,
                data={"text": text, "delay": delay}
            )
            
            self.actions_taken.append(result)
            logger.info(f"Typed text into {selector}: {text[:50]}...")
            
            return result
            
        except PlaywrightError as e:
            error_msg = f"Type failed: {e}"
            logger.error(error_msg, selector=selector, text=text[:50])
            
            result = ActionResult(
                success=False,
                action="type",
                element=selector,
                error=error_msg,
                screenshot=await self._safe_screenshot()
            )
            
            self.actions_taken.append(result)
            raise BrowserError(error_msg)
    
    async def select_option(
        self,
        selector: str,
        value: Optional[str] = None,
        label: Optional[str] = None,
        index: Optional[int] = None
    ) -> ActionResult:
        """
        Select an option from a dropdown.
        
        Args:
            selector: Select element selector
            value: Option value to select
            label: Option label to select
            index: Option index to select
            
        Returns:
            ActionResult with selection details
        """
        try:
            element = await self.find_element(selector)
            if not element:
                raise BrowserError(f"Select element not found: {selector}")
            
            # Select based on provided criteria
            if value is not None:
                await element.first.select_option(value=value)
                selection_info = {"method": "value", "selection": value}
            elif label is not None:
                await element.first.select_option(label=label)
                selection_info = {"method": "label", "selection": label}
            elif index is not None:
                await element.first.select_option(index=index)
                selection_info = {"method": "index", "selection": index}
            else:
                raise ValidationError("Must provide value, label, or index for selection")
            
            result = ActionResult(
                success=True,
                action="select",
                element=selector,
                data=selection_info
            )
            
            self.actions_taken.append(result)
            logger.info(f"Selected option in {selector}: {selection_info}")
            
            return result
            
        except PlaywrightError as e:
            error_msg = f"Select failed: {e}"
            logger.error(error_msg, selector=selector)
            
            result = ActionResult(
                success=False,
                action="select",
                element=selector,
                error=error_msg,
                screenshot=await self._safe_screenshot()
            )
            
            self.actions_taken.append(result)
            raise BrowserError(error_msg)
    
    # Information extraction methods
    
    async def get_text(self, selector: str) -> Optional[str]:
        """Get text content from an element."""
        try:
            element = await self.find_element(selector)
            if element:
                return await element.first.text_content()
            return None
        except PlaywrightError:
            return None
    
    async def get_all_text(self, selector: str) -> List[str]:
        """Get text content from all elements matching the selector."""
        try:
            elements = await self.page.locator(selector).all()
            texts = []
            for element in elements:
                text = await element.text_content()
                if text:
                    texts.append(text.strip())
            return texts
        except PlaywrightError as e:
            logger.warning(f"Failed to get text from elements: {selector}, error: {e}")
            return []
    
    async def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get an attribute value from an element."""
        try:
            element = await self.find_element(selector)
            if element:
                return await element.first.get_attribute(attribute)
            return None
        except PlaywrightError:
            return None
    
    async def get_all_attributes(self, selector: str, attribute: str) -> List[str]:
        """Get attribute values from all elements matching the selector."""
        try:
            elements = await self.page.locator(selector).all()
            attributes = []
            for element in elements:
                attr_value = await element.get_attribute(attribute)
                if attr_value:
                    attributes.append(attr_value)
            return attributes
        except PlaywrightError as e:
            logger.warning(f"Failed to get attributes from elements: {selector}, error: {e}")
            return []
    
    async def get_page_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the current page."""
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "viewport": self.page.viewport_size,
            "content": await self.page.content(),
            "cookies": await self.page.context.cookies(),
            "local_storage": await self.page.evaluate("Object.fromEntries(Object.entries(localStorage))"),
            "session_storage": await self.page.evaluate("Object.fromEntries(Object.entries(sessionStorage))")
        }
    
    async def extract_structured_data(self) -> Dict[str, Any]:
        """Extract structured data from the page (JSON-LD, microdata, etc.)."""
        return await self.page.evaluate("""
            () => {
                const data = {
                    jsonLd: [],
                    microdata: [],
                    openGraph: {},
                    meta: {}
                };
                
                // Extract JSON-LD
                document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
                    try {
                        data.jsonLd.push(JSON.parse(script.textContent));
                    } catch (e) {}
                });
                
                // Extract Open Graph
                document.querySelectorAll('meta[property^="og:"]').forEach(meta => {
                    data.openGraph[meta.getAttribute('property')] = meta.getAttribute('content');
                });
                
                // Extract other meta tags
                document.querySelectorAll('meta[name]').forEach(meta => {
                    data.meta[meta.getAttribute('name')] = meta.getAttribute('content');
                });
                
                return data;
            }
        """)
    
    # Utility methods
    
    async def scroll_to_element(self, selector: str) -> ActionResult:
        """Scroll to make an element visible."""
        try:
            element = await self.find_element(selector, WaitStrategy.ATTACHED)
            if not element:
                raise BrowserError(f"Element not found: {selector}")
            
            await element.first.scroll_into_view_if_needed()
            await self._human_delay(0.2, 0.5)
            
            result = ActionResult(
                success=True,
                action="scroll",
                element=selector
            )
            
            self.actions_taken.append(result)
            return result
            
        except PlaywrightError as e:
            error_msg = f"Scroll failed: {e}"
            result = ActionResult(
                success=False,
                action="scroll",
                element=selector,
                error=error_msg
            )
            self.actions_taken.append(result)
            raise BrowserError(error_msg)
    
    async def wait_for_page_load(self, timeout: Optional[int] = None) -> None:
        """Wait for page to fully load."""
        progress = get_progress_manager()
        
        async with progress_task("Waiting for page to fully load..."):
            await self.page.wait_for_load_state("networkidle", timeout=timeout or self.timeout)
        
        await self._wait_for_stable_dom()
    
    async def take_screenshot(
        self,
        full_page: bool = False,
        element_selector: Optional[str] = None
    ) -> bytes:
        """Take a screenshot of the page or specific element."""
        # Check cache first if enabled
        if self.enable_caching and hasattr(self, '_cache_manager'):
            cache_key = element_selector or ('full' if full_page else 'viewport')
            cached_screenshot = await self._cache_manager.get_cached_screenshot(
                self.page.url, 
                cache_key
            )
            if cached_screenshot:
                logger.debug("Using cached screenshot")
                return cached_screenshot
        
        # Take new screenshot
        if element_selector:
            element = await self.find_element(element_selector)
            if element:
                screenshot = await element.first.screenshot()
            else:
                raise BrowserError(f"Element not found for screenshot: {element_selector}")
        else:
            screenshot = await self.page.screenshot(full_page=full_page)
        
        # Cache the screenshot if enabled
        if self.enable_caching and hasattr(self, '_cache_manager'):
            cache_key = element_selector or ('full' if full_page else 'viewport')
            await self._cache_manager.cache_screenshot(
                self.page.url,
                cache_key,
                screenshot,
                ttl=300  # Cache for 5 minutes
            )
        
        return screenshot
    
    # Private helper methods
    
    async def _human_delay(self, min_delay: float = 0.1, max_delay: float = 0.5) -> None:
        """Add random human-like delay between actions."""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def _wait_for_stable_dom(self, stability_time: float = 0.5) -> None:
        """Wait for DOM to stabilize (no changes for specified time)."""
        try:
            await self.page.wait_for_function(
                f"""
                () => {{
                    return new Promise(resolve => {{
                        let timeout;
                        const observer = new MutationObserver(() => {{
                            clearTimeout(timeout);
                            timeout = setTimeout(() => {{
                                observer.disconnect();
                                resolve(true);
                            }}, {stability_time * 1000});
                        }});
                        
                        observer.observe(document.body, {{
                            childList: true,
                            subtree: true,
                            attributes: true
                        }});
                        
                        // Initial timeout in case no mutations occur
                        timeout = setTimeout(() => {{
                            observer.disconnect();
                            resolve(true);
                        }}, {stability_time * 1000});
                    }});
                }}
                """,
                timeout=self.timeout
            )
        except PlaywrightError:
            # If waiting fails, just continue
            pass
    
    async def _wait_for_element_stable(self, locator: Locator) -> None:
        """Wait for element to be stable (not moving)."""
        try:
            # Wait for element to be stable for 100ms
            prev_box = None
            stable_count = 0
            max_attempts = 50  # 5 seconds max
            
            for _ in range(max_attempts):
                try:
                    box = await locator.first.bounding_box()
                    if box == prev_box:
                        stable_count += 1
                        if stable_count >= 3:  # Stable for 300ms
                            break
                    else:
                        stable_count = 0
                    prev_box = box
                    await asyncio.sleep(0.1)
                except PlaywrightError:
                    break
        except Exception:
            # If stability check fails, continue anyway
            pass
    
    async def _get_element_info(self, locator: Locator) -> ElementInfo:
        """Get comprehensive information about an element."""
        try:
            tag_name = await locator.first.evaluate("el => el.tagName.toLowerCase()")
            text = await locator.first.text_content()
            is_visible = await locator.first.is_visible()
            is_enabled = await locator.first.is_enabled()
            bounding_box = await locator.first.bounding_box()
            
            # Get attributes
            attributes = await locator.first.evaluate("""
                el => {
                    const attrs = {};
                    for (const attr of el.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    return attrs;
                }
            """)
            
            return ElementInfo(
                tag_name=tag_name,
                text=text,
                attributes=attributes,
                bounding_box=bounding_box,
                is_visible=is_visible,
                is_enabled=is_enabled
            )
            
        except PlaywrightError:
            return ElementInfo(tag_name="unknown")
    
    async def _safe_screenshot(self) -> Optional[bytes]:
        """Take a screenshot safely (don't fail if it errors)."""
        try:
            return await self.page.screenshot()
        except Exception:
            return None
    
    def get_action_history(self) -> List[ActionResult]:
        """Get history of all actions taken."""
        return self.actions_taken.copy()
    
    def clear_action_history(self) -> None:
        """Clear the action history."""
        self.actions_taken.clear()