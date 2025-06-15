"""
Pytest configuration and fixtures for BrowserBot tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import Mock, AsyncMock

from src.browserbot.core.config import Settings
from src.browserbot.browser.browser_manager import BrowserManager
from src.browserbot.browser.page_controller import PageController
from src.browserbot.browser.stealth import StealthConfig
from src.browserbot.agents.browser_agent import BrowserAgent


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Test configuration settings."""
    return Settings(
        openrouter_api_key="test-key",
        model_name="test-model",
        browser_headless=True,
        browser_timeout=5000,
        max_concurrent_browsers=1,
        log_level="DEBUG",
        redis_url="redis://localhost:6379/1",  # Use test database
        database_url="sqlite:///:memory:",  # In-memory database for tests
    )


@pytest.fixture
def stealth_config():
    """Test stealth configuration."""
    return StealthConfig(
        randomize_user_agent=False,  # Consistent for testing
        randomize_viewport=False,
        randomize_timings=False,
        min_action_delay=0.01,  # Faster for tests
        max_action_delay=0.02,
    )


@pytest.fixture
async def browser_manager(test_settings, stealth_config):
    """Browser manager fixture."""
    manager = BrowserManager(
        max_browsers=test_settings.max_concurrent_browsers,
        stealth_config=stealth_config
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
async def page_controller(browser_manager):
    """Page controller fixture."""
    async with browser_manager.get_browser() as context:
        page = await context.new_page()
        controller = PageController(page, timeout=5000)
        yield controller


@pytest.fixture
def mock_llm():
    """Mock LLM for testing without API calls."""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value="Test response")
    mock.astream = AsyncMock(return_value=["Test", " response"])
    return mock


@pytest.fixture
async def browser_agent(test_settings, stealth_config, mock_llm):
    """Browser agent fixture with mocked LLM."""
    agent = BrowserAgent(
        model_name="test-model",
        max_browsers=1,
        stealth_config=stealth_config
    )
    
    # Replace LLM with mock
    agent.llm = mock_llm
    
    await agent.browser_manager.initialize()
    yield agent
    await agent.shutdown()


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="A test page for browser automation">
    </head>
    <body>
        <h1 id="main-heading">Welcome to Test Page</h1>
        <p class="intro">This is a test page for browser automation.</p>
        
        <form id="test-form">
            <input type="text" id="name-input" name="name" placeholder="Enter your name">
            <input type="email" id="email-input" name="email" placeholder="Enter your email">
            <select id="country-select" name="country">
                <option value="">Select Country</option>
                <option value="us">United States</option>
                <option value="uk">United Kingdom</option>
                <option value="ca">Canada</option>
            </select>
            <button type="submit" id="submit-btn">Submit</button>
        </form>
        
        <div id="results" style="display: none;">
            <h2>Results</h2>
            <p id="result-text"></p>
        </div>
        
        <script>
            document.getElementById('test-form').addEventListener('submit', function(e) {
                e.preventDefault();
                const name = document.getElementById('name-input').value;
                const email = document.getElementById('email-input').value;
                const country = document.getElementById('country-select').value;
                
                document.getElementById('result-text').textContent = 
                    `Name: ${name}, Email: ${email}, Country: ${country}`;
                document.getElementById('results').style.display = 'block';
            });
        </script>
    </body>
    </html>
    """


@pytest.fixture
async def test_page_with_content(page_controller, sample_html):
    """Page controller with test HTML content loaded."""
    await page_controller.page.set_content(sample_html)
    await page_controller.page.wait_for_load_state("domcontentloaded")
    return page_controller


# Test marks for categorizing tests
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow


class TestServer:
    """Test HTTP server for integration tests."""
    
    def __init__(self, port: int = 8888):
        self.port = port
        self.server = None
        
    async def start(self, html_content: str = None):
        """Start the test server."""
        from aiohttp import web
        
        async def handler(request):
            content = html_content or "<html><body><h1>Test Server</h1></body></html>"
            return web.Response(text=content, content_type="text/html")
        
        app = web.Application()
        app.router.add_get("/", handler)
        app.router.add_get("/{path:.*}", handler)
        
        from aiohttp.web_runner import AppRunner, TCPSite
        runner = AppRunner(app)
        await runner.setup()
        
        site = TCPSite(runner, "localhost", self.port)
        await site.start()
        
        self.server = runner
        return f"http://localhost:{self.port}"
    
    async def stop(self):
        """Stop the test server."""
        if self.server:
            await self.server.cleanup()
            self.server = None


@pytest.fixture
async def test_server():
    """Test server fixture."""
    server = TestServer()
    yield server
    await server.stop()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment."""
    import os
    
    # Set test environment variables
    os.environ["BROWSERBOT_TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Cleanup
    os.environ.pop("BROWSERBOT_TESTING", None)