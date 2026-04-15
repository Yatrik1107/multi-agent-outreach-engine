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


def format_pipeline_context_for_prompt(max_chars: int = 12000) -> str | None:
    rows = get_last_lead_results()
    if not rows:
        return None
    parts: list[str] = []
    for i, row in enumerate(rows, start=1):
        parts.append(f"Lead #{i}:\n{json.dumps(row.model_dump(), ensure_ascii=False)}")
    text = (
        "Most recent lead pipeline run on this server (one JSON object per lead, "
        "fields: lead, research, score, outreach):\n\n" + "\n\n".join(parts)
    )
    if len(text) > max_chars:
        return text[: max_chars - 20] + "\n…(truncated)"
    return text


def last_run_summary() -> dict[str, bool | int]:
    rows = get_last_lead_results()
    if not rows:
        return {"available": False, "lead_count": 0}
    return {"available": True, "lead_count": len(rows)}