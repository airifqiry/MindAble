from __future__ import annotations

from typing import List, Tuple
from django.contrib.auth import get_user_model

Embedding = List[float]
User = get_user_model()


def record_rejection(
    user_id: int,
    job_id: str,
    skills_embedding: Embedding,
    needs_embedding: Embedding,
    reason: str | None = None,
) -> None:


    from mindable_app.models import RejectedJob

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
    from mindable_app.models import RejectedJob

    rejections = RejectedJob.objects.filter(
        user_id=user_id,
    ).values_list("skills_embedding", "needs_embedding")

    return [(skills, needs) for skills, needs in rejections]


def clear_rejections(user_id: int) -> int:

    from mindable_app.models import RejectedJob

    deleted_count, _ = RejectedJob.objects.filter(
        user_id=user_id,
    ).delete()

    return deleted_count