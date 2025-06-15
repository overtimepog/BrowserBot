"""
Unit tests for error handling.
"""

import pytest
from datetime import datetime

from src.browserbot.core.errors import (
    BrowserBotError,
    BrowserError,
    NetworkError,
    AIModelError,
    AuthenticationError,
    ValidationError,
    ConfigurationError,
    RateLimitError,
    TimeoutError,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext
)


@pytest.mark.unit
class TestErrorContext:
    """Test ErrorContext functionality."""
    
    def test_default_context(self):
        """Test default error context."""
        context = ErrorContext(
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM
        )
        
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.category == ErrorCategory.SYSTEM
        assert context.retry_count == 0
        assert context.max_retries == 3
        assert context.metadata is None
    
    def test_should_retry(self):
        """Test retry logic."""
        context = ErrorContext(
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            max_retries=3
        )
        
        # Should retry initially
        assert context.should_retry() is True
        
        # Should retry after first increment
        context.increment_retry()
        assert context.retry_count == 1
        assert context.should_retry() is True
        
        # Should not retry after max retries
        context.retry_count = 3
        assert context.should_retry() is False
    
    def test_increment_retry(self):
        """Test retry count increment."""
        context = ErrorContext(
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION
        )
        
        initial_count = context.retry_count
        context.increment_retry()
        
        assert context.retry_count == initial_count + 1


@pytest.mark.unit
class TestBrowserBotError:
    """Test base BrowserBotError functionality."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = BrowserBotError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.context.severity == ErrorSeverity.MEDIUM
        assert error.context.category == ErrorCategory.SYSTEM
        assert error.cause is None
    
    def test_error_with_context(self):
        """Test error with custom context."""
        context = ErrorContext(
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.BROWSER,
            metadata={"selector": ".test-element"}
        )
        
        error = BrowserBotError("Custom error", context=context)
        
        assert error.context.severity == ErrorSeverity.HIGH
        assert error.context.category == ErrorCategory.BROWSER
        assert error.context.metadata["selector"] == ".test-element"
    
    def test_error_with_cause(self):
        """Test error with underlying cause."""
        original_error = ValueError("Original error")
        error = BrowserBotError("Wrapper error", cause=original_error)
        
        assert error.cause == original_error
        assert error.traceback is not None
    
    def test_to_dict(self):
        """Test error serialization to dictionary."""
        context = ErrorContext(
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.BROWSER,
            retry_count=2,
            metadata={"url": "https://example.com"}
        )
        
        error = BrowserBotError("Test error", context=context)
        error_dict = error.to_dict()
        
        assert error_dict["error_type"] == "BrowserBotError"
        assert error_dict["message"] == "Test error"
        assert error_dict["severity"] == "high"
        assert error_dict["category"] == "browser"
        assert error_dict["retry_count"] == 2
        assert error_dict["metadata"]["url"] == "https://example.com"


@pytest.mark.unit
class TestSpecificErrors:
    """Test specific error types."""
    
    def test_browser_error(self):
        """Test BrowserError."""
        error = BrowserError("Browser failed")
        
        assert error.context.severity == ErrorSeverity.HIGH
        assert error.context.category == ErrorCategory.BROWSER
    
    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("Network timeout")
        
        assert error.context.severity == ErrorSeverity.MEDIUM
        assert error.context.category == ErrorCategory.NETWORK
        assert error.context.max_retries == 5  # Network errors get more retries
    
    def test_ai_model_error(self):
        """Test AIModelError."""
        error = AIModelError("Model API failed")
        
        assert error.context.severity == ErrorSeverity.HIGH
        assert error.context.category == ErrorCategory.AI_MODEL
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid API key")
        
        assert error.context.severity == ErrorSeverity.CRITICAL
        assert error.context.category == ErrorCategory.AUTHENTICATION
        assert error.context.max_retries == 1  # Limited retries for auth
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid input", field="email")
        
        assert error.context.severity == ErrorSeverity.LOW
        assert error.context.category == ErrorCategory.VALIDATION
        assert error.context.max_retries == 0  # No retries for validation
        assert error.context.metadata["field"] == "email"
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Missing configuration")
        
        assert error.context.severity == ErrorSeverity.CRITICAL
        assert error.context.category == ErrorCategory.CONFIGURATION
        assert error.context.max_retries == 0  # No retries for config
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        
        assert error.context.category == ErrorCategory.NETWORK
        assert error.context.metadata["retry_after"] == 60
    
    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("Operation timed out", timeout=30000)
        
        assert error.context.category == ErrorCategory.BROWSER
        assert error.context.metadata["timeout"] == 30000


@pytest.mark.unit
class TestErrorSeverityAndCategory:
    """Test error severity and category enums."""
    
    def test_error_severity_values(self):
        """Test ErrorSeverity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"
    
    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.BROWSER.value == "browser"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.AI_MODEL.value == "ai_model"
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.SYSTEM.value == "system"
        assert ErrorCategory.CONFIGURATION.value == "configuration"