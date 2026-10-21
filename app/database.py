"""LESSON 2 - SQLite persistence.

SQLite is a database stored in ONE file (chat.db). Python ships with it
(`sqlite3` module), so there is nothing to install or run.

Schema (two tables, one-to-many):
    conversations 1 ──< messages
Each message row stores its role ("user" / "assistant") and text.
LLMs are STATELESS: they remember nothing between calls. "Memory" is
just us re-sending the earlier messages every time. This DB is that memory.
"""
import sqlite3
import uuid
from contextlib import contextmanager

from .config import DB_PATH


@contextmanager
def get_conn():
    """Open a connection, commit on success, rollback on error, always close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["content"]
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist yet (safe to call on every start)."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                role            TEXT NOT NULL CHECK (role IN ('user','assistant')),
                content         TEXT NOT NULL,
                created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id, id);
            """
        )


def create_conversation(title: str) -> str:
    conv_id = uuid.uuid4().hex
    with get_conn() as conn:
        # "?" placeholders = parameterized queries. NEVER build SQL with
        # f-strings: that's how SQL injection happens.
        conn.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (conv_id, title[:60]),
        )
    return conv_id


def conversation_exists(conv_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
    return row is not None


def add_message(conv_id: str, role: str, content: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conv_id, role, content),
        )


def get_messages(conv_id: str, limit: int | None = None) -> list[dict]:
    """Oldest-first. `limit` keeps only the most recent N (saves tokens)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY id",
            (conv_id,),
        ).fetchall()
    msgs = [dict(r) for r in rows]
    return msgs[-limit:] if limit else msgs


def list_conversations() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM conversations ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_conversation(conv_id: str) -> None:
    with get_conn() as conn:
        # SQLite only enforces ON DELETE CASCADE if foreign keys are on,
        # so delete children explicitly to be safe.
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
