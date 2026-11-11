from __future__ import annotations

import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings
from app.db.database import Database


def export_table_csv(db: Database, table_name: str, out_dir: Path) -> Path:
    rows = db.fetch_all_rows(table_name)
    out_path = out_dir / f"{table_name}.csv"
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        if not rows:
            f.write("")
            return out_path
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def main() -> None:
    settings = Settings.from_env()
    db = Database(settings.database_path)
    out_dir = BACKEND_DIR / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    rec_rows = db.fetch_all_rows("recommendation_logs")
    event_rows = db.fetch_all_rows("session_events")
    eval_rows = db.fetch_all_rows("evaluations")

    for table in ("recommendation_logs", "session_events", "evaluations"):
        path = export_table_csv(db, table, out_dir)
        print(f"내보내기 완료: {path}")

    print("\n=== 서비스 평가 요약 ===")
    print(f"- 총 추천 호출 수: {len(rec_rows)}건")
    if rec_rows:
        fallback_cnt = sum(1 for r in rec_rows if r["source"] == "fallback")
        avg_ms = sum(r["latency_ms"] for r in rec_rows) / len(rec_rows)
        print(f"- 폴백 발생률: {fallback_cnt}/{len(rec_rows)}건 (평균 응답 {avg_ms:.0f}ms)")

    nav_started = sum(1 for e in event_rows if e["event_type"] == "nav_started")
    nav_arrived = sum(1 for e in event_rows if e["event_type"] == "nav_arrived")
    print(f"- 서가 주행 기록: 시작 {nav_started}회 / 도착 {nav_arrived}회")

    if eval_rows:
        top3_rate = (
            sum(1 for e in eval_rows if e["top3_satisfied"]) / len(eval_rows) * 100
        )
        avg_reason = sum(e["reason_score"] for e in eval_rows) / len(eval_rows)
        avg_usability = sum(e["usability_score"] for e in eval_rows) / len(eval_rows)
        music_scores = [
            e["music_helpful_score"]
            for e in eval_rows
            if e["music_helpful_score"] is not None
        ]
        avg_music = (
            f"{sum(music_scores) / len(music_scores):.2f}" if music_scores else "응답 없음"
        )
        rerec_rate = (
            sum(1 for e in eval_rows if e["used_rerecommend"]) / len(eval_rows) * 100
        )
        print(f"- 총 평가 수: {len(eval_rows)}명")
        print(f"- Top-3 선택 성공률: {top3_rate:.1f}%")
        print(f"- 추천 이유 적합도 평균: {avg_reason:.2f} / 5.0")
        print(f"- 음악 유용성 평균: {avg_music}")
        print(f"- 이용 편의성 평균: {avg_usability:.2f} / 5.0")
        print(f"- 재추천 사용률: {rerec_rate:.1f}%")
    else:
        print("- 아직 저장된 평가 데이터가 없습니다.")


if __name__ == "__main__":
    main()

