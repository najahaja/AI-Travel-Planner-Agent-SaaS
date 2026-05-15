import sys
import io
# pyrefly: ignore [missing-import]
from loguru import logger
from app.core.config import settings


def setup_logging():
    logger.remove()  # Remove default handler

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Wrap stdout with UTF-8 encoding to handle emoji on Windows
    try:
        utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        utf8_stdout = sys.stdout

    # Console handler
    logger.add(
        utf8_stdout,
        format=log_format,
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=False,  # Disable color to avoid encoding issues on Windows
    )

    # File handler — rotating logs
    logger.add(
        "logs/app.log",
        format=log_format,
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    logger.info(f"[APP] {settings.APP_NAME} v{settings.APP_VERSION} - Logging initialized")
