"""
Production-grade observability system for BrowserBot.
Implements distributed tracing, metrics, and structured logging.
"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable, TypeVar
from datetime import datetime
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
import uuid

from prometheus_client import Counter, Histogram, Gauge, Info
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)

T = TypeVar("T")

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Metrics
operation_counter = Counter(
    'browserbot_operations_total',
    'Total number of operations',
    ['operation', 'status', 'error_type']
)

operation_duration = Histogram(
    'browserbot_operation_duration_seconds',
    'Operation duration in seconds',
    ['operation', 'status']
)

active_operations = Gauge(
    'browserbot_active_operations',
    'Number of currently active operations',
    ['operation']
)

browser_pool_size = Gauge(
    'browserbot_browser_pool_size',
    'Number of browsers in the pool'
)

memory_usage = Gauge(
    'browserbot_memory_usage_bytes',
    'Memory usage in bytes'
)

system_info = Info(
    'browserbot_system',
    'System information'
)


class ObservabilityManager:
    """
    Manages observability features including tracing, metrics, and logging.
    """
    
    def __init__(self):
        self.tracer = tracer
        self._setup_exporters()
        self._instrument_libraries()
        
        # Start background tasks
        asyncio.create_task(self._collect_system_metrics())
    
    def _setup_exporters(self) -> None:
        """Setup trace exporters."""
        if settings.otlp_endpoint:
            # Setup OTLP exporter for traces
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.otlp_endpoint,
                insecure=True
            )
            
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            logger.info("OTLP exporter configured", endpoint=settings.otlp_endpoint)
    
    def _instrument_libraries(self) -> None:
        """Instrument third-party libraries."""
        # Instrument aiohttp for automatic HTTP tracing
        AioHttpClientInstrumentor().instrument()
    
    @asynccontextmanager
    async def trace_operation(
        self,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing operations.
        
        Usage:
            async with observability.trace_operation("fetch_page", {"url": url}) as span:
                # Operation code here
                pass
        """
        with self.tracer.start_as_current_span(operation_name) as span:
            # Add attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            # Track active operations
            active_operations.labels(operation=operation_name).inc()
            
            start_time = time.time()
            status = "success"
            error_type = None
            
            try:
                yield span
                
            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                status = "error"
                error_type = type(e).__name__
                
                # Re-raise the exception
                raise
                
            finally:
                # Update metrics
                duration = time.time() - start_time
                
                operation_counter.labels(
                    operation=operation_name,
                    status=status,
                    error_type=error_type or ""
                ).inc()
                
                operation_duration.labels(
                    operation=operation_name,
                    status=status
                ).observe(duration)
                
                active_operations.labels(operation=operation_name).dec()
    
    def trace_function(
        self,
        operation_name: Optional[str] = None,
        capture_args: bool = False
    ):
        """
        Decorator for tracing functions.
        
        Usage:
            @observability.trace_function()
            async def my_function(arg1, arg2):
                pass
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            name = operation_name or f"{func.__module__}.{func.__name__}"
            
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs) -> T:
                    attributes = {}
                    
                    if capture_args:
                        # Capture function arguments
                        attributes["args"] = str(args)[:200]  # Limit size
                        attributes["kwargs"] = str(kwargs)[:200]
                    
                    async with self.trace_operation(name, attributes):
                        return await func(*args, **kwargs)
                
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs) -> T:
                    attributes = {}
                    
                    if capture_args:
                        attributes["args"] = str(args)[:200]
                        attributes["kwargs"] = str(kwargs)[:200]
                    
                    with self.tracer.start_as_current_span(name) as span:
                        if attributes:
                            for key, value in attributes.items():
                                span.set_attribute(key, value)
                        
                        try:
                            return func(*args, **kwargs)
                        except Exception as e:
                            span.record_exception(e)
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                            raise
                
                return sync_wrapper
        
        return decorator
    
    async def _collect_system_metrics(self) -> None:
        """Background task to collect system metrics."""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil not available, system metrics disabled")
            return
        
        # Set system info once
        try:
            system_info.info({
                'version': getattr(settings, 'version', '0.1.0'),
                'environment': getattr(settings, 'environment', 'development'),
                'python_version': getattr(settings, 'python_version', '3.11')
            })
        except Exception as e:
            logger.warning("Failed to set system info", error=str(e))
        
        while True:
            try:
                # Collect memory usage
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_usage.set(memory_info.rss)
                
                # Collect CPU usage
                cpu_percent = process.cpu_percent()
                
                # Collect disk I/O
                io_counters = process.io_counters()
                
                logger.debug(
                    "System metrics collected",
                    memory_mb=memory_info.rss / 1024 / 1024,
                    cpu_percent=cpu_percent,
                    disk_read_mb=io_counters.read_bytes / 1024 / 1024,
                    disk_write_mb=io_counters.write_bytes / 1024 / 1024
                )
                
            except Exception as e:
                logger.error("Failed to collect system metrics", error=str(e))
            
            await asyncio.sleep(30)  # Collect every 30 seconds
    
    def record_browser_pool_size(self, size: int) -> None:
        """Record browser pool size."""
        browser_pool_size.set(size)
    
    def create_span_context(self, operation: str) -> Dict[str, Any]:
        """Create span context for distributed tracing."""
        span = trace.get_current_span()
        if span and span.is_recording():
            context = span.get_span_context()
            return {
                "trace_id": format(context.trace_id, '032x'),
                "span_id": format(context.span_id, '016x'),
                "operation": operation
            }
        return {}


class PerformanceMonitor:
    """
    Monitor and track performance metrics.
    """
    
    def __init__(self):
        self.operation_times: Dict[str, List[float]] = {}
        self.slow_operation_threshold = 5.0  # seconds
    
    @contextmanager
    def measure_time(self, operation: str):
        """
        Context manager to measure operation time.
        
        Usage:
            with performance_monitor.measure_time("fetch_page"):
                # Operation code
                pass
        """
        start_time = time.time()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            
            # Track operation time
            if operation not in self.operation_times:
                self.operation_times[operation] = []
            
            self.operation_times[operation].append(duration)
            
            # Keep only last 100 measurements
            if len(self.operation_times[operation]) > 100:
                self.operation_times[operation] = self.operation_times[operation][-100:]
            
            # Log slow operations
            if duration > self.slow_operation_threshold:
                logger.warning(
                    "Slow operation detected",
                    operation=operation,
                    duration=duration,
                    threshold=self.slow_operation_threshold
                )
    
    def get_operation_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        if operation not in self.operation_times:
            return {}
        
        times = self.operation_times[operation]
        if not times:
            return {}
        
        return {
            "count": len(times),
            "min": min(times),
            "max": max(times),
            "avg": sum(times) / len(times),
            "p50": self._percentile(times, 50),
            "p95": self._percentile(times, 95),
            "p99": self._percentile(times, 99)
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations."""
        return {
            operation: self.get_operation_stats(operation)
            for operation in self.operation_times
        }


class HealthChecker:
    """
    Health checking system for production monitoring.
    """
    
    def __init__(self):
        self.checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self.last_check_results: Dict[str, Dict[str, Any]] = {}
    
    def register_check(self, name: str, check_func: Callable[[], Dict[str, Any]]) -> None:
        """Register a health check."""
        self.checks[name] = check_func
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                results[name] = {
                    "healthy": result.get("healthy", True),
                    "message": result.get("message", "OK"),
                    "metadata": result.get("metadata", {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if not results[name]["healthy"]:
                    overall_healthy = False
                    
            except Exception as e:
                logger.error(f"Health check failed: {name}", error=str(e))
                results[name] = {
                    "healthy": False,
                    "message": f"Check failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                overall_healthy = False
        
        self.last_check_results = results
        
        return {
            "healthy": overall_healthy,
            "checks": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get last health check status."""
        return {
            "checks": self.last_check_results,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global instances
observability = ObservabilityManager()
performance_monitor = PerformanceMonitor()
health_checker = HealthChecker()


# Convenience decorators
def trace_operation(operation_name: Optional[str] = None, capture_args: bool = False):
    """Convenience decorator for tracing operations."""
    return observability.trace_function(operation_name, capture_args)


@contextmanager
def measure_time(operation: str):
    """Convenience context manager for measuring time."""
    with performance_monitor.measure_time(operation):
        yield