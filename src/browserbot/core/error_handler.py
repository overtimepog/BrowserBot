"""
Enhanced error handling system implementing 2024 best practices.
"""

import asyncio
import traceback
import uuid
from typing import Optional, Dict, Any, List, Callable, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from prometheus_client import Counter, Histogram, Gauge
import structlog

from .errors import (
    BrowserBotError, ErrorSeverity, ErrorCategory, ErrorContext,
    BrowserError, NetworkError, AIModelError, RateLimitError
)
from .logger import get_logger
from .retry import CircuitBreaker, CircuitBreakerConfig

logger = get_logger(__name__)

# Metrics
error_counter = Counter(
    'browserbot_errors_total',
    'Total number of errors',
    ['error_type', 'severity', 'category', 'component']
)

error_recovery_counter = Counter(
    'browserbot_error_recoveries_total',
    'Total number of successful error recoveries',
    ['error_type', 'recovery_strategy']
)

error_response_time = Histogram(
    'browserbot_error_handling_duration_seconds',
    'Time spent handling errors'
)


@dataclass
class ErrorPattern:
    """Pattern for error analysis."""
    error_type: str
    frequency: int
    time_window: timedelta
    first_occurrence: datetime
    last_occurrence: datetime
    contexts: List[Dict[str, Any]] = field(default_factory=list)


class RecoveryStrategy(Enum):
    """Available recovery strategies."""
    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK = "fallback"
    CACHE = "cache"
    DEGRADED = "degraded"
    ALTERNATIVE = "alternative"


@dataclass
class UserErrorResponse:
    """User-friendly error response."""
    message: str
    action: str
    error_id: str
    timestamp: str
    additional_info: Optional[Dict[str, Any]] = None


class ErrorHandler:
    """
    Comprehensive error handling system with recovery strategies,
    user-friendly messages, and production monitoring.
    """
    
    # User-friendly error messages
    USER_ERROR_MESSAGES = {
        "ElementNotFound": {
            "message": "Unable to find the requested element on the page.",
            "action": "The page layout may have changed. Please refresh and try again."
        },
        "TimeoutError": {
            "message": "The operation is taking longer than expected.",
            "action": "Please check your connection and try again in a moment."
        },
        "NetworkError": {
            "message": "Unable to connect to the service.",
            "action": "Please check your internet connection and try again."
        },
        "AuthenticationError": {
            "message": "Unable to verify your credentials.",
            "action": "Please check your login information and try again."
        },
        "RateLimitError": {
            "message": "Too many requests. Please slow down.",
            "action": "Wait a moment before trying again."
        },
        "AIModelError": {
            "message": "The AI assistant encountered an issue.",
            "action": "Please try rephrasing your request or try again later."
        },
        "ValidationError": {
            "message": "The provided information appears to be incorrect.",
            "action": "Please check your input and try again."
        }
    }
    
    def __init__(self, enable_monitoring: bool = True):
        self.enable_monitoring = enable_monitoring
        self.error_buffer: List[Dict[str, Any]] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.recovery_strategies: Dict[Type[Exception], List[RecoveryStrategy]] = {
            NetworkError: [RecoveryStrategy.RETRY, RecoveryStrategy.CIRCUIT_BREAKER, RecoveryStrategy.CACHE],
            RateLimitError: [RecoveryStrategy.CIRCUIT_BREAKER, RecoveryStrategy.DEGRADED],
            BrowserError: [RecoveryStrategy.RETRY, RecoveryStrategy.ALTERNATIVE],
            AIModelError: [RecoveryStrategy.FALLBACK, RecoveryStrategy.DEGRADED]
        }
        
        # Start background error analysis
        if self.enable_monitoring:
            asyncio.create_task(self._analyze_error_patterns())
    
    def get_circuit_breaker(self, service: str) -> CircuitBreaker:
        """Get or create circuit breaker for a service."""
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreaker(
                CircuitBreakerConfig(
                    failure_threshold=5,
                    recovery_timeout=60,
                    expected_exception=Exception
                )
            )
        return self.circuit_breakers[service]
    
    async def handle_error(
        self,
        error: Exception,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        recovery_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Handle error with logging, monitoring, and recovery attempts.
        
        Args:
            error: The exception that occurred
            operation: Name of the operation that failed
            context: Additional context about the error
            recovery_enabled: Whether to attempt recovery
            
        Returns:
            Dictionary with error details and recovery status
        """
        with error_response_time.time():
            error_id = str(uuid.uuid4())
            error_context = context or {}
            
            # Log error with full context
            self._log_error(error, operation, error_id, error_context)
            
            # Update metrics
            if self.enable_monitoring:
                self._update_error_metrics(error)
            
            # Buffer error for pattern analysis
            self._buffer_error(error, operation, error_context)
            
            # Attempt recovery if enabled
            recovery_result = None
            if recovery_enabled:
                recovery_result = await self._attempt_recovery(
                    error, operation, error_context
                )
            
            # Format response
            return {
                "error_id": error_id,
                "success": False,
                "error_type": type(error).__name__,
                "operation": operation,
                "recovery_attempted": recovery_enabled,
                "recovery_result": recovery_result,
                "user_response": self.format_user_response(error, error_id),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _log_error(
        self,
        error: Exception,
        operation: str,
        error_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Log error with structured context."""
        error_details = {
            "error_id": error_id,
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context
        }
        
        # Add BrowserBot-specific error context if available
        if isinstance(error, BrowserBotError):
            error_details.update({
                "severity": error.context.severity.value,
                "category": error.context.category.value,
                "retry_count": error.context.retry_count,
                "metadata": error.context.metadata
            })
        
        logger.error("operation_failed", **error_details)
    
    def _update_error_metrics(self, error: Exception) -> None:
        """Update Prometheus metrics."""
        error_type = type(error).__name__
        
        # Determine severity and category
        if isinstance(error, BrowserBotError):
            severity = error.context.severity.value
            category = error.context.category.value
        else:
            severity = ErrorSeverity.MEDIUM.value
            category = ErrorCategory.SYSTEM.value
        
        error_counter.labels(
            error_type=error_type,
            severity=severity,
            category=category,
            component="browserbot"
        ).inc()
    
    def _buffer_error(
        self,
        error: Exception,
        operation: str,
        context: Dict[str, Any]
    ) -> None:
        """Buffer error for pattern analysis."""
        self.error_buffer.append({
            "timestamp": datetime.utcnow(),
            "error_type": type(error).__name__,
            "operation": operation,
            "context": context,
            "error": error
        })
        
        # Keep buffer size manageable
        if len(self.error_buffer) > 1000:
            self.error_buffer = self.error_buffer[-500:]
    
    async def _attempt_recovery(
        self,
        error: Exception,
        operation: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Attempt to recover from error using configured strategies."""
        error_type = type(error)
        strategies = self.recovery_strategies.get(
            error_type,
            [RecoveryStrategy.RETRY]  # Default strategy
        )
        
        for strategy in strategies:
            try:
                logger.info(
                    "Attempting error recovery",
                    strategy=strategy.value,
                    error_type=error_type.__name__
                )
                
                result = await self._execute_recovery_strategy(
                    strategy, error, operation, context
                )
                
                if result and result.get("success"):
                    error_recovery_counter.labels(
                        error_type=error_type.__name__,
                        recovery_strategy=strategy.value
                    ).inc()
                    
                    logger.info(
                        "Error recovery successful",
                        strategy=strategy.value,
                        error_type=error_type.__name__
                    )
                    
                    return result
                    
            except Exception as recovery_error:
                logger.warning(
                    "Recovery strategy failed",
                    strategy=strategy.value,
                    error=str(recovery_error)
                )
                continue
        
        return None
    
    async def _execute_recovery_strategy(
        self,
        strategy: RecoveryStrategy,
        error: Exception,
        operation: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Execute specific recovery strategy."""
        if strategy == RecoveryStrategy.RETRY:
            # Simple retry for transient errors
            if hasattr(error, 'context') and error.context.should_retry():
                return {"success": True, "strategy": "retry", "message": "Retry available"}
        
        elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
            # Check circuit breaker state
            breaker = self.get_circuit_breaker(operation)
            if breaker.state.state.value != "open":
                return {"success": True, "strategy": "circuit_breaker", "message": "Circuit breaker allows retry"}
        
        elif strategy == RecoveryStrategy.FALLBACK:
            # Use fallback method
            return {"success": True, "strategy": "fallback", "message": "Fallback method available"}
        
        elif strategy == RecoveryStrategy.CACHE:
            # Return cached result if available
            if context.get("cached_result"):
                return {
                    "success": True,
                    "strategy": "cache",
                    "message": "Using cached result",
                    "data": context["cached_result"]
                }
        
        elif strategy == RecoveryStrategy.DEGRADED:
            # Operate in degraded mode
            return {
                "success": True,
                "strategy": "degraded",
                "message": "Operating in degraded mode"
            }
        
        elif strategy == RecoveryStrategy.ALTERNATIVE:
            # Use alternative method
            if context.get("alternative_method"):
                return {
                    "success": True,
                    "strategy": "alternative",
                    "message": "Using alternative method"
                }
        
        return None
    
    def format_user_response(
        self,
        error: Exception,
        error_id: str
    ) -> UserErrorResponse:
        """Format user-friendly error response."""
        error_type = type(error).__name__
        
        # Get user-friendly message
        error_info = self.USER_ERROR_MESSAGES.get(
            error_type,
            {
                "message": "An unexpected error occurred.",
                "action": "Please try again later or contact support if the issue persists."
            }
        )
        
        # Add specific information for certain errors
        additional_info = {}
        if isinstance(error, RateLimitError) and hasattr(error, 'retry_after'):
            additional_info["retry_after"] = error.retry_after
        
        return UserErrorResponse(
            message=error_info["message"],
            action=error_info["action"],
            error_id=error_id,
            timestamp=datetime.utcnow().isoformat(),
            additional_info=additional_info if additional_info else None
        )
    
    async def _analyze_error_patterns(self) -> None:
        """Background task to analyze error patterns."""
        while True:
            await asyncio.sleep(300)  # Analyze every 5 minutes
            
            if self.error_buffer:
                patterns = self._identify_patterns()
                
                for pattern in patterns:
                    if pattern.frequency > 10:
                        logger.warning(
                            "Error pattern detected",
                            error_type=pattern.error_type,
                            frequency=pattern.frequency,
                            time_window=str(pattern.time_window)
                        )
                        
                        # Could trigger alerts here
                        await self._alert_on_pattern(pattern)
    
    def _identify_patterns(self) -> List[ErrorPattern]:
        """Identify error patterns in buffer."""
        patterns = {}
        current_time = datetime.utcnow()
        
        for error_entry in self.error_buffer:
            error_type = error_entry["error_type"]
            timestamp = error_entry["timestamp"]
            
            # Group errors by type within 5-minute windows
            if current_time - timestamp < timedelta(minutes=5):
                if error_type not in patterns:
                    patterns[error_type] = ErrorPattern(
                        error_type=error_type,
                        frequency=0,
                        time_window=timedelta(minutes=5),
                        first_occurrence=timestamp,
                        last_occurrence=timestamp,
                        contexts=[]
                    )
                
                pattern = patterns[error_type]
                pattern.frequency += 1
                pattern.last_occurrence = timestamp
                pattern.contexts.append(error_entry["context"])
        
        return list(patterns.values())
    
    async def _alert_on_pattern(self, pattern: ErrorPattern) -> None:
        """Send alert for error pattern."""
        # This is where you would integrate with alerting systems
        # For now, just log it
        logger.critical(
            "Error pattern alert",
            error_type=pattern.error_type,
            frequency=pattern.frequency,
            first_occurrence=pattern.first_occurrence.isoformat(),
            last_occurrence=pattern.last_occurrence.isoformat()
        )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        if not self.error_buffer:
            return {"total_errors": 0, "patterns": []}
        
        error_counts = {}
        for error_entry in self.error_buffer:
            error_type = error_entry["error_type"]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "total_errors": len(self.error_buffer),
            "error_types": error_counts,
            "patterns": [
                {
                    "type": p.error_type,
                    "frequency": p.frequency,
                    "time_window": str(p.time_window)
                }
                for p in self._identify_patterns()
            ],
            "circuit_breakers": {
                name: {
                    "state": breaker.state.state.value,
                    "failure_count": breaker.state.failure_count
                }
                for name, breaker in self.circuit_breakers.items()
            }
        }


class GlobalErrorHandler:
    """Global error handler singleton."""
    _instance: Optional[ErrorHandler] = None
    
    @classmethod
    def get_instance(cls) -> ErrorHandler:
        """Get or create global error handler instance."""
        if cls._instance is None:
            cls._instance = ErrorHandler()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset global instance (mainly for testing)."""
        cls._instance = None