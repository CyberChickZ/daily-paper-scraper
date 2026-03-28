from __future__ import annotations
import logging
import time
from functools import wraps


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("daily_paper_scraper")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
    return logger


def retry(max_retries: int = 3, backoff_base: int = 2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    sleep_time = backoff_base ** attempt
                    logging.getLogger(__name__).warning(
                        f"Retry {attempt+1}/{max_retries} for {func.__name__}: {e}, sleeping {sleep_time}s"
                    )
                    time.sleep(sleep_time)
        return wrapper
    return decorator


def split_rich_text(text: str, limit: int = 2000) -> list[dict]:
    chunks = []
    for i in range(0, len(text), limit):
        chunks.append({"type": "text", "text": {"content": text[i:i+limit]}})
    return chunks if chunks else [{"type": "text", "text": {"content": ""}}]
