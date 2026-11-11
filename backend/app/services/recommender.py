from __future__ import annotations

from app.models import (
    Book,
    GOAL_MOOD_MAP,
    Music,
    RecommendationError,
    SIMILAR_GOALS,
    ScoredCandidate,
    SurveyAnswers,
    VALID_DEPTHS,
    VALID_FEEDBACK_TYPES,
    VALID_GOALS,
    VALID_QUERY_GENRES,
)


def validate_answers(
    raw_answers: dict | None,
    feedback_type: str | None = None,
) -> SurveyAnswers:
    if not isinstance(raw_answers, dict):
        raise RecommendationError("INVALID_INPUT", "문진 응답(answers)이 누락되었습니다.")

    goal = str(raw_answers.get("goal", "")).strip()
    genre = str(raw_answers.get("genre", "")).strip()
    raw_depth = raw_answers.get("depth")

    if goal not in VALID_GOALS:
        raise RecommendationError("INVALID_INPUT", f"허용되지 않은 goal 값입니다: {goal}")
    if genre not in VALID_QUERY_GENRES:
        raise RecommendationError("INVALID_INPUT", f"허용되지 않은 genre 값입니다: {genre}")

    if isinstance(raw_depth, bool):
        raise RecommendationError("INVALID_INPUT", f"허용되지 않은 depth 값입니다: {raw_depth}")

    try:
        depth = int(raw_depth)
    except (TypeError, ValueError):
        raise RecommendationError("INVALID_INPUT", f"허용되지 않은 depth 값입니다: {raw_depth}")

    if depth not in VALID_DEPTHS:
        raise RecommendationError("INVALID_INPUT", f"depth는 1 또는 2여야 합니다: {depth}")

    if feedback_type is not None and feedback_type not in VALID_FEEDBACK_TYPES:
        raise RecommendationError(
            "INVALID_INPUT", f"허용되지 않은 feedback_type입니다: {feedback_type}"
        )

    # '더 가벼운 책' 재추천 사유 선택 시 깊이를 1(단편)로 전환
    if feedback_type == "lighter":
        depth = 1

    return SurveyAnswers(goal=goal, genre=genre, depth=depth)


def score_book(book: Book, answers: SurveyAnswers) -> ScoredCandidate:
    # 1. 독서 목적 (기본 40점 + 첫 번째 주 목적 일치 시 타이브레이킹 +5점)
    if answers.goal in book.goal_tags:
        goal_score = 45 if book.goal_tags[0] == answers.goal else 40
    else:
        goal_score = 20  # allow_goal_relaxation으로 포함된 유사 목적 도서

    # 2. 도서 유형 (일치 25 / any는 일괄 25)
    if answers.genre == "any" or book.genre == answers.genre:
        genre_score = 25
    else:
        genre_score = 0

    # 3. 독서 깊이 (일치 20)
    depth_score = 20 if book.depth == answers.depth else 0

    # 4. 분위기 적합성 (교집합 2개 이상 15 / 1개 8 / 0개 0)
    target_moods = GOAL_MOOD_MAP.get(answers.goal, set())
    overlap_count = len(set(book.mood_tags) & target_moods)
    if overlap_count >= 2:
        mood_score = 15
    elif overlap_count == 1:
        mood_score = 8
    else:
        mood_score = 0

    total = goal_score + genre_score + depth_score + mood_score
    return ScoredCandidate(
        book=book,
        total_score=total,
        goal_score=goal_score,
        genre_score=genre_score,
        depth_score=depth_score,
        mood_score=mood_score,
        mood_overlap_count=overlap_count,
    )


def extract_top_candidates(
    all_books: list[Book],
    answers: SurveyAnswers,
    exclude_book_ids: list[str] | None = None,
    allow_goal_relaxation: bool = False,
    limit: int = 8,
) -> list[ScoredCandidate]:
    eligible = [b for b in all_books if b.is_recommendable()]
    if len(eligible) < 3:
        raise RecommendationError(
            "CATALOG_INSUFFICIENT",
            "추천 가능한 활성 도서가 3권 미만입니다.",
            http_status=503,
        )

    excluded = set(exclude_book_ids or [])
    available = [b for b in eligible if b.book_id not in excluded]
    if len(available) < 3:
        raise RecommendationError(
            "NO_MORE_BOOKS",
            "제외 조건을 반영하면 추천 가능한 도서가 부족합니다.",
        )

    # 2단계: 선택한 독서 목적 우선 필터링
    goal_matched = [b for b in available if answers.goal in b.goal_tags]
    if len(goal_matched) < 3:
        if not allow_goal_relaxation:
            raise RecommendationError(
                "GOAL_COVERAGE_INSUFFICIENT",
                "선택하신 독서 목적에 해당하는 도서가 3권 미만입니다.",
                details={"similar_goals": SIMILAR_GOALS.get(answers.goal, [])},
            )
        similar = set(SIMILAR_GOALS.get(answers.goal, []))
        goal_matched = [
            b for b in available if (answers.goal in b.goal_tags) or (set(b.goal_tags) & similar)
        ]
        if len(goal_matched) < 3:
            raise RecommendationError(
                "NO_MORE_BOOKS",
                "유사 목적까지 포함해도 추천 가능한 도서가 부족합니다.",
            )

    scored = [score_book(b, answers) for b in goal_matched]
    scored.sort(
        key=lambda c: (c.total_score, c.mood_overlap_count, c.book.book_id),
        reverse=True,
    )
    return scored[:limit]


def match_music_for_book(book: Book, all_musics: list[Music]) -> Music | None:
    usable = [m for m in all_musics if m.is_usable()]
    if not usable:
        return None

    book_moods = set(book.mood_tags)
    scored_musics: list[tuple[int, int, str, Music]] = []
    for m in usable:
        overlap = len(book_moods & set(m.mood_tags))
        if overlap > 0:
            scored_musics.append((-overlap, m.priority, m.music_id, m))

    if not scored_musics:
        return None

    scored_musics.sort(key=lambda item: (item[0], item[1], item[2]))
    return scored_musics[0][3]