#!/usr/bin/env python3
"""Quick test to verify Hacker News extraction fix."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from browserbot.browser.browser_manager import BrowserManager
from browserbot.browser.page_controller import PageController
from browserbot.agents.tools import create_browser_tools
from browserbot.agents.mistral_tool_executor import MistralToolExecutor
from langchain_openai import ChatOpenAI


async def test_extraction():
    """Test the extraction fix."""
    print("=== Testing Hacker News Extraction Fix ===\n")
    
    # Initialize browser
    browser_manager = BrowserManager()
    await browser_manager.initialize()
    
    async with browser_manager.get_page(url="https://news.ycombinator.com") as page:
        page_controller = PageController(page)
        
        # Test 1: Direct extraction
        print("1. Testing direct extraction with .titleline selector...")
        titles = await page_controller.get_all_text('.titleline')
        print(f"   ✓ Found {len(titles)} story titles")
        if titles:
            print(f"   First title: {titles[0][:80]}...")
        print()
        
        # Test 2: Tool execution
        print("2. Testing extraction tool...")
        tools = create_browser_tools(page_controller)
        extract_tool = next(t for t in tools if t.name == "extract")
        
        result = await extract_tool.execute({
            "selector": ".titleline",
            "extract_type": "text_all"
        })
        
        if result["success"]:
            data = result.get("data", [])
            print(f"   ✓ Tool extracted {len(data)} items")
            if data and len(data) >= 5:
                print("\n   Top 5 stories:")
                for i, title in enumerate(data[:5], 1):
                    print(f"   {i}. {title}")
        else:
            print(f"   ✗ Tool failed: {result.get('error', 'Unknown error')}")
        print()
        
        # Test 3: Mistral executor
        print("3. Testing Mistral tool executor parsing...")
        llm = ChatOpenAI(
            model="mistralai/mistral-7b-instruct:free",
            temperature=0.1,
            max_tokens=4096
        )
        
        tool_dict = {tool.name: tool for tool in tools}
        executor = MistralToolExecutor(tool_dict, llm)
        
        # Test tool call parsing
        test_response = """
        I'll extract the story titles from Hacker News.
        
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
        
        tool_calls = executor._extract_tool_calls(test_response)
        if tool_calls:
            print("   ✓ Successfully parsed tool call")
            print(f"   Tool: {tool_calls[0]['name']}")
            print(f"   Args: {tool_calls[0]['arguments']}")
        else:
            print("   ✗ Failed to parse tool call")
    
    await browser_manager.shutdown()
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_extraction())