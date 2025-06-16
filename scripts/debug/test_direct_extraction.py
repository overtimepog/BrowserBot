#!/usr/bin/env python3
"""
Direct test of the extraction improvements without Docker.
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from browserbot.browser.browser_manager import BrowserManager
from browserbot.browser.page_controller import PageController
from browserbot.agents.tools import create_browser_tools
from browserbot.core.logger import get_logger

logger = get_logger(__name__)


async def test_direct_extraction():
    """Test extraction directly without the full agent."""
    browser_manager = BrowserManager()
    
    try:
        await browser_manager.initialize()
        
        async with browser_manager.get_page(url="https://news.ycombinator.com") as page:
            page_controller = PageController(page)
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Test 1: Get all story titles using the new method
            logger.info("Test 1: Extracting all story titles with .titleline selector")
            titles = await page_controller.get_all_text('.titleline')
            logger.info(f"Found {len(titles)} story titles:")
            for i, title in enumerate(titles[:5], 1):
                logger.info(f"  {i}. {title}")
            
            # Test 2: Get all story links
            logger.info("\nTest 2: Extracting all story links")
            links = await page_controller.get_all_attributes('.titleline a', 'href')
            logger.info(f"Found {len(links)} story links:")
            for i, link in enumerate(links[:5], 1):
                logger.info(f"  {i}. {link}")
            
            # Test 3: Use the extraction tool directly
            logger.info("\nTest 3: Testing extraction tool")
            tools = create_browser_tools(page_controller)
            extract_tool = next(t for t in tools if t.name == "extract")
            
            # Test text_all extraction
            result = await extract_tool.execute({
                "selector": ".titleline",
                "extract_type": "text_all"
            })
            
            if result["success"]:
                data = result["data"]
                logger.info(f"Extract tool found {len(data)} titles")
            else:
                logger.error("Extract tool failed:", result["error"])
            
            # Test multiple=true extraction
            result2 = await extract_tool.execute({
                "selector": ".titleline",
                "extract_type": "text",
                "multiple": True
            })
            
            if result2["success"]:
                data2 = result2["data"]
                logger.info(f"Extract tool with multiple=true found {len(data2)} titles")
            else:
                logger.error("Extract tool with multiple failed:", result2["error"])
                
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    
    finally:
        await browser_manager.shutdown()


async def test_mistral_parsing():
    """Test Mistral tool call parsing."""
    from browserbot.agents.mistral_tool_executor import MistralToolExecutor
    
    test_cases = [
        # Test case 1: text_all extraction
        {
            "response": """I'll extract all story titles from Hacker News.
            
            ```json
            {
              "name": "extract",
              "arguments": {
                "selector": ".titleline",
                "extract_type": "text_all"
              }
            }
            ```""",
            "expected": {
                "name": "extract",
                "arguments": {
                    "selector": ".titleline",
                    "extract_type": "text_all"
                }
            }
        },
        # Test case 2: multiple=true extraction
        {
            "response": """I'll extract all titles using multiple flag.
            
            ```json
            {
              "name": "extract",
              "arguments": {
                "selector": ".titleline",
                "extract_type": "text",
                "multiple": true
              }
            }
            ```""",
            "expected": {
                "name": "extract",
                "arguments": {
                    "selector": ".titleline",
                    "extract_type": "text",
                    "multiple": True
                }
            }
        }
    ]
    
    executor = MistralToolExecutor([], None)
    
    for i, test_case in enumerate(test_cases):
        logger.info(f"\nTest case {i+1}:")
        tool_calls = executor._extract_tool_calls(test_case["response"])
        
        if len(tool_calls) == 1:
            actual = tool_calls[0]
            expected = test_case["expected"]
            
            # Check name
            if actual["name"] == expected["name"]:
                logger.info(f"✓ Tool name correct: {actual['name']}")
            else:
                logger.error(f"✗ Tool name mismatch: expected {expected['name']}, got {actual['name']}")
            
            # Check arguments
            for key, value in expected["arguments"].items():
                if key in actual["arguments"] and actual["arguments"][key] == value:
                    logger.info(f"✓ Argument '{key}' correct: {value}")
                else:
                    logger.error(f"✗ Argument '{key}' mismatch: expected {value}, got {actual['arguments'].get(key)}")
        else:
            logger.error(f"✗ Expected 1 tool call, got {len(tool_calls)}")


async def main():
    """Run all tests."""
    logger.info("=== Testing Extraction Improvements ===")
    
    # Test Mistral parsing
    logger.info("\n--- Testing Mistral Tool Call Parsing ---")
    await test_mistral_parsing()
    
    # Test direct extraction
    logger.info("\n--- Testing Direct Extraction ---")
    await test_direct_extraction()
    
    logger.info("\n=== All tests completed ===")


if __name__ == "__main__":
    asyncio.run(main())