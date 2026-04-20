"""Thread-safe in-memory ICP for this process (POC). Resets on server restart."""

from __future__ import annotations

from threading import Lock

from smartlead.services.icp import (
    ICP,
    get_default_icp,
    get_default_template_id,
    get_template_by_id,
)

_lock = Lock()
_current: ICP | None = None
_active_template_id: str | None = None


def _ensure_loaded() -> None:
    global _current, _active_template_id
    if _current is None:
        default_template = get_template_by_id(get_default_template_id())
        if default_template is not None:
            _active_template_id = default_template.id
            _current = default_template.icp.model_copy(deep=True)
        else:
            _active_template_id = get_default_template_id()
            _current = get_default_icp()


def get_active_icp() -> ICP:
    with _lock:
        _ensure_loaded()
        assert _current is not None
        return _current.model_copy(deep=True)


def set_active_icp(icp: ICP) -> None:
    global _current
    with _lock:
        _ensure_loaded()
        _current = icp.model_copy(deep=True)


def get_active_template_id() -> str:
    with _lock:
        _ensure_loaded()
        assert _active_template_id is not None
        return _active_template_id


def apply_template_defaults(template_id: str) -> ICP:
    global _current, _active_template_id
    with _lock:
        _ensure_loaded()
        template = get_template_by_id(template_id)
        if template is None:
            raise ValueError(f"Unknown template_id: {template_id}")

        _active_template_id = template.id
        _current = template.icp.model_copy(deep=True)
        return _current.model_copy(deep=True)


def reset_icp_to_default() -> ICP:
    global _current
    with _lock:
        _ensure_loaded()
        current_template = get_template_by_id(_active_template_id or "")
        if current_template is not None:
            _current = current_template.icp.model_copy(deep=True)
        else:
            default_template = get_template_by_id(get_default_template_id())
            if default_template is not None:
                _current = default_template.icp.model_copy(deep=True)
            else:
                _current = get_default_icp().model_copy(deep=True)
        return _current.model_copy(deep=True)