"""
Retry mechanisms with exponential backoff and circuit breaker patterns.
"""

import asyncio
import random
import time
from typing import TypeVar, Callable, Optional, Any, Union
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState
)

# Try to import before_retry and after_retry, fallback if not available
try:
    from tenacity import before_retry, after_retry
except ImportError:
    # Fallback for older versions of tenacity
    def before_retry(func):
        return func
    
    def after_retry(func):
        return func

from .logger import get_logger
from .errors import BrowserBotError, NetworkError, RateLimitError

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception: type[Exception] = Exception


@dataclass
class CircuitBreakerState:
    """State tracking for circuit breaker."""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: CircuitState = CircuitState.CLOSED
    
    def record_success(self) -> None:
        """Record successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self) -> None:
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
    
    def should_attempt_reset(self, recovery_timeout: int) -> bool:
        """Check if circuit should attempt reset."""
        if self.last_failure_time is None:
            return False
        return datetime.utcnow() - self.last_failure_time > timedelta(seconds=recovery_timeout)


class CircuitBreaker:
    """Circuit breaker implementation."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState()
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if self.state.state == CircuitState.OPEN:
            if self.state.should_attempt_reset(self.config.recovery_timeout):
                logger.info("Circuit breaker attempting reset", state="half_open")
                self.state.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker reset successful", state="closed")
            self.state.record_success()
            return result
            
        except self.config.expected_exception as e:
            self.state.record_failure()
            
            if self.state.failure_count >= self.config.failure_threshold:
                logger.warning(
                    "Circuit breaker opened",
                    failure_count=self.state.failure_count,
                    threshold=self.config.failure_threshold
                )
                self.state.state = CircuitState.OPEN
            
            raise e
    
    async def async_call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with circuit breaker protection."""
        if self.state.state == CircuitState.OPEN:
            if self.state.should_attempt_reset(self.config.recovery_timeout):
                logger.info("Circuit breaker attempting reset", state="half_open")
                self.state.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker reset successful", state="closed")
            self.state.record_success()
            return result
            
        except self.config.expected_exception as e:
            self.state.record_failure()
            
            if self.state.failure_count >= self.config.failure_threshold:
                logger.warning(
                    "Circuit breaker opened",
                    failure_count=self.state.failure_count,
                    threshold=self.config.failure_threshold
                )
                self.state.state = CircuitState.OPEN
            
            raise e


def calculate_backoff_with_jitter(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: float = 0.1
) -> float:
    """
    Calculate exponential backoff with jitter.
    
    Args:
        attempt: Current attempt number
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Jitter factor (0-1)
    
    Returns:
        Delay in seconds
    """
    # Calculate exponential backoff
    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    
    # Add jitter
    jitter_range = delay * jitter
    actual_delay = delay + random.uniform(-jitter_range, jitter_range)
    
    return max(0, actual_delay)


def log_before_retry(retry_state: RetryCallState) -> None:
    """Log before retry attempt."""
    # Only log if this is actually a retry (attempt > 1)
    if retry_state.attempt_number > 1:
        logger.warning(
            "Retrying function",
            function=retry_state.fn.__name__,
            attempt=retry_state.attempt_number,
            exception=str(retry_state.outcome.exception()) if retry_state.outcome else None
        )


def log_after_retry(retry_state: RetryCallState) -> None:
    """Log after retry attempt."""
    if retry_state.outcome and not retry_state.outcome.failed:
        logger.info(
            "Retry successful",
            function=retry_state.fn.__name__,
            attempt=retry_state.attempt_number
        )


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (NetworkError, RateLimitError)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        exceptions: Exceptions to retry on
    """
    retry_kwargs = {
        'stop': stop_after_attempt(max_attempts),
        'wait': wait_exponential(multiplier=base_delay, max=max_delay),
        'retry': retry_if_exception_type(exceptions)
    }
    
    # Add before/after callbacks if available
    try:
        retry_kwargs['before'] = before_retry(log_before_retry)
        retry_kwargs['after'] = after_retry(log_after_retry)
    except (TypeError, ImportError):
        # Use older parameter names or skip callbacks
        try:
            retry_kwargs['before_sleep'] = log_before_retry
        except:
            pass  # Skip callbacks if not supported
    
    return retry(**retry_kwargs)


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type[Exception] = Exception
):
    """
    Decorator for circuit breaker pattern.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time in seconds before attempting reset
        expected_exception: Exception type to track
    """
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await breaker.async_call(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return breaker.call(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


class RetryableOperation:
    """Context manager for retryable operations with manual control."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        exceptions: tuple[type[Exception], ...] = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.exceptions = exceptions
        self.attempt = 0
        self.last_exception: Optional[Exception] = None
    
    def __enter__(self):
        self.attempt = 0
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, self.exceptions):
            self.last_exception = exc_val
            return True  # Suppress exception
        return False
    
    async def __aenter__(self):
        self.attempt = 0
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, self.exceptions):
            self.last_exception = exc_val
            return True  # Suppress exception
        return False
    
    def should_retry(self) -> bool:
        """Check if operation should be retried."""
        return self.attempt < self.max_attempts and self.last_exception is not None
    
    async def wait_before_retry(self) -> None:
        """Wait before next retry with exponential backoff."""
        if self.should_retry():
            delay = calculate_backoff_with_jitter(self.attempt, self.base_delay)
            logger.info(f"Waiting {delay:.2f}s before retry {self.attempt + 1}")
            await asyncio.sleep(delay)
            self.attempt += 1
            self.last_exception = None