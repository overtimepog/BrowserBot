# Production-Grade Error Handling Best Practices for BrowserBot

## Overview

This document outlines production-grade error handling best practices for Python web automation applications, based on 2024 industry standards and research from leading tech companies.

## Table of Contents

1. [Error Handling Patterns for Browser Automation](#1-error-handling-patterns-for-browser-automation)
2. [LangChain Agent Error Handling](#2-langchain-agent-error-handling)
3. [Production Error Monitoring and Alerting](#3-production-error-monitoring-and-alerting)
4. [Graceful Degradation Patterns](#4-graceful-degradation-patterns)
5. [Error Categorization and Prioritization](#5-error-categorization-and-prioritization)
6. [Retry Strategies with Circuit Breakers](#6-retry-strategies-with-circuit-breakers)
7. [User-Friendly Error Messages](#7-user-friendly-error-messages)
8. [Error Logging and Observability](#8-error-logging-and-observability)
9. [Implementation Examples](#9-implementation-examples)

## 1. Error Handling Patterns for Browser Automation

### Playwright Best Practices (2024)

#### Common Error Types
- **Timeout Errors**: Operations taking longer than expected
- **Element Not Found**: Scripts trying to interact with unavailable elements
- **Network Issues**: Connection problems, DNS failures
- **Flaky Tests**: Intermittent failures due to timing issues

#### Best Practices

1. **Use Auto-Retrying Assertions**
```python
# Good: Auto-retrying assertion
await expect(page.locator(".button")).to_be_visible()

# Instead of manual waits
await page.wait_for_selector(".button")
```

2. **Implement Proper Error Handling**
```python
async def safe_click(page, selector: str, timeout: int = 30000):
    try:
        await page.locator(selector).click(timeout=timeout)
    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout clicking {selector}", error=str(e))
        # Take screenshot for debugging
        await page.screenshot(path=f"error_{selector}_{datetime.now()}.png")
        raise
    except Exception as e:
        logger.error(f"Unexpected error clicking {selector}", error=str(e))
        raise
```

3. **Use Resilient Locators**
```python
# Prefer data attributes and stable selectors
page.locator("[data-testid='submit-button']")

# Over fragile selectors
page.locator("div.btn.btn-primary:nth-child(3)")
```

4. **Implement Test Isolation**
```python
async def test_with_fresh_context(browser):
    context = await browser.new_context(
        # Fresh state for each test
        storage_state=None,
        locale='en-US',
        timezone_id='America/New_York'
    )
    try:
        page = await context.new_page()
        # Test logic here
    finally:
        await context.close()
```

## 2. LangChain Agent Error Handling

### Recovery Strategies (2024)

1. **Error Propagation to LLM**
```python
class AgentErrorHandler:
    def handle_tool_error(self, error: Exception, tool_name: str) -> str:
        """Format error for LLM understanding"""
        error_context = {
            "tool": tool_name,
            "error_type": type(error).__name__,
            "message": str(error),
            "suggestion": self._get_error_suggestion(error)
        }
        
        return f"""Tool execution failed:
        Tool: {error_context['tool']}
        Error: {error_context['message']}
        Suggestion: {error_context['suggestion']}
        
        Please try an alternative approach or tool."""
```

2. **Retry with Backoff Pattern**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientAgent:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def execute_with_retry(self, task: str):
        try:
            return await self.agent_executor.ainvoke({"input": task})
        except Exception as e:
            logger.warning(f"Agent execution failed: {e}")
            raise
```

3. **Multi-Agent Fallback**
```python
class MultiAgentSystem:
    def __init__(self):
        self.primary_agent = PrimaryAgent()
        self.fallback_agent = SimplifiedAgent()
    
    async def execute(self, task: str):
        try:
            return await self.primary_agent.execute(task)
        except Exception as e:
            logger.warning(f"Primary agent failed, using fallback: {e}")
            return await self.fallback_agent.execute(task)
```

## 3. Production Error Monitoring and Alerting

### Modern Observability Stack (2024)

1. **Structured Logging with Context**
```python
import structlog

logger = structlog.get_logger()

def log_error_with_context(error: Exception, context: dict):
    logger.error(
        "operation_failed",
        error_type=type(error).__name__,
        error_message=str(error),
        traceback=traceback.format_exc(),
        **context
    )
```

2. **Metrics Collection**
```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
error_counter = Counter(
    'browserbot_errors_total',
    'Total number of errors',
    ['error_type', 'severity', 'component']
)

operation_duration = Histogram(
    'browserbot_operation_duration_seconds',
    'Operation duration',
    ['operation_type', 'status']
)

# Use in code
@operation_duration.time()
def perform_operation():
    try:
        # Operation logic
        pass
    except Exception as e:
        error_counter.labels(
            error_type=type(e).__name__,
            severity='high',
            component='browser'
        ).inc()
        raise
```

3. **Distributed Tracing**
```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

async def traced_operation(operation_name: str):
    with tracer.start_as_current_span(operation_name) as span:
        try:
            # Operation logic
            span.set_attribute("operation.status", "success")
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
```

## 4. Graceful Degradation Patterns

### Implementation Strategies

1. **Feature Flags for Degradation**
```python
class FeatureFlags:
    def __init__(self):
        self.flags = {
            "use_advanced_ai": True,
            "enable_screenshots": True,
            "parallel_execution": True
        }
    
    def degrade_features(self, error_rate: float):
        """Automatically degrade features based on error rate"""
        if error_rate > 0.5:
            self.flags["parallel_execution"] = False
        if error_rate > 0.7:
            self.flags["use_advanced_ai"] = False
```

2. **Fallback Mechanisms**
```python
class BrowserOperations:
    async def click_element(self, selector: str):
        strategies = [
            self._click_with_playwright,
            self._click_with_javascript,
            self._click_with_coordinates
        ]
        
        for strategy in strategies:
            try:
                return await strategy(selector)
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue
        
        raise Exception(f"All click strategies failed for {selector}")
```

3. **Load Shedding**
```python
class LoadManager:
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.request_count = 0
        self.error_rate = 0.0
    
    async def acquire(self):
        if self.error_rate > 0.8:
            # Shed 50% of load when error rate is high
            if random.random() > 0.5:
                raise Exception("Load shedding: Request rejected")
        
        await self.semaphore.acquire()
```

## 5. Error Categorization and Prioritization

### Error Severity Levels

```python
from enum import Enum

class ErrorSeverity(Enum):
    DEBUG = 10      # Diagnostic information
    INFO = 20       # Informational messages
    WARNING = 30    # Warning conditions
    ERROR = 40      # Error conditions
    CRITICAL = 50   # Critical conditions

class ErrorClassifier:
    def classify_error(self, error: Exception) -> ErrorSeverity:
        if isinstance(error, AuthenticationError):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, RateLimitError):
            return ErrorSeverity.WARNING
        elif isinstance(error, TimeoutError):
            return ErrorSeverity.ERROR
        elif isinstance(error, ValidationError):
            return ErrorSeverity.INFO
        else:
            return ErrorSeverity.ERROR
```

### Alert Routing

```python
class AlertRouter:
    def __init__(self):
        self.routes = {
            ErrorSeverity.CRITICAL: self.page_oncall,
            ErrorSeverity.ERROR: self.send_to_slack,
            ErrorSeverity.WARNING: self.log_to_dashboard,
            ErrorSeverity.INFO: self.log_only
        }
    
    async def route_alert(self, error: Exception, context: dict):
        severity = ErrorClassifier().classify_error(error)
        handler = self.routes.get(severity, self.log_only)
        await handler(error, context)
```

## 6. Retry Strategies with Circuit Breakers

### Advanced Retry Implementation

```python
class SmartRetry:
    def __init__(self):
        self.circuit_breakers = {}
    
    def get_circuit_breaker(self, service: str) -> CircuitBreaker:
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=Exception
            )
        return self.circuit_breakers[service]
    
    async def execute_with_circuit_breaker(
        self, 
        service: str, 
        operation: Callable,
        *args, 
        **kwargs
    ):
        breaker = self.get_circuit_breaker(service)
        
        try:
            return await breaker.async_call(operation, *args, **kwargs)
        except CircuitBreakerOpen:
            # Use fallback or cached data
            return await self.get_fallback_response(service)
```

### Adaptive Retry Strategy

```python
class AdaptiveRetry:
    def __init__(self):
        self.performance_history = []
    
    def calculate_delay(self, attempt: int, error: Exception) -> float:
        """Calculate delay based on error type and system performance"""
        base_delay = 1.0
        
        if isinstance(error, RateLimitError):
            # Respect rate limit headers
            return error.retry_after or 60
        elif isinstance(error, NetworkError):
            # Exponential backoff for network errors
            return min(base_delay * (2 ** attempt), 300)
        else:
            # Linear backoff for other errors
            return min(base_delay * attempt, 60)
```

## 7. User-Friendly Error Messages

### Error Message Guidelines

```python
class UserFriendlyErrors:
    ERROR_MESSAGES = {
        "ElementNotFound": {
            "user": "Unable to find the requested element on the page. The page layout may have changed.",
            "action": "Please refresh the page and try again."
        },
        "NetworkTimeout": {
            "user": "The connection is taking longer than expected.",
            "action": "Check your internet connection and try again."
        },
        "AuthenticationFailed": {
            "user": "Unable to verify your credentials.",
            "action": "Please check your username and password."
        }
    }
    
    def format_error_for_user(self, error: Exception) -> dict:
        error_type = type(error).__name__
        error_info = self.ERROR_MESSAGES.get(error_type, {
            "user": "An unexpected error occurred.",
            "action": "Please try again later or contact support."
        })
        
        return {
            "message": error_info["user"],
            "action": error_info["action"],
            "error_id": self.generate_error_id(),
            "timestamp": datetime.now().isoformat()
        }
```

### Progressive Error Disclosure

```python
class ProgressiveErrorHandler:
    def format_error_response(
        self, 
        error: Exception, 
        user_type: str = "end_user"
    ) -> dict:
        base_response = {
            "success": False,
            "error_id": str(uuid.uuid4())
        }
        
        if user_type == "end_user":
            base_response.update({
                "message": self.get_user_friendly_message(error),
                "action": self.get_suggested_action(error)
            })
        elif user_type == "developer":
            base_response.update({
                "message": str(error),
                "type": type(error).__name__,
                "stack_trace": traceback.format_exc(),
                "context": self.get_error_context(error)
            })
        
        return base_response
```

## 8. Error Logging and Observability

### Comprehensive Error Context

```python
class ErrorLogger:
    def log_error(self, error: Exception, operation: str, context: dict):
        error_details = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            },
            "context": {
                "user_id": context.get("user_id"),
                "session_id": context.get("session_id"),
                "browser_info": context.get("browser_info"),
                "page_url": context.get("page_url"),
                "action_history": context.get("action_history", [])
            },
            "system": {
                "memory_usage": self.get_memory_usage(),
                "cpu_usage": self.get_cpu_usage(),
                "active_connections": self.get_active_connections()
            }
        }
        
        logger.error("operation_failed", **error_details)
```

### Error Aggregation and Analysis

```python
class ErrorAnalyzer:
    def __init__(self):
        self.error_buffer = []
        self.analysis_interval = 300  # 5 minutes
    
    async def analyze_error_patterns(self):
        """Identify error patterns and potential root causes"""
        while True:
            await asyncio.sleep(self.analysis_interval)
            
            if self.error_buffer:
                patterns = self.identify_patterns(self.error_buffer)
                
                for pattern in patterns:
                    if pattern["frequency"] > 10:
                        await self.alert_on_pattern(pattern)
                
                self.error_buffer.clear()
    
    def identify_patterns(self, errors: List[dict]) -> List[dict]:
        """Group errors by type, component, and time window"""
        # Implementation for pattern detection
        pass
```

## 9. Implementation Examples

### Complete Error Handling Flow

```python
class ResilientBrowserBot:
    def __init__(self):
        self.error_handler = ErrorHandler()
        self.retry_manager = SmartRetry()
        self.monitor = ErrorMonitor()
    
    async def execute_task(self, task: str) -> dict:
        operation_id = str(uuid.uuid4())
        
        try:
            # Start monitoring
            with self.monitor.track_operation(operation_id):
                # Execute with circuit breaker
                result = await self.retry_manager.execute_with_circuit_breaker(
                    service="browser_automation",
                    operation=self._perform_task,
                    task=task
                )
                
                return {
                    "success": True,
                    "result": result,
                    "operation_id": operation_id
                }
                
        except Exception as e:
            # Log error with full context
            self.error_handler.log_error(e, operation_id)
            
            # Format user-friendly response
            user_response = self.error_handler.format_user_response(e)
            
            # Trigger appropriate alerts
            await self.error_handler.send_alerts(e)
            
            return {
                "success": False,
                **user_response,
                "operation_id": operation_id
            }
```

### Error Recovery Workflow

```python
class ErrorRecoveryWorkflow:
    async def recover_from_error(
        self, 
        error: Exception, 
        context: dict
    ) -> Optional[dict]:
        """Attempt to recover from error"""
        
        recovery_strategies = [
            self.retry_with_fresh_session,
            self.use_alternative_method,
            self.degrade_to_simple_mode,
            self.return_cached_result
        ]
        
        for strategy in recovery_strategies:
            try:
                logger.info(f"Attempting recovery: {strategy.__name__}")
                result = await strategy(error, context)
                if result:
                    return result
            except Exception as recovery_error:
                logger.warning(
                    f"Recovery strategy failed: {strategy.__name__}",
                    error=str(recovery_error)
                )
                continue
        
        return None
```

## Conclusion

These best practices represent the current state-of-the-art in production error handling for Python web automation applications. Key takeaways:

1. **Proactive Error Prevention**: Use resilient selectors, auto-retrying assertions, and proper test isolation
2. **Intelligent Recovery**: Implement circuit breakers, adaptive retry strategies, and graceful degradation
3. **Comprehensive Monitoring**: Use structured logging, distributed tracing, and real-time metrics
4. **User Experience**: Provide clear, actionable error messages without exposing technical details
5. **Continuous Improvement**: Analyze error patterns and continuously refine error handling strategies

Remember that error handling is not just about catching exceptions—it's about building resilient systems that can gracefully handle failures and provide value even under adverse conditions.