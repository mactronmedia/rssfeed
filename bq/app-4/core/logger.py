import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.config import settings

class Logger:
    def __init__(self):
        self.logger = logging.getLogger("rss_aggregator")
        self._setup_logger()

    def _setup_logger(self):
        """Configure the logger with handlers and formatters."""
        # Set log level from settings
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Clear existing handlers to avoid duplicate logs
        self.logger.handlers = []

        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Standard output handler
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(log_level)
        stdout_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        stdout_handler.setFormatter(stdout_formatter)
        self.logger.addHandler(stdout_handler)

        # File handler with rotation (only in production)
        if not settings.debug:
            file_handler = RotatingFileHandler(
                "logs/rss_aggregator.log",
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3,
                encoding="utf-8"
            )
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]"
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

        # Capture warnings
        logging.captureWarnings(True)

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger

# Initialize logger when module is imported
logger = Logger().get_logger()

def log_error(
    error: Exception,
    message: Optional[str] = None,
    context: Optional[dict] = None,
    exc_info: bool = True
):
    """Helper function to log errors with context.
    
    Args:
        error: The exception that occurred
        message: Custom error message
        context: Additional context data to log
        exc_info: Whether to include exception info in the log
    """
    log_message = message or str(error)
    if context:
        log_message = f"{log_message} - Context: {context}"
    logger.error(log_message, exc_info=exc_info)


def log_request_completion(
    method: str,
    path: str,
    status_code: int,
    duration: float,
    request_id: Optional[str] = None
):
    """Log HTTP request completion with relevant details.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: Response status code
        duration: Request duration in seconds
        request_id: Optional request ID for tracing
    """
    extra = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration": duration,
    }
    if request_id:
        extra["request_id"] = request_id

    logger.info(
        f"{method} {path} completed with {status_code} in {duration:.4f}s",
        extra=extra
    )


def log_feed_processing(
    feed_url: str,
    items_processed: int,
    new_items: int,
    duration: float
):
    """Log feed processing results.
    
    Args:
        feed_url: The feed URL being processed
        items_processed: Total items processed
        new_items: Number of new items added
        duration: Processing duration in seconds
    """
    logger.info(
        f"Processed feed {feed_url} - {items_processed} items ({new_items} new) in {duration:.2f}s",
        extra={
            "feed_url": feed_url,
            "items_processed": items_processed,
            "new_items": new_items,
            "duration": duration
        }
    )