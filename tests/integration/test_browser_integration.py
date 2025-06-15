"""
Integration tests for browser automation components.
"""

import pytest
import asyncio
from unittest.mock import patch

from src.browserbot.browser.browser_manager import BrowserManager
from src.browserbot.browser.page_controller import PageController, WaitStrategy
from src.browserbot.browser.stealth import StealthConfig
from src.browserbot.core.errors import BrowserError


@pytest.mark.integration
class TestBrowserManagerIntegration:
    """Test BrowserManager integration."""
    
    @pytest.mark.asyncio
    async def test_browser_lifecycle(self, stealth_config):
        """Test complete browser lifecycle."""
        manager = BrowserManager(max_browsers=1, stealth_config=stealth_config)
        
        try:
            # Initialize
            await manager.initialize()
            assert manager._initialized is True
            
            # Get browser context
            async with manager.get_browser() as context:
                assert context is not None
                
                # Create page
                page = await context.new_page()
                assert page is not None
                
                # Test basic navigation
                await page.goto("data:text/html,<html><body><h1>Test</h1></body></html>")
                title = await page.title()
                assert title == ""  # Data URLs don't have titles
                
        finally:
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_multiple_browser_contexts(self, stealth_config):
        """Test multiple browser contexts."""
        manager = BrowserManager(max_browsers=2, stealth_config=stealth_config)
        
        try:
            await manager.initialize()
            
            # Create multiple contexts
            contexts = []
            for i in range(2):
                context_mgr = manager.get_browser()
                context = await context_mgr.__aenter__()
                contexts.append((context_mgr, context))
            
            # Verify both contexts work
            for i, (_, context) in enumerate(contexts):
                page = await context.new_page()
                await page.goto(f"data:text/html,<html><body><h1>Page {i}</h1></body></html>")
                content = await page.content()
                assert f"Page {i}" in content
            
            # Cleanup contexts
            for context_mgr, context in contexts:
                await context_mgr.__aexit__(None, None, None)
                
        finally:
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_browser_stats(self, stealth_config):
        """Test browser statistics collection."""
        manager = BrowserManager(max_browsers=2, stealth_config=stealth_config)
        
        try:
            await manager.initialize()
            
            # Initially no browsers
            stats = manager.get_stats()
            assert stats["active_browsers"] == 0
            assert stats["max_browsers"] == 2
            
            # Create browser context
            async with manager.get_browser() as context:
                stats = manager.get_stats()
                assert stats["active_browsers"] == 1
                assert len(stats["browser_stats"]) == 1
                
                browser_stat = stats["browser_stats"][0]
                assert "instance_id" in browser_stat
                assert "created_at" in browser_stat
                assert "usage_count" in browser_stat
                assert browser_stat["is_connected"] is True
                
        finally:
            await manager.shutdown()


@pytest.mark.integration
class TestPageControllerIntegration:
    """Test PageController integration."""
    
    @pytest.mark.asyncio
    async def test_navigation_and_interaction(self, test_page_with_content):
        """Test navigation and basic interactions."""
        controller = test_page_with_content
        
        # Test text extraction
        heading_text = await controller.get_text("#main-heading")
        assert heading_text == "Welcome to Test Page"
        
        # Test attribute extraction
        name_placeholder = await controller.get_attribute("#name-input", "placeholder")
        assert name_placeholder == "Enter your name"
        
        # Test form interaction
        await controller.type_text("#name-input", "John Doe")
        await controller.type_text("#email-input", "john@example.com")
        await controller.select_option("#country-select", value="us")
        
        # Verify values were set
        name_value = await controller.get_attribute("#name-input", "value")
        email_value = await controller.get_attribute("#email-input", "value")
        country_value = await controller.get_attribute("#country-select", "value")
        
        assert name_value == "John Doe"
        assert email_value == "john@example.com" 
        assert country_value == "us"
    
    @pytest.mark.asyncio
    async def test_element_waiting(self, page_controller, sample_html):
        """Test element waiting strategies."""
        # Load page with delayed element
        delayed_html = sample_html + """
        <script>
            setTimeout(() => {
                const div = document.createElement('div');
                div.id = 'delayed-element';
                div.textContent = 'I appeared later!';
                document.body.appendChild(div);
            }, 100);
        </script>
        """
        
        await page_controller.page.set_content(delayed_html)
        
        # Element should not exist immediately
        element = await page_controller.find_element(
            "#delayed-element",
            wait_strategy=WaitStrategy.VISIBLE,
            timeout=50  # Short timeout
        )
        assert element is None
        
        # Element should exist after waiting longer
        element = await page_controller.find_element(
            "#delayed-element",
            wait_strategy=WaitStrategy.VISIBLE,
            timeout=200  # Longer timeout
        )
        assert element is not None
        
        text = await element.text_content()
        assert text == "I appeared later!"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, page_controller):
        """Test error handling in page controller."""
        await page_controller.page.set_content("<html><body></body></html>")
        
        # Test clicking non-existent element
        with pytest.raises(BrowserError):
            await page_controller.click("#non-existent-element")
        
        # Test typing to non-existent element
        with pytest.raises(BrowserError):
            await page_controller.type_text("#non-existent-input", "test")
    
    @pytest.mark.asyncio
    async def test_screenshot_functionality(self, test_page_with_content):
        """Test screenshot functionality."""
        controller = test_page_with_content
        
        # Take full page screenshot
        screenshot = await controller.take_screenshot(full_page=True)
        assert isinstance(screenshot, bytes)
        assert len(screenshot) > 0
        
        # Take element screenshot
        element_screenshot = await controller.take_screenshot(
            element_selector="#main-heading"
        )
        assert isinstance(element_screenshot, bytes)
        assert len(element_screenshot) > 0
        
        # Element screenshot should be smaller than full page
        assert len(element_screenshot) < len(screenshot)
    
    @pytest.mark.asyncio
    async def test_page_info_extraction(self, test_page_with_content):
        """Test page information extraction."""
        controller = test_page_with_content
        
        # Get basic page info
        page_info = await controller.get_page_info()
        
        assert "url" in page_info
        assert "title" in page_info
        assert "viewport" in page_info
        assert "content" in page_info
        
        assert page_info["title"] == "Test Page"
        assert "Welcome to Test Page" in page_info["content"]
        
        # Get structured data
        structured_data = await controller.extract_structured_data()
        
        assert "jsonLd" in structured_data
        assert "openGraph" in structured_data
        assert "meta" in structured_data
        
        # Should find the description meta tag
        assert structured_data["meta"].get("description") == "A test page for browser automation"
    
    @pytest.mark.asyncio
    async def test_action_history(self, test_page_with_content):
        """Test action history tracking."""
        controller = test_page_with_content
        
        # Initially no actions
        history = controller.get_action_history()
        assert len(history) == 0
        
        # Perform some actions
        await controller.click("#name-input")
        await controller.type_text("#name-input", "Test User")
        
        # Check history
        history = controller.get_action_history()
        assert len(history) == 2
        
        assert history[0].action == "click"
        assert history[0].element == "#name-input"
        assert history[0].success is True
        
        assert history[1].action == "type"
        assert history[1].element == "#name-input"
        assert history[1].success is True
        
        # Clear history
        controller.clear_action_history()
        history = controller.get_action_history()
        assert len(history) == 0


@pytest.mark.integration
@pytest.mark.slow
class TestRealWebsiteIntegration:
    """Test integration with real websites (slower tests)."""
    
    @pytest.mark.asyncio
    async def test_httpbin_integration(self, browser_manager):
        """Test integration with httpbin.org for HTTP testing."""
        async with browser_manager.get_page() as page:
            controller = PageController(page)
            
            # Navigate to httpbin
            result = await controller.navigate("https://httpbin.org/")
            assert result.success is True
            
            # Get page title
            title = await controller.get_text("title")
            assert "httpbin" in title.lower()
            
            # Find and click a link
            forms_link = await controller.find_element("a[href='/forms/post']")
            if forms_link:
                await controller.click("a[href='/forms/post']")
                
                # Wait for navigation
                await controller.wait_for_page_load()
                
                # Verify we're on the forms page
                page_info = await controller.get_page_info()
                assert "/forms/post" in page_info["url"]
    
    @pytest.mark.asyncio
    async def test_search_engine_integration(self, browser_manager):
        """Test integration with a search engine."""
        async with browser_manager.get_page() as page:
            controller = PageController(page)
            
            # Navigate to DuckDuckGo (privacy-focused, no complex blocking)
            result = await controller.navigate("https://duckduckgo.com/")
            assert result.success is True
            
            # Find search box
            search_box = await controller.find_element("input[name='q']")
            if search_box:
                # Type search query
                await controller.type_text("input[name='q']", "browser automation")
                
                # Find and click search button
                search_btn = await controller.find_element("input[type='submit']")
                if search_btn:
                    await controller.click("input[type='submit']")
                    
                    # Wait for results
                    await asyncio.sleep(2)  # Give time for results to load
                    
                    # Check if we got results
                    page_info = await controller.get_page_info()
                    assert "browser automation" in page_info["content"].lower()