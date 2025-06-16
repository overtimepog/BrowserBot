"""Example test file to demonstrate Docker-based testing."""

import pytest
import sys
import os


def test_python_version():
    """Verify we're running Python 3.11."""
    assert sys.version_info.major == 3
    assert sys.version_info.minor == 11


def test_environment():
    """Verify we're running inside Docker container."""
    # In Docker, the hostname is set to 'browserbot' or 'browserbot-test'
    hostname = os.uname().nodename
    assert 'browserbot' in hostname.lower() or 'test' in hostname.lower()


def test_display_env():
    """Verify X11 display is configured for browser tests."""
    display = os.environ.get('DISPLAY')
    assert display is not None
    assert display == ':99'


def test_browserbot_import():
    """Verify BrowserBot modules can be imported."""
    from browserbot.config import Settings
    from browserbot.browser.manager import BrowserManager
    from browserbot.errors import BrowserBotError
    
    # Basic instantiation test
    settings = Settings()
    assert settings is not None


def test_redis_env():
    """Verify Redis URL is configured when needed."""
    redis_url = os.environ.get('REDIS_URL')
    # Redis URL is optional but if present should be valid
    if redis_url:
        assert redis_url.startswith('redis://')


@pytest.mark.parametrize("module", [
    "browserbot.config",
    "browserbot.browser.manager",
    "browserbot.errors",
    "browserbot.ai.orchestrator",
])
def test_module_imports(module):
    """Test that all major modules can be imported."""
    __import__(module)


def test_working_directory():
    """Verify we're in the correct working directory."""
    cwd = os.getcwd()
    assert cwd == '/home/browserbot/app'


def test_logs_directory():
    """Verify logs directory exists."""
    logs_dir = '/home/browserbot/app/logs'
    assert os.path.exists(logs_dir)
    assert os.path.isdir(logs_dir)