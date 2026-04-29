import sqlite3
from typing import Any
from config.settings import settings
from agent.state import ConversationStep
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

try:
    from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
except ModuleNotFoundError:
    SqliteSaver = None  # type: ignore
    from langgraph.checkpoint.memory import InMemorySaver


def _build_serde() -> JsonPlusSerializer:
    # Explicitly allow ConversationStep enum so LangGraph msgpack checkpoints
    # can deserialize it without runtime warnings.
    return JsonPlusSerializer().with_msgpack_allowlist([("agent.state", "ConversationStep")])


def get_checkpointer() -> Any:
    serde = _build_serde()
    if SqliteSaver is not None:
        db_path = settings.database_url.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        try:
            return SqliteSaver(conn, serde=serde)
        except TypeError:
            # Backward-compatibility if this SqliteSaver version doesn't accept serde.
            return SqliteSaver(conn)
    return InMemorySaver(serde=serde)

def get_initial_state(phone: str, message: str, media_url: str = None) -> dict:
    return {
        "phone": phone,
        "message": message,
        "step": ConversationStep.INITIAL,
        "user_data": {},
        "response": "",
        "media_url": media_url,
    }
