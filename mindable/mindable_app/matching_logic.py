from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, List, Optional, Sequence, Tuple

Embedding = Sequence[float]

SKILLS_WEIGHT = 0.7
NEEDS_WEIGHT  = 0.3


@dataclass(frozen=True)
class JobEmbedding:
    job_id:          str
    skills_embedding: Embedding
    needs_embedding:  Embedding


@dataclass(frozen=True)
class RankedJob:
    job_id: str
    score:  float


def _dot(a: Embedding, b: Embedding) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: Embedding) -> float:
    return sqrt(sum(x * x for x in a))


def cosine_similarity(a: Embedding, b: Embedding) -> float:

    if len(a) != len(b):
        raise ValueError(f"Embedding length mismatch: {len(a)} != {len(b)}")
    denom = _norm(a) * _norm(b)
    if denom == 0.0:
        return 0.0
    return _dot(a, b) / denom


def rank_jobs_combined(
    user_skills_embedding: Embedding,
    user_needs_embedding:  Embedding,
    jobs: Iterable[JobEmbedding],
    *,
    top_k:     int   = 10,
    min_score: float = 0.45,
) -> List[RankedJob]:

    scored: List[RankedJob] = []

    for job in jobs:
        skills_score = cosine_similarity(user_skills_embedding, job.skills_embedding)
        needs_score  = cosine_similarity(user_needs_embedding,  job.needs_embedding)
        final_score  = (SKILLS_WEIGHT * skills_score) + (NEEDS_WEIGHT * needs_score)

        if final_score >= min_score:
            scored.append(RankedJob(job_id=job.job_id, score=round(final_score, 4)))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:max(0, top_k)]


def get_top_matches(
    *,
    user_skills_embedding:        Embedding,
    user_needs_embedding:         Embedding,
    candidate_jobs:               Iterable[JobEmbedding],
    rejected_job_embeddings:      Optional[Iterable[Tuple[Embedding, Embedding]]] = None,
    rejection_similarity_threshold: float = 0.85,
    top_k: int = 10,
) -> Tuple[List[RankedJob], List[RankedJob]]:

    candidate_jobs = list(candidate_jobs)

    ranked = rank_jobs_combined(
        user_skills_embedding,
        user_needs_embedding,
        candidate_jobs,
        top_k=top_k,
    )

    rejected_list = list(rejected_job_embeddings or [])
    if not rejected_list:
        return ranked, []

    job_embedding_by_id = {
        j.job_id: (j.skills_embedding, j.needs_embedding)
        for j in candidate_jobs
    }

    kept:     List[RankedJob] = []
    rejected: List[RankedJob] = []

    for r in ranked:
        embeddings = job_embedding_by_id.get(r.job_id)

        if embeddings is None:
            kept.append(r)
            continue

        job_skills_emb, job_needs_emb = embeddings

        too_close = any(
            cosine_similarity(job_skills_emb, rej_skills) >= rejection_similarity_threshold
            or
            cosine_similarity(job_needs_emb,  rej_needs)  >= rejection_similarity_threshold
            for rej_skills, rej_needs in rejected_list
        )

        if too_close:
            rejected.append(r)
        else:
            kept.append(r)

    return kept, rejected