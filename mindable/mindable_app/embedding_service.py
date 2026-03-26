from __future__ import annotations

from typing import List
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")


def _embed(text: str) -> List[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text.")
    vector = _model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def _safe_join(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v)
    return str(value)


def build_user_embeddings(profile: dict) -> tuple[List[float], List[float]]:
    skills_text = " ".join(filter(None, [
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
        raise ValueError("Profile has no environment/needs information to embed.")

    return _embed(skills_text), _embed(needs_text)


def build_job_embeddings(job_skills_text: str, job_environment_text: str) -> tuple[List[float], List[float]]:
    return _embed(job_skills_text), _embed(job_environment_text)