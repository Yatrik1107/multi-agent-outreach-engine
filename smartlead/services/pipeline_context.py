from __future__ import annotations

import json
from threading import Lock

from smartlead.api.v1.schemas.leads import LeadResult

_lock = Lock()
_last_results: list[LeadResult] | None = None


def set_last_lead_results(rows: list[LeadResult]) -> None:
    global _last_results
    with _lock:
        _last_results = list(rows)


def get_last_lead_results() -> list[LeadResult] | None:
    with _lock:
        if not _last_results:
            return None
        return list(_last_results)


def format_pipeline_context_for_prompt(max_chars: int = 14000) -> str | None:
    rows = get_last_lead_results()
    if not rows:
        return None

    names_ordered = [r.lead.company_name for r in rows]
    score_lines = [f"- {r.lead.company_name}: score {r.score.score}" for r in rows]

    summary = (
        "PIPELINE_SUMMARY (read this first; answers must agree with it):\n"
        f"- lead_count: {len(rows)}\n"
        f"- companies_in_order: {json.dumps(names_ordered, ensure_ascii=False)}\n"
        "- scores:\n"
        + "\n".join(score_lines)
        + "\n"
        "- Rule: If lead_count >= 1, you MUST treat these companies as already processed. "
        "Do NOT tell the user to run the pipeline or upload a CSV for questions about this list, "
        "scores, or outreach drafts. List companies from companies_in_order when asked.\n"
    )

    parts: list[str] = []
    for i, row in enumerate(rows, start=1):
        parts.append(f"Lead #{i} (full JSON):\n{json.dumps(row.model_dump(), ensure_ascii=False)}")

    detail = (
        "\nDETAIL (full lead payloads; use for email text, research fields, rationale):\n\n"
        + "\n\n".join(parts)
    )
    text = summary + detail
    if len(text) > max_chars:
        return text[: max_chars - 30] + "\n…(truncated; PIPELINE_SUMMARY at top is authoritative)"
    return text


def last_run_summary() -> dict[str, bool | int]:
    rows = get_last_lead_results()
    if not rows:
        return {"available": False, "lead_count": 0}
    return {"available": True, "lead_count": len(rows)}