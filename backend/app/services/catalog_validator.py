from __future__ import annotations

from app.models import (
    Book,
    Music,
    VALID_BOOK_GENRES,
    VALID_DEPTHS,
    VALID_GOALS,
    VALID_MOOD_TAGS,
)


def validate_books_catalog(books: list[Book]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    for idx, b in enumerate(books, start=1):
        prefix = f"[{b.book_id or f'row#{idx}'}]"
        if not b.book_id.strip():
            errors.append(f"{prefix} book_id가 비어 있습니다.")
        elif b.book_id in seen_ids:
            errors.append(f"{prefix} 중복된 book_id입니다.")
        seen_ids.add(b.book_id)

        if not b.title.strip():
            errors.append(f"{prefix} title이 비어 있습니다.")
        if not b.author.strip():
            errors.append(f"{prefix} author가 비어 있습니다.")
        if b.genre not in VALID_BOOK_GENRES:
            errors.append(
                f"{prefix} 허용되지 않은 genre='{b.genre}' (허용: {VALID_BOOK_GENRES})"
            )
        if not b.summary.strip():
            errors.append(f"{prefix} summary가 비어 있습니다.")
        if not b.themes:
            errors.append(f"{prefix} themes가 최소 1개 이상 필요합니다.")

        if not (2 <= len(b.mood_tags) <= 3):
            errors.append(f"{prefix} mood_tags는 2~3개여야 합니다 (현재 {len(b.mood_tags)}개).")
        invalid_moods = [t for t in b.mood_tags if t not in VALID_MOOD_TAGS]
        if invalid_moods:
            errors.append(f"{prefix} 허용되지 않은 mood_tags: {invalid_moods}")

        if not (1 <= len(b.goal_tags) <= 3):
            errors.append(f"{prefix} goal_tags는 1~3개여야 합니다 (현재 {len(b.goal_tags)}개).")
        invalid_goals = [g for g in b.goal_tags if g not in VALID_GOALS]
        if invalid_goals:
            errors.append(f"{prefix} 허용되지 않은 goal_tags: {invalid_goals}")

        if b.depth not in VALID_DEPTHS:
            errors.append(f"{prefix} depth는 1 또는 2여야 합니다 (현재 {b.depth}).")
        if not b.depth_reason.strip():
            errors.append(f"{prefix} depth_reason이 비어 있습니다.")

        if b.page_count is not None and b.page_count <= 0:
            errors.append(f"{prefix} page_count는 양수여야 합니다.")

        if b.active:
            if not b.holding_verified:
                errors.append(f"{prefix} active=true인데 holding_verified=false입니다.")
            if not b.navigation_verified:
                errors.append(f"{prefix} active=true인데 navigation_verified=false입니다.")
            if not b.call_number.strip():
                errors.append(f"{prefix} active=true인데 call_number가 비어 있습니다.")
            if not b.shelf_label.strip():
                errors.append(f"{prefix} active=true인데 shelf_label이 비어 있습니다.")
            if not b.poi_id.strip():
                errors.append(f"{prefix} active=true인데 poi_id가 비어 있습니다.")

    return errors


def validate_musics_catalog(musics: list[Music]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    for idx, m in enumerate(musics, start=1):
        prefix = f"[{m.music_id or f'row#{idx}'}]"
        if not m.music_id.strip():
            errors.append(f"{prefix} music_id가 비어 있습니다.")
        elif m.music_id in seen_ids:
            errors.append(f"{prefix} 중복된 music_id입니다.")
        seen_ids.add(m.music_id)

        if not m.title.strip():
            errors.append(f"{prefix} title이 비어 있습니다.")
        if not m.mood_tags:
            errors.append(f"{prefix} mood_tags가 최소 1개 이상 필요합니다.")
        invalid_moods = [t for t in m.mood_tags if t not in VALID_MOOD_TAGS]
        if invalid_moods:
            errors.append(f"{prefix} 허용되지 않은 mood_tags: {invalid_moods}")
        if not m.style.strip():
            errors.append(f"{prefix} style이 비어 있습니다.")
        if m.active:
            if not m.is_instrumental_verified:
                errors.append(f"{prefix} active=true인데 is_instrumental_verified=false입니다.")
            if not m.url_verified:
                errors.append(f"{prefix} active=true인데 url_verified=false입니다.")
            if not m.youtube_url.startswith(("https://", "http://")):
                errors.append(f"{prefix} active=true인데 youtube_url 형식이 올바르지 않습니다.")

    return errors
