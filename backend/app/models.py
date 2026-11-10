from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALID_GOALS = ("comfort", "rest", "refresh", "motivate")
VALID_BOOK_GENRES = ("fiction", "essay", "humanities")
VALID_QUERY_GENRES = (*VALID_BOOK_GENRES, "any")
VALID_DEPTHS = (1, 2)
VALID_MOOD_TAGS = (
    "따뜻함",
    "위로",
    "평온함",
    "설렘",
    "활력",
    "희망",
    "유쾌함",
    "쓸쓸함",
    "긴장감",
    "신비로움",
)
VALID_FEEDBACK_TYPES = (
    "different_genre",
    "lighter",
    "different_mood",
    "already_read",
)
VALID_EVENT_TYPES = (
    "book_selected",
    "qr_displayed",
    "nav_started",
    "nav_arrived",
    "nav_failed",
    "returned_home",
)

GOAL_MOOD_MAP: dict[str, set[str]] = {
    "comfort": {"위로", "따뜻함", "희망"},
    "rest": {"평온함", "따뜻함"},
    "refresh": {"활력", "유쾌함", "설렘", "신비로움"},
    "motivate": {"희망", "활력"},
}

SIMILAR_GOALS: dict[str, list[str]] = {
    "comfort": ["rest", "motivate"],
    "rest": ["comfort", "refresh"],
    "refresh": ["rest", "motivate"],
    "motivate": ["refresh", "comfort"],
}


@dataclass
class Book:
    book_id: str
    title: str
    author: str
    genre: str
    summary: str
    themes: list[str]
    mood_tags: list[str]
    goal_tags: list[str]
    depth: int
    depth_reason: str
    page_count: int | None = None
    call_number: str = ""
    shelf_label: str = ""
    poi_id: str = ""
    cover_path: str = ""
    holding_verified: bool = False
    navigation_verified: bool = False
    active: bool = False

    def is_recommendable(self) -> bool:
        return (
            self.active
            and self.holding_verified
            and self.navigation_verified
            and bool(self.poi_id.strip())
            and bool(self.call_number.strip())
        )

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "author": self.author,
            "genre": self.genre,
            "depth": self.depth,
            "cover_path": self.cover_path,
        }

    def to_detail_dict(self) -> dict[str, Any]:
        return {
            "book_id": self.book_id,
            "title": self.title,
            "author": self.author,
            "genre": self.genre,
            "summary": self.summary,
            "themes": list(self.themes),
            "mood_tags": list(self.mood_tags),
            "goal_tags": list(self.goal_tags),
            "depth": self.depth,
            "depth_reason": self.depth_reason,
            "page_count": self.page_count,
            "call_number": self.call_number,
            "shelf_label": self.shelf_label,
            "poi_id": self.poi_id,
            "cover_path": self.cover_path,
        }


@dataclass
class Music:
    music_id: str
    title: str
    mood_tags: list[str]
    style: str
    youtube_url: str
    is_instrumental_verified: bool = False
    url_verified: bool = False
    active: bool = False
    priority: int = 100

    def is_usable(self) -> bool:
        return (
            self.active
            and self.is_instrumental_verified
            and self.url_verified
            and self.youtube_url.startswith(("https://", "http://"))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "music_id": self.music_id,
            "title": self.title,
            "style": self.style,
            "mood_tags": list(self.mood_tags),
            "youtube_url": self.youtube_url,
        }


@dataclass
class SurveyAnswers:
    goal: str
    genre: str
    depth: int | str  # 1(단편), 2(장편)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "genre": self.genre,
            "depth": self.depth,
        }


@dataclass
class ScoredCandidate:
    book: Book
    total_score: int
    goal_score: int
    genre_score: int
    depth_score: int
    mood_score: int
    mood_overlap_count: int


@dataclass
class RecommendationItem:
    book_id: str
    reason: str
    book: Book | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "book_id": self.book_id,
            "reason": self.reason,
        }
        if self.book is not None:
            payload["book"] = self.book.to_summary_dict()
        return payload


@dataclass
class RecommendationRequest:
    session_id: str
    answers: SurveyAnswers
    exclude_book_ids: list[str] = field(default_factory=list)
    feedback_type: str | None = None
    allow_goal_relaxation: bool = False


class RecommendationError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def to_error_response(self) -> dict[str, Any]:
        return {
            "status": "error",
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }

