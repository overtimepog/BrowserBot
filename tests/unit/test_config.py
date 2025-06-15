"""
Unit tests for configuration management.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.browserbot.core.config import Settings


@pytest.mark.unit
class TestSettings:
    """Test settings configuration."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings(openrouter_api_key="test-key")
        
        assert settings.openrouter_api_key == "test-key"
        assert settings.model_name == "deepseek/deepseek-chat:free"
        assert settings.browser_headless is False
        assert settings.browser_timeout == 30000
        assert settings.max_concurrent_browsers == 5
        assert settings.log_level == "INFO"
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict('os.environ', {
            'OPENROUTER_API_KEY': 'env-test-key',
            'BROWSER_HEADLESS': 'true',
            'BROWSER_TIMEOUT': '15000',
            'LOG_LEVEL': 'DEBUG'
        }):
            settings = Settings()
            
            assert settings.openrouter_api_key == "env-test-key"
            assert settings.browser_headless is True
            assert settings.browser_timeout == 15000
            assert settings.log_level == "DEBUG"
    
    def test_model_config(self):
        """Test model configuration generation."""
        settings = Settings(
            openrouter_api_key="test-key",
            model_name="test-model",
            model_temperature=0.5,
            model_max_tokens=2048
        )
        
        config = settings.get_model_config()
        
        assert config["model"] == "test-model"
        assert config["temperature"] == 0.5
        assert config["max_tokens"] == 2048
        assert config["api_key"] == "test-key"
    
    def test_browser_config(self):
        """Test browser configuration generation."""
        settings = Settings(
            openrouter_api_key="test-key",
            browser_headless=True,
            browser_timeout=10000,
            browser_viewport_width=1280,
            browser_viewport_height=720,
            browser_user_agent="test-agent"
        )
        
        config = settings.get_browser_config()
        
        assert config["headless"] is True
        assert config["timeout"] == 10000
        assert config["viewport"]["width"] == 1280
        assert config["viewport"]["height"] == 720
        assert config["user_agent"] == "test-agent"
    
    def test_log_file_directory_creation(self):
        """Test that log directory is created."""
        test_log_path = Path("/tmp/test_browserbot_logs/test.log")
        
        # Ensure directory doesn't exist initially
        if test_log_path.parent.exists():
            test_log_path.parent.rmdir()
        
        settings = Settings(
            openrouter_api_key="test-key",
            log_file=test_log_path
        )
        
        assert test_log_path.parent.exists()
        
        # Cleanup
        if test_log_path.parent.exists():
            test_log_path.parent.rmdir()
    
    def test_database_directory_creation(self):
        """Test that database directory is created for SQLite."""
        test_db_path = "/tmp/test_browserbot_data/test.db"
        db_url = f"sqlite:///{test_db_path}"
        
        # Ensure directory doesn't exist initially
        db_dir = Path(test_db_path).parent
        if db_dir.exists():
            db_dir.rmdir()
        
        settings = Settings(
            openrouter_api_key="test-key",
            database_url=db_url
        )
        
        assert db_dir.exists()
        
        # Cleanup
        if db_dir.exists():
            db_dir.rmdir()
    
    def test_validation_error_handling(self):
        """Test validation error handling."""
        with pytest.raises(ValueError):
            # Missing required API key
            Settings()
    
    @pytest.mark.parametrize("log_level", ["DEBUG", "INFO", "WARNING", "ERROR"])
    def test_valid_log_levels(self, log_level):
        """Test valid log levels."""
        settings = Settings(
            openrouter_api_key="test-key",
            log_level=log_level
        )
        assert settings.log_level == log_level
    
    @pytest.mark.parametrize("format_type", ["json", "text"])
    def test_log_formats(self, format_type):
        """Test log format options."""
        settings = Settings(
            openrouter_api_key="test-key",
            log_format=format_type
        )
        assert settings.log_format == format_type