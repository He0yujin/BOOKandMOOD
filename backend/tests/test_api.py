from __future__ import annotations

import json
import sys
import urllib.request
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import app.main as main_module
from app.db.database import Database
from app.models import ScoredCandidate
from app.services.llm_client import _call_gemini, validate_llm_items
from scripts.export_logs import export_table_csv
from scripts.seed_db import load_books_from_csv, load_musics_from_csv


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    test_db = Database(tmp_path / "test_bookmood.db")
    books = load_books_from_csv(BACKEND_DIR / "data" / "sample_books_48.csv")
    musics = load_musics_from_csv(BACKEND_DIR / "data" / "sample_musics.csv")
    test_db.upsert_books(books)
    test_db.upsert_musics(musics)
    monkeypatch.setattr(main_module, "db", test_db)
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, llm_provider="mock", llm_api_key=""),
    )
    return TestClient(main_module.app)


def test_health_check(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["active_books"] == 48
    assert body["active_musics"] == 6


def test_recommendations_and_rerecommend(client: TestClient) -> None:
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
    assert data["source"] == "llm"
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


def test_lighter_feedback_switches_to_depth_1(client: TestClient) -> None:
    res = client.post(
        "/v1/recommendations",
        json={
            "session_id": "pytest-session-lighter",
            "answers": {"goal": "refresh", "genre": "essay", "depth": 2},
            "exclude_book_ids": [],
            "feedback_type": "lighter",
        },
    )
    assert res.status_code == 200
    recs = res.json()["recommendations"]
    assert len(recs) == 3
    assert any(item["book"]["depth"] == 1 for item in recs)


def test_llm_failure_returns_fallback_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated api outage")

    monkeypatch.setattr(main_module, "recommend_with_llm", boom)

    res = client.post(
        "/v1/recommendations",
        json={
            "session_id": "pytest-session-fallback",
            "answers": {"goal": "comfort", "genre": "any", "depth": 1},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "fallback"
    assert len(data["recommendations"]) == 3


def test_book_detail_and_not_found(client: TestClient) -> None:
    res = client.get("/v1/books/887231")
    assert res.status_code == 200
    data = res.json()
    assert data["book"]["title"] == "안녕이라 그랬어"
    assert data["music"] is not None
    assert data["music"]["youtube_url"].startswith("https://")

    not_found = client.get("/v1/books/NON_EXISTENT_ID")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "BOOK_NOT_FOUND"


def test_events_evaluations_and_standardized_validation_error(
    client: TestClient,
) -> None:
    ev_ok = client.post(
        "/v1/events",
        json={
            "session_id": "pytest-session-ev",
            "event_type": "book_selected",
            "book_id": "887231",
        },
    )
    assert ev_ok.status_code == 200
    assert ev_ok.json()["status"] == "ok"

    ev_bad = client.post(
        "/v1/events",
        json={"session_id": "pytest-session-ev", "event_type": "invalid_ev"},
    )
    assert ev_bad.status_code == 400
    assert ev_bad.json()["error"]["code"] == "INVALID_INPUT"

    eval_ok = client.post(
        "/v1/evaluations",
        json={
            "session_id": "pytest-session-ev",
            "top3_satisfied": True,
            "reason_score": 5,
            "music_helpful_score": 4,
            "usability_score": 5,
            "used_rerecommend": False,
        },
    )
    assert eval_ok.status_code == 200

    # Pydantic validation (reason_score > 5) 도 표준 INVALID_INPUT 포맷으로 반환되어야 함
    eval_bad = client.post(
        "/v1/evaluations",
        json={
            "session_id": "pytest-session-ev",
            "top3_satisfied": True,
            "reason_score": 99,
            "usability_score": 5,
        },
    )
    assert eval_bad.status_code == 400
    assert eval_bad.json()["error"]["code"] == "INVALID_INPUT"


def test_invalid_survey_and_no_more_books(client: TestClient) -> None:
    bad = client.post(
        "/v1/recommendations",
        json={
            "session_id": "pytest-session-bad",
            "answers": {"goal": "unknown_goal", "genre": "fiction", "depth": 1},
        },
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "INVALID_INPUT"

    all_ids = [b.book_id for b in main_module.db.list_books(active_only=True)]
    exhausted = client.post(
        "/v1/recommendations",
        json={
            "session_id": "pytest-session-empty",
            "answers": {"goal": "refresh", "genre": "fiction", "depth": 1},
            "exclude_book_ids": all_ids[:-2],
        },
    )
    assert exhausted.status_code == 400
    assert exhausted.json()["error"]["code"] == "NO_MORE_BOOKS"


def test_goal_relaxation_flow(client: TestClient) -> None:
    motivate_ids = [
        b.book_id
        for b in main_module.db.list_books(active_only=True)
        if "motivate" in b.goal_tags
    ]
    # motivate 태그 도서를 2권만 남기도록 제외하면 GOAL_COVERAGE_INSUFFICIENT 반환
    excluded = motivate_ids[:-2]
    res = client.post(
        "/v1/recommendations",
        json={
            "session_id": "pytest-session-relax",
            "answers": {"goal": "motivate", "genre": "any", "depth": 1},
            "exclude_book_ids": excluded,
            "allow_goal_relaxation": False,
        },
    )
    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "GOAL_COVERAGE_INSUFFICIENT"
    assert "similar_goals" in body["error"]["details"]

    # allow_goal_relaxation=True 허용 시 유사 목적 도서를 포함해 정상 3권 추천
    relaxed = client.post(
        "/v1/recommendations",
        json={
            "session_id": "pytest-session-relax",
            "answers": {"goal": "motivate", "genre": "any", "depth": 1},
            "exclude_book_ids": excluded,
            "allow_goal_relaxation": True,
        },
    )
    assert relaxed.status_code == 200
    assert len(relaxed.json()["recommendations"]) == 3


def test_inactive_book_excluded_and_music_null_fallback(client: TestClient) -> None:
    book = main_module.db.get_book("887231")
    assert book is not None
    book.active = False
    main_module.db.upsert_books([book])

    # 비활성 도서는 상세 조회 시 404 BOOK_NOT_FOUND
    detail_hidden = client.get("/v1/books/887231")
    assert detail_hidden.status_code == 404
    assert detail_hidden.json()["error"]["code"] == "BOOK_NOT_FOUND"

    # 모든 음악 비활성화 시에도 도서 상세 조회는 music=null로 정상 200 응답
    musics = main_module.db.list_musics()
    for m in musics:
        m.active = False
    main_module.db.upsert_musics(musics)

    detail_ok = client.get("/v1/books/885996")
    assert detail_ok.status_code == 200
    assert detail_ok.json()["music"] is None


def test_llm_validator_blocks_hallucination_and_urls(client: TestClient) -> None:
    books = main_module.db.list_books(active_only=True)[:3]
    candidates = {
        b.book_id: ScoredCandidate(
            book=b,
            total_score=80,
            goal_score=40,
            genre_score=25,
            depth_score=15,
            mood_score=0,
            mood_overlap_count=0,
        )
        for b in books
    }
    valid_reason = "차분하고 따뜻한 문장으로 하루의 긴장을 천천히 내려놓을 수 있는 책이에요."

    with pytest.raises(ValueError, match="후보에 없는 book_id"):
        validate_llm_items(
            [
                {"book_id": "FAKE_ID", "reason": valid_reason},
                {"book_id": books[1].book_id, "reason": valid_reason},
                {"book_id": books[2].book_id, "reason": valid_reason},
            ],
            candidates,
        )

    with pytest.raises(ValueError, match="URL"):
        validate_llm_items(
            [
                {"book_id": books[0].book_id, "reason": f"추천 링크 https://example.com 참고 {valid_reason}"},
                {"book_id": books[1].book_id, "reason": valid_reason},
                {"book_id": books[2].book_id, "reason": valid_reason},
            ],
            candidates,
        )


def test_static_cover_mount_and_export_logs(client: TestClient, tmp_path: Path) -> None:
    res = client.get("/static/covers/.gitkeep")
    assert res.status_code == 200

    client.post(
        "/v1/events",
        json={"session_id": "pytest-export", "event_type": "nav_arrived", "book_id": "887231"},
    )
    out_csv = export_table_csv(main_module.db, "session_events", tmp_path)
    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf-8-sig")
    assert "pytest-export" in content
    assert "nav_arrived" in content


def test_bool_depth_rejected_as_invalid_input(client: TestClient) -> None:
    res = client.post(
        "/v1/recommendations",
        json={
            "session_id": "pytest-bool-depth",
            "answers": {"goal": "refresh", "genre": "fiction", "depth": True},
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_INPUT"


def test_openapi_schema_includes_swagger_examples(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    rec_example = schema["components"]["schemas"]["RecommendationBody"]["example"]
    assert rec_example["answers"]["goal"] == "refresh"
    assert rec_example["answers"]["depth"] == 1


def test_gemini_request_uses_header_and_disables_25_thinking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            payload = {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        [
                                            {
                                                "book_id": "887231",
                                                "reason": "차분하게 마음을 다독여 주는 따뜻한 이야기예요.",
                                            }
                                        ],
                                        ensure_ascii=False,
                                    )
                                }
                            ]
                        }
                    }
                ]
            }
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(req, timeout=8.0):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    test_settings = replace(
        main_module.settings,
        llm_provider="gemini",
        llm_api_key="test-key-123",
        llm_model="gemini-2.5-flash",
    )

    items = _call_gemini("test prompt", test_settings)
    assert len(items) == 1
    assert items[0]["book_id"] == "887231"
    assert "key=" not in str(captured["url"])
    headers_lower = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers_lower["x-goog-api-key"] == "test-key-123"
    assert captured["body"]["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 0
