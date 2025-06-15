"""
BrowserBot monitoring and observability components.
"""

from .metrics_server import MetricsServer, task_counter, task_duration, active_browsers
from .observability import (
    observability,
    performance_monitor,
    health_checker,
    trace_operation,
    measure_time,
    ObservabilityManager,
    PerformanceMonitor,
    HealthChecker
)

__version__ = "0.1.0"

__all__ = [
    # Metrics server
    "MetricsServer",
    "task_counter",
    "task_duration",
    "active_browsers",
    
    # Observability
    "observability",
    "performance_monitor",
    "health_checker",
    "trace_operation",
    "measure_time",
    "ObservabilityManager",
    "PerformanceMonitor",
    "HealthChecker"
]