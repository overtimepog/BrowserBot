"""
Structured logging configuration for BrowserBot.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import structlog
from structlog.types import EventDict, Processor



def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to event dict."""
    event_dict["level"] = method_name.upper()
    return event_dict


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[Path] = None,
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level
        log_format: Output format (json or text)
        log_file: Optional log file path
    """
    # Configure standard library logging
    # Use stderr for logs to avoid interfering with progress display on stdout
    log_stream = sys.stderr
    
    logging.basicConfig(
        format="%(message)s",
        stream=log_stream,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure processors
    processors: list[Processor] = [
        structlog.stdlib.add_logger_name,
        add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add appropriate renderer based on format
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set up file logging if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Use JSON format for file logs
        file_processors = processors.copy()
        if log_format != "json":
            file_processors[-1] = structlog.processors.JSONRenderer()
        
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=file_processors,
        )
        file_handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)


def get_logger(name: str, **kwargs: Any) -> structlog.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        **kwargs: Additional context to bind to logger
        
    Returns:
        Configured structlog logger
    """
    logger = structlog.get_logger(name)
    if kwargs:
        logger = logger.bind(**kwargs)
    return logger


# Initialize logging on import
import os
from .config import settings

# Check if LOG_FORMAT is set via environment variable (e.g., from run.sh)
log_format = os.environ.get("LOG_FORMAT", settings.log_format)

setup_logging(
    log_level=settings.log_level,
    log_format=log_format,
    log_file=settings.log_file,
)