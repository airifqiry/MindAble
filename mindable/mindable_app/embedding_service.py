from __future__ import annotations

import hashlib
import math
import re
from typing import List

_EMBED_SIZE = 384


def _embed(text: str) -> List[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text.")
    vec = [0.0] * _EMBED_SIZE
    tokens = re.findall(r"[a-zA-Z0-9\-\+#]{2,}", text.lower())
    if not tokens:
        raise ValueError("Cannot embed text with no valid tokens.")

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % _EMBED_SIZE
        sign = -1.0 if int(digest[8:10], 16) % 2 else 1.0
        weight = 1.0 + (len(token) / 20.0)
        vec[idx] += sign * weight

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def _safe_join(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v)
    return str(value)


def build_user_embeddings(profile: dict) -> tuple[List[float], List[float]]:
    skills_text = " ".join(filter(None, [
        _safe_join(profile.get("technical_skills")),
        _safe_join(profile.get("general_skills")),
        _safe_join(profile.get("skills")),
        _safe_join(profile.get("communication_style")),
        _safe_join(profile.get("work_values")),
    ]))

    needs_text = " ".join(filter(None, [
        _safe_join(profile.get("preferred_environment")),
        _safe_join(profile.get("limitations")),
        _safe_join(profile.get("accommodations_needed")),
    ]))

    if not skills_text.strip():
        raise ValueError("Profile has no skills information to embed.")
    if not needs_text.strip():
        # Keep onboarding resilient: fallback to skills context when needs are missing.
        needs_text = skills_text

    return _embed(skills_text), _embed(needs_text)


def build_job_embeddings(job_skills_text: str, job_environment_text: str) -> tuple[List[float], List[float]]:
    return _embed(job_skills_text), _embed(job_environment_text)