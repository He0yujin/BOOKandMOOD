"""End-to-end integration test verifying the exact contract and flow used by the Android Client."""
from __future__ import annotations

import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import app.main as main_module
from app.db.database import Database
from scripts.seed_db import load_books_from_csv, load_musics_from_csv

YOUTUBE_VIDEO_REGEX = re.compile(r"^[A-Za-z0-9_-]{11}$")


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    test_db = Database(tmp_path / "test_bookmood.db")
    books = load_books_from_csv(BACKEND_DIR / "data" / "books.csv")
    musics = load_musics_from_csv(BACKEND_DIR / "data" / "musics.csv")
    test_db.upsert_books(books)
    test_db.upsert_musics(musics)
    monkeypatch.setattr(main_module, "db", test_db)
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, llm_provider="mock", llm_api_key=""),
    )
    return TestClient(main_module.app)


def test_android_full_user_journey(client: TestClient) -> None:
    session_id = "android-test-session-001"

    # 1. 문진 완료 후 추천 요청 (POST /v1/recommendations)
    rec_req = {
        "session_id": session_id,
        "answers": {
            "goal": "comfort",
            "genre": "fiction",
            "depth": 1,
        },
        "exclude_book_ids": [],
        "feedback_type": None,
        "allow_goal_relaxation": False,
    }
    rec_res = client.post("/v1/recommendations", json=rec_req)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["status"] == "ok"
    assert len(rec_data["recommendations"]) == 3

    # 추천 카드 3개 검증 (Android RecommendationsScreen에서 사용하는 필드)
    for item in rec_data["recommendations"]:
        book = item["book"]
        assert book is not None
        assert book["title"] != ""
        assert book["author"] != ""
        assert book["short_summary"] != ""
        assert book["cover_path"].startswith("/static/covers/")
        assert item["reason"] != ""

        # Android HttpURLConnection 표지 다운로드 시뮬레이션
        cover_res = client.get(book["cover_path"])
        assert cover_res.status_code == 200
        assert len(cover_res.content) > 0

    first_item = rec_data["recommendations"][0]
    selected_book_id = first_item["book_id"]

    # 2. 도서 선택 이벤트 (POST /v1/events)
    ev_sel = client.post(
        "/v1/events",
        json={
            "session_id": session_id,
            "event_type": "book_selected",
            "book_id": selected_book_id,
            "music_id": None,
            "metadata": {},
        },
    )
    assert ev_sel.status_code == 200

    # 3. 도서 상세 및 음악 정보 조회 (GET /v1/books/{book_id})
    detail_res = client.get(f"/v1/books/{selected_book_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["status"] == "ok"
    detail_book = detail_data["book"]
    assert detail_book["book_id"] == selected_book_id
    assert detail_book["call_number"] != ""
    assert detail_book["shelf_label"] != ""
    assert detail_book["poi_id"] != ""
    assert detail_book["summary"] != ""
    assert detail_book["short_summary"] != ""

    # 음악 정보 및 Android playableMusicLink 검증
    music = detail_data["music"]
    assert music is not None
    assert music["youtube_url"].startswith("https://")
    # YouTube URL 검증 (android-client playableMusicLink 정규식과 일치하는지)
    assert "watch?v=" in music["youtube_url"] or "youtu.be/" in music["youtube_url"]
    video_id = music["youtube_url"].split("v=")[-1].split("&")[0]
    assert YOUTUBE_VIDEO_REGEX.match(video_id)

    # 정적 QR 이미지 다운로드 확인 (fallback/asset 경로)
    if music.get("qr_path"):
        qr_res = client.get(music["qr_path"])
        assert qr_res.status_code == 200
        assert len(qr_res.content) > 0

    # 4. QR 표시 이벤트 (POST /v1/events)
    ev_qr = client.post(
        "/v1/events",
        json={
            "session_id": session_id,
            "event_type": "qr_displayed",
            "book_id": selected_book_id,
            "music_id": music["music_id"],
            "metadata": {},
        },
    )
    assert ev_qr.status_code == 200

    # 5. 테미 서가 이동 시작 이벤트 (POST /v1/events)
    ev_nav_start = client.post(
        "/v1/events",
        json={
            "session_id": session_id,
            "event_type": "nav_started",
            "book_id": selected_book_id,
            "music_id": None,
            "metadata": {"poi_id": detail_book["poi_id"]},
        },
    )
    assert ev_nav_start.status_code == 200

    # 6. 테미 서가 도착 이벤트 (POST /v1/events)
    ev_nav_arr = client.post(
        "/v1/events",
        json={
            "session_id": session_id,
            "event_type": "nav_arrived",
            "book_id": selected_book_id,
            "music_id": None,
            "metadata": {"poi_id": detail_book["poi_id"]},
        },
    )
    assert ev_nav_arr.status_code == 200

    # 7. 테미 대기장소 복귀 완료 이벤트 (POST /v1/events)
    ev_home = client.post(
        "/v1/events",
        json={
            "session_id": session_id,
            "event_type": "returned_home",
            "book_id": selected_book_id,
            "music_id": None,
            "metadata": {},
        },
    )
    assert ev_home.status_code == 200

    # 8. 최종 평가 등록 (POST /v1/evaluations)
    eval_res = client.post(
        "/v1/evaluations",
        json={
            "session_id": session_id,
            "top3_satisfied": True,
            "reason_score": 5,
            "music_helpful_score": 5,
            "usability_score": 5,
            "used_rerecommend": False,
        },
    )
    assert eval_res.status_code == 200
    assert eval_res.json()["status"] == "ok"
