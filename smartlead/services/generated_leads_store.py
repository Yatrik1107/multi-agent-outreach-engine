"""Thread-safe in-memory store for generated leads (POC). Resets on restart."""

from __future__ import annotations

from threading import Lock

from smartlead.api.v1.schemas.leads import LeadInput

_lock = Lock()
_generated: list[LeadInput] | None = None
_warnings: list[str] = []


def set_generated_leads(leads: list[LeadInput], warnings: list[str] | None = None) -> None:
    global _generated, _warnings
    with _lock:
        _generated = [row.model_copy(deep=True) for row in leads]
        _warnings = list(warnings or [])


def get_generated_leads() -> list[LeadInput] | None:
    with _lock:
        if not _generated:
            return None
        return [row.model_copy(deep=True) for row in _generated]


def get_generated_warnings() -> list[str]:
    with _lock:
        return list(_warnings)


def clear_generated_leads() -> None:
    global _generated, _warnings
    with _lock:
        _generated = None
        _warnings = []


def generated_leads_summary() -> dict[str, bool | int | list[str]]:
    with _lock:
        count = len(_generated) if _generated else 0
        return {
            "available": count > 0,
            "lead_count": count,
            "warnings": list(_warnings),
        }
