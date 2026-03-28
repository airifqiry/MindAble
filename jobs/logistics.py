from __future__ import annotations

import re

_PAY_RE = re.compile(
    r"(?:£|€|\$)\s*[\d,.]+(?:\s*[-–]\s*(?:£|€|\$)?\s*[\d,.]+)?(?:\s*(?:k|K|\/yr|(?:per|\/)\s*year))?",
    re.IGNORECASE,
)


def logistics_highlights_for_job(job) -> list[str]:
    """
    Short, candidate-facing lines about work setup and perks.
    Uses Job fields plus light keyword checks on the original description.
    """
    lines: list[str] = []
    jt = (getattr(job, "job_type", None) or "").strip().lower()
    loc = (getattr(job, "location", None) or "").strip()

    if jt == "remote":
        lines.append(
            f"Remote role — hiring region or geography: {loc}."
            if loc
            else "This posting is for remote work."
        )
    elif jt == "hybrid":
        lines.append(
            f"Hybrid role (on-site and remote). Office or region: {loc}."
            if loc
            else "This posting is for hybrid work (mix of on-site and remote)."
        )
    elif jt == "full-time":
        lines.append("Full-time employment.")
    elif jt == "part-time":
        lines.append("Part-time employment.")
    elif jt:
        lines.append(f"Work type on the listing: {jt.replace('-', ' ')}.")

    if loc and jt not in ("remote", "hybrid"):
        lines.append(f"Location or region: {loc}.")

    text = getattr(job, "original_description", None) or ""
    lower = text.lower()

    if _PAY_RE.search(text) or re.search(
        r"(?:salary|compensation|pay range|base pay)\s*[:]\s*",
        lower,
    ):
        lines.append("The listing mentions pay or a compensation range — see the full post for details.")

    if any(p in lower for p in ("health insurance", "medical benefit", "dental", "vision coverage")):
        lines.append("Health-related benefits are mentioned.")

    if "401" in lower or "retirement plan" in lower or "pension" in lower:
        lines.append("Retirement or pension benefits are mentioned.")

    if any(
        p in lower
        for p in ("paid time off", "paid time-off", "pto", "vacation days", "unlimited time off")
    ):
        lines.append("Paid time off or vacation is mentioned.")

    if any(p in lower for p in ("flexible hours", "flexible schedule", "async-first", "async first")):
        lines.append("Flexible scheduling or async-friendly work is mentioned.")

    if any(p in lower for p in ("equity", "stock options", "rsu")):
        lines.append("Equity or stock compensation is mentioned.")

    if "home office" in lower or "home-office stipend" in lower or "equipment stipend" in lower:
        lines.append("Home office or equipment support is mentioned.")

    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = line.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(line.strip())
    return out[:10]
