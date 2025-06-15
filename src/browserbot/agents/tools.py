"""
LangChain tools for browser automation.
"""

from typing import Dict, Any, List, Optional, Union, Type
import asyncio
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, ConfigDict
import json

from langchain.tools import BaseTool
try:
    from langchain.callbacks.manager import CallbackManagerForToolRun as CallbackManagerForToolUse
except ImportError:
    # Fallback for older versions or different callback manager names
    try:
        from langchain.callbacks.manager import CallbackManagerForToolUse
    except ImportError:
        # Create a minimal fallback callback manager
        class CallbackManagerForToolUse:
            def on_tool_end(self, result): pass
            def on_tool_error(self, error): pass

from ..browser.browser_manager import BrowserManager
from ..browser.page_controller import PageController, ActionResult, WaitStrategy
from ..core.logger import get_logger
from ..core.errors import BrowserError, ValidationError

logger = get_logger(__name__)


class BrowserToolInput(BaseModel):
    """Base input model for browser tools."""
    pass


class NavigationInput(BrowserToolInput):
    """Input for navigation operations."""
    url: str = Field(description="URL to navigate to")
    wait_until: str = Field(default="domcontentloaded", description="When to consider navigation complete")


class ClickInput(BrowserToolInput):
    """Input for click operations."""
    selector: str = Field(description="CSS selector or element identifier")
    button: str = Field(default="left", description="Mouse button to click (left, right, middle)")
    force: bool = Field(default=False, description="Force click even if element not visible")


class TypeInput(BrowserToolInput):
    """Input for typing operations."""
    selector: str = Field(description="CSS selector for input element")
    text: str = Field(description="Text to type")
    clear_first: bool = Field(default=True, description="Clear existing text first")


class SelectInput(BrowserToolInput):
    """Input for select operations."""
    selector: str = Field(description="CSS selector for select element")
    value: Optional[str] = Field(default=None, description="Option value to select")
    label: Optional[str] = Field(default=None, description="Option label to select")
    index: Optional[int] = Field(default=None, description="Option index to select")


class ExtractInput(BrowserToolInput):
    """Input for data extraction operations."""
    selector: Optional[str] = Field(default=None, description="CSS selector for specific element")
    extract_type: str = Field(default="text", description="Type of data to extract (text, attribute, html)")
    attribute: Optional[str] = Field(default=None, description="Attribute name if extracting attribute")


class ScreenshotInput(BrowserToolInput):
    """Input for screenshot operations."""
    full_page: bool = Field(default=False, description="Take full page screenshot")
    element_selector: Optional[str] = Field(default=None, description="Take screenshot of specific element")


class BrowserTool(BaseTool, ABC):
    """Base class for browser automation tools."""
    
    # Pydantic v2 configuration to allow arbitrary types
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Define page_controller as a Pydantic field
    # Note: We don't exclude it since it's needed for the tool to function
    page_controller: PageController = Field(default=None)
    
    def _run(self, *args, **kwargs) -> str:
        """Synchronous run method (not used for async tools)."""
        raise NotImplementedError("Use async_run for browser tools")
    
    async def _arun(
        self,
        tool_input: Union[str, Dict],
        run_manager: Optional[CallbackManagerForToolUse] = None
    ) -> str:
        """Async run method for browser tools."""
        try:
            if isinstance(tool_input, str):
                # Parse JSON string input
                try:
                    tool_input = json.loads(tool_input)
                except json.JSONDecodeError:
                    # If not JSON, treat as simple string input
                    tool_input = {"input": tool_input}
            
            # Convert dict to appropriate input model
            parsed_input = self.args_schema(**tool_input)
            
            # Execute the tool
            result = await self.execute(parsed_input)
            
            # Log the action
            if run_manager:
                run_manager.on_tool_end(str(result))
            
            return str(result)
            
        except Exception as e:
            error_msg = f"{self.name} failed: {str(e)}"
            logger.error(error_msg, tool_input=tool_input)
            
            if run_manager:
                run_manager.on_tool_error(e)
            
            return f"Error: {error_msg}"
    
    @abstractmethod
    async def execute(self, tool_input: BrowserToolInput) -> Dict[str, Any]:
        """Execute the tool with the given input."""
        pass


class NavigationTool(BrowserTool):
    """Tool for page navigation."""
    
    name: str = "navigate"
    description: str = "Navigate to a specific URL. Use this to go to websites or change pages."
    args_schema: Type[BaseModel] = NavigationInput
    
    async def execute(self, tool_input: NavigationInput) -> Dict[str, Any]:
        """Navigate to the specified URL."""
        try:
            result = await self.page_controller.navigate(
                url=tool_input.url,
                wait_until=tool_input.wait_until
            )
            
            # Get additional page info
            page_info = await self.page_controller.get_page_info()
            
            return {
                "success": result.success,
                "action": "navigate",
                "url": tool_input.url,
                "title": page_info["title"],
                "final_url": page_info["url"],
                "message": f"Successfully navigated to {tool_input.url}"
            }
            
        except BrowserError as e:
            return {
                "success": False,
                "action": "navigate",
                "url": tool_input.url,
                "error": str(e),
                "message": f"Failed to navigate to {tool_input.url}: {e}"
            }


class InteractionTool(BrowserTool):
    """Tool for element interactions (click, type, select)."""
    
    name: str = "interact"
    description: str = "Interact with web elements - click buttons, type text, select options, etc."
    
    class InteractionInput(BrowserToolInput):
        """Input for interaction operations."""
        action: str = Field(description="Action to perform (click, type, select)")
        selector: str = Field(description="CSS selector for target element")
        text: Optional[str] = Field(default=None, description="Text to type (for type action)")
        value: Optional[str] = Field(default=None, description="Value to select (for select action)")
        button: str = Field(default="left", description="Mouse button for click")
        clear_first: bool = Field(default=True, description="Clear before typing")
    
    args_schema: Type[BaseModel] = InteractionInput
    
    async def execute(self, tool_input: InteractionInput) -> Dict[str, Any]:
        """Execute the interaction."""
        try:
            if tool_input.action == "click":
                result = await self.page_controller.click(
                    selector=tool_input.selector,
                    button=tool_input.button
                )
                
            elif tool_input.action == "type":
                if not tool_input.text:
                    raise ValidationError("Text is required for type action")
                
                result = await self.page_controller.type_text(
                    selector=tool_input.selector,
                    text=tool_input.text,
                    clear_first=tool_input.clear_first
                )
                
            elif tool_input.action == "select":
                result = await self.page_controller.select_option(
                    selector=tool_input.selector,
                    value=tool_input.value
                )
                
            else:
                raise ValidationError(f"Unknown action: {tool_input.action}")
            
            return {
                "success": result.success,
                "action": tool_input.action,
                "selector": tool_input.selector,
                "data": result.data,
                "message": f"Successfully executed {tool_input.action} on {tool_input.selector}"
            }
            
        except (BrowserError, ValidationError) as e:
            return {
                "success": False,
                "action": tool_input.action,
                "selector": tool_input.selector,
                "error": str(e),
                "message": f"Failed to {tool_input.action} on {tool_input.selector}: {e}"
            }


class ExtractionTool(BrowserTool):
    """Tool for extracting data from web pages."""
    
    name: str = "extract"
    description: str = "Extract text, attributes, or structured data from web pages."
    args_schema: Type[BaseModel] = ExtractInput
    
    async def execute(self, tool_input: ExtractInput) -> Dict[str, Any]:
        """Extract data from the page."""
        try:
            if tool_input.selector:
                # Extract from specific element
                if tool_input.extract_type == "text":
                    data = await self.page_controller.get_text(tool_input.selector)
                elif tool_input.extract_type == "attribute":
                    if not tool_input.attribute:
                        raise ValidationError("Attribute name required for attribute extraction")
                    data = await self.page_controller.get_attribute(
                        tool_input.selector,
                        tool_input.attribute
                    )
                else:
                    raise ValidationError(f"Unknown extract type: {tool_input.extract_type}")
            else:
                # Extract page-level data
                if tool_input.extract_type == "structured":
                    data = await self.page_controller.extract_structured_data()
                elif tool_input.extract_type == "page_info":
                    data = await self.page_controller.get_page_info()
                else:
                    # Default to page text
                    data = await self.page_controller.get_text("body")
            
            return {
                "success": True,
                "action": "extract",
                "extract_type": tool_input.extract_type,
                "selector": tool_input.selector,
                "data": data,
                "message": f"Successfully extracted {tool_input.extract_type} data"
            }
            
        except (BrowserError, ValidationError) as e:
            return {
                "success": False,
                "action": "extract",
                "extract_type": tool_input.extract_type,
                "error": str(e),
                "message": f"Failed to extract data: {e}"
            }


class ScreenshotTool(BrowserTool):
    """Tool for taking screenshots."""
    
    name: str = "screenshot"
    description: str = "Take screenshots of the current page or specific elements."
    args_schema: Type[BaseModel] = ScreenshotInput
    
    async def execute(self, tool_input: ScreenshotInput) -> Dict[str, Any]:
        """Take a screenshot."""
        try:
            screenshot_data = await self.page_controller.take_screenshot(
                full_page=tool_input.full_page,
                element_selector=tool_input.element_selector
            )
            
            # Convert to base64 for transport
            import base64
            screenshot_b64 = base64.b64encode(screenshot_data).decode()
            
            return {
                "success": True,
                "action": "screenshot",
                "full_page": tool_input.full_page,
                "element_selector": tool_input.element_selector,
                "screenshot_size": len(screenshot_data),
                "screenshot_b64": screenshot_b64,
                "message": "Screenshot taken successfully"
            }
            
        except BrowserError as e:
            return {
                "success": False,
                "action": "screenshot",
                "error": str(e),
                "message": f"Failed to take screenshot: {e}"
            }


class WaitTool(BrowserTool):
    """Tool for waiting and page state management."""
    
    name: str = "wait"
    description: str = "Wait for specific conditions or elements on the page."
    
    class WaitInput(BrowserToolInput):
        """Input for wait operations."""
        wait_type: str = Field(description="Type of wait (element, page_load, time)")
        selector: Optional[str] = Field(default=None, description="Element selector to wait for")
        timeout: int = Field(default=30000, description="Timeout in milliseconds")
        state: str = Field(default="visible", description="Element state to wait for")
    
    args_schema: Type[BaseModel] = WaitInput
    
    async def execute(self, tool_input: WaitInput) -> Dict[str, Any]:
        """Execute the wait operation."""
        try:
            if tool_input.wait_type == "element":
                if not tool_input.selector:
                    raise ValidationError("Selector required for element wait")
                
                element = await self.page_controller.find_element(
                    selector=tool_input.selector,
                    wait_strategy=WaitStrategy(tool_input.state),
                    timeout=tool_input.timeout
                )
                
                success = element is not None
                message = f"Element {tool_input.selector} is {tool_input.state}" if success else f"Element {tool_input.selector} not found"
                
            elif tool_input.wait_type == "page_load":
                await self.page_controller.wait_for_page_load(timeout=tool_input.timeout)
                success = True
                message = "Page fully loaded"
                
            elif tool_input.wait_type == "time":
                await asyncio.sleep(tool_input.timeout / 1000)  # Convert to seconds
                success = True
                message = f"Waited {tool_input.timeout}ms"
                
            else:
                raise ValidationError(f"Unknown wait type: {tool_input.wait_type}")
            
            return {
                "success": success,
                "action": "wait",
                "wait_type": tool_input.wait_type,
                "selector": tool_input.selector,
                "timeout": tool_input.timeout,
                "message": message
            }
            
        except (BrowserError, ValidationError) as e:
            return {
                "success": False,
                "action": "wait",
                "wait_type": tool_input.wait_type,
                "error": str(e),
                "message": f"Wait operation failed: {e}"
            }


def create_browser_tools(page_controller: PageController) -> List[BrowserTool]:
    """
    Create all browser automation tools.
    
    Args:
        page_controller: PageController instance
        
    Returns:
        List of browser tools
    """
    return [
        NavigationTool(page_controller=page_controller),
        InteractionTool(page_controller=page_controller),
        ExtractionTool(page_controller=page_controller),
        ScreenshotTool(page_controller=page_controller),
        WaitTool(page_controller=page_controller)
    ]