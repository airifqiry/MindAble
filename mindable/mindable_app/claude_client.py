from __future__ import annotations

import logging
import os
import time
from functools import lru_cache

import anthropic
import httpx

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0


@lru_cache(maxsize=1)
def get_claude_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY.")
    http_client = httpx.Client(trust_env=False, timeout=45.0)
    return anthropic.Anthropic(api_key=api_key, http_client=http_client)


def extract_text(response: anthropic.types.Message) -> str:
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def claude_messages_create(**kwargs) -> anthropic.types.Message:
    client = get_claude_client()
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.messages.create(**kwargs)
            if not extract_text(response):
                raise ValueError("Claude returned an empty response.")
            return response
        except anthropic.RateLimitError as exc:
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Claude rate-limited, retrying in %.1fs", delay)
            time.sleep(delay)
        except anthropic.APIStatusError as exc:
            if exc.status_code and exc.status_code < 500:
                raise
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Claude server error %s, retrying in %.1fs", exc.status_code, delay)
            time.sleep(delay)
        except anthropic.APIConnectionError as exc:
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Claude connection error, retrying in %.1fs", delay)
            time.sleep(delay)
    raise RuntimeError("Claude request failed after retries.") from last_exc
