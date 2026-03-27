from __future__ import annotations
from users.models import RejectedJob

from typing import List, Tuple
from django.contrib.auth import get_user_model

Embedding = List[float]


def record_rejection(
    user_id: int,
    job_id: str,
    skills_embedding: Embedding,
    needs_embedding: Embedding,
    reason: str | None = None,
) -> None:


    already_exists = RejectedJob.objects.filter(
        user_id=user_id,
        job_id=job_id,
    ).exists()

    if already_exists:
        return

    RejectedJob.objects.create(
        user_id=user_id,
        job_id=job_id,
        skills_embedding=skills_embedding,
        needs_embedding=needs_embedding,
        reason=reason,
    )


def get_rejected_embeddings(
    user_id: int,
) -> List[Tuple[Embedding, Embedding]]:

    rejections = RejectedJob.objects.filter(
        user_id=user_id,
    ).values_list("skills_embedding", "needs_embedding")

    return [(skills, needs) for skills, needs in rejections]


def clear_rejections(user_id: int) -> int:

    deleted_count, _ = RejectedJob.objects.filter(
        user_id=user_id,
    ).delete()

    return deleted_count