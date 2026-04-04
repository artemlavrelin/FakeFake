"""
Centralized logging configuration for ContestBot.
All modules import logger from here for consistent formatting.
"""
import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Optional: write to file alongside stdout
LOG_FILE = Path("logs/contest_bot.log")


def setup_logging(level: int = logging.INFO, to_file: bool = False) -> None:
    """Call once at startup in bot.py."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if to_file:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=handlers,
    )

    # Suppress noisy libs
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
