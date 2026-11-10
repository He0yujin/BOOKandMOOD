from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings
from app.db.database import Database
from app.models import Book, Music
from app.services.catalog_validator import (
    validate_books_catalog,
    validate_musics_catalog,
)


def parse_list(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    if text.startswith("["):
        return [str(x).strip() for x in json.loads(text) if str(x).strip()]
    return [x.strip() for x in text.split("|") if x.strip()]


def parse_bool(raw: str) -> bool:
    return (raw or "").strip().lower() in {"true", "1", "yes", "y"}


def load_books_from_csv(csv_path: Path, dev_activate: bool = False) -> list[Book]:
    books: list[Book] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            page_raw = (row.get("page_count") or "").strip()
            poi_id = (row.get("poi_id") or "").strip()
            holding = parse_bool(row.get("holding_verified", ""))
            nav = parse_bool(row.get("navigation_verified", ""))
            active = parse_bool(row.get("active", ""))

            if dev_activate:
                poi_id = poi_id or "SHELF_DEV_TEST"
                holding = True
                nav = True
                active = True

            books.append(
                Book(
                    book_id=row["book_id"].strip(),
                    title=row["title"].strip(),
                    author=row["author"].strip(),
                    genre=row["genre"].strip(),
                    summary=row["summary"].strip(),
                    themes=parse_list(row["themes"]),
                    mood_tags=parse_list(row["mood_tags"]),
                    goal_tags=parse_list(row["goal_tags"]),
                    depth=int(row["depth"]),
                    depth_reason=row["depth_reason"].strip(),
                    page_count=int(page_raw) if page_raw else None,
                    call_number=(row.get("call_number") or "").strip(),
                    shelf_label=(row.get("shelf_label") or "").strip(),
                    poi_id=poi_id,
                    cover_path=(row.get("cover_path") or "").strip(),
                    holding_verified=holding,
                    navigation_verified=nav,
                    active=active,
                )
            )
    return books


def load_musics_from_csv(csv_path: Path) -> list[Music]:
    musics: list[Music] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            priority_raw = (row.get("priority") or "").strip()
            musics.append(
                Music(
                    music_id=row["music_id"].strip(),
                    title=row["title"].strip(),
                    mood_tags=parse_list(row["mood_tags"]),
                    style=row["style"].strip(),
                    youtube_url=row["youtube_url"].strip(),
                    is_instrumental_verified=parse_bool(
                        row.get("is_instrumental_verified", "")
                    ),
                    url_verified=parse_bool(row.get("url_verified", "")),
                    active=parse_bool(row.get("active", "")),
                    priority=int(priority_raw) if priority_raw else 100,
                )
            )
    return musics


def main() -> None:
    parser = argparse.ArgumentParser(description="BOOK & MOOD CSV → SQLite 적재")
    parser.add_argument(
        "--books-csv",
        type=Path,
        default=BACKEND_DIR / "data" / "sample_books_48.csv",
    )
    parser.add_argument(
        "--musics-csv",
        type=Path,
        default=BACKEND_DIR / "data" / "sample_musics.csv",
    )
    parser.add_argument(
        "--dev-activate",
        action="store_true",
        help="미검증 도서도 개발 테스트용으로 임시 활성화하여 적재",
    )
    args = parser.parse_args()

    books = load_books_from_csv(args.books_csv, dev_activate=args.dev_activate)
    musics = load_musics_from_csv(args.musics_csv)

    errors = validate_books_catalog(books) + validate_musics_catalog(musics)
    if errors:
        print("카탈로그 검증 실패:")
        for err in errors:
            print(" -", err)
        sys.exit(1)

    settings = Settings.from_env()
    db = Database(settings.database_path)
    book_count = db.upsert_books(books)
    music_count = db.upsert_musics(musics)
    print(f"적재 완료: 도서 {book_count}권, 음악 {music_count}개 -> {settings.database_path}")


if __name__ == "__main__":
    main()

