from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse
from typing import Any

logger = logging.getLogger(__name__)

_HIMALAYAS_SEARCH_URL = "https://himalayas.app/jobs/api/search"
_ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


def _fetch_url(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read())


def _fetch_himalayas(skills: list[str], limit: int = 20) -> list[dict]:
    query = "+".join(skills[:3])
    url = f"{_HIMALAYAS_SEARCH_URL}?q={urllib.parse.quote(query)}&limit={limit}"
    try:
        data = _fetch_url(url)
        jobs = []
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
        logger.info("Fetched %d jobs from Himalayas.", len(jobs))
        return jobs
    except Exception as exc:
        logger.error("Himalayas fetch failed: %s", exc)
        return []


def _fetch_arbeitnow(skills: list[str], page: int = 1) -> list[dict]:
    url = f"{_ARBEITNOW_URL}?page={page}"
    try:
        data = _fetch_url(url)
        skill_keywords = [s.lower() for s in skills]
        jobs = []
        for job in data.get('data', []):
            title = job.get('title', '').lower()
            description = job.get('description', '').lower()
            tags = [t.lower() for t in job.get('tags', [])]
            combined = title + description + " ".join(tags)
            if not any(skill in combined for skill in skill_keywords):
                continue
            jobs.append({
                'title':          job.get('title', ''),
                'company':        job.get('company_name', ''),
                'location':       job.get('location', ''),
                'job_type':       ", ".join(job.get('job_types', [])) or 'Full Time',
                'external_url':   job.get('url', ''),
                'description':    job.get('description', ''),
                'required_skills': job.get('tags', []),
                'is_remote':      job.get('remote', False),
                'source':         'arbeitnow',
            })
        logger.info("Fetched %d matching jobs from Arbeitnow.", len(jobs))
        return jobs
    except Exception as exc:
        logger.error("Arbeitnow fetch failed: %s", exc)
        return []


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
        all_jobs.extend(_fetch_himalayas(skills, limit=20))

    if include_onsite:
        all_jobs.extend(_fetch_arbeitnow(skills, page=1))

    scored = [job for job in all_jobs if _score_neurodivergent_friendly(job)]
    seen_urls: set[str] = set()
    unique_jobs: list[dict] = []
    for job in scored:
        url = job.get('external_url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)

    logger.info(
        "fetch_jobs complete. Total: %d, after ND filtering and dedup: %d.",
        len(all_jobs), len(unique_jobs),
    )
    return unique_jobs


def fetch_and_save_jobs(
    skills: list[str],
    include_remote: bool = True,
    include_onsite: bool = True,
) -> int:
    from jobs.models import Job, Company

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
            _, created = Job.objects.get_or_create(
                external_url=job_data['external_url'],
                defaults={
                    'company':              company,
                    'title':                job_data.get('title', ''),
                    'location':             str(job_data.get('location') or 'Remote'),
                    'job_type':             job_data.get('job_type', 'Full Time')[:20],
                    'original_description': job_data.get('description', ''),
                    'required_skills':      job_data.get('required_skills', []),
                    'is_translated':        False,
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