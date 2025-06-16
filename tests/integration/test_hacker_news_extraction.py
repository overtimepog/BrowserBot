"""
Integration tests for Hacker News extraction with multiple elements.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from browserbot.browser.page_controller import PageController
from browserbot.agents.tools import ExtractionTool, ExtractInput
from browserbot.agents.mistral_tool_executor import MistralToolExecutor


class TestHackerNewsExtraction:
    """Test extraction of multiple elements from Hacker News."""
    
    @pytest.mark.asyncio
    async def test_get_all_text_method(self):
        """Test the get_all_text method returns multiple elements."""
        # Mock page and locator
        mock_element1 = AsyncMock()
        mock_element1.text_content = AsyncMock(return_value="Story Title 1")
        
        mock_element2 = AsyncMock()
        mock_element2.text_content = AsyncMock(return_value="Story Title 2")
        
        mock_element3 = AsyncMock()
        mock_element3.text_content = AsyncMock(return_value="Story Title 3")
        
        mock_locator = AsyncMock()
        mock_locator.all = AsyncMock(return_value=[mock_element1, mock_element2, mock_element3])
        
        mock_page = AsyncMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        
        # Create page controller
        controller = PageController(mock_page)
        
        # Test get_all_text
        texts = await controller.get_all_text('.titleline')
        
        assert len(texts) == 3
        assert texts[0] == "Story Title 1"
        assert texts[1] == "Story Title 2"
        assert texts[2] == "Story Title 3"
        
        # Verify the locator was called with correct selector
        mock_page.locator.assert_called_once_with('.titleline')
        mock_locator.all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_attributes_method(self):
        """Test the get_all_attributes method returns multiple attributes."""
        # Mock elements with href attributes
        mock_element1 = AsyncMock()
        mock_element1.get_attribute = AsyncMock(return_value="https://example1.com")
        
        mock_element2 = AsyncMock()
        mock_element2.get_attribute = AsyncMock(return_value="https://example2.com")
        
        mock_element3 = AsyncMock()
        mock_element3.get_attribute = AsyncMock(return_value="https://example3.com")
        
        mock_locator = AsyncMock()
        mock_locator.all = AsyncMock(return_value=[mock_element1, mock_element2, mock_element3])
        
        mock_page = AsyncMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        
        # Create page controller
        controller = PageController(mock_page)
        
        # Test get_all_attributes
        links = await controller.get_all_attributes('.titleline a', 'href')
        
        assert len(links) == 3
        assert links[0] == "https://example1.com"
        assert links[1] == "https://example2.com"
        assert links[2] == "https://example3.com"
        
        # Verify calls
        mock_page.locator.assert_called_once_with('.titleline a')
        for element in [mock_element1, mock_element2, mock_element3]:
            element.get_attribute.assert_called_once_with('href')
    
    @pytest.mark.asyncio
    async def test_extraction_tool_text_all(self):
        """Test ExtractionTool with extract_type='text_all'."""
        # Mock page controller
        mock_controller = AsyncMock()
        mock_controller.get_all_text = AsyncMock(return_value=[
            "Story 1: AI News",
            "Story 2: Tech Update",
            "Story 3: Programming Tips"
        ])
        mock_controller.page = AsyncMock()
        mock_controller.page.url = "https://news.ycombinator.com"
        mock_controller.enable_caching = False
        
        # Create extraction tool
        tool = ExtractionTool(page_controller=mock_controller)
        
        # Test with text_all
        input_data = ExtractInput(
            selector=".titleline",
            extract_type="text_all"
        )
        
        result = await tool.execute(input_data)
        
        assert result["success"] is True
        assert result["action"] == "extract"
        assert result["extract_type"] == "text_all"
        assert result["selector"] == ".titleline"
        assert len(result["data"]) == 3
        assert "Story 1: AI News" in result["data"]
        assert "Story 2: Tech Update" in result["data"]
        assert "Story 3: Programming Tips" in result["data"]
        
        # Verify the correct method was called
        mock_controller.get_all_text.assert_called_once_with(".titleline")
    
    @pytest.mark.asyncio
    async def test_extraction_tool_multiple_flag(self):
        """Test ExtractionTool with multiple=True flag."""
        # Mock page controller
        mock_controller = AsyncMock()
        mock_controller.get_all_text = AsyncMock(return_value=[
            "Title A",
            "Title B",
            "Title C"
        ])
        mock_controller.page = AsyncMock()
        mock_controller.page.url = "https://news.ycombinator.com"
        mock_controller.enable_caching = False
        
        # Create extraction tool
        tool = ExtractionTool(page_controller=mock_controller)
        
        # Test with multiple=True
        input_data = ExtractInput(
            selector=".titleline",
            extract_type="text",
            multiple=True
        )
        
        result = await tool.execute(input_data)
        
        assert result["success"] is True
        assert len(result["data"]) == 3
        assert "Title A" in result["data"]
        
        # Verify get_all_text was called (not get_text)
        mock_controller.get_all_text.assert_called_once_with(".titleline")
    
    def test_mistral_tool_parsing_text_all(self):
        """Test Mistral executor parses text_all extraction correctly."""
        executor = MistralToolExecutor([], None)
        
        response = """I'll extract all story titles from Hacker News.
        
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
        
        tool_calls = executor._extract_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "extract"
        assert tool_calls[0]["arguments"]["selector"] == ".titleline"
        assert tool_calls[0]["arguments"]["extract_type"] == "text_all"
    
    def test_mistral_tool_parsing_multiple_flag(self):
        """Test Mistral executor parses multiple=true correctly."""
        executor = MistralToolExecutor([], None)
        
        response = """Extracting all titles with multiple flag.
        
        ```json
        {
          "name": "extract",
          "arguments": {
            "selector": ".titleline",
            "extract_type": "text",
            "multiple": true
          }
        }
        ```
        """
        
        tool_calls = executor._extract_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "extract"
        assert tool_calls[0]["arguments"]["selector"] == ".titleline"
        assert tool_calls[0]["arguments"]["extract_type"] == "text"
        assert tool_calls[0]["arguments"]["multiple"] is True
    
    def test_mistral_normalize_extract_arguments(self):
        """Test Mistral normalizes extract tool arguments correctly."""
        executor = MistralToolExecutor([], None)
        
        # Test normalization doesn't break extract arguments
        args = executor._normalize_tool_arguments("extract", {
            "selector": ".titleline",
            "extract_type": "text_all"
        })
        
        assert args["selector"] == ".titleline"
        assert args["extract_type"] == "text_all"
        
        # Test with multiple flag
        args2 = executor._normalize_tool_arguments("extract", {
            "selector": ".story",
            "extract_type": "text",
            "multiple": True
        })
        
        assert args2["selector"] == ".story"
        assert args2["extract_type"] == "text"
        assert args2["multiple"] is True