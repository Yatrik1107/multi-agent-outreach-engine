from threading import Lock
from uuid import uuid4

from smartlead.api.v1.schemas.chat import ChatMessage


class ChatSessionStore:
    """In-memory chat history for POC demos (lost on server restart)."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._lock = Lock()

    def create_session(self) -> str:
        session_id = str(uuid4())
        with self._lock:
            self._sessions[session_id] = []
        return session_id

    def touch(self, session_id: str) -> None:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []

    def append(self, session_id: str, message: ChatMessage) -> None:
        with self._lock:
            self.touch_unlocked(session_id)
            self._sessions[session_id].append(message)

    def history(self, session_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def touch_unlocked(self, session_id: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []


_store: ChatSessionStore | None = None


def get_chat_session_store() -> ChatSessionStore:
    global _store
    if _store is None:
        _store = ChatSessionStore()
    return _store