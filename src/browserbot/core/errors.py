"""
Error handling and exception classes for BrowserBot.
"""

from typing import Optional, Any, Dict
from dataclasses import dataclass
from enum import Enum
import traceback


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    BROWSER = "browser"
    NETWORK = "network"
    AI_MODEL = "ai_model"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    SYSTEM = "system"
    CONFIGURATION = "configuration"


@dataclass
class ErrorContext:
    """Context information for errors."""
    severity: ErrorSeverity
    category: ErrorCategory
    retry_count: int = 0
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None
    
    def should_retry(self) -> bool:
        """Check if error should be retried."""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1


class BrowserBotError(Exception):
    """Base exception for all BrowserBot errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext(
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM
        )
        self.cause = cause
        self.traceback = traceback.format_exc() if cause else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.context.severity.value,
            "category": self.context.category.value,
            "retry_count": self.context.retry_count,
            "metadata": self.context.metadata,
            "cause": str(self.cause) if self.cause else None,
            "traceback": self.traceback
        }


class BrowserError(BrowserBotError):
    """Browser-related errors."""
    
    def __init__(self, message: str, **kwargs):
        context = ErrorContext(
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.BROWSER
        )
        super().__init__(message, context, **kwargs)


class NetworkError(BrowserBotError):
    """Network-related errors."""
    
    def __init__(self, message: str, **kwargs):
        context = ErrorContext(
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            max_retries=5  # Network errors get more retries
        )
        super().__init__(message, context, **kwargs)


class AIModelError(BrowserBotError):
    """AI model-related errors."""
    
    def __init__(self, message: str, **kwargs):
        context = ErrorContext(
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.AI_MODEL
        )
        super().__init__(message, context, **kwargs)


class AuthenticationError(BrowserBotError):
    """Authentication-related errors."""
    
    def __init__(self, message: str, **kwargs):
        context = ErrorContext(
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.AUTHENTICATION,
            max_retries=1  # Limited retries for auth errors
        )
        super().__init__(message, context, **kwargs)


class ValidationError(BrowserBotError):
    """Input validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        context = ErrorContext(
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            max_retries=0,  # No retries for validation errors
            metadata={"field": field} if field else None
        )
        super().__init__(message, context, **kwargs)


class ConfigurationError(BrowserBotError):
    """Configuration-related errors."""
    
    def __init__(self, message: str, **kwargs):
        context = ErrorContext(
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CONFIGURATION,
            max_retries=0  # No retries for config errors
        )
        super().__init__(message, context, **kwargs)


class RateLimitError(NetworkError):
    """Rate limit errors from APIs."""
    
    def __init__(
        self, 
        message: str, 
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if retry_after:
            self.context.metadata = {"retry_after": retry_after}


class TimeoutError(BrowserError):
    """Timeout errors from browser operations."""
    
    def __init__(self, message: str, timeout: int, **kwargs):
        super().__init__(message, **kwargs)
        self.context.metadata = {"timeout": timeout}