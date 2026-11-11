from __future__ import annotations

import json
import urllib.request
from typing import Any

from app.config import Settings
from app.models import (
    RecommendationItem,
    ScoredCandidate,
    SurveyAnswers,
)


GOAL_LABELS = {
    "comfort": "위로와 공감을 얻고 싶어요",
    "rest": "편안하게 쉬고 싶어요",
    "refresh": "기분을 전환하고 싶어요",
    "motivate": "동기부여와 용기를 얻고 싶어요",
}

GENRE_LABELS = {
    "fiction": "이야기에 빠져드는 소설",
    "essay": "공감할 수 있는 에세이",
    "humanities": "생각을 넓히는 인문·교양",
    "any": "상관없어요",
}

DEPTH_LABELS = {
    1: "부담 없이 가볍게 읽고 싶어요 (단편)",
    2: "깊이 생각하며 읽고 싶어요 (장편)",
}


def build_prompt(answers: SurveyAnswers, candidates: list[ScoredCandidate]) -> str:
    candidate_payload = [
        {
            "book_id": c.book.book_id,
            "title": c.book.title,
            "author": c.book.author,
            "genre": c.book.genre,
            "depth": c.book.depth,
            "summary": c.book.summary,
            "themes": c.book.themes,
            "mood_tags": c.book.mood_tags,
            "goal_tags": c.book.goal_tags,
            "rule_score": c.total_score,
        }
        for c in candidates
    ]

    return (
        "당신은 도서관 북 큐레이션 로봇 BOOK & MOOD의 추천 엔진입니다.\n"
        "아래 사용자 문진 응답과 후보 도서 목록만을 근거로 가장 적합한 서로 다른 도서 3권을 선정하세요.\n\n"
        "[규칙]\n"
        "1. 반드시 후보 목록의 book_id만 사용하세요.\n"
        "2. 서로 다른 3권을 선택하세요.\n"
        "3. 추천 이유(reason)는 각 책의 실제 summary·themes에만 근거하여 한국어 60~100자 이내의 친근한 해요체로 작성하세요.\n"
        "4. 줄거리에 없는 사실, 청구기호, URL, 이동 명령은 절대 생성하지 마세요.\n"
        "5. 반드시 아래 JSON 형식으로만 응답하세요.\n"
        '{"recommendations":[{"book_id":"...","reason":"..."}]}\n\n'
        f"[사용자 문진]\n"
        f"- 독서 목적: {GOAL_LABELS.get(answers.goal, answers.goal)}\n"
        f"- 선호 유형: {GENRE_LABELS.get(answers.genre, answers.genre)}\n"
        f"- 독서 깊이: {DEPTH_LABELS.get(int(answers.depth), str(answers.depth))}\n\n"
        f"[후보 도서 ({len(candidate_payload)}권)]\n"
        f"{json.dumps(candidate_payload, ensure_ascii=False)}"
    )


def validate_llm_items(
    raw_items: Any,
    candidate_map: dict[str, ScoredCandidate],
) -> list[RecommendationItem]:
    if not isinstance(raw_items, list) or len(raw_items) != 3:
        raise ValueError("LLM 응답은 정확히 3권의 리스트여야 합니다.")

    seen_ids: set[str] = set()
    validated: list[RecommendationItem] = []

    for entry in raw_items:
        if not isinstance(entry, dict):
            raise ValueError("추천 항목 형식이 올바르지 않습니다.")
        book_id = str(entry.get("book_id", "")).strip()
        reason = " ".join(str(entry.get("reason", "")).split())

        if book_id not in candidate_map:
            raise ValueError(f"후보에 없는 book_id 반환: {book_id}")
        if book_id in seen_ids:
            raise ValueError(f"중복된 book_id 반환: {book_id}")
        if not (15 <= len(reason) <= 130):
            raise ValueError(f"추천 이유 길이 부적절 ({len(reason)}자)")
        lowered_reason = reason.lower()
        if any(token in lowered_reason for token in ("http://", "https://", "youtu.be", "youtube.com")):
            raise ValueError("추천 이유에 허용되지 않은 URL이 포함되어 있습니다.")

        seen_ids.add(book_id)
        validated.append(
            RecommendationItem(
                book_id=book_id,
                reason=reason,
                book=candidate_map[book_id].book,
            )
        )

    return validated


def _call_mock_llm(
    answers: SurveyAnswers,
    candidates: list[ScoredCandidate],
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for c in candidates[:3]:
        b = c.book
        theme_text = "·".join(b.themes[:2]) if b.themes else "다양한 이야기"
        mood_text = "·".join(b.mood_tags[:2]) if b.mood_tags else "잔잔한"
        reason = (
            f"{theme_text} 이야기를 {mood_text} 분위기로 풀어내어 "
            f"지금 원하시는 독서 시간에 편안히 몰입하기 좋은 책이에요."
        )
        results.append({"book_id": b.book_id, "reason": reason[:100]})
    return results


def _call_openai(prompt: str, settings: Settings) -> list[dict[str, Any]]:
    url = "https://api.openai.com/v1/chat/completions"
    body = json.dumps(
        {
            "model": settings.llm_model,
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=settings.llm_timeout_sec) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if isinstance(parsed, list):
        return parsed
    return parsed.get("recommendations", [])


def _call_gemini(prompt: str, settings: Settings) -> list[dict[str, Any]]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.llm_model}:generateContent"
    )
    generation_config: dict[str, Any] = {
        "temperature": 0.4,
        "responseMimeType": "application/json",
    }
    if "2.5" in settings.llm_model:
        generation_config["thinkingConfig"] = {"thinkingBudget": 0}

    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": settings.llm_api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=settings.llm_timeout_sec) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(content)
    if isinstance(parsed, list):
        return parsed
    return parsed.get("recommendations", [])


def recommend_with_llm(
    answers: SurveyAnswers,
    candidates: list[ScoredCandidate],
    settings: Settings,
) -> list[RecommendationItem]:
    candidate_map = {c.book.book_id: c for c in candidates}
    prompt = build_prompt(answers, candidates)

    last_error: Exception | None = None
    attempts = max(1, settings.llm_max_retries + 1)

    for _ in range(attempts):
        try:
            provider = settings.llm_provider
            if provider == "mock" or not settings.llm_api_key:
                raw_items = _call_mock_llm(answers, candidates)
            elif provider == "openai":
                raw_items = _call_openai(prompt, settings)
            elif provider == "gemini":
                raw_items = _call_gemini(prompt, settings)
            else:
                raise ValueError(f"지원하지 않는 LLM_PROVIDER: {provider}")

            return validate_llm_items(raw_items, candidate_map)
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"LLM 추천 실패: {last_error}")


def build_fallback_recommendations(
    candidates: list[ScoredCandidate],
) -> list[RecommendationItem]:
    return [
        RecommendationItem(
            book_id=c.book.book_id,
            reason="선택하신 독서 목적과 선호 유형을 기준으로 추천한 책이에요.",
            book=c.book,
        )
        for c in candidates[:3]
    ]