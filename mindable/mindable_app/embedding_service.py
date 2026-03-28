from __future__ import annotations

import logging
import os
import threading
from typing import List

logger = logging.getLogger(__name__)


_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_EXPECTED_DIM = 384

_model_lock = threading.Lock()
_model = None


def get_embedding_model_name() -> str:
    try:
        from django.conf import settings

        if settings.configured:
            return getattr(settings, "MINDABLE_EMBEDDING_MODEL", _DEFAULT_MODEL)
    except Exception:
        pass
    return os.environ.get("MINDABLE_EMBEDDING_MODEL", _DEFAULT_MODEL)


def get_embedding_version() -> str:
    try:
        from django.conf import settings

        if settings.configured:
            return getattr(settings, "MINDABLE_EMBEDDING_VERSION", "st-v1")
    except Exception:
        pass
    return os.environ.get("MINDABLE_EMBEDDING_VERSION", "st-v1")


def _get_sentence_transformer():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from sentence_transformers import SentenceTransformer

        name = get_embedding_model_name()
        logger.info("Loading SentenceTransformer model: %s", name)
        _model = SentenceTransformer(name)
        return _model


def _encode(text: str) -> List[float]:
    if not text or not str(text).strip():
        raise ValueError("Cannot embed empty text.")
    model = _get_sentence_transformer()
    vec = model.encode(
        str(text).strip(),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    out = vec.tolist()
    if len(out) != _EXPECTED_DIM:
        raise ValueError(
            f"Embedding dimension {len(out)} != expected {_EXPECTED_DIM} for model {get_embedding_model_name()}. "
            "Use a 384-d model (e.g. all-MiniLM-L6-v2) or migrate DB field sizes."
        )
    return out


def _safe_join(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v)
    return str(value)


def build_user_embeddings(profile: dict) -> tuple[List[float], List[float]]:
    skills_text = " ".join(
        filter(
            None,
            [
                _safe_join(profile.get("technical_skills")),
                _safe_join(profile.get("general_skills")),
                _safe_join(profile.get("skills")),
                _safe_join(profile.get("communication_style")),
                _safe_join(profile.get("work_values")),
            ],
        )
    )

    needs_text = " ".join(
        filter(
            None,
            [
                _safe_join(profile.get("preferred_environment")),
                _safe_join(profile.get("limitations")),
                _safe_join(profile.get("accommodations_needed")),
            ],
        )
    )

    if not skills_text.strip():
        raise ValueError("Profile has no skills information to embed.")
    if not needs_text.strip():
        needs_text = skills_text

    return _encode(skills_text), _encode(needs_text)


def build_job_embeddings(job_skills_text: str, job_environment_text: str) -> tuple[List[float], List[float]]:
    return _encode(job_skills_text), _encode(job_environment_text)
