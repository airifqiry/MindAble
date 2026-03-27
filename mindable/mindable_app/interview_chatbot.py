from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from jobs.models import Job
from mindable.mindable_app.claude_client import claude_messages_create, extract_text
from mindable.mindable_app.matching_logic import cosine_similarity
from mindable.mindable_app.profile_analyzer import analyze_profile
from mindable.mindable_app.prompts import (
    INTERVIEW_CHATBOT_MODEL,
    INTERVIEW_CHATBOT_SYSTEM,
    INTERVIEW_CHATBOT_USER_CONTEXT,
)
from users.models import WorkplaceProfile, User

load_dotenv()


@dataclass
class CoachTurn:
    assistant_message: str
    stage: str
    next_question: str
    feedback_good: str
    feedback_improve: str
    feedback_how: str
    strengths: list[str]
    improvements: list[str]
    difficulty: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "assistant_message": self.assistant_message,
            "stage": self.stage,
            "next_question": self.next_question,
            "feedback_good": self.feedback_good,
            "feedback_improve": self.feedback_improve,
            "feedback_how": self.feedback_how,
            "strengths": self.strengths,
            "improvements": self.improvements,
            "difficulty": self.difficulty,
        }
def _parse_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Chatbot output must be a JSON object.")
    return parsed


def _profile_payload(profile: WorkplaceProfile) -> dict[str, Any]:
    enablers = profile.success_enablers if isinstance(profile.success_enablers, dict) else {}
    analyzed = enablers.get("analyzed_profile")
    if not isinstance(analyzed, dict):
        text = " ".join(
            filter(
                None,
                [
                    profile.skills or "",
                    profile.experience_summary or "",
                    profile.mental_disability or "",
                    str(enablers.get("text", "") or ""),
                ],
            )
        )
        analyzed = analyze_profile(text)
    return {
        "skills_raw": profile.skills or "",
        "experience_summary": profile.experience_summary or "",
        "mental_disability": profile.mental_disability or "",
        "success_enablers_text": str(enablers.get("text", "") or ""),
        "dealbreakers": profile.dealbreakers or [],
        "analyzed_profile": analyzed,
    }


def _job_payload(job: Job, profile: WorkplaceProfile) -> dict[str, Any]:
    user_sk = profile.skills_embedding or []
    user_nd = profile.needs_embedding or []
    job_sk = job.skills_embedding or []
    job_nd = job.needs_embedding or []
    sim = None
    try:
        if user_sk and job_sk and user_nd and job_nd:
            sim = round((0.7 * cosine_similarity(user_sk, job_sk)) + (0.3 * cosine_similarity(user_nd, job_nd)), 4)
    except Exception:
        sim = None

    return {
        "id": job.id,
        "title": job.translated_title or job.title,
        "company": job.company.name,
        "location": job.location,
        "job_type": job.job_type,
        "required_skills": job.required_skills or [],
        "translated_tasks": job.translated_tasks or [],
        "toxicity_warnings": job.toxicity_warnings or [],
        "original_description": job.original_description or "",
        "embedding_similarity": sim,
    }


def _default_state() -> dict[str, Any]:
    return {
        "stage": "warmup",
        "turn": 0,
        "difficulty": "medium",
        "strengths": [],
        "improvements": [],
        "asked_questions": [],
    }


def _choose_difficulty(state: dict[str, Any], job_info: dict[str, Any]) -> str:
    sim = job_info.get("embedding_similarity")
    if isinstance(sim, (int, float)):
        if sim >= 0.75:
            return "advanced"
        if sim >= 0.55:
            return "medium"
        return "foundational"
    return state.get("difficulty", "medium")


def _compose_user_prompt(
    *,
    profile_json: dict[str, Any],
    job_json: dict[str, Any],
    topic: str,
    user_message: str,
    state: dict[str, Any],
    history: list[dict[str, str]],
) -> str:
    context = INTERVIEW_CHATBOT_USER_CONTEXT.format(
        cv_profile_json=json.dumps(profile_json, ensure_ascii=True),
        job_listing=json.dumps(job_json, ensure_ascii=True),
    )
    return (
        f"{context}\n\n"
        "You are running an interview coaching turn.\n"
        "Return STRICT JSON only with keys:\n"
        "assistant_message, stage, next_question, feedback_good, feedback_improve, feedback_how, strengths, improvements, difficulty.\n"
        "- Keep assistant_message <= 4 short sentences.\n"
        "- Ask exactly ONE clear question in next_question.\n"
        "- feedback_good/feedback_improve/feedback_how must be concise and concrete.\n"
        "- strengths and improvements are short bullet-like strings.\n"
        "- stage must be one of: warmup, technical, behavioral, summary.\n"
        "- difficulty must be one of: foundational, medium, advanced.\n"
        f"Current topic: {topic}\n"
        f"Current state JSON: {json.dumps(state, ensure_ascii=True)}\n"
        f"Recent history JSON: {json.dumps(history[-8:], ensure_ascii=True)}\n"
        f"Latest user answer: {user_message}\n"
    )


def run_interview_turn(
    *,
    user: User,
    topic: str,
    history: list[dict[str, str]],
    job_id: int | None = None,
) -> dict[str, Any]:
    profile = WorkplaceProfile.objects.filter(user=user).first()
    if not profile:
        raise ValueError("No workplace profile found for this user.")

    job = None
    if job_id is not None:
        job = Job.objects.filter(id=job_id).first()
        if not job:
            raise ValueError(f"No job with id={job_id} found. Choose a job from your listings.")
    else:
        job = Job.objects.filter(is_translated=True).order_by("-created_at").first()
    if not job:
        raise ValueError("No job context available for interview prep.")

    profile_json = _profile_payload(profile)
    job_json = _job_payload(job, profile)
    current_state = _default_state()
    current_state["turn"] = max(0, len(history) // 2)
    current_state["difficulty"] = _choose_difficulty(current_state, job_json)

    prompt = _compose_user_prompt(
        profile_json=profile_json,
        job_json=job_json,
        topic=topic,
        user_message=(history[-1]["content"] if history else ""),
        state=current_state,
        history=history,
    )

    messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
    for msg in history:
        role = str(msg.get("role", "")).strip()
        content = str(msg.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        messages.append({"role": role, "content": content})

    response = claude_messages_create(
        model=INTERVIEW_CHATBOT_MODEL,
        max_tokens=900,
        system=INTERVIEW_CHATBOT_SYSTEM,
        messages=messages,
    )
    raw = extract_text(response)
    parsed = _parse_json(raw)

    turn = CoachTurn(
        assistant_message=str(parsed.get("assistant_message", "")).strip(),
        stage=str(parsed.get("stage", current_state.get("stage", "warmup"))).strip() or "warmup",
        next_question=str(parsed.get("next_question", "")).strip(),
        feedback_good=str(parsed.get("feedback_good", "")).strip(),
        feedback_improve=str(parsed.get("feedback_improve", "")).strip(),
        feedback_how=str(parsed.get("feedback_how", "")).strip(),
        strengths=[str(x).strip() for x in (parsed.get("strengths") or []) if str(x).strip()][:5],
        improvements=[str(x).strip() for x in (parsed.get("improvements") or []) if str(x).strip()][:5],
        difficulty=str(parsed.get("difficulty", current_state.get("difficulty", "medium"))).strip() or "medium",
    )

    next_state = {
        "stage": turn.stage,
        "turn": int(current_state.get("turn", 0)) + 1,
        "difficulty": turn.difficulty,
        "strengths": list(dict.fromkeys((current_state.get("strengths") or []) + turn.strengths))[:8],
        "improvements": list(dict.fromkeys((current_state.get("improvements") or []) + turn.improvements))[:8],
        "asked_questions": list(dict.fromkeys((current_state.get("asked_questions") or []) + [turn.next_question]))[:20],
    }

    return {
        "job_id": job.id,
        "topic": topic,
        "state": next_state,
        "turn": turn.to_dict(),
    }
