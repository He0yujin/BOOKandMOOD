from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.models import Book, Music


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_conn: sqlite3.Connection | None = None
        if str(self.db_path) == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
        self.init_schema()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if self._memory_conn is not None:
            try:
                yield self._memory_conn
                self._memory_conn.commit()
            except Exception:
                self._memory_conn.rollback()
                raise
            return

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS books (
                    book_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    genre TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    themes_json TEXT NOT NULL,
                    mood_tags_json TEXT NOT NULL,
                    goal_tags_json TEXT NOT NULL,
                    depth INTEGER NOT NULL,
                    depth_reason TEXT NOT NULL,
                    page_count INTEGER,
                    call_number TEXT NOT NULL DEFAULT '',
                    shelf_label TEXT NOT NULL DEFAULT '',
                    poi_id TEXT NOT NULL DEFAULT '',
                    cover_path TEXT NOT NULL DEFAULT '',
                    holding_verified INTEGER NOT NULL DEFAULT 0,
                    navigation_verified INTEGER NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS musics (
                    music_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    mood_tags_json TEXT NOT NULL,
                    style TEXT NOT NULL,
                    youtube_url TEXT NOT NULL,
                    is_instrumental_verified INTEGER NOT NULL DEFAULT 0,
                    url_verified INTEGER NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 0,
                    priority INTEGER NOT NULL DEFAULT 100,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS recommendation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    catalog_version TEXT NOT NULL,
                    answers_json TEXT NOT NULL,
                    exclude_book_ids_json TEXT NOT NULL,
                    feedback_type TEXT,
                    allow_goal_relaxation INTEGER NOT NULL DEFAULT 0,
                    candidate_book_ids_json TEXT NOT NULL,
                    recommended_json TEXT NOT NULL,
                    source TEXT NOT NULL,
                    error_code TEXT,
                    latency_ms INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS session_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    book_id TEXT,
                    music_id TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    top3_satisfied INTEGER NOT NULL,
                    reason_score INTEGER NOT NULL,
                    music_helpful_score INTEGER,
                    usability_score INTEGER NOT NULL,
                    used_rerecommend INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                """
            )

    def upsert_books(self, books: list[Book]) -> int:
        now = _utc_now_iso()
        with self.connection() as conn:
            for book in books:
                conn.execute(
                    """
                    INSERT INTO books (
                        book_id, title, author, genre, summary,
                        themes_json, mood_tags_json, goal_tags_json,
                        depth, depth_reason, page_count,
                        call_number, shelf_label, poi_id, cover_path,
                        holding_verified, navigation_verified, active, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(book_id) DO UPDATE SET
                        title = excluded.title,
                        author = excluded.author,
                        genre = excluded.genre,
                        summary = excluded.summary,
                        themes_json = excluded.themes_json,
                        mood_tags_json = excluded.mood_tags_json,
                        goal_tags_json = excluded.goal_tags_json,
                        depth = excluded.depth,
                        depth_reason = excluded.depth_reason,
                        page_count = excluded.page_count,
                        call_number = excluded.call_number,
                        shelf_label = excluded.shelf_label,
                        poi_id = excluded.poi_id,
                        cover_path = excluded.cover_path,
                        holding_verified = excluded.holding_verified,
                        navigation_verified = excluded.navigation_verified,
                        active = excluded.active,
                        updated_at = excluded.updated_at
                    """,
                    (
                        book.book_id,
                        book.title,
                        book.author,
                        book.genre,
                        book.summary,
                        json.dumps(book.themes, ensure_ascii=False),
                        json.dumps(book.mood_tags, ensure_ascii=False),
                        json.dumps(book.goal_tags, ensure_ascii=False),
                        book.depth,
                        book.depth_reason,
                        book.page_count,
                        book.call_number,
                        book.shelf_label,
                        book.poi_id,
                        book.cover_path,
                        int(book.holding_verified),
                        int(book.navigation_verified),
                        int(book.active),
                        now,
                    ),
                )
        return len(books)

    def upsert_musics(self, musics: list[Music]) -> int:
        now = _utc_now_iso()
        with self.connection() as conn:
            for music in musics:
                conn.execute(
                    """
                    INSERT INTO musics (
                        music_id, title, mood_tags_json, style, youtube_url,
                        is_instrumental_verified, url_verified, active, priority, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(music_id) DO UPDATE SET
                        title = excluded.title,
                        mood_tags_json = excluded.mood_tags_json,
                        style = excluded.style,
                        youtube_url = excluded.youtube_url,
                        is_instrumental_verified = excluded.is_instrumental_verified,
                        url_verified = excluded.url_verified,
                        active = excluded.active,
                        priority = excluded.priority,
                        updated_at = excluded.updated_at
                    """,
                    (
                        music.music_id,
                        music.title,
                        json.dumps(music.mood_tags, ensure_ascii=False),
                        music.style,
                        music.youtube_url,
                        int(music.is_instrumental_verified),
                        int(music.url_verified),
                        int(music.active),
                        music.priority,
                        now,
                    ),
                )
        return len(musics)

    @staticmethod
    def _row_to_book(row: sqlite3.Row) -> Book:
        return Book(
            book_id=row["book_id"],
            title=row["title"],
            author=row["author"],
            genre=row["genre"],
            summary=row["summary"],
            themes=json.loads(row["themes_json"]),
            mood_tags=json.loads(row["mood_tags_json"]),
            goal_tags=json.loads(row["goal_tags_json"]),
            depth=int(row["depth"]),
            depth_reason=row["depth_reason"],
            page_count=row["page_count"],
            call_number=row["call_number"],
            shelf_label=row["shelf_label"],
            poi_id=row["poi_id"],
            cover_path=row["cover_path"],
            holding_verified=bool(row["holding_verified"]),
            navigation_verified=bool(row["navigation_verified"]),
            active=bool(row["active"]),
        )

    @staticmethod
    def _row_to_music(row: sqlite3.Row) -> Music:
        return Music(
            music_id=row["music_id"],
            title=row["title"],
            mood_tags=json.loads(row["mood_tags_json"]),
            style=row["style"],
            youtube_url=row["youtube_url"],
            is_instrumental_verified=bool(row["is_instrumental_verified"]),
            url_verified=bool(row["url_verified"]),
            active=bool(row["active"]),
            priority=int(row["priority"]),
        )

    def list_books(self, active_only: bool = False) -> list[Book]:
        with self.connection() as conn:
            if active_only:
                rows = conn.execute(
                    "SELECT * FROM books WHERE active = 1 ORDER BY book_id ASC"
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM books ORDER BY book_id ASC").fetchall()
        return [self._row_to_book(r) for r in rows]

    def get_book(self, book_id: str) -> Book | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM books WHERE book_id = ?", (book_id,)
            ).fetchone()
        return self._row_to_book(row) if row else None

    def list_musics(self, active_only: bool = False) -> list[Music]:
        with self.connection() as conn:
            if active_only:
                rows = conn.execute(
                    "SELECT * FROM musics WHERE active = 1 ORDER BY priority ASC, music_id ASC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM musics ORDER BY priority ASC, music_id ASC"
                ).fetchall()
        return [self._row_to_music(r) for r in rows]

    def log_recommendation(
        self,
        *,
        session_id: str,
        catalog_version: str,
        answers: dict[str, Any],
        exclude_book_ids: list[str],
        feedback_type: str | None,
        allow_goal_relaxation: bool,
        candidate_book_ids: list[str],
        recommended: list[dict[str, Any]],
        source: str,
        error_code: str | None,
        latency_ms: int,
    ) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO recommendation_logs (
                    session_id, created_at, catalog_version,
                    answers_json, exclude_book_ids_json, feedback_type,
                    allow_goal_relaxation, candidate_book_ids_json,
                    recommended_json, source, error_code, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    _utc_now_iso(),
                    catalog_version,
                    json.dumps(answers, ensure_ascii=False),
                    json.dumps(exclude_book_ids, ensure_ascii=False),
                    feedback_type,
                    int(allow_goal_relaxation),
                    json.dumps(candidate_book_ids, ensure_ascii=False),
                    json.dumps(recommended, ensure_ascii=False),
                    source,
                    error_code,
                    latency_ms,
                ),
            )
            return int(cur.lastrowid)

    def log_event(
        self,
        *,
        session_id: str,
        event_type: str,
        book_id: str | None = None,
        music_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO session_events (
                    session_id, event_type, book_id, music_id, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    event_type,
                    book_id,
                    music_id,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    _utc_now_iso(),
                ),
            )
            return int(cur.lastrowid)

    def log_evaluation(
        self,
        *,
        session_id: str,
        top3_satisfied: bool,
        reason_score: int,
        music_helpful_score: int | None,
        usability_score: int,
        used_rerecommend: bool,
    ) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO evaluations (
                    session_id, top3_satisfied, reason_score,
                    music_helpful_score, usability_score, used_rerecommend, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    int(top3_satisfied),
                    reason_score,
                    music_helpful_score,
                    usability_score,
                    int(used_rerecommend),
                    _utc_now_iso(),
                ),
            )
            return int(cur.lastrowid)

    def fetch_all_rows(self, table_name: str) -> list[dict[str, Any]]:
        allowed_tables = {
            "books",
            "musics",
            "recommendation_logs",
            "session_events",
            "evaluations",
        }
        if table_name not in allowed_tables:
            raise ValueError(f"Unsupported table: {table_name}")
        with self.connection() as conn:
            rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY id ASC" if table_name not in {"books", "musics"} else f"SELECT * FROM {table_name}").fetchall()
        return [dict(r) for r in rows]

