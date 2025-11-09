import structlog
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "app.log")

    # --- 1️⃣ Base Python logging configuration ---
    handlers = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=5)
    ]

    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=handlers)

    # --- 2️⃣ Detect if terminal supports color ---
    is_tty = sys.stdout.isatty()
    dev_mode = os.getenv("ENVIRONMENT", "development") != "production"

    # --- 3️⃣ Configure structlog processors ---
    force_plain = os.getenv("FORCE_PLAIN_LOGS") == "1"
    if dev_mode and (not is_tty or force_plain):
        # Pretty, colorized output for interactive terminals
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    elif dev_mode and not is_tty:
        # Plain readable output (no ANSI codes)
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(colors=False),
        ]
    else:
        # Production: JSON structured logs
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    # --- 4️⃣ Configure structlog globally ---
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("snug")

log = setup_logging()
