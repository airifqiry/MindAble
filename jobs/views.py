from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Case, When, IntegerField, QuerySet
from django.utils import timezone
from datetime import timedelta
from math import ceil
import hashlib
import logging
import re

from .models import Job, UserJobInteraction
from .serializers import JobListSerializer, JobDetailSerializer
from users.models import WorkplaceProfile
from mindable.mindable_app.job_fetcher import fetch_and_save_jobs
from mindable.mindable_app.matching_logic import cosine_similarity
from mindable.mindable_app.skill_classifier import split_technical_general

logger = logging.getLogger(__name__)

# Suitability tiers (for labeling only — not hard API cutoffs).
_STRONG_TIER_MIN = 0.55
_MODERATE_TIER_MIN = 0.43
# Max share of score that penalties can remove (prevents total collapse).
_MAX_TOTAL_PENALTY = 0.48
# Secondary floor used only inside progressive fallback (never a single global gate).
_FALLBACK_RELAXED_FLOOR = 0.25


def _natural_job_key(job: Job) -> str:
    """Stable key for deduplication across duplicate DB rows (same listing, different ids)."""
    company_name = ""
    try:
        company_name = (job.company.name or "").strip().lower()
    except Exception:
        pass
    parts = [
        (job.title or "").strip().lower(),
        company_name,
        (job.location or "").strip().lower(),
        (job.external_url or "").strip().lower(),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe_jobs_keep_best_score(jobs: list[Job], score_map: dict[int, float]) -> tuple[list[Job], int]:
    """
    One row per natural key; keep the instance with the highest score.
    Returns (deduped list sorted by score desc, number of rows dropped).
    """
    before = len(jobs)
    best: dict[str, Job] = {}
    best_score: dict[str, float] = {}
    for job in jobs:
        key = _natural_job_key(job)
        sc = float(score_map.get(job.id, 0.0))
        if key not in best or sc > best_score[key]:
            best[key] = job
            best_score[key] = sc
    out = list(best.values())
    out.sort(key=lambda j: best_score[_natural_job_key(j)], reverse=True)
    return out, before - len(out)


def _filter_by_min_score(
    jobs: list[Job],
    score_map: dict[int, float],
    min_score: float,
) -> list[Job]:
    """Keep jobs whose score is at or above min_score; skip rows without scores."""
    kept: list[Job] = []
    for job in jobs:
        if job.id not in score_map:
            continue
        if float(score_map[job.id]) >= min_score:
            kept.append(job)
    return kept


def _percentile_threshold(scores: list[float], keep_top_fraction: float) -> float:
    """
    Minimum score needed to land in the top keep_top_fraction of jobs (e.g. 0.30 => top 30%).
    Uses the smallest score among the top ceil(fraction * n) jobs.
    """
    if not scores:
        return 0.0
    if len(scores) == 1:
        return float(scores[0])
    sorted_asc = sorted(scores)
    n = len(sorted_asc)
    k = max(1, int(ceil(keep_top_fraction * n)))
    idx = max(0, n - k)
    return float(sorted_asc[idx])


def _label_match_quality(
    jobs: list[Job],
    score_map: dict[int, float],
    *,
    smax: float,
    smin: float,
    stage: str,
) -> None:
    """Assign match_quality: high / standard / exploratory (never pretend weak matches are strong)."""
    spread = max(1e-6, smax - smin)
    for j in jobs:
        sc = float(score_map.get(j.id, 0.0))
        if sc >= smax - 0.08 * spread:
            q = "high"
        elif stage in ("relaxed", "exploratory") or sc <= smin + 0.38 * spread:
            q = "exploratory"
        else:
            q = "standard"
        setattr(j, "_match_quality", q)


def _finalize_ranked_feed(
    ranked: list | QuerySet,
    score_map: dict[int, float],
) -> tuple[list[Job], dict[int, float], dict]:
    """
    Dedupe, then progressive filtering with guaranteed non-empty output when candidates exist.
    Stage 1: percentile-based (top ~30% by score) with a floor for tight distributions.
    Stage 2: relaxed floor (e.g. 0.25).
    Stage 3: top-N by score only (exploratory quality label).
    """
    meta: dict = {
        "fallback_stage": 0,
        "effective_threshold": None,
        "score_min": None,
        "score_max": None,
        "score_avg": None,
    }
    ranked_list = list(ranked) if not isinstance(ranked, list) else ranked
    before = len(ranked_list)
    if not ranked_list:
        logger.info("JOBS_FEED|before=0|after_dedupe=0|after_threshold=0")
        return [], score_map, meta

    deduped, dupes_dropped = _dedupe_jobs_keep_best_score(ranked_list, score_map)
    scored_ids = [j.id for j in deduped if j.id in score_map]
    scores = [float(score_map[jid]) for jid in scored_ids]

    if not scores:
        logger.warning("JOBS_FEED|no_scores_after_dedupe|returning_top_n_unscored")
        return deduped[:20], score_map, meta

    smin, smax, savg = min(scores), max(scores), sum(scores) / len(scores)
    meta["score_min"], meta["score_max"], meta["score_avg"] = smin, smax, savg
    logger.info(
        "JOBS_FEED|scores|min=%.3f|max=%.3f|avg=%.3f|n=%d|before_dedupe=%d|after_dedupe=%d|dupes=%d",
        smin,
        smax,
        savg,
        len(scores),
        before,
        len(deduped),
        dupes_dropped,
    )

    # Primary: dynamic percentile (top ~30% of jobs) with a floor so tight spreads still return rows.
    p_top = _percentile_threshold(scores, keep_top_fraction=0.30)
    spread = smax - smin
    if spread < 0.06:
        primary_threshold = max(0.12, smin - 1e-6)
    else:
        primary_threshold = max(0.12, min(p_top, smax - 0.02 * spread))

    primary_threshold = min(primary_threshold, smax)
    meta["effective_threshold"] = primary_threshold
    filtered = _filter_by_min_score(deduped, score_map, primary_threshold)

    if filtered:
        meta["fallback_stage"] = 1
        logger.info(
            "JOBS_FEED|filtered|kept=%d|threshold=%.3f|stage=percentile_top30",
            len(filtered),
            primary_threshold,
        )
        _label_match_quality(filtered, score_map, smax=smax, smin=smin, stage="primary")
        for j in filtered[:5]:
            logger.info(
                "TOP5|title=%s|score=%.3f|tech=%s|general=%s|penalties=%s|tier=%s",
                j.title,
                float(score_map.get(j.id, 0.0)),
                getattr(j, "_matched_technical_skills", []),
                getattr(j, "_matched_general_skills", []),
                getattr(j, "_penalties_applied", []),
                getattr(j, "_match_tier", ""),
            )
        return filtered, score_map, meta

    # Stage 2: lower threshold (never rely on one static 0.43).
    relaxed = max(0.10, min(_FALLBACK_RELAXED_FLOOR, smin + 0.4 * spread))
    meta["effective_threshold"] = relaxed
    filtered = _filter_by_min_score(deduped, score_map, relaxed)
    logger.warning(
        "JOBS_FEED|fallback_step2|threshold=%.3f|kept=%d|after_percentile_empty",
        relaxed,
        len(filtered),
    )

    if filtered:
        meta["fallback_stage"] = 2
        _label_match_quality(filtered, score_map, smax=smax, smin=smin, stage="relaxed")
        for j in filtered[:5]:
            logger.info(
                "TOP5|title=%s|score=%.3f|tech=%s|general=%s|penalties=%s|tier=%s",
                j.title,
                float(score_map.get(j.id, 0.0)),
                getattr(j, "_matched_technical_skills", []),
                getattr(j, "_matched_general_skills", []),
                getattr(j, "_penalties_applied", []),
                getattr(j, "_match_tier", ""),
            )
        return filtered, score_map, meta

    # Stage 3: top N by score — always non-empty if deduped non-empty.
    top_n = min(20, len(deduped))
    ordered = sorted(
        deduped,
        key=lambda j: float(score_map.get(j.id, 0.0)),
        reverse=True,
    )[:top_n]
    meta["fallback_stage"] = 3
    meta["effective_threshold"] = None
    logger.warning(
        "JOBS_FEED|fallback_triggered|top_n=%d|stage=unfiltered_ranked|quality=exploratory",
        len(ordered),
    )
    for j in ordered:
        setattr(j, "_match_quality", "exploratory")
        setattr(j, "_fallback_used", True)
    return ordered, score_map, meta


def _suitability_tier(score: float) -> str:
    if score >= _STRONG_TIER_MIN:
        return "strong"
    if score >= _MODERATE_TIER_MIN:
        return "moderate"
    return "weak"


class JobDiscoveryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


def _extract_skills(user_skills_raw: str) -> list[str]:
    # Supports both comma-separated skills and free-text profile summaries.
    if not user_skills_raw:
        return []

    chunks = [s.strip() for s in re.split(r"[,;\n]+", str(user_skills_raw)) if s.strip()]
    if len(chunks) > 1:
        return chunks

    text = chunks[0].lower() if chunks else ""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-\+#]{1,}", text)
    stopwords = {
        "and", "the", "that", "this", "with", "from", "have", "know", "into",
        "highly", "really", "very", "area", "areas", "about", "behind", "making",
        "im", "i", "m", "am", "in", "of", "to", "for", "on", "is", "are",
        "patient", "hardworking",
    }
    keywords: list[str] = []
    seen: set[str] = set()
    for w in words:
        if len(w) < 3 or w in stopwords:
            continue
        if w not in seen:
            seen.add(w)
            keywords.append(w)

    # Add high-signal multi-word terms when present.
    if "machine" in seen and "learning" in seen:
        keywords.insert(0, "machine learning")
    if "artificial" in seen and "intelligence" in seen:
        keywords.insert(0, "artificial intelligence")
    if "ai" in seen:
        keywords.insert(0, "ai")

    return keywords[:10]


def _apply_embedding_ranking(
    qs,
    passport: WorkplaceProfile,
    profile: dict | None = None,
):
    user_skills_embedding = passport.skills_embedding or []
    user_needs_embedding = passport.needs_embedding or []
    if not user_skills_embedding and not user_needs_embedding:
        return qs.order_by("-created_at"), {}, {}

    candidate_jobs = list(qs)
    if not candidate_jobs:
        return qs.order_by("-created_at"), {}, {}

    if profile is None:
        profile = _get_profile_structure(passport)
    tech_mode = profile["tech_mode"]
    mode_label = "technical-skill-driven" if tech_mode else "general-skill-driven"
    logger.info(
        "PROFILE|user=%s|mode=%s|technical_skills=%s|general_skills=%s|limitations=%s|disadvantages=%s",
        passport.user_id,
        mode_label,
        profile["technical_skills"][:12],
        profile["general_skills"][:12],
        profile["limitations"][:10],
        profile["behavioral_constraints"][:10],
    )

    scored: list[tuple[int, float]] = []
    explanation_map: dict[int, str] = {}
    hits_map: dict[int, dict[str, int]] = {}
    details_map: dict[int, dict[str, list[str] | str]] = {}
    excluded_ids: set[int] = set()

    for job in candidate_jobs:
        try:
            raw_skills_score = 0.0
            raw_needs_score = 0.0
            if user_skills_embedding and getattr(job, "skills_embedding", None):
                try:
                    raw_skills_score = cosine_similarity(user_skills_embedding, job.skills_embedding)
                except Exception:
                    raw_skills_score = 0.0
            if user_needs_embedding and getattr(job, "needs_embedding", None):
                try:
                    raw_needs_score = cosine_similarity(user_needs_embedding, job.needs_embedding)
                except Exception:
                    raw_needs_score = 0.0

            e_skill = float((raw_skills_score + 1.0) / 2.0)
            e_needs = float((raw_needs_score + 1.0) / 2.0)

            text = _job_text(job)
            text_tokens = set(_extract_skills(text))
            title_text = (job.title or "").lower()
            title_tokens = set(_extract_skills(title_text))

            matched_prefs = [p for p in profile["work_preferences"] if _term_matches_text(p, text, text_tokens)][:4]
            matched_interests = [i for i in profile["interests"] if _term_matches_text(i, text, text_tokens)][:4]
            pref_hits = len(matched_prefs)
            pref_fit = min(1.0, pref_hits / 4.0)
            interest_fit = min(1.0, len(matched_interests) / 3.0)

            avoid_hits = sum(
                1
                for term in profile["limitations"] + profile["unsuitable_environments"]
                if _term_matches_text(term, text, text_tokens)
            )

            tech_pool = profile["technical_skills"]
            gen_pool = profile["general_skills"]
            strength_pool = profile["strengths"]

            matched_technical = [t for t in tech_pool if _term_matches_text(t, text, text_tokens)][:8]
            title_tech_hits = sum(1 for t in tech_pool if _term_matches_text(t, title_text, title_tokens))
            matched_general = [t for t in gen_pool if _term_matches_text(t, text, text_tokens)][:8]
            matched_strength = [t for t in strength_pool if _term_matches_text(t, text, text_tokens)][:6]

            # Combined non-tech overlap for general mode / supporting signals
            matched_skills = [s for s in profile["skills"] if _term_matches_text(s, text, text_tokens)][:8]
            keyword_hits = len(matched_skills)
            title_hits = sum(1 for term in profile["skills"] if _term_matches_text(term, title_text, title_tokens))

            conflicts, penalties_applied, constraint_penalty, hard_block = _constraint_conflicts(profile, job)
            if hard_block:
                excluded_ids.add(job.id)
                continue

            environment_penalty = (
                0.10 if any(k in text for k in ["open office", "high pressure", "on-site required"]) else 0.0
            )
            avoid_environment_penalty = min(0.12, 0.04 * min(avoid_hits, 4))

            if tech_mode:
                # MODE A: technical alignment first, then general/support, then preferences — penalties last.
                n_tech = max(len(tech_pool), 1)
                tech_ratio = min(1.0, len(matched_technical) / n_tech)
                title_tech_ratio = min(1.0, title_tech_hits / max(2, min(4, (len(tech_pool) + 1) // 2)))
                n_gen = max(len(gen_pool), 1)
                general_support = min(1.0, (len(matched_general) + len(matched_strength)) / max(n_gen, 3))

                # Never exclude the row: demote weak technical fit (prevents empty feeds).
                tech_weak = not matched_technical and title_tech_hits == 0 and e_skill < 0.44

                positive = (
                    0.42 * e_skill
                    + 0.28 * tech_ratio
                    + 0.12 * title_tech_ratio
                    + 0.10 * general_support
                    + 0.05 * e_needs
                    + 0.03 * pref_fit
                )
                if tech_weak:
                    positive *= 0.38
                elif tech_ratio < 0.12 and title_tech_ratio < 0.12:
                    positive *= 0.62
            else:
                # MODE B: general skills, strengths, embedding — no technical primacy.
                n_all = max(len(gen_pool) + len(strength_pool), 1)
                general_lex = min(1.0, (len(matched_general) + len(matched_strength)) / n_all)
                n_skills_profile = max(len(profile["skills"]), 1)
                lexical_skill_fit = min(1.0, keyword_hits / min(8, n_skills_profile))
                title_fit = min(1.0, title_hits / 4.0)

                signal_count = sum(
                    [
                        1 if keyword_hits else 0,
                        1 if title_hits else 0,
                        1 if pref_hits else 0,
                        1 if matched_interests else 0,
                        1 if e_skill >= 0.58 else 0,
                    ]
                )
                weak_guard = 0.52 if signal_count < 2 else 1.0

                positive = (
                    0.32 * e_skill
                    + 0.22 * e_needs
                    + 0.20 * general_lex
                    + 0.12 * lexical_skill_fit
                    + 0.08 * title_fit
                    + 0.06 * pref_fit
                ) * weak_guard + 0.06 * interest_fit

            structured_penalty = min(0.42, float(constraint_penalty) * 0.52)
            total_penalty = structured_penalty + environment_penalty + avoid_environment_penalty
            total_penalty = min(_MAX_TOTAL_PENALTY, total_penalty)

            raw = positive - total_penalty
            final_score = max(0.0, min(1.0, raw))
            tier = _suitability_tier(final_score)

            scored.append((job.id, final_score))
            hits_map[job.id] = {
                "_match_keyword_hits": len(matched_technical) if tech_mode else keyword_hits,
                "_match_title_hits": title_tech_hits if tech_mode else title_hits,
                "_match_pref_hits": pref_hits,
                "_match_avoid_hits": avoid_hits,
            }

            parts: list[str] = [f"Matching mode: {mode_label}."]
            if tech_mode:
                if matched_technical:
                    parts.append(f"Technical overlap: {', '.join(matched_technical[:4])}.")
                elif title_tech_hits:
                    parts.append(f"Technical signals in title ({title_tech_hits}) plus embedding alignment.")
                if matched_general or matched_strength:
                    parts.append(
                        "Supporting overlap: "
                        + ", ".join((matched_general + matched_strength)[:4])
                        + "."
                    )
            else:
                overlap = matched_general + matched_strength or matched_skills
                if overlap:
                    parts.append(f"Profile overlap: {', '.join(overlap[:4])}.")
            if matched_prefs:
                parts.append(f"Preferences: {', '.join(matched_prefs[:2])}.")
            if conflicts or total_penalty > 0.02:
                neg_bits = []
                if conflicts:
                    neg_bits.append(f"conflicts: {', '.join(conflicts[:4])}")
                if structured_penalty > 0.02:
                    neg_bits.append(f"structured penalty ({structured_penalty:.2f})")
                if environment_penalty > 0.02:
                    neg_bits.append("environment cue penalty")
                if avoid_environment_penalty > 0.02:
                    neg_bits.append("avoid-term overlap")
                parts.append(
                    "Penalties (capped): total "
                    + f"{total_penalty:.2f} — "
                    + "; ".join(neg_bits)
                    + "."
                )
            parts.append(f"Suitability: {tier} (score {final_score:.2f}).")
            final_reason = " ".join(parts)

            explanation_map[job.id] = final_reason
            details_map[job.id] = {
                "matched_skills": matched_skills,
                "matched_technical_skills": matched_technical,
                "matched_general_skills": matched_general + matched_strength,
                "matched_strengths": matched_strength,
                "detected_conflicts": conflicts,
                "penalties_applied": penalties_applied,
                "penalty_total": round(total_penalty, 4),
                "structured_penalty": round(structured_penalty, 4),
                "final_reason": final_reason,
                "match_tier": tier,
                "matching_mode": mode_label,
            }
        except Exception:
            logger.exception("REC|scoring_failed|job_id=%s", getattr(job, "id", None))
            continue

    if not scored:
        qs_ex = qs.exclude(id__in=excluded_ids) if excluded_ids else qs
        return qs_ex.order_by("-created_at"), {}, {}

    scored.sort(key=lambda item: item[1], reverse=True)
    ranked_ids = [job_id for job_id, _ in scored]
    score_map = {job_id: score for job_id, score in scored}

    unranked_qs = qs.exclude(id__in=ranked_ids).exclude(id__in=excluded_ids).order_by("-created_at")
    ordered_ranked_qs = qs.filter(id__in=ranked_ids).order_by(
        Case(*[When(id=job_id, then=pos) for pos, job_id in enumerate(ranked_ids)], output_field=IntegerField())
    )

    ranked_instances = list(ordered_ranked_qs) + list(unranked_qs)
    for j in ranked_instances:
        if j.id in explanation_map:
            setattr(j, "_match_explanation", explanation_map[j.id])
        if j.id in hits_map:
            for k, v in hits_map[j.id].items():
                setattr(j, k, v)
        details = details_map.get(j.id, {})
        setattr(j, "_matched_skills", details.get("matched_skills", []))
        setattr(j, "_matched_technical_skills", details.get("matched_technical_skills", []))
        setattr(j, "_matched_general_skills", details.get("matched_general_skills", []))
        setattr(j, "_matched_strengths", details.get("matched_strengths", []))
        setattr(j, "_detected_conflicts", details.get("detected_conflicts", []))
        setattr(j, "_penalties_applied", details.get("penalties_applied", []))
        setattr(j, "_penalty_total", details.get("penalty_total"))
        setattr(j, "_structured_penalty", details.get("structured_penalty"))
        setattr(j, "_final_reason", details.get("final_reason", getattr(j, "_match_explanation", "")))
        setattr(j, "_match_tier", details.get("match_tier", _suitability_tier(float(score_map.get(j.id, 0.0)))))
        setattr(j, "_matching_mode", details.get("matching_mode", ""))

    for j in ranked_instances[:50]:
        logger.info(
            "REC|job=%s|score=%.3f|tech=%s|general=%s|conflicts=%s|penalties=%s|tier=%s",
            j.title,
            score_map.get(j.id, 0.0),
            getattr(j, "_matched_technical_skills", []),
            getattr(j, "_matched_general_skills", []),
            getattr(j, "_detected_conflicts", []),
            getattr(j, "_penalties_applied", []),
            getattr(j, "_match_tier", ""),
        )
    return ranked_instances, score_map, explanation_map


def _ensure_user_embeddings(passport: WorkplaceProfile) -> WorkplaceProfile:
    current_enablers = passport.success_enablers if isinstance(passport.success_enablers, dict) else {}
    has_analyzed = isinstance(current_enablers.get("analyzed_profile"), dict)
    has_embeddings = bool(passport.skills_embedding and passport.needs_embedding)
    if has_embeddings and has_analyzed:
        return passport

    from mindable.mindable_app.profile_analyzer import analyze_profile
    from mindable.mindable_app.embedding_service import build_user_embeddings

    profile_text = " ".join(filter(None, [
        passport.skills or "",
        passport.experience_summary or "",
        passport.mental_disability or "",
        str(passport.success_enablers or {}),
    ])).strip()
    if not profile_text:
        return passport

    analyzed = analyze_profile(profile_text)
    if not has_embeddings:
        skills_emb, needs_emb = build_user_embeddings(analyzed)
        passport.skills_embedding = skills_emb
        passport.needs_embedding = needs_emb
    current_enablers["analyzed_profile"] = analyzed
    passport.success_enablers = current_enablers
    passport.dealbreakers = analyzed.get("limitations") or passport.dealbreakers
    passport.save(update_fields=[
        "skills_embedding",
        "needs_embedding",
        "success_enablers",
        "dealbreakers",
        "last_updated",
    ])
    return passport


def _get_profile_signals(passport: WorkplaceProfile) -> tuple[list[str], list[str], list[str]]:
    enablers = passport.success_enablers if isinstance(passport.success_enablers, dict) else {}
    analyzed = enablers.get("analyzed_profile") if isinstance(enablers.get("analyzed_profile"), dict) else {}

    raw_skills = _extract_skills(passport.skills or "")
    analyzed_skills = analyzed.get("skills") or []
    skill_terms = [str(s).strip().lower() for s in (raw_skills + analyzed_skills) if str(s).strip()]

    preference_terms: list[str] = []
    for key in ("preferred_environment", "communication_style"):
        value = analyzed.get(key)
        if value:
            preference_terms.extend(_extract_skills(str(value)))
    for key in ("accommodations_needed", "work_values"):
        values = analyzed.get(key) or []
        preference_terms.extend(_extract_skills(" ".join(str(v) for v in values if v)))

    avoid_terms: list[str] = []
    limitations = analyzed.get("limitations") or []
    avoid_terms.extend(_extract_skills(" ".join(str(v) for v in limitations if v)))
    avoid_terms.extend(_extract_skills(" ".join(str(v) for v in (passport.dealbreakers or []) if v)))

    # Deduplicate but keep stable order.
    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            t = item.strip().lower()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out

    return _dedupe(skill_terms)[:25], _dedupe(preference_terms)[:25], _dedupe(avoid_terms)[:20]


def _get_profile_structure(passport: WorkplaceProfile) -> dict:
    enablers = passport.success_enablers if isinstance(passport.success_enablers, dict) else {}
    analyzed = enablers.get("analyzed_profile") if isinstance(enablers.get("analyzed_profile"), dict) else {}
    skills, preferences, avoid_terms = _get_profile_signals(passport)

    analyzed_tech = [
        str(x).strip().lower()
        for x in (analyzed.get("technical_skills") or [])
        if str(x).strip()
    ]
    analyzed_gen = [
        str(x).strip().lower()
        for x in (analyzed.get("general_skills") or [])
        if str(x).strip()
    ]
    tech_h, gen_h = split_technical_general(skills)
    technical_skills = list(dict.fromkeys(analyzed_tech + tech_h))[:40]
    general_skills = list(dict.fromkeys(analyzed_gen + gen_h))[:40]
    tech_mode = len(technical_skills) > 0

    exp_terms = [s for s in _extract_skills(str(passport.experience_summary or "")) if len(s) > 2][:20]
    strengths = list(dict.fromkeys([s for s in general_skills if len(s) > 2] + exp_terms))[:30]
    interests = [s for s in _extract_skills(str(passport.experience_summary or "")) if len(s) > 2][:20]
    limitations = [s for s in _extract_skills(" ".join(str(v) for v in (analyzed.get("limitations") or []))) if len(s) > 2]
    behavioral_constraints = limitations + [s for s in _extract_skills(passport.mental_disability or "") if len(s) > 2]
    unsuitable = [s for s in avoid_terms if len(s) > 2]
    hard_disqualifiers = [s for s in _extract_skills(" ".join(str(v) for v in (passport.dealbreakers or []))) if len(s) > 2]

    return {
        "skills": list(dict.fromkeys(skills)),
        "technical_skills": technical_skills,
        "general_skills": general_skills,
        "tech_mode": tech_mode,
        "strengths": strengths,
        "interests": list(dict.fromkeys(interests)),
        "work_preferences": list(dict.fromkeys(preferences)),
        "limitations": list(dict.fromkeys(limitations)),
        "behavioral_constraints": list(dict.fromkeys(behavioral_constraints)),
        "unsuitable_environments": list(dict.fromkeys(unsuitable)),
        "hard_disqualifiers": list(dict.fromkeys(hard_disqualifiers)),
    }


def _job_text(job: Job) -> str:
    return " ".join(
        [
            job.title or "",
            job.original_description or "",
            " ".join(job.required_skills or []),
            job.location or "",
            job.job_type or "",
        ]
    ).lower()


def _term_matches_text(term: str, text: str, text_tokens: set[str]) -> bool:
    t = (term or "").strip().lower()
    if not t:
        return False
    if t in text:
        return True
    parts = [p for p in _extract_skills(t) if p]
    if not parts:
        return False
    return all(p in text_tokens for p in parts)


def _constraint_conflicts(profile: dict, job: Job) -> tuple[list[str], list[str], float, bool]:
    text = _job_text(job)
    text_tokens = set(_extract_skills(text))
    conflicts: list[str] = []
    penalties: list[str] = []
    penalty_score = 0.0
    hard_block = False

    for term in profile["hard_disqualifiers"]:
        if _term_matches_text(term, text, text_tokens):
            hard_block = True
            conflicts.append(f"hard disqualifier: {term}")
            penalties.append(f"hard:{term}")
            penalty_score += 0.95

    contradiction_rules = [
        (["patience", "impatient"], ["teaching", "mentoring", "support", "customer", "stakeholder"], "requires sustained patience"),
        (["communication", "social", "anxiety"], ["client-facing", "sales", "customer", "public speaking", "presentation"], "high communication demand"),
        (["emotional", "regulation", "stress"], ["high pressure", "escalation", "conflict", "incident response"], "high emotional regulation demand"),
        (["sensory", "noise", "noisy"], ["open office", "busy environment", "retail", "warehouse"], "noisy/chaotic environment"),
        (["deadline", "time management"], ["fast-paced", "tight deadline", "urgent", "on call"], "high deadline pressure"),
        (["leadership", "manage"], ["lead", "manager", "supervise", "people management"], "leadership requirement"),
    ]
    user_constraints = set(profile["limitations"] + profile["behavioral_constraints"] + profile["unsuitable_environments"])
    soft_hits = 0
    for triggers, job_terms, label in contradiction_rules:
        trigger_hit = any(t in user_constraints for t in triggers)
        job_hit = any(jt in text for jt in job_terms)
        if trigger_hit and job_hit:
            soft_hits += 1
            conflicts.append(f"soft conflict: {label}")
            penalties.append(f"soft:{label}")

    # Cap soft rule stacking: diminishing returns (avoid total collapse).
    penalty_score += min(0.36, 0.14 * soft_hits + 0.08 * max(0, soft_hits - 2))

    lim_hits = 0
    for lim in profile["limitations"][:12]:
        if _term_matches_text(lim, text, text_tokens):
            lim_hits += 1
            conflicts.append(f"limitation overlap: {lim}")
            penalties.append(f"soft_limit:{lim}")
    penalty_score += min(0.22, 0.07 * min(lim_hits, 4))

    # Final cap before application layer (second cap also applied in scoring).
    penalty_score = min(0.92, penalty_score)
    return conflicts[:10], penalties[:12], penalty_score, hard_block


def _ensure_job_embeddings(qs) -> None:
    from mindable.mindable_app.embedding_service import build_job_embeddings

    # Backfill more jobs so personalization has enough candidates.
    missing = list(qs.filter(Q(skills_embedding__isnull=True) | Q(needs_embedding__isnull=True))[:150])
    for job in missing:
        skills_text = " ".join(
            [job.title or "", " ".join(job.required_skills or [])]
        ).strip()
        needs_text = " ".join(
            [job.location or "", job.job_type or "", job.original_description or ""]
        ).strip()
        if not skills_text or not needs_text:
            continue
        try:
            skills_emb, needs_emb = build_job_embeddings(skills_text, needs_text)
            job.skills_embedding = skills_emb
            job.needs_embedding = needs_emb
            job.save(update_fields=["skills_embedding", "needs_embedding"])
        except Exception as exc:
            logger.warning("Failed to backfill embeddings for job %s: %s", job.id, exc)


def _extract_bullets(block: str) -> list[str]:
    lines = []
    for line in (block or "").splitlines():
        t = line.strip()
        if t.startswith(("-", "*", "•")):
            item = t[1:].strip()
            if item:
                lines.append(item)
    return lines


def _build_toxicity_warnings(text: str) -> list[str]:
    lower = (text or "").lower()
    flags = []
    if "fast-paced" in lower or "fast paced" in lower:
        flags.append("Fast-paced environment mentioned.")
    if "high pressure" in lower or "high-pressure" in lower:
        flags.append("High-pressure language found.")
    if "must multitask" in lower or "multi-task" in lower:
        flags.append("Heavy multitasking requirement mentioned.")
    if "on-site" in lower or "onsite required" in lower:
        flags.append("On-site requirement mentioned.")
    return flags[:3]


def _rewrite_and_enrich_job(job: Job) -> str:
    from mindable.mindable_app.description_rewriter import rewrite_job_description
    rewritten = rewrite_job_description(job.original_description or "")
    lower = rewritten.lower()

    imp_start = lower.find("important things")
    day_start = lower.find("a typical day")

    important_block = ""
    typical_day_block = ""
    if imp_start >= 0 and day_start > imp_start:
        important_block = rewritten[imp_start:day_start]
        typical_day_block = rewritten[day_start:]
    elif day_start >= 0:
        typical_day_block = rewritten[day_start:]
    else:
        important_block = rewritten

    important = _extract_bullets(important_block)
    typical_day = _extract_bullets(typical_day_block)
    merged_tasks = (important + typical_day)[:8]
    if not merged_tasks:
        merged_tasks = _extract_bullets(rewritten)[:8]

    update_fields: list[str] = []
    if merged_tasks:
        job.translated_tasks = merged_tasks
        update_fields.append("translated_tasks")
    if not job.translated_title:
        job.translated_title = job.title
        update_fields.append("translated_title")
    if not job.toxicity_warnings:
        job.toxicity_warnings = _build_toxicity_warnings(job.original_description or "")
        update_fields.append("toxicity_warnings")
    if not job.is_translated:
        job.is_translated = True
        update_fields.append("is_translated")

    if update_fields:
        job.save(update_fields=update_fields)

    return rewritten


class JobDiscoveryHubView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JobListSerializer
    pagination_class = JobDiscoveryPagination
    _MIN_FEED_SIZE = 10
    _REFRESH_IF_MATCHES_LT = 25
    _STALE_AFTER_HOURS = 2

    def get_queryset(self):
        print("JOBS API HIT")
        user = self.request.user

        print("DEBUG: get_queryset called for user:", user)

        try:
            passport = WorkplaceProfile.objects.get(user=user)
            user_skills_raw = passport.skills
            try:
                passport = _ensure_user_embeddings(passport)
            except Exception as exc:
                logger.error("Failed to ensure user embeddings for %s: %s", user, exc)
        except WorkplaceProfile.DoesNotExist:
            print("DEBUG: No WorkplaceProfile found for user", user)
            return Job.objects.none()

        print("DEBUG skills raw:", user_skills_raw)

        if not user_skills_raw:
            print("DEBUG: skills field is empty")
            return Job.objects.none()

        skills = _extract_skills(user_skills_raw)
        skill_terms, preference_terms, _avoid_terms = _get_profile_signals(passport)
        fetch_terms = list(dict.fromkeys(skills + skill_terms + preference_terms))[:24]
        print("DEBUG skills list:", skills)
        print("DEBUG total jobs in DB:", Job.objects.count())
        print("DEBUG translated jobs:", Job.objects.filter(is_translated=True).count())

        
        # Decide whether we should refresh the job pool using the broader
        # profile-derived fetch terms (not only raw extracted keywords).
        user_has_matching_jobs = Job.objects.none()
        try:
            skill_filter = Q()
            for term in list(dict.fromkeys(fetch_terms))[:18]:
                skill_filter |= Q(title__icontains=term)
                skill_filter |= Q(original_description__icontains=term)
            user_has_matching_jobs = Job.objects.filter(skill_filter, is_translated=True).exists()
        except Exception:
            user_has_matching_jobs = Job.objects.filter(is_translated=True).exists()

        newest = Job.objects.order_by("-created_at").first()
        is_stale_pool = (
            newest is None or newest.created_at < timezone.now() - timedelta(hours=self._STALE_AFTER_HOURS)
        )
        should_refresh = (not user_has_matching_jobs) or is_stale_pool

        if should_refresh:
            try:
                fetch_and_save_jobs(
                    skills=fetch_terms or skills,
                    include_remote=True,
                    include_onsite=True,
                )
            except Exception as e:
                logger.error("fetch_and_save_jobs failed: %s", e)
                print("DEBUG fetch error:", e)
                return Job.objects.none()

        dismissed_job_ids = UserJobInteraction.objects.filter(
            user=user,
            status='not_interested'
        ).values_list('job_id', flat=True)

        qs = Job.objects.filter(is_translated=True).exclude(id__in=dismissed_job_ids)

        location = self.request.query_params.get('location')
        if location:
            qs = qs.filter(location__icontains=location)

        job_type = self.request.query_params.get('job_type')
        if job_type:
            qs = qs.filter(job_type=job_type)

        
        # Refill when user has dismissed many roles and feed gets too small.
        if qs.count() < self._MIN_FEED_SIZE:
            try:
                fetch_and_save_jobs(
                    skills=fetch_terms or skills,
                    include_remote=True,
                    include_onsite=True,
                )
                qs = Job.objects.filter(is_translated=True).exclude(id__in=dismissed_job_ids)
            except Exception as e:
                logger.error("feed refill fetch failed: %s", e)

        # If pool is still thin, perform one wider refresh using full analyzed terms.
        if qs.count() < self._REFRESH_IF_MATCHES_LT and fetch_terms:
            try:
                fetch_and_save_jobs(
                    skills=fetch_terms,
                    include_remote=True,
                    include_onsite=True,
                )
                qs = Job.objects.filter(is_translated=True).exclude(id__in=dismissed_job_ids)
            except Exception as e:
                logger.error("wide refresh fetch failed: %s", e)

        if qs.count() < self._MIN_FEED_SIZE:
            # Keep fallback personalized: pick from all jobs, then rank by embeddings per user.
            qs = Job.objects.filter(is_translated=True).exclude(id__in=dismissed_job_ids)

        print("DEBUG: final qs count:", qs.count())
        _ensure_job_embeddings(qs)
        profile_struct = _get_profile_structure(passport)
        self._matching_mode = (
            "technical-skill-driven" if profile_struct["tech_mode"] else "general-skill-driven"
        )
        logger.info("JOB_PIPELINE|matching_mode=%s", self._matching_mode)
        ranked_qs, score_map, _explanations = _apply_embedding_ranking(qs, passport, profile_struct)

        # If the ranking has too few "role-aligned" jobs, refresh once more with
        # broader fetch terms and re-rank. This prevents the UI from showing only
        # 1-2 strong matches while many weaker matches exist in the pool.
        top_n = getattr(self.pagination_class, "page_size", 10)
        role_aligned = sum(
            1
            for j in ranked_qs[:top_n]
            if getattr(j, "_match_keyword_hits", 0) > 0 or getattr(j, "_match_pref_hits", 0) > 0
        )
        if role_aligned < max(3, top_n // 2) and fetch_terms:
            try:
                fetch_and_save_jobs(
                    skills=fetch_terms,
                    include_remote=True,
                    include_onsite=True,
                )
                qs = Job.objects.filter(is_translated=True).exclude(id__in=dismissed_job_ids)
                _ensure_job_embeddings(qs)
                ranked_qs, score_map, _explanations = _apply_embedding_ranking(
                    qs, passport, profile_struct
                )
            except Exception as e:
                logger.error("refresh after low role alignment failed: %s", e)

        ranked_qs, score_map, feed_meta = _finalize_ranked_feed(ranked_qs, score_map)
        self._score_map = score_map
        self._feed_meta = feed_meta
        logger.info(
            "JOBS_FEED|pipeline_done|fallback_stage=%s|eff_threshold=%s|score_min=%s|score_max=%s",
            feed_meta.get("fallback_stage"),
            feed_meta.get("effective_threshold"),
            feed_meta.get("score_min"),
            feed_meta.get("score_max"),
        )
        return ranked_qs

    def list(self, request, *args, **kwargs):
        print("JOBS API HIT (list)")
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        score_map = getattr(self, "_score_map", {})

        if page is not None:
            mode = getattr(self, "_matching_mode", "")
            feed_meta = getattr(self, "_feed_meta", {}) or {}
            for job in page:
                setattr(job, "_dedupe_key", _natural_job_key(job))
                setattr(job, "_matching_mode", mode)
                if job.id in score_map:
                    sc = float(score_map[job.id])
                    setattr(job, "_match_score", sc)
                    if not getattr(job, "_match_tier", None):
                        setattr(job, "_match_tier", _suitability_tier(sc))
            serializer = self.get_serializer(page, many=True)
            payload = {
                "jobs": serializer.data,
                "matching_mode": getattr(self, "_matching_mode", "unknown"),
                "score_distribution": {
                    "min": feed_meta.get("score_min"),
                    "max": feed_meta.get("score_max"),
                    "avg": feed_meta.get("score_avg"),
                },
                "effective_threshold": feed_meta.get("effective_threshold"),
                "fallback_stage": feed_meta.get("fallback_stage"),
                "count": self.paginator.page.paginator.count,
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
            }
            logger.info("Job API returning %d jobs (paginated).", len(serializer.data))
            print("DEBUG: API jobs returned:", len(serializer.data))
            return Response(payload)

        mode = getattr(self, "_matching_mode", "")
        feed_meta = getattr(self, "_feed_meta", {}) or {}
        for job in queryset:
            setattr(job, "_dedupe_key", _natural_job_key(job))
            setattr(job, "_matching_mode", mode)
            if job.id in score_map:
                sc = float(score_map[job.id])
                setattr(job, "_match_score", sc)
                if not getattr(job, "_match_tier", None):
                    setattr(job, "_match_tier", _suitability_tier(sc))
        serializer = self.get_serializer(queryset, many=True)
        logger.info("Job API returning %d jobs (non-paginated).", len(serializer.data))
        print("DEBUG: API jobs returned:", len(serializer.data))
        return Response(
            {
                "jobs": serializer.data,
                "matching_mode": getattr(self, "_matching_mode", "unknown"),
                "score_distribution": {
                    "min": feed_meta.get("score_min"),
                    "max": feed_meta.get("score_max"),
                    "avg": feed_meta.get("score_avg"),
                },
                "effective_threshold": feed_meta.get("effective_threshold"),
                "fallback_stage": feed_meta.get("fallback_stage"),
            }
        )


class JobDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JobDetailSerializer
    queryset = Job.objects.all()

    def retrieve(self, request, *args, **kwargs):
        job = self.get_object()
        if not job.translated_tasks or not job.is_translated:
            try:
                accessible = _rewrite_and_enrich_job(job)
                setattr(job, "_accessible_summary", accessible)
            except Exception as exc:
                logger.error("description rewrite failed for job %s: %s", job.id, exc)
                return Response(
                    {
                        "detail": (
                            "AI rewrite is required but unavailable right now. "
                            "Check Anthropic dependency and API key configuration."
                        )
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
        else:
            setattr(job, "_accessible_summary", "\n".join(f"- {t}" for t in job.translated_tasks))
        return super().retrieve(request, *args, **kwargs)


class NotInterestedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        interaction, created = UserJobInteraction.objects.get_or_create(
            user=request.user,
            job=job,
            defaults={'status': 'not_interested'}
        )
        if not created and interaction.status != 'not_interested':
            interaction.status = 'not_interested'
            interaction.save()
        return Response(
            {"detail": "Job dismissed. We won't show you similar listings."},
            status=status.HTTP_200_OK
        )