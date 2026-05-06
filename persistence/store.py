import sqlite3
from typing import Any

from loguru import logger

from agent.state import ConversationStep
from config.settings import settings

try:
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    _HAS_SERDE = True
except ImportError:
    _HAS_SERDE = False

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    _HAS_SQLITE = True
except ModuleNotFoundError:
    _HAS_SQLITE = False

if not _HAS_SQLITE:
    from langgraph.checkpoint.memory import InMemorySaver


def _build_serde():
    if not _HAS_SERDE:
        return None
    return JsonPlusSerializer().with_msgpack_allowlist([("agent.state", "ConversationStep")])


def _is_postgres(url: str) -> bool:
    return url.startswith(("postgresql://", "postgres://"))


def _get_postgres_checkpointer():
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError:
        raise RuntimeError(
            "DATABASE_URL aponta para PostgreSQL mas 'langgraph-checkpoint-postgres' "
            "não está instalado. Verifique requirements.txt."
        )

    try:
        import psycopg
    except ImportError:
        raise RuntimeError(
            "Pacote 'psycopg' não encontrado. Adicione 'psycopg[binary]>=3.1.0' ao requirements.txt."
        )

    url = settings.database_url
    conn = psycopg.connect(url, autocommit=True)
    checkpointer = PostgresSaver(conn)
    checkpointer.setup()
    logger.info("Checkpointer: PostgreSQL")
    return checkpointer


def _get_sqlite_checkpointer():
    db_path = settings.database_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    serde = _build_serde()
    try:
        cp = SqliteSaver(conn, serde=serde) if serde else SqliteSaver(conn)
    except TypeError:
        cp = SqliteSaver(conn)
    logger.info(f"Checkpointer: SQLite ({db_path})")
    return cp


def get_checkpointer() -> Any:
    url = settings.database_url

    if _is_postgres(url):
        return _get_postgres_checkpointer()

    if _HAS_SQLITE:
        return _get_sqlite_checkpointer()

    logger.warning("Checkpointer: InMemory — dados perdidos ao reiniciar")
    serde = _build_serde()
    return InMemorySaver(serde=serde) if serde else InMemorySaver()


def get_initial_state(phone: str, message: str, media_url: str = None) -> dict:
    return {
        "phone": phone,
        "message": message,
        "step": ConversationStep.INITIAL,
        "user_data": {},
        "response": "",
        "media_url": media_url,
    }
