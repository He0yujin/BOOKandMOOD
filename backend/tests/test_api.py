from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["active_books"] >= 3


def test_recommendations_and_rerecommend() -> None:
    payload = {
        "session_id": "pytest-session-01",
        "answers": {"goal": "refresh", "genre": "fiction", "depth": 1},
        "exclude_book_ids": [],
        "feedback_type": None,
        "allow_goal_relaxation": False,
    }
    res = client.post("/v1/recommendations", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert len(data["recommendations"]) == 3

    first_ids = [item["book_id"] for item in data["recommendations"]]
    assert len(set(first_ids)) == 3

    # 이미 읽은 책으로 제외 후 재추천 요청
    payload["exclude_book_ids"] = first_ids
    payload["feedback_type"] = "already_read"
    res2 = client.post("/v1/recommendations", json=payload)
    assert res2.status_code == 200
    second_ids = [item["book_id"] for item in res2.json()["recommendations"]]
    assert set(first_ids).isdisjoint(set(second_ids))


def test_book_detail_with_music() -> None:
    res = client.get("/v1/books/887231")
    assert res.status_code == 200
    data = res.json()
    assert data["book"]["title"] == "안녕이라 그랬어"
    assert data["music"] is not None
    assert data["music"]["youtube_url"].startswith("https://")


def test_invalid_input_returns_400() -> None:
    res = client.post(
        "/v1/recommendations",
        json={
            "session_id": "pytest-session-02",
            "answers": {"goal": "unknown_goal", "genre": "fiction", "depth": 1},
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_INPUT"