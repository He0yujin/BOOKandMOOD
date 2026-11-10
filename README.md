# 📚 BOOK & MOOD

> **LLM 기반 독서 목적·취향 맞춤형 도서 큐레이션 및 TEMI 서가 안내 서비스**

지금의 나에게 맞는 한 권을 발견하고, 책의 분위기를 음악으로 경험한 뒤, **TEMI V1 모바일 로봇**과 함께 실제 도서관 서가까지 이동하는 온·오프라인 통합 북 큐레이션 서비스입니다.

---

## 1. 기획 배경 및 해결하고자 하는 문제

도서관에는 수많은 책이 있지만, 이용자가 자신의 현재 상태와 독서 목적에 맞는 책을 직접 고르기는 쉽지 않습니다.

* **기존 탐색의 한계:** 제목·저자·베스트셀러 순위만으로는 *"지금 어떤 시간을 보내고 싶은지"*에 맞는 책을 찾기 어렵습니다.
* **공간 탐색의 단절:** 마음에 드는 책을 발견해도 실제 도서관 서가 위치를 다시 찾아 헤매야 합니다.
* **분위기 경험 부재:** 책을 고르기 전에 책이 가진 정서적 분위기와 결을 직관적으로 느끼기 어렵습니다.

**BOOK & MOOD**는 **3문항 문진 → 하이브리드(규칙 + LLM) 도서 3권 추천 → 선택형 음악 QR → TEMI 자율주행 서가 안내**까지 하나의 흐름으로 연결합니다.

---

## 2. 핵심 서비스 흐름

```text
[S00 대기 화면]
   │  터치 시작
   ▼
[S01~S03 사용자 문진 (3문항)]  ── Q1 독서 목적 · Q2 선호 유형 · Q3 독서 깊이
   │
   ▼
[S04~S05 하이브리드 도서 추천] ── 규칙 기반 Top 8 추출 → LLM 3권 선정 & 개인화 추천 이유
   │  ├─ 불만족 시 → [S06 재추천] (유형 변경 / 더 가벼운 책 / 목적 변경 / 이미 읽은 책 제외)
   │  ▼
[S07 도서·음악 상세 화면]     ── 책 소개·청구기호 + 분위기 매칭 연주곡 유튜브 QR (선택 이용)
   │  '서가로 이동하기' 선택
   ▼
[S08~S10 서가 안내 및 복귀]   ── TEMI POI 자율주행 → 도착 안내 → 종료 후 출발 위치 복귀
```

---

## 3. 문진 및 추천 시스템 설계

### 3.1 사용자 문진 (3문항 · 단일 선택)

| 문항 | 질문 | 선택지 (내부 코드) | 분류 기준 |
| --- | --- | --- | --- |
| **Q1** | 책을 통해 어떤 시간을 보내고 싶나요? | 위로와 공감을 얻고 싶어요 (`comfort`)<br>편안하게 쉬고 싶어요 (`rest`)<br>기분을 전환하고 싶어요 (`refresh`)<br>동기부여와 용기를 얻고 싶어요 (`motivate`) | 독서 목적 (`goal`, 최우선 기준) |
| **Q2** | 어떤 종류의 책이 끌리나요? | 이야기에 빠져드는 소설 (`fiction`)<br>공감할 수 있는 에세이 (`essay`)<br>생각을 넓히는 인문·교양 (`humanities`)<br>상관없어요 (`any`) | 선호 도서 유형 (`genre`) |
| **Q3** | 어느 정도 깊이의 책을 원하나요? | 부담 없이 가볍게 읽고 싶어요 (`1`, 단편)<br>깊이 생각하며 읽고 싶어요 (`2`, 장편) | **소설:** 단편소설·소설집 vs 장편소설<br>**에세이·인문·교양:** 274쪽 이하 vs 이상 *(대한출판문화협회 2024 출판생산통계 기준)* |

### 3.2 하이브리드 추천 파이프라인

1. **실소장·주행 검증 필터링:** `active=true`, `holding_verified=true`, `navigation_verified=true` 및 유효한 `poi_id`가 등록된 도서만 후보로 사용합니다.
2. **규칙 기반 후보 점수화 (100점 만점 → 상위 8권 추출):**
   * 독서 목적 일치 `40점` *(주 목적 일치 시 타이브레이킹 가산)* + 도서 유형 일치 `25점` + 독서 깊이 일치 `20점` + 분위기 태그 교집합 최대 `15점`
3. **LLM 최종 큐레이션 & 안전 검증:**
   * LLM은 후보 8권 내에서 서로 다른 3권을 선정하고 각 책의 실제 줄거리(`summary`)·주제(`themes`)에 근거한 개인화 추천 이유(60~100자)를 생성합니다.
   * LLM 응답 오류·타임아웃·후보 외 ID 반환 시 자동 재시도 후 **규칙 기반 상위 3권(`fallback`)**으로 전환되어 서비스가 중단되지 않습니다.
4. **도서 선택 후 음악 매칭:**
   * 선택된 도서의 `mood_tags`와 가사 없는 플레이리스트 DB의 `mood_tags` 교집합이 가장 많은 음악 1개를 QR 코드로 제공합니다. *(도서관 정숙성을 위해 로봇 스피커 자동 재생 금지)*

---

## 4. 레포지토리 구조

```text
BOOKandMOOD/
├── backend/                        # FastAPI 추천 API 서버 (Python)
│   ├── app/
│   │   ├── main.py                 # REST API 엔드포인트 (/v1/recommendations, /v1/books/{id} 등)
│   │   ├── models.py               # 도서·음악·문진 도메인 모델 및 허용 태그 상수
│   │   ├── config.py               # 환경변수(.env) 로드 설정
│   │   ├── db/database.py          # SQLite 스키마 및 CRUD · 로그 적재
│   │   └── services/
│   │       ├── catalog_validator.py # 도서·음악 DB 무결성 검증기
│   │       ├── recommender.py      # 규칙 기반 점수 계산 · 후보 추출 · 음악 매칭
│   │       └── llm_client.py       # LLM(Mock / OpenAI / Gemini) 호출 · 검증 · 폴백
│   ├── data/
│   │   ├── sample_books_48.csv     # 개발용 48권 샘플 도서 데이터
│   │   └── sample_musics.csv       # 샘플 연주곡 플레이리스트 6개
│   ├── scripts/seed_db.py          # CSV → SQLite DB 적재 스크립트
│   ├── tests/test_api.py           # pytest API 자동 테스트
│   ├── requirements.txt
│   └── .env.example
├── android-client/                 # TEMI Android 앱 연동용 Kotlin Retrofit2 클라이언트 키트
│   ├── Android(Kotlin) 백엔드 API 연동 가이드.md  # Android Studio 연동 가이드
│   └── network/
│       ├── BookMoodModels.kt       # 요청/응답 DTO
│       ├── BookMoodApiService.kt   # Retrofit2 API 인터페이스
│       └── BookMoodClient.kt       # 네트워크 호출 및 오류 파싱 래퍼
├── BOOK & MOOD 도서DB_기분전환_12권.csv
├── BOOK & MOOD 최종기획서 .md
├── BOOK & MOOD 개발명세서.md
└── BOOK & MOOD 백엔드 개발 가이드.md
```

---

## 5. 백엔드 실행 및 테스트 방법

```bash
# 1. 백엔드 폴더 이동 및 패키지 설치
cd backend
pip3 install -r requirements.txt

# 2. 샘플 도서(48권)·음악(6개) CSV를 SQLite DB로 적재
python3 scripts/seed_db.py

# 3. API 서버 실행 (Swagger 문서: http://127.0.0.1:8000/docs)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 자동 테스트 실행
pytest
```

### 실제 LLM API 연결 시 (선택)
`backend/.env.example`을 복사해 `backend/.env`를 생성한 뒤 API 키를 입력하면 코드 수정 없이 실제 모델로 전환됩니다.

```env
LLM_PROVIDER=gemini          # mock | openai | gemini
LLM_API_KEY=your_api_key_here
LLM_MODEL=gemini-2.5-flash
```
