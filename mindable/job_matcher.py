
from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import Final

from dotenv import load_dotenv
import anthropic

from mindable.prompts import JOB_MATCHER_MODEL, JOB_MATCHER_SYSTEM

load_dotenv()

logger = logging.getLogger(__name__)


_MAX_SEARCH_USES: Final[int] = 3


_MAX_RETRIES: Final[int] = 3
_RETRY_BASE_DELAY: Final[float] = 1.0


_WEB_SEARCH_TOOL: Final[dict] = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": _MAX_SEARCH_USES,
}

_USER_PROMPT_TEMPLATE: Final[str] = """
Developer skill profile:
{skills}


Preferred location: {location}
Preferred work type: {work_type}

Search for current {work_type} job listings that match this skill profile.
Find real, active job postings — not general advice.
Return the top 3 best matches ranked from best to worst fit.

For each job include:
- Job title
- Company name
- Location or remote status
- Why it matches this developer's skills
- A direct link to apply
""".strip()


@lru_cache(maxsize=1)
def _get_client() -> anthropic.Anthropic:
   
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing ANTHROPIC_API_KEY. Set it in your environment or a .env file."
        )
    return anthropic.Anthropic(api_key=key)


def _extract_text(response: anthropic.types.Message) -> str:

    return "".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    ).strip()


def _call_with_retry(client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Rate limited; retrying in %.1fs (attempt %d/%d).",
                delay, attempt + 1, _MAX_RETRIES,
            )
            time.sleep(delay)
        except anthropic.APIStatusError as exc:
            if exc.status_code and exc.status_code < 500:
                raise
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Server error %d; retrying in %.1fs (attempt %d/%d).",
                exc.status_code, delay, attempt + 1, _MAX_RETRIES,
            )
            time.sleep(delay)
        except anthropic.APIConnectionError as exc:
            last_exc = exc
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Connection error; retrying in %.1fs (attempt %d/%d).",
                delay, attempt + 1, _MAX_RETRIES,
            )
            time.sleep(delay)

    raise RuntimeError("Job matching failed after all retries.") from last_exc


def match_jobs(
    skills: list[str],
    location: str = "Remote",
    work_type: str = "remote",
) -> str:
    
    if not skills:
        raise ValueError("skills must be a non-empty list.")

    skills_str = ", ".join(skills)
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        skills=skills_str,
        location=location,
        work_type=work_type,
    )

    client = _get_client()

    response = _call_with_retry(
        client,
        model=JOB_MATCHER_MODEL,
        max_tokens=1024,
        system=JOB_MATCHER_SYSTEM,
        tools=[_WEB_SEARCH_TOOL],
        messages=[{"role": "user", "content": user_prompt}],
    )

    out = _extract_text(response)
    if not out:
        raise ValueError("Job matching produced an empty response.")

    logger.info(
        "Job matching complete. Stop reason: %s. Searches used: up to %d.",
        response.stop_reason,
        _MAX_SEARCH_USES,
    )

    return out


def match_jobs_with_ranker(
    skills: list[str],
    ranked_job_texts: list[str],
    years_experience: int = 0,
    work_type: str = "remote",
) -> str:
   
    if not skills:
        raise ValueError("skills must be a non-empty list.")
    if not ranked_job_texts:
        raise ValueError("ranked_job_texts must be a non-empty list.")

    skills_str = ", ".join(skills)
    jobs_block = "\n\n---\n\n".join(
        f"Job {i + 1}:\n{text}" for i, text in enumerate(ranked_job_texts)
    )

    user_prompt = (
        f"Developer skills: {skills_str}\n"
       
        f"Preferred work type: {work_type}\n\n"
        f"The following job listings have already been ranked by skill similarity. "
        f"Explain in plain language why each job is or isn't a good match, "
        f"starting with the best match. Be specific about which skills align.\n\n"
        f"{jobs_block}"
    )

    client = _get_client()

    
    response = _call_with_retry(
        client,
        model=JOB_MATCHER_MODEL,
        max_tokens=1024,
        system=JOB_MATCHER_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    out = _extract_text(response)
    if not out:
        raise ValueError("Job analysis produced an empty response.")

    return out