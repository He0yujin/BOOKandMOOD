from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import Settings
from app.db.database import Database
from app.models import (
    RecommendationError,
    VALID_EVENT_TYPES,
)
from app.services.llm_client import (
    build_fallback_recommendations,
    recommend_with_llm,
)
from app.services.recommender import (
    extract_top_candidates,
    match_music_for_book,
    validate_answers,
)


settings = Settings.from_env()
db = Database(settings.database_path)

app = FastAPI(
    title="BOOK & MOOD API",
    version="1.0.0",
    description="도서관 북 큐레이션 & TEMI 서가 안내 서비스 백엔드 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
(STATIC_DIR / "covers").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class RecommendationBody(BaseModel):
    session_id: str = Field(..., min_length=1)
    answers: dict[str, Any]
    exclude_book_ids: list[str] = Field(default_factory=list)
    feedback_type: str | None = None
    allow_goal_relaxation: bool = False


class EventBody(BaseModel):
    session_id: str = Field(..., min_length=1)
    event_type: str
    book_id: str | None = None
    music_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationBody(BaseModel):
    session_id: str = Field(..., min_length=1)
    top3_satisfied: bool
    reason_score: int = Field(..., ge=1, le=5)
    music_helpful_score: int | None = Field(default=None, ge=1, le=5)
    usability_score: int = Field(..., ge=1, le=5)
    used_rerecommend: bool = False


@app.exception_handler(RecommendationError)
async def handle_recommendation_error(_, exc: RecommendationError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.to_error_response())


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "error": {
                "code": "INVALID_INPUT",
                "message": "요청 데이터 형식이 올바르지 않습니다.",
                "details": {"errors": jsonable_encoder(exc.errors())},
            },
        },
    )


@app.get("/health")
def health_check() -> dict[str, Any]:
    active_books = len(db.list_books(active_only=True))
    active_musics = len(db.list_musics(active_only=True))
    return {
        "status": "ok",
        "catalog_version": settings.catalog_version,
        "llm_provider": settings.llm_provider,
        "active_books": active_books,
        "active_musics": active_musics,
    }


@app.post("/v1/recommendations")
def create_recommendations(body: RecommendationBody) -> dict[str, Any]:
    started = time.perf_counter()
    answers = validate_answers(body.answers, feedback_type=body.feedback_type)

    all_books = db.list_books(active_only=False)
    candidates = extract_top_candidates(
        all_books=all_books,
        answers=answers,
        exclude_book_ids=body.exclude_book_ids,
        allow_goal_relaxation=body.allow_goal_relaxation,
        limit=8,
    )

    try:
        items = recommend_with_llm(answers, candidates, settings)
        source = "llm"
        error_code = None
    except Exception:
        items = build_fallback_recommendations(candidates)
        source = "fallback"
        error_code = "MODEL_UNAVAILABLE"

    latency_ms = int((time.perf_counter() - started) * 1000)
    recommended_payload = [item.to_dict() for item in items]

    db.log_recommendation(
        session_id=body.session_id,
        catalog_version=settings.catalog_version,
        answers=answers.to_dict(),
        exclude_book_ids=body.exclude_book_ids,
        feedback_type=body.feedback_type,
        allow_goal_relaxation=body.allow_goal_relaxation,
        candidate_book_ids=[c.book.book_id for c in candidates],
        recommended=recommended_payload,
        source=source,
        error_code=error_code,
        latency_ms=latency_ms,
    )

    return {
        "status": "ok",
        "source": source,
        "catalog_version": settings.catalog_version,
        "recommendations": recommended_payload,
    }


@app.get("/v1/books/{book_id}")
def get_book_detail(book_id: str) -> dict[str, Any]:
    book = db.get_book(book_id)
    if book is None or not book.is_recommendable():
        raise RecommendationError(
            "BOOK_NOT_FOUND",
            f"도서를 찾을 수 없습니다: {book_id}",
            http_status=404,
        )

    matched_music = match_music_for_book(book, db.list_musics(active_only=True))
    return {
        "status": "ok",
        "book": book.to_detail_dict(),
        "music": matched_music.to_dict() if matched_music else None,
    }


@app.post("/v1/events")
def record_event(body: EventBody) -> dict[str, Any]:
    if body.event_type not in VALID_EVENT_TYPES:
        raise RecommendationError(
            "INVALID_INPUT", f"허용되지 않은 event_type입니다: {body.event_type}"
        )
    event_id = db.log_event(
        session_id=body.session_id,
        event_type=body.event_type,
        book_id=body.book_id,
        music_id=body.music_id,
        metadata=body.metadata,
    )
    return {"status": "ok", "event_id": event_id}


@app.post("/v1/evaluations")
def record_evaluation(body: EvaluationBody) -> dict[str, Any]:
    eval_id = db.log_evaluation(
        session_id=body.session_id,
        top3_satisfied=body.top3_satisfied,
        reason_score=body.reason_score,
        music_helpful_score=body.music_helpful_score,
        usability_score=body.usability_score,
        used_rerecommend=body.used_rerecommend,
    )
    return {"status": "ok", "evaluation_id": eval_id}