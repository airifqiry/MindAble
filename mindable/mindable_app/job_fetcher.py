from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.request
import urllib.parse
import urllib.error
from itertools import islice
from typing import Any

logger = logging.getLogger(__name__)


def _ssl_context_for_https() -> ssl.SSLContext:
    """
    Use certifi's CA bundle so HTTPS works on macOS / Windows where the
    default Python install may not trust remote APIs (fixes CERTIFICATE_VERIFY_FAILED).
    Set MINDABLE_INSECURE_SSL=1 only for local debugging (disables verification).
    """
    if os.environ.get("MINDABLE_INSECURE_SSL", "").lower() in ("1", "true", "yes"):
        logger.warning(
            "MINDABLE_INSECURE_SSL is set — HTTPS certificate verification is disabled (dev only)."
        )
        return ssl._create_unverified_context()
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()

_HIMALAYAS_SEARCH_URL = "https://himalayas.app/jobs/api/search"
_ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
_REMOTEOK_URL = "https://remoteok.com/api"
_REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


def _build_search_queries(skills: list[str]) -> list[str]:
    cleaned = [s.strip().lower() for s in skills if s and s.strip()]
    cleaned = list(dict.fromkeys(cleaned))
    if not cleaned:
        return []

    queries: list[str] = []
    # Prioritize specific terms first.
    for term in cleaned[:8]:
        queries.append(term)

    # Add small combos to broaden retrieval without overfitting.
    it = iter(cleaned[:6])
    while True:
        pair = list(islice(it, 2))
        if len(pair) < 2:
            break
        queries.append(" ".join(pair))

    # Add a couple of generic software queries so we fetch a larger candidate pool,
    # then ranking + embeddings can personalize results reliably.
    queries.extend([
        "software engineer",
        "software developer",
        "web developer",
        "application developer",
    ])

    return list(dict.fromkeys(queries))[:20]


def _fetch_url(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; Mindable/1.0)"},
    )
    ctx = _ssl_context_for_https()
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            return json.loads(response.read())
    except urllib.error.URLError:
        # Some environments inject an HTTPS proxy that blocks these APIs.
        # Retry once without proxies; keep same SSL context (certifi / macOS fix).
        https_handler = urllib.request.HTTPSHandler(context=ctx)
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            https_handler,
        )
        with opener.open(req, timeout=15) as response:
            return json.loads(response.read())


def _fetch_himalayas(skills: list[str], limit: int = 20) -> list[dict]:
    jobs: list[dict] = []
    queries = _build_search_queries(skills) or ["remote developer"]
    for query in queries:
        url = f"{_HIMALAYAS_SEARCH_URL}?q={urllib.parse.quote(query)}&limit={limit}"
        try:
            data = _fetch_url(url)
            for job in data.get('jobs', []):
                jobs.append({
                    'title':       job.get('title', ''),
                    'company':     job.get('company', {}).get('name', ''),
                    'location':    job.get('locationRestrictions') or 'Remote',
                    'job_type':    job.get('employmentType', 'Full Time'),
                    'external_url': job.get('applicationUrl', ''),
                    'description': job.get('description', ''),
                    'required_skills': job.get('categories', []),
                    'is_remote':   True,
                    'source':      'himalayas',
                })
        except Exception as exc:
            logger.error("Himalayas fetch failed for query '%s': %s", query, exc)
            continue
    logger.info("Fetched %d jobs from Himalayas across %d queries.", len(jobs), len(queries))
    return jobs


def _fetch_arbeitnow(skills: list[str], page: int = 1) -> list[dict]:
    url = f"{_ARBEITNOW_URL}?page={page}"
    try:
        data = _fetch_url(url)
        skill_keywords = [s.lower() for s in skills]
        jobs = []
        fallback_jobs = []

        def _to_job_payload(job: dict[str, Any]) -> dict[str, Any]:
            return {
                'title':          job.get('title', ''),
                'company':        job.get('company_name', ''),
                'location':       job.get('location', ''),
                'job_type':       ", ".join(job.get('job_types', [])) or 'Full Time',
                'external_url':   job.get('url', ''),
                'description':    job.get('description', ''),
                'required_skills': job.get('tags', []),
                'is_remote':      job.get('remote', False),
                'source':         'arbeitnow',
            }

        for job in data.get('data', []):
            title = job.get('title', '').lower()
            description = job.get('description', '').lower()
            tags = [t.lower() for t in job.get('tags', [])]
            combined = title + description + " ".join(tags)
            payload = _to_job_payload(job)
            fallback_jobs.append(payload)
            if skill_keywords and not any(skill in combined for skill in skill_keywords):
                continue
            jobs.append(payload)

        # Graceful fallback: if keyword matching found nothing, still return fresh jobs.
        if not jobs and fallback_jobs:
            jobs = fallback_jobs[:20]
        logger.info("Fetched %d matching jobs from Arbeitnow.", len(jobs))
        return jobs
    except Exception as exc:
        logger.error("Arbeitnow fetch failed: %s", exc)
        return []


def _fetch_remoteok(skills: list[str], limit: int = 30) -> list[dict]:
    try:
        data = _fetch_url(_REMOTEOK_URL)
        if not isinstance(data, list):
            return []

        skill_keywords = [s.lower() for s in skills]
        jobs: list[dict] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            if not item.get("id"):
                # First object in this API is metadata.
                continue

            title = (item.get("position") or item.get("role") or "").strip()
            company = (item.get("company") or "").strip()
            description = (item.get("description") or "").strip()
            tags = item.get("tags") or []
            combined = " ".join([title.lower(), description.lower(), " ".join(str(t).lower() for t in tags)])
            if skill_keywords and not any(skill in combined for skill in skill_keywords):
                continue

            external_url = item.get("apply_url") or item.get("url") or ""
            if not external_url:
                continue

            jobs.append({
                "title": title,
                "company": company,
                "location": item.get("location") or "Remote",
                "job_type": "remote",
                "external_url": external_url,
                "description": description,
                "required_skills": tags if isinstance(tags, list) else [],
                "is_remote": True,
                "source": "remoteok",
            })
            if len(jobs) >= limit:
                break
        logger.info("Fetched %d matching jobs from RemoteOK.", len(jobs))
        return jobs
    except Exception as exc:
        logger.error("RemoteOK fetch failed: %s", exc)
        return []


def _fetch_remotive(skills: list[str], limit: int = 40) -> list[dict]:
    queries = _build_search_queries(skills) or ["developer"]
    jobs: list[dict] = []
    for query in queries:
        url = f"{_REMOTIVE_URL}?search={urllib.parse.quote(query)}"
        try:
            data = _fetch_url(url)
            for job in data.get("jobs", []):
                title = job.get("title", "")
                company = job.get("company_name", "")
                description = job.get("description", "")
                tags = job.get("tags") or []
                url_apply = job.get("url", "")
                if not url_apply:
                    continue
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": job.get("candidate_required_location") or "Remote",
                    "job_type": "remote",
                    "external_url": url_apply,
                    "description": description,
                    "required_skills": tags if isinstance(tags, list) else [],
                    "is_remote": True,
                    "source": "remotive",
                })
                if len(jobs) >= limit:
                    break
            if len(jobs) >= limit:
                break
        except Exception as exc:
            logger.error("Remotive fetch failed for query '%s': %s", query, exc)
            continue
    logger.info("Fetched %d jobs from Remotive.", len(jobs))
    return jobs


def _score_neurodivergent_friendly(job: dict) -> bool:
    friendly_signals = [
        'async', 'asynchronous', 'flexible hours', 'remote-first',
        'written communication', 'no open plan', 'neurodiverg',
        'psychological safety', 'work from home', 'flexible schedule',
        'autonomous', 'self-directed', 'no meetings', 'documentation',
    ]
    unfriendly_signals = [
        'fast-paced', 'fast paced', 'high pressure', 'always on call',
        'open plan', 'must multitask', 'on-site required', 'high stress',
    ]
    text = (job.get('description', '') + job.get('title', '')).lower()
    if any(signal in text for signal in unfriendly_signals):
        return False
    if job.get('is_remote'):
        return True
    if any(signal in text for signal in friendly_signals):
        return True
    return False


def fetch_jobs(
    skills: list[str],
    include_remote: bool = True,
    include_onsite: bool = True,
) -> list[dict]:
    if not skills:
        raise ValueError("skills must be a non-empty list.")

    all_jobs: list[dict] = []

    if include_remote:
        all_jobs.extend(_fetch_himalayas(skills, limit=30))
        all_jobs.extend(_fetch_remoteok(skills, limit=30))
        all_jobs.extend(_fetch_remotive(skills, limit=40))

    if include_onsite:
        # Pull a few pages to avoid tiny feeds after dismissals.
        for page in (1, 2, 3):
            all_jobs.extend(_fetch_arbeitnow(skills, page=page))

    seen_urls: set[str] = set()
    unique_jobs: list[dict] = []
    # IMPORTANT: do not hard-filter by neurodivergence friendliness at fetch-time.
    # We keep high recall here, and apply neurodivergence preferences during ranking
    # so we don't accidentally drop good semantic matches.
    for job in all_jobs:
        url = job.get('external_url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)

    logger.info(
        "fetch_jobs complete. Total: %d, after dedup: %d.",
        len(all_jobs), len(unique_jobs),
    )
    return unique_jobs


def fetch_and_save_jobs(
    skills: list[str],
    include_remote: bool = True,
    include_onsite: bool = True,
) -> int:
    from jobs.models import Job, Company
    from mindable.mindable_app.embedding_service import build_job_embeddings, get_embedding_version

    def _normalize_job_type(raw_type: str) -> str:
        value = (raw_type or "").strip().lower().replace("_", "-")
        if "part" in value:
            return "part-time"
        if "hybrid" in value:
            return "hybrid"
        if "remote" in value:
            return "remote"
        return "full-time"

    jobs_data = fetch_jobs(
        skills=skills,
        include_remote=include_remote,
        include_onsite=include_onsite,
    )

    saved = 0
    for job_data in jobs_data:
        if not job_data.get('external_url'):
            continue
        try:
            company, _ = Company.objects.get_or_create(
                name=job_data.get('company') or 'Unknown Company'
            )
            job_skills_text = " ".join(
                [job_data.get('title', ''), " ".join(job_data.get('required_skills', []) or [])]
            ).strip()
            job_needs_text = " ".join(
                [job_data.get('location', ''), job_data.get('job_type', ''), job_data.get('description', '')]
            ).strip()
            skills_embedding = None
            needs_embedding = None
            emb_ver = ""
            if job_skills_text and job_needs_text:
                try:
                    skills_embedding, needs_embedding = build_job_embeddings(job_skills_text, job_needs_text)
                    emb_ver = get_embedding_version()
                except Exception as exc:
                    logger.warning("Job embedding build failed for %s: %s", job_data.get('title', ''), exc)

            _, created = Job.objects.get_or_create(
                external_url=job_data['external_url'],
                defaults={
                    'company':              company,
                    'title':                job_data.get('title', ''),
                    'location':             str(job_data.get('location') or 'Remote'),
                    'job_type':             _normalize_job_type(job_data.get('job_type', '')),
                    'original_description': job_data.get('description', ''),
                    'required_skills':      job_data.get('required_skills', []),
                    'skills_embedding':     skills_embedding,
                    'needs_embedding':      needs_embedding,
                    'embedding_version':    emb_ver,
                    # Fallback so jobs appear in the feed even before AI translation runs.
                    'translated_title':     job_data.get('title', ''),
                    'is_translated':        True,
                }
            )
            if created:
                saved += 1
                logger.info("Saved: %s at %s", job_data.get('title'), job_data.get('company'))
        except Exception as exc:
            logger.error("Failed to save job %s: %s", job_data.get('title'), exc)
            continue

    logger.info("fetch_and_save_jobs done. Saved %d new jobs.", saved)
    return saved