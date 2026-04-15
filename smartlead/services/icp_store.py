"""Thread-safe in-memory ICP for this process (POC). Resets on server restart."""

from __future__ import annotations

from threading import Lock

from smartlead.services.icp import ICP, get_default_icp

_lock = Lock()
_current: ICP | None = None


def _ensure_loaded() -> None:
    global _current
    if _current is None:
        _current = get_default_icp()


def get_active_icp() -> ICP:
    with _lock:
        _ensure_loaded()
        assert _current is not None
        return _current.model_copy(deep=True)


def set_active_icp(icp: ICP) -> None:
    global _current
    with _lock:
        _current = icp.model_copy(deep=True)


def reset_icp_to_default() -> ICP:
    global _current
    with _lock:
        _current = get_default_icp().model_copy(deep=True)
        return _current.model_copy(deep=True)