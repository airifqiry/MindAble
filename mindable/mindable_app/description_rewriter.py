

from __future__ import annotations

import logging
import re
from typing import Final

from dotenv import load_dotenv

from mindable.mindable_app.prompts import (
    DESCRIPTION_REWRITER_MODEL,
    DESCRIPTION_REWRITER_SYSTEM,
    DESCRIPTION_REWRITER_USER,
    REWRITER_MAX_TOTAL_TOKENS,
)
from mindable.mindable_app.claude_client import claude_messages_create, extract_text

load_dotenv()

logger = logging.getLogger(__name__)


_CHARS_PER_TOKEN: Final[int] = 4


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


def rewrite_job_description(job_text: str) -> str:
    sanitized = _sanitize_for_prompt(job_text)
    truncated = _truncate_job_text_for_budget(sanitized)

    user_prompt = DESCRIPTION_REWRITER_USER.format(job_text=truncated)

    response = claude_messages_create(
        model=DESCRIPTION_REWRITER_MODEL,
        max_tokens=1024,
        system=DESCRIPTION_REWRITER_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    out = extract_text(response)
    if not out:
        raise ValueError("Job description rewriting produced an empty response.")

    return _normalize_rewriter_output(out)


def _normalize_rewriter_output(text: str) -> str:
    """
    Collapse list-like lines into a single conversational paragraph for display.
    Strips common bullet/number prefixes the model might still emit.
    """
    raw = (text or "").strip()
    if not raw:
        return raw

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    cleaned: list[str] = []
    for ln in lines:
        ln = re.sub(r"^[\-\*•]+\s*", "", ln)
        ln = re.sub(r"^\d{1,2}[\.)]\s*", "", ln)
        if ln:
            cleaned.append(ln)

    merged = " ".join(cleaned) if cleaned else raw
    merged = re.sub(r"\s+", " ", merged).strip()
    return merged