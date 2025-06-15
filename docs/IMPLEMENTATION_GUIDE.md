# BrowserBot Error Handling Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing production-grade error handling in BrowserBot based on 2024 best practices.

## Quick Start

### 1. Install Additional Dependencies

```bash
pip install -r requirements-monitoring.txt
```

### 2. Basic Error Handling

```python
from browserbot.core.error_handler import GlobalErrorHandler
from browserbot.monitoring.observability import trace_operation

# Get the global error handler
error_handler = GlobalErrorHandler.get_instance()

# Use in your code
@trace_operation("my_operation")
async def my_function():
    try:
        # Your code here
        result = await perform_operation()
        return result
    except Exception as e:
        # Handle error with recovery
        error_result = await error_handler.handle_error(
            error=e,
            operation="my_operation",
            context={"additional": "context"},
            recovery_enabled=True
        )
        
        # Return user-friendly response
        return {
            "success": False,
            **error_result["user_response"].__dict__
        }
```

## Core Components

### 1. Error Handler

The `ErrorHandler` class provides:
- Automatic error categorization and severity assessment
- Recovery strategy selection based on error type
- User-friendly error message formatting
- Error pattern detection and alerting
- Integration with monitoring systems

### 2. Observability Manager

The `ObservabilityManager` provides:
- Distributed tracing with OpenTelemetry
- Prometheus metrics collection
- Performance monitoring
- Health checking system

### 3. Circuit Breaker

Prevents cascading failures:

```python
from browserbot.core.error_handler import GlobalErrorHandler

error_handler = GlobalErrorHandler.get_instance()
breaker = error_handler.get_circuit_breaker("external_service")

try:
    result = await breaker.async_call(external_service_call)
except Exception as e:
    # Circuit is open, use fallback
    result = get_cached_result()
```

## Integration Examples

### 1. Browser Operations with Error Handling

```python
from browserbot.monitoring.observability import observability

class ResilientPageController:
    async def safe_click(self, selector: str):
        """Click with comprehensive error handling."""
        
        async with observability.trace_operation(
            "safe_click",
            {"selector": selector}
        ) as span:
            strategies = [
                self._click_with_playwright,
                self._click_with_javascript,
                self._click_with_coordinates
            ]
            
            for i, strategy in enumerate(strategies):
                try:
                    result = await strategy(selector)
                    span.set_attribute("strategy_used", strategy.__name__)
                    span.set_attribute("attempt", i + 1)
                    return result
                    
                except Exception as e:
                    logger.warning(
                        f"Strategy {strategy.__name__} failed",
                        error=str(e)
                    )
                    
                    if i == len(strategies) - 1:
                        # All strategies failed
                        span.record_exception(e)
                        raise
                    
                    # Try next strategy
                    continue
```

### 2. LangChain Agent with Error Recovery

```python
class ResilientAgent:
    def __init__(self):
        self.error_handler = GlobalErrorHandler.get_instance()
    
    async def execute_with_fallback(self, task: str):
        """Execute task with fallback to simpler agent."""
        
        # Try primary agent
        try:
            return await self.primary_agent.execute(task)
            
        except AIModelError as e:
            # Log error
            await self.error_handler.handle_error(
                error=e,
                operation="primary_agent_execution",
                context={"task": task}
            )
            
            # Try fallback agent
            logger.info("Falling back to simple agent")
            return await self.simple_agent.execute(task)
```

### 3. Health Checks

```python
from browserbot.monitoring.observability import health_checker

# Register custom health checks
async def database_health():
    try:
        # Check database connection
        await db.execute("SELECT 1")
        return {"healthy": True, "message": "Database connected"}
    except Exception as e:
        return {
            "healthy": False,
            "message": f"Database error: {str(e)}"
        }

health_checker.register_check("database", database_health)

# Run health checks
health_status = await health_checker.run_checks()
```

## Production Deployment

### 1. Environment Variables

```bash
# Monitoring
export METRICS_PORT=8000
export OTLP_ENDPOINT=http://localhost:4317

# Error handling
export ERROR_REPORTING_ENABLED=true
export ERROR_PATTERN_THRESHOLD=10
export CIRCUIT_BREAKER_TIMEOUT=60
```

### 2. Docker Configuration

Add to your `docker-compose.yml`:

```yaml
services:
  browserbot:
    environment:
      - METRICS_PORT=8000
      - OTLP_ENDPOINT=otel-collector:4317
    ports:
      - "8000:8000"  # Prometheus metrics
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### 3. Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'browserbot'
    static_configs:
      - targets: ['browserbot:8000']
```

## Monitoring Dashboards

### Key Metrics to Monitor

1. **Error Rates**
   - `browserbot_errors_total` - Total errors by type and severity
   - `browserbot_error_recoveries_total` - Successful recoveries

2. **Performance**
   - `browserbot_operation_duration_seconds` - Operation latency
   - `browserbot_active_operations` - Currently running operations

3. **System Health**
   - `browserbot_active_browsers` - Browser pool size
   - `browserbot_memory_usage_bytes` - Memory consumption

### Example Grafana Query

```promql
# Error rate by type (last 5 minutes)
rate(browserbot_errors_total[5m])

# P95 operation latency
histogram_quantile(0.95, 
  sum(rate(browserbot_operation_duration_seconds_bucket[5m])) 
  by (operation, le)
)

# Circuit breaker status
browserbot_circuit_breaker_state
```

## Best Practices

### 1. Error Context

Always provide rich context when handling errors:

```python
context = {
    "user_id": user.id,
    "session_id": session.id,
    "operation": "page_navigation",
    "url": target_url,
    "browser_state": await page.evaluate("() => document.readyState"),
    "timestamp": datetime.utcnow().isoformat()
}

await error_handler.handle_error(error, "navigation", context)
```

### 2. Graceful Degradation

Implement feature flags for degradation:

```python
class FeatureManager:
    def __init__(self):
        self.features = {
            "advanced_ai": True,
            "parallel_execution": True,
            "screenshot_capture": True
        }
    
    async def check_system_health(self):
        """Degrade features based on system health."""
        health = await health_checker.run_checks()
        
        if not health["healthy"]:
            # Disable non-critical features
            self.features["parallel_execution"] = False
            self.features["screenshot_capture"] = False
            
            logger.warning(
                "System degraded - disabled non-critical features",
                health=health
            )
```

### 3. Testing Error Scenarios

```python
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_error_recovery():
    """Test error recovery mechanisms."""
    
    bot = ResilientBrowserBot()
    
    # Simulate network error
    with patch.object(bot.agent, 'execute_task') as mock_execute:
        mock_execute.side_effect = [
            NetworkError("Connection failed"),
            NetworkError("Connection failed"),
            {"success": True, "result": "Task completed"}
        ]
        
        result = await bot.execute_task_with_monitoring(
            "Test task",
            max_retries=3
        )
        
        assert result["success"] is True
        assert mock_execute.call_count == 3
```

## Troubleshooting

### Common Issues

1. **Circuit Breaker Always Open**
   - Check recovery timeout setting
   - Verify service is actually recovering
   - Look for persistent errors in logs

2. **High Error Rates**
   - Check error patterns in monitoring
   - Review recent deployments
   - Verify external service status

3. **Performance Degradation**
   - Check operation duration metrics
   - Review trace data for bottlenecks
   - Monitor resource usage

### Debug Commands

```python
# Get error statistics
stats = error_handler.get_error_stats()
print(json.dumps(stats, indent=2))

# Check circuit breaker states
for name, breaker in error_handler.circuit_breakers.items():
    print(f"{name}: {breaker.state.state.value}")

# Get performance stats
perf_stats = performance_monitor.get_all_stats()
print(json.dumps(perf_stats, indent=2))
```

## Conclusion

This implementation provides a robust foundation for production error handling in BrowserBot. Key benefits:

1. **Resilience**: Automatic recovery and graceful degradation
2. **Observability**: Comprehensive monitoring and tracing
3. **User Experience**: Clear, actionable error messages
4. **Maintainability**: Centralized error handling logic
5. **Scalability**: Circuit breakers prevent cascade failures

Remember to continuously monitor error patterns and adjust recovery strategies based on real-world usage.