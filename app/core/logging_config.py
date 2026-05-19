"""
Logging configuration for the assessment backend.
Logs to both console and file with timestamps and log levels.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from app.core.config import settings


# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log file paths
SUBMISSION_LOG_FILE = LOG_DIR / "submission.log"
ERROR_LOG_FILE = LOG_DIR / "error.log"
DEBUG_LOG_FILE = LOG_DIR / "debug.log"

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


class SafeStreamHandler(logging.StreamHandler):
    """Console handler that degrades unsupported Unicode instead of crashing."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except UnicodeEncodeError:
            try:
                msg = self.format(record)
                stream = self.stream
                encoding = getattr(stream, "encoding", None) or "utf-8"
                safe_msg = msg.encode(encoding, errors="replace").decode(
                    encoding,
                    errors="replace",
                )
                stream.write(safe_msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)


def setup_logging() -> None:
    """Configure logging for the application."""
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    # Console handler - INFO level. On Windows, unsupported Unicode is replaced.
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    root_logger.addHandler(console_handler)
    
    # Submission log file handler - DEBUG level
    submission_handler = logging.handlers.RotatingFileHandler(
        SUBMISSION_LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    submission_handler.setLevel(logging.DEBUG)
    submission_formatter = logging.Formatter(LOG_FORMAT)
    submission_handler.setFormatter(submission_formatter)
    root_logger.addHandler(submission_handler)
    
    # Error log file handler - ERROR level
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(LOG_FORMAT)
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # Debug log file handler - DEBUG level (only in local environment)
    if settings.ENVIRONMENT == "local":
        debug_handler = logging.handlers.RotatingFileHandler(
            DEBUG_LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
            encoding="utf-8",
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_formatter = logging.Formatter(LOG_FORMAT)
        debug_handler.setFormatter(debug_formatter)
        root_logger.addHandler(debug_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)
