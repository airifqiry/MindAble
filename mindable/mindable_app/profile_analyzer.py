from __future__ import annotations
import json
import re
from typing import Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
import anthropic
from mindable.mindable_app.prompts import (
    PROFILE_ANALYSIS_MAX_TOTAL_TOKENS,
    PROFILE_ANALYSIS_MODEL,
    PROFILE_ANALYSIS_RETRY_SUFFIX,
    PROFILE_ANALYSIS_SYSTEM,
    PROFILE_ANALYSIS_USER,
)
from mindable.mindable_app.claude_client import claude_messages_create, extract_text
load_dotenv()
class ProfileModel(BaseModel):
    
    skills: list[str] | None = Field(default=None)
    technical_skills: list[str] | None = Field(default=None)
    general_skills: list[str] | None = Field(default=None)
    preferred_environment: str | None = Field(default=None)
    communication_style: str | None = Field(default=None)
    limitations: list[str] | None = Field(default=None)
    accommodations_needed: list[str] | None = Field(default=None)
    work_values: list[str] | None = Field(default=None)
def _sanitize_for_prompt(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("profile_text must be a string")
    cleaned = text.replace("\x00", "").strip()
    patterns: tuple[re.Pattern[str], ...] = (
        re.compile(r"(?im)^\s*ignore\s+(all\s+)?(previous|prior)\s+instructions?\b.*$"),
        re.compile(r"(?im)^\s*disregard\s+(the\s+)?(above|prior)\b.*$"),
        re.compile(r"(?im)^\s*you\s+are\s+now\b.*$"),
        re.compile(r"(?im)^\s*new\s+instructions?\s*:\s*.*$"),
        re.compile(r"(?im)^\s*system\s*:\s*.*$"),
        re.compile(r"(?im)^<\s*/\s*system\s*>\s*$"),
        re.compile(r"(?im)^\s*\[?\s*INST\s*\]?\s*.*$"),
    )
    kept_lines: list[str] = []
    for line in cleaned.splitlines():
        if any(p.search(line) for p in patterns):
            continue
        kept_lines.append(line)
    out = "\n".join(kept_lines).strip()
    return out
def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)
def _truncate_profile_text_for_budget(profile_text: str) -> str:
    system_tokens = _estimate_tokens(PROFILE_ANALYSIS_SYSTEM)
    user_prefix_tokens = _estimate_tokens(PROFILE_ANALYSIS_USER.replace("{profile_text}", ""))
    overhead = system_tokens + user_prefix_tokens + 50
    remaining_tokens = PROFILE_ANALYSIS_MAX_TOTAL_TOKENS - overhead
    if remaining_tokens <= 0:
        return profile_text[:800]
    max_chars = remaining_tokens * 4
    if len(profile_text) <= max_chars:
        return profile_text
    return profile_text[:max_chars]
def _extract_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Model output was not valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("Model JSON root must be an object")
    return data
def analyze_profile(profile_text: str) -> dict[str, Any]:
    sanitized = _sanitize_for_prompt(profile_text)
    truncated_profile = _truncate_profile_text_for_budget(sanitized)
    user_prompt = PROFILE_ANALYSIS_USER.format(profile_text=truncated_profile)
    last_error: Exception | None = None
    for attempt in range(2):
        content = user_prompt + (PROFILE_ANALYSIS_RETRY_SUFFIX if attempt == 1 else "")
        try:
            message = claude_messages_create(
                model=PROFILE_ANALYSIS_MODEL,
                max_tokens=1024,
                system=PROFILE_ANALYSIS_SYSTEM,
                messages=[{"role": "user", "content": content}],
            )
            text = extract_text(message)
            parsed = _extract_json_object(text)
            model = ProfileModel.model_validate(parsed)
            return model.model_dump()
        except anthropic.APIError as exc:
            raise RuntimeError(
                "Profile analysis failed because the Anthropic API request did not succeed."
            ) from exc
        except (ValidationError, ValueError) as exc:
            last_error = exc
            continue
        except Exception as exc:
            last_error = exc
            continue
    raise ValueError(
        "Profile analysis output could not be validated as the expected schema."
    ) from last_error