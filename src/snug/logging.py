import structlog
import logging
import sys
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Configure unified structured logging for Snug Rental AI."""

    # ─────────────────────────────
    # 1️⃣ Base setup
    # ─────────────────────────────
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "app.log")

    handlers = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=5)
    ]

    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=handlers)

    # ─────────────────────────────
    # 2️⃣ Determine mode
    # ─────────────────────────────
    dev_mode = os.getenv("ENVIRONMENT", "development") != "production"
    force_plain = True  # 💡 force disable colors permanently

    # ─────────────────────────────
    # 3️⃣ Configure structlog processors
    # ─────────────────────────────
    if dev_mode:
        # Plain readable logs in dev — no color codes
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(colors=False),  # ✅ no ANSI escapes
        ]
    else:
        # Production: JSON structured logs
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("snug")


# ─────────────────────────────
# 🌐 Global default logger
# ─────────────────────────────
log = setup_logging()


# ─────────────────────────────
# 🧩 Helper for contextual loggers
# ─────────────────────────────
def get_agent_logger(agent_name: str, request_id: str = None):
    """
    Create a bound logger for a specific AI agent (IntentAgent, ComplianceAgent, etc.).
    Automatically attaches the agent name and request ID to every log entry.
    """
    bound = log.bind(agent=agent_name)
    if request_id:
        bound = bound.bind(request_id=request_id)
    return bound
