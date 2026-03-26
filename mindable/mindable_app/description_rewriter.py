

from __future__ import annotations

import logging
import os
import re
import time
from functools import lru_cache
from typing import Final

from dotenv import load_dotenv
import anthropic

from mindable.mindable_app.prompts import (
    DESCRIPTION_REWRITER_MODEL,
    DESCRIPTION_REWRITER_SYSTEM,
    DESCRIPTION_REWRITER_USER,
    REWRITER_MAX_TOTAL_TOKENS,
)

load_dotenv()

logger = logging.getLogger(__name__)


_CHARS_PER_TOKEN: Final[int] = 4


_MAX_RETRIES: Final[int] = 3
_RETRY_BASE_DELAY: Final[float] = 1.0  


_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?im)^\s*ignore\s+(all\s+)?(previous|prior)\s+instructions?\b"),
    re.compile(r"(?im)^\s*disregard\s+(the\s+)?(above|prior)\b"),
    re.compile(r"(?im)^\s*new\s+instructions?\s*:\s*\S"),
    re.compile(r"(?im)^\s*system\s*:\s*\S"),
    re.compile(r"(?im)^<\s*/\s*system\s*>\s*$"),
    re.compile(r"(?im)^\s*you\s+are\s+now\s+(a|an|the)\s+\w"),
)


def _sanitize_for_prompt(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("job_text must be a string")

    cleaned = text.replace("\x00", "").strip()
    kept_lines: list[str] = []
    for line in cleaned.splitlines():
        if any(p.search(line) for p in _INJECTION_PATTERNS):
            logger.debug("Stripped potential injection line: %r", line[:80])
            continue
        kept_lines.append(line)

    return "\n".join(kept_lines).strip()


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _truncate_job_text_for_budget(job_text: str) -> str:
    sys_tokens = _estimate_tokens(DESCRIPTION_REWRITER_SYSTEM)
    user_template_tokens = _estimate_tokens(
        DESCRIPTION_REWRITER_USER.replace("{job_text}", "")
    )
    overhead_tokens = sys_tokens + user_template_tokens + 80
    remaining_tokens = REWRITER_MAX_TOTAL_TOKENS - overhead_tokens

    if remaining_tokens <= 0:
        raise ValueError(
            f"Token budget ({REWRITER_MAX_TOTAL_TOKENS}) is too small to accommodate "
            f"the system prompt and user template ({overhead_tokens} tokens overhead). "
            "Increase REWRITER_MAX_TOTAL_TOKENS."
        )

    max_chars = remaining_tokens * _CHARS_PER_TOKEN
    if len(job_text) <= max_chars:
        return job_text

    logger.warning(
        "Job text truncated from %d to %d characters to stay within token budget.",
        len(job_text),
        max_chars,
    )
    return job_text[:max_chars]


@lru_cache(maxsize=1)
def _get_client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing ANTHROPIC_API_KEY. Set it in your environment or a .env file."
        )
    return anthropic.Anthropic(api_key=key)


def _message_text(response: anthropic.types.Message) -> str:
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def _call_with_retry(client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Rate limited; retrying in %.1fs (attempt %d/%d).", delay, attempt + 1, _MAX_RETRIES)
            time.sleep(delay)
        except anthropic.APIStatusError as exc:
            if exc.status_code and exc.status_code < 500:
                raise
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Server error %d; retrying in %.1fs (attempt %d/%d).", exc.status_code, delay, attempt + 1, _MAX_RETRIES)
            time.sleep(delay)
        except anthropic.APIConnectionError as exc:
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Connection error; retrying in %.1fs (attempt %d/%d).", delay, attempt + 1, _MAX_RETRIES)
            time.sleep(delay)

    raise RuntimeError(
        "Job description rewriting failed after all retries."
    ) from last_exc


def rewrite_job_description(job_text: str) -> str:
    
    sanitized = _sanitize_for_prompt(job_text)
    truncated = _truncate_job_text_for_budget(sanitized)

    user_prompt = DESCRIPTION_REWRITER_USER.format(job_text=truncated)

    client = _get_client()

    response = _call_with_retry(
        client,
        model=DESCRIPTION_REWRITER_MODEL,
        max_tokens=1024,
        system=DESCRIPTION_REWRITER_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    out = _message_text(response)
    if not out:
        raise ValueError("Job description rewriting produced an empty response.")

    return out