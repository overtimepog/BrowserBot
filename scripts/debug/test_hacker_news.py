#!/usr/bin/env python3
"""
Test script for Hacker News extraction to verify proper selectors and multiple element extraction.
"""

import asyncio
import json
from browserbot import BrowserAgent
from browserbot.core.logger import get_logger

logger = get_logger(__name__)


async def test_hacker_news_extraction():
    """Test extraction of stories from Hacker News."""
    agent = BrowserAgent()
    
    try:
        # Navigate to Hacker News
        logger.info("Navigating to Hacker News...")
        nav_result = await agent.execute_task(
            "Navigate to https://news.ycombinator.com"
        )
        logger.info("Navigation result:", nav_result)
        
        # Test 1: Extract using the correct selector for story titles
        logger.info("\nTest 1: Extracting story titles using .titleline selector...")
        extraction_result = await agent.execute_task(
            """Extract all story titles from the page using the selector '.titleline' with extract_type='text_all'.
            The titles are inside elements with class 'titleline'."""
        )
        
        if extraction_result.get("success"):
            data = extraction_result.get("output", {})
            if isinstance(data, dict) and "data" in data:
                titles = data["data"]
                logger.info(f"Extracted {len(titles)} story titles:")
                for i, title in enumerate(titles[:10], 1):  # Show first 10
                    logger.info(f"{i}. {title}")
            else:
                logger.error("Unexpected data format:", data)
        else:
            logger.error("Extraction failed:", extraction_result)
        
        # Test 2: Extract story links
        logger.info("\nTest 2: Extracting story links...")
        link_result = await agent.execute_task(
            """Extract all story links from the page. 
            Use selector '.titleline a' and extract the 'href' attribute."""
        )
        
        if link_result.get("success"):
            logger.info("Successfully extracted story links")
        
        # Test 3: Manual extraction using raw tools
        logger.info("\nTest 3: Direct tool execution test...")
        from browserbot.browser.browser_manager import BrowserManager
        from browserbot.browser.page_controller import PageController
        from browserbot.agents.tools import create_browser_tools
        
        browser_manager = BrowserManager()
        await browser_manager.initialize()
        
        async with browser_manager.get_page(url="https://news.ycombinator.com") as page:
            page_controller = PageController(page)
            
            # Direct method call
            logger.info("Using direct page_controller.get_all_text method...")
            titles = await page_controller.get_all_text('.titleline')
            logger.info(f"Direct extraction found {len(titles)} titles:")
            for i, title in enumerate(titles[:5], 1):
                logger.info(f"  {i}. {title}")
            
            # Test extraction tool directly
            tools = create_browser_tools(page_controller)
            extract_tool = next(t for t in tools if t.name == "extract")
            
            tool_result = await extract_tool.execute({
                "selector": ".titleline",
                "extract_type": "text_all"
            })
            
            logger.info("Direct tool execution result:", tool_result)
        
        await browser_manager.shutdown()
        
    except Exception as e:
        logger.error("Test failed with error:", error=str(e), exc_info=True)
    
    finally:
        await agent.close()


async def test_mistral_parsing():
    """Test if Mistral is correctly parsing tool calls for multiple extraction."""
    from browserbot.agents.mistral_tool_executor import MistralToolExecutor
    
    # Test parsing of extract tool call
    test_response = """
    I'll extract all the story titles from Hacker News.
    
    ```json
    {
      "name": "extract",
      "arguments": {
        "selector": ".titleline",
        "extract_type": "text_all"
      }
    }
    ```
    """
    
    executor = MistralToolExecutor([], None)
    tool_calls = executor._extract_tool_calls(test_response)
    
    logger.info("Parsed tool calls:", tool_calls)
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "extract"
    assert tool_calls[0]["arguments"]["selector"] == ".titleline"
    assert tool_calls[0]["arguments"]["extract_type"] == "text_all"
    
    logger.info("Tool call parsing test passed!")


async def main():
    """Run all tests."""
    logger.info("=== Testing Hacker News Extraction ===")
    
    # Test Mistral parsing first
    logger.info("\n--- Testing Mistral Tool Call Parsing ---")
    await test_mistral_parsing()
    
    # Test actual extraction
    logger.info("\n--- Testing Hacker News Story Extraction ---")
    await test_hacker_news_extraction()
    
    logger.info("\n=== All tests completed ===")


if __name__ == "__main__":
    asyncio.run(main())