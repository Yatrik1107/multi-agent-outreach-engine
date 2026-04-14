from fastapi import APIRouter, Depends, HTTPException

from smartlead.agents.chat_agent import ChatAgent
from smartlead.api.v1.schemas.chat import (
    ChatMessage,
    ChatMessageCreate,
    ChatSessionCreateResponse,
    ChatTurnResponse,
)
from smartlead.core.settings import Settings, get_settings
from smartlead.services.chat_session import ChatSessionStore, get_chat_session_store

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionCreateResponse)
def create_session(
    store: ChatSessionStore = Depends(get_chat_session_store),
) -> ChatSessionCreateResponse:
    return ChatSessionCreateResponse(session_id=store.create_session())


@router.post("/messages", response_model=ChatTurnResponse)
def send_message(
    body: ChatMessageCreate,
    store: ChatSessionStore = Depends(get_chat_session_store),
    settings: Settings = Depends(get_settings),
) -> ChatTurnResponse:
    if not settings.use_mock_llm and not (settings.gemini_api_key or "").strip():
        raise HTTPException(
            status_code=503,
            detail="Live mode requires GEMINI_API_KEY (or GOOGLE_API_KEY). Or set USE_MOCK_LLM=true.",
        )

    if body.session_id is None:
        session_id = store.create_session()
    else:
        session_id = body.session_id
        store.touch(session_id)

    user_msg = ChatMessage(role="user", content=body.message)
    store.append(session_id, user_msg)

    history_before_reply: list[dict[str, str]] = [
        {"role": m.role, "content": m.content}
        for m in store.history(session_id)
    ]

    try:
        agent = ChatAgent(settings=settings)
        reply_text = agent.reply(body.message, history_before_reply)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Chat model error: {exc}") from exc

    store.append(session_id, ChatMessage(role="assistant", content=reply_text))

    return ChatTurnResponse(
        session_id=session_id,
        reply=reply_text,
        messages=store.history(session_id),
    )