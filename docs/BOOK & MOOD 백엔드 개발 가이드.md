# BOOK & MOOD 백엔드 개발 가이드

> **기준 문서:** `BOOK & MOOD 최종기획서 (1).md`, `BOOK & MOOD 개발명세서.md`  
> **대상 환경:** 광운대학교 중앙도서관 L층 인문자료실 / TEMI V1 Android 앱 연동 API 서버  
> **담당 영역:** 추천 API 서버, 규칙 기반 후보 추출·점수화, LLM 연동·검증·폴백, 재추천, 도서/음악 DB 조회·매칭, 세션·평가 로깅

---

## 1. 백엔드 역할 및 책임 범위 (Scope)

전체 시스템은 다음과 같이 분리된다.

```text
[TEMI Android 앱 (Kotlin + TEMI SDK)]
        │  HTTPS (JSON REST API)
        ▼
[추천 API 서버 (백엔드)]  ◀── 내가 개발하는 영역
   ├── 도서 DB / 음악 DB / 세션·평가 로그 DB
   ├── 규칙 기반 필터링 & 점수 엔진 (상위 최대 8권 추출)
   ├── LLM API 연동 & 응답 검증 & 폴백 엔진 (최종 3권 선정)
   └── 도서 상세 & 음악 매칭 엔진 (LLM 미사용)
```

### 1.1 백엔드가 직접 구현해야 하는 것
1. **API 서버 구축 및 배포**: TEMI Android 앱과 통신할 REST API 서버 (도서관 Wi-Fi에서 접근 가능한 HTTPS 엔드포인트 권장)
2. **도서/음악 데이터 파이프라인**: 기획·DB팀이 넘겨줄 실소장 도서(20권 목표) 및 유튜브 플레이리스트(6~8개) 데이터 정합성 검증 및 적재
3. **추천 엔진 (`POST /v1/recommendations`)**:
   - 문진 입력 검증 (`mood`, `goal`, `genre`, `depth`)
   - 활성·소장·주행 검증 완료 도서 필터링
   - 독서 목적(`goal`) 우선 필터링 및 부족 시 안내/완화 처리
   - 규칙 기반 100점 점수 산정 및 상위 최대 8권 추출
   - LLM 호출을 통한 최종 3권 선정 및 개인화 추천 이유(60~100자) 생성
   - LLM 결과 2중 검증(존재 ID, 중복, 형식, 할루시네이션 차단) 및 실패 시 규칙 기반 폴백
4. **재추천 로직**: 불만족 사유(`different_genre`, `lighter`, `different_mood`, `already_read`) 및 제외 도서 목록 반영
5. **도서 상세 및 음악 매칭 API**: 선택된 도서의 서지·위치 정보(`call_number`, `shelf_label`, `poi_id`)와 `mood_tags` 교집합 기반 음악 매칭 결과 반환
6. **보안 및 로깅**: LLM API 키 서버 환경변수 격리, 개인정보 미수집 원칙 준수, 사용자 평가 지표(기획서 12장) 수집용 로그 저장

### 1.2 백엔드 범위 밖 (타 파트 담당)
- **Android / UI**: 문진·추천·상세·QR 렌더링·눈동자 애니메이션 (`Kotlin`)
- **TEMI SDK 제어**: `poi_id` 존재 여부 확인, `goTo()`, 주행 상태 이벤트 수신, 출발 위치 복귀 (단, 백엔드는 `navigation_verified=true`인 도서와 정확한 `poi_id`만 제공)
- **콘텐츠 선정**: 실소장 도서 20권 선정/태그 작성, 유튜브 가사 없는 플레이리스트 6~8개 검증

### 1.3 절대 원칙 (개발명세서 1.1, 5.6, 7.4)
- **LLM은 오직 후보(최대 8권) 중 3권 선정과 추천 이유 작성만 담당한다.** 도서관 위치(`poi_id`, `call_number`), 유튜브 URL, QR, 로봇 이동 명령은 LLM이 생성하지 않으며 반드시 검증된 DB 값을 내려준다.
- **미검증 도서(`active=false` 또는 `holding_verified=false` 또는 `navigation_verified=false`)는 절대 추천 후보에 포함하지 않는다.**
- **LLM API 키는 절대 Android 앱에 전달/저장하지 않는다.**
- **이름·학번·로그인 정보 등 개인정보는 MVP에서 수집하지 않는다.**

---

## 2. 개발 착수 전 팀과 먼저 합의해야 할 5가지 불일치·미확정 사항

`최종기획서`와 `개발명세서` 사이에 충돌하거나 API 명세에 빠져 있는 부분이 있다. 백엔드 코드를 짜기 전에 **기획·Android 팀과 아래 5가지를 먼저 확정**해야 재작업을 막을 수 있다.

### 이슈 1. 문진 문항 수 및 선택지 불일치
- **현황:**
  - `최종기획서` 04장·09장은 "4문항(감정·목적·유형·강도)"이라 적혀 있으나, 05장 실제 문항에는 **3문항(목적·유형·강도)**만 있고, Q1(목적)에 `learn(지식/관점)`이 없으며, Q2(유형)에 `selfhelp(자기계발)`가 없고, Q3(강도)가 `단편(274쪽 이하)/장편(274쪽 이상)` 2지선다로 적혀 있다.
  - `개발명세서` 02장에는 **4문항(`mood` 5종, `goal` 5종, `genre` 5종, `depth` 4종 `1|2|3|any`)**으로 명확히 정의되어 있다.
- **백엔드 조치:** `개발명세서` 02장 기준(4문항)으로 API를 설계하되, 기획/Android 팀에 **실제 앱에서 Q1(`mood`)을 받는지, `learn`/`selfhelp`/`depth(1·2·3·any)`를 그대로 쓰는지** 최종 확인받을 것.

### 이슈 2. `depth` 자료형 및 도서 목표 권수 통일
- **현황:** `개발명세서` 2.2 표에는 `depth` 저장값이 `1`, `2`, `3`, `any`이고, 2.3 JSON 예시에는 숫자 `1`로 되어 있다. 도서 권수도 `최종기획서` 일부는 `50~60권`, 명세서는 `20권`으로 적혀 있다.
- **백엔드 조치:**
  - Request의 `answers.depth`는 서버가 숫자 `1, 2, 3`과 문자열 `"1", "2", "3", "any"`를 모두 유연하게 파싱(또는 `"1"|"2"|"3"|"any"` 문자열로 Android와 계약 통일)하도록 구현한다.
  - DB는 권수에 무관하게 동작하게 하되, **20권 규모에서는 특정 조건 + 제외 목록 조합 시 3권 미만 부족 상황이 자주 발생**하므로 부족 예외/완화 흐름을 철저히 구현해야 한다.

### 이슈 3. 추천 응답 API에 도서 상세·음악 정보 포함 범위 누락
- **현황:** `개발명세서` 7.2 `POST /v1/recommendations` 응답 예시에는 `{ "book_id": "B001", "reason": "..." }`만 있고, 제목·저자·표지·소개·청구기호·서가명·`poi_id`·매칭 음악(`youtube_url`)을 앱이 어디서 가져오는지 엔드포인트가 빠져 있다.
- **백엔드 조치 (둘 중 하나 Android와 합의 — 옵션 A 권장):**
  - **옵션 A (추천):** `POST /v1/recommendations` 응답 각 항목에 카드 표시에 필요한 기본 도서 정보(`title`, `author`, `genre`, `depth`, `cover_url`)를 함께 내려주고, 도서 1권 선택 시 호출하는 **`GET /v1/books/{book_id}`** (또는 `GET /v1/books/{book_id}?include_music=true`)에서 전체 `summary`, `call_number`, `shelf_label`, `poi_id`, **자동 매칭된 `music` 객체**를 반환한다.
  - **표지 이미지(`cover_path`)**: 서버 `/static/covers/B001.jpg` 정적 URL로 서빙할지, 앱 내 로컬 리소스명(`cover_b001`)으로 약속할지 Android 팀과 확정한다.

### 이슈 4. 재추천 피드백 처리 주체 (`different_genre`, `different_mood`, `lighter`)
- **현황:** `개발명세서` 6.2에는 `different_genre`("장르 선호 변경 또는 재선택"), `different_mood`("독서 목적 재선택"), `lighter`("희망 독서 강도 한 단계 하향"), `already_read`("해당 도서 ID 제외")로 정의되어 있다.
- **확정할 계약:**
  1. `different_genre` / `different_mood` 선택 시 앱(S07)이 새 선택지를 입력받아 `answers`를 갱신해 보내는지, 아니면 서버가 기존 `genre`/`goal`을 자동으로 다른 값으로 우회할지 정해야 한다. (**권장:** `different_genre`나 `different_mood`를 앱에서 재선택하지 않고 바로 요청한다면, 서버가 기존 `genre`와 다른 책에 가산점을 주거나 기존 노출 3권을 `exclude_book_ids`로 빼고 재추천; 앱이 S07에서 새 값을 선택한다면 `answers`를 바꿔 보내기)
  2. `lighter` 요청 시 현재 `depth`가 `3 -> 2`, `2 -> 1`, `"any" -> 1`로 내리면 되지만, **이미 `depth == 1`인 경우**가 문제다. 이때는 기존 추천 3권을 `exclude_book_ids`에 포함시켜 다른 가벼운 책을 찾거나, 없으면 `NO_MORE_BOOKS`를 반환하도록 처리한다.
  3. **재추천 시 기존 3권 제외 규칙(6.3):** `already_read`는 읽은 책만 제외할 수도 있고, 전체 재추천 시 직전 노출된 3권을 모두 제외해야 하므로 앱이 누적된 `exclude_book_ids`를 요청에 실어 보내도록 규약화한다(서버도 `session_id` 기준으로 직전 노출 이력을 참고할 수 있으나 Stateless API가 테스트·디버깅에 유리함).

### 이슈 5. 유사 목적 완화(`allow_goal_relaxation: true`) 규칙 & 음악 우선순위 필드
- **현황:** 명세서 5.2에서 `goal` 일치 도서가 3권 미만일 때 사용자 동의 후 유사 목적 포함(`allow_goal_relaxation: true`)을 허용하지만, 어떤 목적이 서로 유사한지 매핑이 미정의 상태다. 또한 4.3에서 음악 매칭 동점 시 "미리 설정한 우선순위 적용"이라 했으나 4.1 테이블에 `priority` 필드가 없다.
- **백엔드 조치:**
  - 유사 목적 매핑표를 백엔드 설정에 명시적으로 정의한다 (예시 아래 5.2절 참고, 기획팀과 컨펌).
  - `musics` 테이블에 `priority` (Integer, 숫자가 작을수록 우선) 필드를 추가한다.

---

## 3. 권장 기술 스택 및 프로젝트 구조

초기 도서가 20~60권, 음악이 6~8개, 동시 접속이 TEMI 1~수 대 수준인 MVP이므로 **개발 속도가 빠르고, JSON 스키마 검증과 Swagger API 문서 자동 공유가 쉬운 스택**이 유리하다.

### 3.1 권장 스택 (Python FastAPI 기준)
- **Framework:** `FastAPI` (비동기 HTTP 처리, Pydantic 기반 요청/응답 엄격 검증, `/docs` Swagger 자동 생성으로 Android 팀과 즉시 협업 가능)
- **Language:** Python 3.11+
- **DB:**
  - **카탈로그(도서/음악):** 초기 20~60권은 **JSON/CSV 파일로 버전 관리(`catalog_v1.json`) + 서버 기동 시 검증 후 메모리/SQLite 로드** 방식 권장 (Git으로 수정 이력 추적 및 기획팀 CSV 임포트가 매우 쉬움)
  - **세션·추천 로그·사용자 평가:** `SQLite` (파일 기반, 별도 DB 서버 세팅 불필요, 추후 PostgreSQL로 전환 용이)
- **LLM SDK:** OpenAI (`gpt-4o-mini` 등) 또는 Google Gemini (`gemini-2.5-flash` 등) — **JSON Schema / Structured Outputs 지원 모델** 선택 (응답 지연 최소화 및 파싱 에러 방지)
- **HTTP/테스트:** `pytest`, `httpx`
- **배포:** Render / Railway / Fly.io / AWS EC2 중 택 1 (HTTPS 자동 지원 PaaS인 Railway 또는 Render가 초기 세팅에 가장 빠름)

> 팀에서 Spring Boot나 Node.js(Express/NestJS)에 더 익숙하다면 해당 스택을 사용해도 무방하며, 아래 데이터 모델·알고리즘·API 계약은 언어 독립적으로 그대로 적용된다.

### 3.2 권장 디렉토리 구조

```text
book-and-mood-backend/
├── app/
│   ├── main.py                  # FastAPI 앱 엔트리, CORS, 정적 파일(/static) 마운트
│   ├── config.py                # 환경변수(.env) 로드 (LLM_API_KEY, TIMEOUT 등)
│   ├── api/
│   │   ├── health.py            # GET /health
│   │   ├── recommendations.py   # POST /v1/recommendations
│   │   ├── books.py             # GET /v1/books, GET /v1/books/{book_id}
│   │   └── events.py            # POST /v1/events, POST /v1/evaluations
│   ├── schemas/
│   │   ├── recommendation.py    # Request/Response/Error Pydantic 모델
│   │   ├── book.py
│   │   ├── music.py
│   │   └── evaluation.py
│   ├── services/
│   │   ├── catalog_loader.py    # 도서/음악 JSON 로드 및 무결성 검증
│   │   ├── scoring_engine.py    # 1~3단계 필터링 & 100점 규칙 점수 계산
│   │   ├── llm_recommender.py   # LLM 프롬프트 구성, 호출, 타임아웃, 재시도
│   │   ├── response_validator.py# LLM 출력 2중 검증 + 규칙 기반 Fallback
│   │   ├── music_matcher.py     # mood_tags 교집합 기반 음악 매칭
│   │   └── logger_service.py    # SQLite 세션/추천/평가 로그 저장
│   └── db/
│       ├── database.py          # SQLite 연결 및 테이블 초기화
│       └── seed_data/
│           ├── books.json       # 검증된 도서 DB (catalog_version 관리)
│           └── musics.json      # 검증된 음악 DB
├── scripts/
│   ├── import_csv.py            # 기획팀 CSV/시트 → JSON 변환기
│   └── validate_catalog.py      # 태그/필수필드/URL/POI 사전 검증 CLI
├── static/
│   └── covers/                  # 도서 표지 이미지 (서버 서빙 시)
├── tests/
│   ├── test_scoring.py          # 규칙 점수 & 동점 & 목적 부족 테스트
│   ├── test_validator.py        # LLM 오답/할루시네이션 차단 & 폴백 테스트
│   ├── test_music_matcher.py    # 음악 매칭 & 예외 테스트
│   └── test_api.py              # 엔드포인트 통합 테스트
├── .env.example
└── requirements.txt
```

### 3.3 환경변수 (`.env`)
```ini
APP_ENV=development
CATALOG_VERSION=v1
LLM_PROVIDER=openai           # 또는 gemini
LLM_API_KEY=sk-...            # 절대 Git 커밋 금지 (.gitignore 등록)
LLM_MODEL=gpt-4o-mini         # 또는 gemini-2.5-flash
LLM_TIMEOUT_SEC=8.0
LLM_MAX_RETRIES=1
DATABASE_URL=sqlite:///./data/bookmood.db
```

---

## 4. 데이터베이스 및 데이터 모델 설계

### 4.1 도서 테이블 / 스키마 (`books`) — 개발명세서 3.2 기준

| 필드명 | 타입 | 필수 | 허용값 / 제약조건 | 비고 |
| --- | --- | --- | --- | --- |
| `book_id` | `str` | O | 고유 ID (예: `B001`) | PK |
| `title` | `str` | O | 빈 문자열 불가 | |
| `author` | `str` | O | 빈 문자열 불가 | |
| `genre` | `str` | O | `fiction`, `essay`, `humanities`, `selfhelp` | 주 장르 |
| `summary` | `str` | O | 검증된 줄거리 (LLM 근거 자료) | 너무 길면 토큰 낭비(200~400자 권장) |
| `themes` | `list[str]` | O | 최소 1개 이상 | 주요 주제 키워드 |
| `mood_tags` | `list[str]` | O | 2~3개, 지정 10종 태그만 허용 | 아래 10종 enum 검증 |
| `goal_tags` | `list[str]` | O | 1~3개, 지정 5종 enum만 허용 | `comfort`, `rest`, `refresh`, `learn`, `motivate` |
| `depth` | `int` | O | `1`, `2`, `3` 중 하나 | 1:가벼움, 2:보통, 3:깊이 있음 |
| `depth_reason` | `str` | O | 강도 분류 근거 | |
| `page_count` | `int \| null` | X | 양의 정수 | 선택 필드 |
| `call_number` | `str` | O* | 실제 도서관 청구기호 | `active=true`면 필수 |
| `shelf_label` | `str` | O* | 화면 표시용 서가명 | `active=true`면 필수 |
| `poi_id` | `str` | O* | TEMI 지도 POI 이름과 대소문자까지 정확히 일치 | `active=true`면 필수 |
| `cover_path` | `str` | O* | 이미지 URL 또는 리소스 키 | |
| `holding_verified` | `bool` | O | `true` / `false` | 소장 확인 |
| `navigation_verified` | `bool` | O | `true` / `false` | TEMI 실주행 검증 |
| `active` | `bool` | O | `true` / `false` | 미검증 도서는 반드시 `false` |

> **허용 `mood_tags` 10종 (명세서 3.3):**  
> `따뜻함`, `위로`, `평온함`, `설렘`, `활력`, `희망`, `유쾌함`, `쓸쓸함`, `긴장감`, `신비로움`  
> 오탈자(`따듯함` 등)로 매칭이 깨지지 않도록 `validate_catalog.py`에서 Enum으로 강제 검증할 것!

### 4.2 음악 테이블 / 스키마 (`musics`) — 개발명세서 4.1 + 보완

| 필드명 | 타입 | 필수 | 허용값 / 제약조건 | 비고 |
| --- | --- | --- | --- | --- |
| `music_id` | `str` | O | 고유 ID (예: `M001`) | PK |
| `title` | `str` | O | 플레이리스트 제목 | |
| `mood_tags` | `list[str]` | O | 지정 10종 태그 중 1개 이상 | 도서 `mood_tags`와 동일 체계 |
| `style` | `str` | O | 피아노, 재즈, 앰비언트 등 | 화면 표시용 |
| `youtube_url` | `str` | O | `https://...` 유효 URL | QR 생성 대상 |
| `is_instrumental_verified` | `bool` | O | 가사 없음 검증 여부 | |
| `url_verified` | `bool` | O | 모바일 재생/광고 점검 여부 | |
| `active` | `bool` | O | 서비스 사용 가능 여부 | |
| `priority` | `int` | O | **보완 필드** (기본 `100`, 낮을수록 우선) | 명세서 4.3 동점 시 타이브레이커 |

### 4.3 세션 · 추천 로그 · 사용자 평가 테이블 (SQLite — 기획서 12장 지표용)

MVP에서는 개인정보(이름/학번)를 수집하지 않고 `session_id`(앱에서 생성한 UUID) 기준으로만 익명 이벤트를 적재한다.

- **`recommendation_logs`**:
  - `id`, `session_id`, `created_at`, `catalog_version`
  - `answers_json` (`mood`, `goal`, `genre`, `depth`)
  - `exclude_book_ids_json`, `feedback_type`, `allow_goal_relaxation`, `attempt_no` (최초=1, 재추천=2+)
  - `candidate_book_ids_json` (최대 8권), `recommended_json` (최종 3권 + `reason`)
  - `source` (`llm` | `fallback` | `error`), `error_code`, `latency_ms`
- **`session_events`** (선택·주행 추적):
  - `id`, `session_id`, `event_type` (`book_selected`, `qr_displayed`, `nav_started`, `nav_arrived`, `nav_failed`, `returned_home`), `book_id`, `music_id`, `metadata_json`, `created_at`
- **`evaluations`** (S11 종료 화면 평가 데이터):
  - `id`, `session_id`, `top3_satisfied` (bool — Top-3 중 읽고 싶은 책 1권 이상 유무), `reason_score` (1~5), `music_helpful_score` (1~5, nullable), `usability_score` (1~5), `used_rerecommend` (bool), `created_at`

이 3개 테이블을 CSV로 덤프하면 기획서 12.2의 7개 지표(Top-3 선택 성공률, 추천 이유 적합도, 재추천 필요율, 최종 도서 선택률, 음악 유용성, 서가 안내 성공률, 이용 편의성)를 자동으로 산출할 수 있다.

---

## 5. 핵심 비즈니스 로직 상세 구현 가이드

### 5.1 1단계 — 입력 검증 및 추천 가능 도서 필터링

1. **입력 검증 (`INVALID_INPUT`)**:
   - `mood` ∈ `{tired, overwhelmed, calm, energetic, neutral}`
   - `goal` ∈ `{comfort, rest, refresh, learn, motivate}`
   - `genre` ∈ `{fiction, essay, humanities, selfhelp, any}`
   - `depth` ∈ `{1, 2, 3, "1", "2", "3", "any"}` (내부적으로 `"any"` 또는 정수 `1|2|3`으로 정규화)
   - 누락되거나 허용 외 값이면 즉시 `INVALID_INPUT` 반환 (LLM 호출 안 함).

2. **활성 카탈로그 필터링**:
   ```python
   eligible_books = [
       b for b in all_books
       if b.active and b.holding_verified and b.navigation_verified
       and bool(b.poi_id) and bool(b.call_number)
   ]
   ```
   - `len(eligible_books) < 3` 이면 → **`CATALOG_INSUFFICIENT`** 반환.

3. **제외 도서(`exclude_book_ids`) 반영**:
   ```python
   available_books = [b for b in eligible_books if b.book_id not in exclude_book_ids]
   ```
   - 만약 `len(available_books) < 3` 이면 → **`NO_MORE_BOOKS`** 반환 (재추천 도중 소진된 경우).

### 5.2 2단계 — 독서 목적(`goal`) 우선 필터링

```python
goal_matched = [b for b in available_books if answers.goal in b.goal_tags]
```

- **분기 A (`len(goal_matched) >= 3`):** `goal_matched`를 후보 풀로 사용하여 3단계(점수 계산) 진행.
- **분기 B (`len(goal_matched) < 3` AND `allow_goal_relaxation == false`):**
  - 이용자가 동의하지 않은 상태에서 다른 목적 책을 임의로 추천하면 안 됨(명세서 5.2).
  - **`GOAL_COVERAGE_INSUFFICIENT`** 반환. (앱은 "다른 목적 선택" 또는 "유사 목적 도서 포함해서 다시 추천받기" UI를 띄우고, 동의 시 `allow_goal_relaxation: true`로 재요청)
- **분기 C (`len(goal_matched) < 3` AND `allow_goal_relaxation == true`):**
  - 유사 목적 매핑 테이블(팀 합의 필요)에 따라 후보 풀 확장:
    ```python
    SIMILAR_GOALS = {
        "comfort": ["rest", "motivate"],
        "rest": ["comfort", "refresh"],
        "refresh": ["rest", "motivate"],
        "learn": ["motivate", "refresh"],
        "motivate": ["learn", "comfort"],
    }
    ```
  - `goal_matched`에 `SIMILAR_GOALS[answers.goal]`이 포함된 책들을 추가하여 3권 이상 확보.
  - 그래도 `available_books` 내 합계가 3권 미만이면 → **`NO_MORE_BOOKS`** 반환.

### 5.3 3단계 — 규칙 기반 점수 계산 (100점 만점, 상위 최대 8권 추출)

개발명세서 5.3과 5.4를 그대로 코드화한다.

1. **목적별 우선 분위기 매핑표 (`GOAL_MOOD_MAP`, 명세서 5.4):**
   - `comfort` → `{"위로", "따뜻함", "희망"}`
   - `rest` → `{"평온함", "따뜻함"}`
   - `refresh` → `{"활력", "유쾌함", "설렘", "신비로움"}`
   - `learn` → 분위기 제한 없음 (일괄 15점)
   - `motivate` → `{"희망", "활력"}`

2. **점수 계산 공식 (총점 100점):**
   - **독서 목적 (`40점`)**: `answers.goal in book.goal_tags` 이면 `40`, 아니면(완화 모드에서 유사 목적일 때) `0` (또는 유사 목적 가산점 별도 구분은 동점 정렬 시 활용; 기본 규칙은 일치 40 / 불일치 0)
   - **도서 유형 (`25점`)**: `answers.genre == "any"` 이거나 `answers.genre == book.genre` 이면 `25`, 아니면 `0`
   - **독서 강도 (`20점`)**: `answers.depth == "any"` 이면 `20`, 아니면 `diff = abs(int(answers.depth) - book.depth)` 계산 후 `diff == 0 -> 20`, `diff == 1 -> 10`, `diff == 2 -> 0`
   - **분위기 적합성 (`15점`)**: `answers.goal == "learn"` 이면 `15`, 아니면 `overlap = len(set(book.mood_tags) & GOAL_MOOD_MAP[answers.goal])` 계산 후 `overlap >= 2 -> 15`, `overlap == 1 -> 8`, `overlap == 0 -> 0`

3. **정렬 및 상위 8권 추출 (Tie-breaker 포함):**
   - 정렬 기준: `(total_score DESC, goal_exact_match DESC, genre_match DESC, depth_match DESC, mood_overlap DESC, book_id ASC)` (또는 동일 점수 그룹 내에서는 약간의 다양성을 위해 `book_id` 고정 대신 세션별 결정적 시드 셔플을 적용할 수도 있음 — **단, 재추천 및 테스트 재현성을 위해 기본은 결정적 정렬 권장**).
   - 정렬 후 **상위 최대 8권 (`candidates[:8]`)** 추출.

### 5.4 4단계 — LLM 추천 + 2중 검증 + 폴백 파이프라인

#### (1) LLM에 전달할 입력 구성 (명세서 5.5)
- `answers`: 4개 문항 응답 (`mood`, `goal`, `genre`, `depth`) — 특히 규칙 점수 계산에 직접 쓰이지 않은 **`mood`(현재 감정)**를 LLM이 읽고 톤앤매너와 추천 이유에 자연스럽게 반영하도록 전달!
- `feedback_context` (재추천인 경우): 예) `"사용자가 이전 추천에 대해 '더 가벼운 책(lighter)'을 원한다고 피드백함"`
- `candidates` (최대 8권):
  - `book_id`, `title`, `author`, `genre`, `depth`, `depth_reason`, `summary`, `themes`, `mood_tags`, `goal_tags`, `rule_score`
  - **주의:** `poi_id`, `call_number`, `shelf_label`, `youtube_url` 등 로봇/링크 정보는 프롬프트에 아예 넣지 않는 것이 할루시네이션 원천 차단에 가장 안전하다!

#### (2) LLM 프롬프트 & Structured Output 제약
- LLM API의 JSON Schema / Structured Output 기능(`response_format`)을 사용하여 반환 형식을 강제한다:
  ```json
  {
    "recommendations": [
      { "book_id": "B001", "reason": "..." },
      { "book_id": "B007", "reason": "..." },
      { "book_id": "B009", "reason": "..." }
    ]
  }
  ```
- **System Prompt 핵심 지시사항:**
  1. 반드시 전달받은 `candidates` 목록의 `book_id` 중에서만 **서로 다른 3권**을 선택하라.
  2. 사용자의 `goal`(최우선), `mood`(현재 감정 맥락), `genre`, `depth`를 종합해 가장 적합한 3권을 고르고, 가능하면 3권이 서로 다른 독서 경험을 주도록 구성하라.
  3. 각 `reason`은 **제공된 `summary`, `themes`, `mood_tags`, `depth_reason`에만 근거**해 작성하고, 책에 없는 줄거리·저자 정보·청구기호·서가 위치·유튜브 링크·QR·로봇 이동 명령을 절대 지어내지 마라.
  4. `reason`은 **한국어 공백 포함 60~100자 이내**, 친근하고 차분한 해요체("...추천해요", "...어울려요")로 작성하라.
  5. `"적합도 95%"` 같은 검증되지 않은 수치/퍼센트를 절대 쓰지 마라.

#### (3) 서버 측 2중 검증 (`response_validator.py`)
LLM 응답을 받자마자 아래 6가지가 하나라도 실패하면 거부(Reject)한다.
1. JSON 파싱 성공 및 `recommendations` 배열 길이 == `3`
2. 모든 `book_id`가 이번 호출에 넘긴 `candidate_ids` 집합에 포함됨
3. `len(set(book_ids)) == 3` (중복 도서 없음)
4. 각 `reason`이 비어있지 않고, 길이가 최소 20자 이상 ~ 최대 120자 이하 (60~100자 권장 범위 초과 시 잘라내거나 재시도 기준 설정)
5. 금지 패턴 미포함 (예: `http://`, `https://`, `youtube`, `QR`, `%` 등 수치형 적합도/외부 링크 차단)
6. (선택) LLM이 임의로 `title` 등을 반환할 경우 무시하고 항상 DB의 원본 `title`/`author` 사용

#### (4) 재시도 및 규칙 기반 Fallback (명세서 5.7)
- LLM 타임아웃(예: 8초), API 오류(429/5xx), 검증 실패 시 → **최대 1회 재시도** (검증 실패 메시지 간단히 포함 또는 동일 요청).
- 재시도 후에도 실패하면 에러를 던지지 않고 **3단계 규칙 점수 상위 3권**으로 대체한다:
  - 응답 필드: `"status": "ok"`, `"source": "fallback"`
  - 추천 이유 문구: 검증 가능한 고정/안전 템플릿 사용
    - 예: `"선택하신 독서 목적과 선호 유형을 기준으로 추천한 책이에요."` (명세서 5.7 예시 문구)

### 5.5 재추천 처리 흐름 (`feedback_type`)

클라이언트로부터 `POST /v1/recommendations` 호출 시 `feedback_type`에 따라 1단계 전처리 수행:
1. `already_read`: 요청의 `exclude_book_ids`에 이미 읽은 책 ID가 포함되어 전달됨 → 해당 ID 제외.
2. `lighter`:
   - `answers.depth == 3` → `effective_depth = 2`
   - `answers.depth == 2` 또는 `"any"` → `effective_depth = 1`
   - `answers.depth == 1` → 더 내릴 수 없으므로 `effective_depth = 1` 유지 (단, 기존 노출 3권이 `exclude_book_ids`에 포함되어야 새로운 책 추천 가능).
3. `different_genre` / `different_mood`:
   - 앱(S07)에서 사용자가 새 `genre`나 `goal`을 다시 선택해서 `answers`에 담아 보내는 것이 가장 명확하다.
   - 만약 앱이 `answers`를 수정하지 않고 `feedback_type`만 보내는 구조로 합의되었다면, `different_genre`는 `book.genre == answers.genre`인 책에 페널티/제외를 적용하거나 `any`로 완화하고, 직전 추천 도서를 제외해 새로운 유형이 상위에 오르게 처리한다. (이 부분은 이슈 4에서 Android 팀과 반드시 통일!)

### 5.6 음악 매칭 로직 (명세서 4.3 — LLM 미사용)

도서 상세 조회 시(또는 별도 매칭 호출 시) 실행:
1. 대상 도서 `book.mood_tags` 조회.
2. 활성 음악 필터: `active == true` AND `is_instrumental_verified == true` AND `url_verified == true`.
3. 각 음악마다 `overlap_count = len(set(book.mood_tags) & set(music.mood_tags))` 계산.
4. `overlap_count > 0`인 음악 중 정렬: `(-overlap_count, priority ASC, music_id ASC)`로 최상위 1개 선택.
5. **예외 처리:** 활성 음악이 없거나 `overlap_count > 0`인 음악이 없으면 에러를 내지 않고 `music: null` 반환 (앱은 음악/QR 영역만 숨기고 서가 안내는 정상 진행).

---

## 6. API 명세 (기존 명세서 7장 + 실구현 보완 엔드포인트)

> **규칙:** 명세서 7장의 `POST /v1/recommendations` 스펙을 100% 유지하면서, 실제 앱 화면(S06 추천 목록, S08 상세·음악, S11 평가) 구현에 반드시 필요한 조회/로깅 엔드포인트를 보완한 API 설계이다.

### 6.1 헬스 체크 — `GET /health`
- **용도:** 서버 상태, 활성 도서/음악 수, 현재 `catalog_version` 확인
- **응답 (200 OK):**
  ```json
  {
    "status": "ok",
    "catalog_version": "v1",
    "active_books_count": 20,
    "active_musics_count": 7
  }
  ```

### 6.2 도서 추천 및 재추천 — `POST /v1/recommendations`
- **요청 (Request Body):**
  ```json
  {
    "session_id": "demo-session-001",
    "answers": {
      "mood": "tired",
      "goal": "comfort",
      "genre": "essay",
      "depth": 1
    },
    "exclude_book_ids": [],
    "feedback_type": null,
    "allow_goal_relaxation": false
  }
  ```
  - `feedback_type`: `null` | `"different_genre"` | `"lighter"` | `"different_mood"` | `"already_read"`

- **정상 응답 (200 OK):**
  ```json
  {
    "status": "ok",
    "source": "llm",
    "catalog_version": "v1",
    "applied_answers": {
      "mood": "tired",
      "goal": "comfort",
      "genre": "essay",
      "depth": 1
    },
    "recommendations": [
      {
        "book_id": "B001",
        "reason": "지친 하루 끝에 부담 없이 읽기 좋고, 따뜻한 시선으로 마음을 어루만져 주는 에세이예요.",
        "book": {
          "title": "예시 도서 1",
          "author": "예시 저자",
          "genre": "essay",
          "depth": 1,
          "cover_path": "/static/covers/B001.jpg"
        }
      }
    ]
  }
  ```
  > **참고:** Android 팀과의 합의에 따라 `book` 요약 객체는 카드 화면(S06)을 한 번의 호출로 그리기 위한 실무 보완 필드다. 명세서 7.2의 `status`, `source`, `catalog_version`, `recommendations[].book_id`, `recommendations[].reason` 구조는 그대로 유지된다.

- **오류 응답 포맷 및 코드 (명세서 7.3):**
  ```json
  {
    "status": "error",
    "error": {
      "code": "GOAL_COVERAGE_INSUFFICIENT",
      "message": "선택하신 독서 목적에 해당하는 추천 가능 도서가 부족합니다.",
      "details": {
        "available_count": 2,
        "required_count": 3
      }
    }
  }
  ```
  | 오류 코드 | HTTP Status (권장) | 발생 조건 | 앱 대응 |
  | --- | --- | --- | --- |
  | `INVALID_INPUT` | `400 Bad Request` | 문진 값 누락 또는 허용 외 값 | 해당 문항 수정 유도 |
  | `CATALOG_INSUFFICIENT` | `503 Service Unavailable` | 활성+검증 완료 도서 총 3권 미만 | 서비스 불가 / 관리자 문의 안내 |
  | `GOAL_COVERAGE_INSUFFICIENT` | `422 Unprocessable Entity` | `goal` 일치 도서 3권 미만 (`allow_goal_relaxation=false`) | 목적 변경 또는 유사 목적 포함 동의 UI |
  | `NO_MORE_BOOKS` | `422 Unprocessable Entity` | 제외 후(`exclude_book_ids`) 추천 가능 도서 3권 미만 | 제외 조건 완화 또는 처음부터 재시작 |
  | `MODEL_UNAVAILABLE` | `503 Service Unavailable` | LLM 장애 + 규칙 기반 폴백마저 불가한 예외 상황 | 오류 안내 (일반 LLM 장애는 `200` + `source="fallback"` 반환) |

### 6.3 도서 상세 및 음악 매칭 조회 — `GET /v1/books/{book_id}`
- **용도:** S08(도서·음악 상세 화면) 및 S09/S10(TEMI 서가 이동·도착 화면) 진입 시 호출. 검증된 서가 정보(`call_number`, `shelf_label`, `poi_id`)와 음악 매칭 결과를 한 번에 반환.
- **응답 (200 OK):**
  ```json
  {
    "book": {
      "book_id": "B001",
      "title": "예시 도서 1",
      "author": "예시 저자",
      "genre": "essay",
      "summary": "검증된 도서 소개 내용...",
      "themes": ["자기이해", "일상"],
      "mood_tags": ["따뜻함", "위로"],
      "goal_tags": ["comfort", "rest"],
      "depth": 1,
      "depth_reason": "독립된 짧은 글 중심",
      "page_count": 210,
      "call_number": "818-김12ㅇ",
      "shelf_label": "인문자료실 A-3 서가",
      "poi_id": "SHELF_A",
      "cover_path": "/static/covers/B001.jpg"
    },
    "music": {
      "music_id": "M002",
      "title": "비 오는 오후의 잔잔한 피아노",
      "style": "피아노 연주곡",
      "mood_tags": ["따뜻함", "위로", "평온함"],
      "youtube_url": "https://www.youtube.com/watch?v=..."
    }
  }
  ```
  - 매칭 가능한 음악이 없거나 비활성화된 경우 `"music": null`을 반환하며, HTTP 200으로 정상 응답한다.
  - 요청한 `book_id`가 존재하지 않거나 `active=false`면 `404 Not Found` 반환.

### 6.4 서비스 이벤트 및 사용자 평가 기록 — `POST /v1/events`, `POST /v1/evaluations`
- **`POST /v1/events` (선택·주행 상태 추적):**
  ```json
  {
    "session_id": "demo-session-001",
    "event_type": "nav_arrived",
    "book_id": "B001",
    "music_id": "M002",
    "metadata": { "poi_id": "SHELF_A" }
  }
  ```
- **`POST /v1/evaluations` (S11 종료 화면 사용자 평가):**
  ```json
  {
    "session_id": "demo-session-001",
    "top3_satisfied": true,
    "reason_score": 5,
    "music_helpful_score": 4,
    "usability_score": 5,
    "used_rerecommend": false
  }
  ```
  - 응답: `201 Created` (`{ "status": "ok" }`)

---

## 7. 단계별 개발 로드맵 (우선순위 반영)

개발명세서 13장(P0/P1/P2) 및 착수 순서에 맞춘 백엔드 실행 계획:

### Step 1. 프로젝트 스캐폴딩 & 더미 카탈로그 구축 (P0 기반)
- [ ] FastAPI 프로젝트 초기화, `.env` 설정, SQLite 연결
- [ ] 더미 도서 JSON(최소 10~15권, 5개 목적 골고루 분포) & 더미 음악 JSON(4~6개) 작성
- [ ] `scripts/validate_catalog.py` 작성 (태그 enum, 필수 필드, `active=true` 조건 검사)
- [ ] `GET /health` 및 `GET /v1/books/{book_id}` 우선 구현

### Step 2. 규칙 기반 점수 엔진 & 단위 테스트 (P0 핵심)
- [ ] `scoring_engine.py` 구현 (1~3단계 필터, 100점 계산, 동점 정렬, 상위 8권 추출)
- [ ] 예외 케이스(`CATALOG_INSUFFICIENT`, `GOAL_COVERAGE_INSUFFICIENT`, `NO_MORE_BOOKS`) 및 `allow_goal_relaxation` 구현
- [ ] `pytest`로 경계값·점수 산식·오류 코드 단위 테스트 작성 및 통과

### Step 3. LLM 연동 + 2중 검증 + 폴백 구현 (P0 핵심)
- [ ] `llm_recommender.py` 구현 (Structured Output JSON Schema 강제, 8초 타임아웃, 1회 재시도)
- [ ] `response_validator.py` 구현 (후보 ID 실존 확인, 3권 확인, 중복 제거, 이유 60~100자, 금지 패턴 필터)
- [ ] 실패 시 규칙 점수 상위 3권 폴백(`source="fallback"`) 구현
- [ ] Mock LLM 응답으로 비정상 JSON / 없는 `book_id` / 중복 ID / 타임아웃 시뮬레이션 테스트

### Step 4. 재추천 & 음악 매칭 구현 (P0 + P1)
- [ ] `feedback_type` 4종(`different_genre`, `lighter`, `different_mood`, `already_read`) 전처리 및 `exclude_book_ids` 반영
- [ ] `music_matcher.py` 구현 (`mood_tags` 교집합 최다 + `priority` 타이브레이커 + 미매칭 시 `null`)

### Step 5. 평가 로깅 & Android 연동 & 실데이터 반영 (P1 & 현장 검증)
- [ ] `POST /v1/events`, `POST /v1/evaluations` 및 SQLite 저장, CSV 내보내기 스크립트 작성
- [ ] 실서버 배포(HTTPS) 및 Swagger(`/docs`) 링크를 Android 팀에 공유하여 연동 테스트
- [ ] 기획·DB팀의 실소장 도서 20권, 음악 6~8개, TEMI `poi_id` 확정본 수신 → `import_csv.py` + `validate_catalog.py` 검증 후 실DB 교체
- [ ] 광운대 중앙도서관 L층 현장 테스트 시 응답 속도(Latency), 와이파이 안정성, `poi_id` 일치 여부 최종 확인

---

## 8. 백엔드 완료 전 자가 검증 체크리스트 (명세서 12장·16장 기준)

배포 및 Android 최종 통합 전, 아래 항목을 모두 테스트 코드 또는 Postman/curl로 검증한다.

- [ ] `active=false`, `holding_verified=false`, `navigation_verified=false`인 책은 어떤 입력을 넣어도 추천되지 않는가?
- [ ] 동일 요청에 대해 동일한 도서가 3권 안에 중복으로 반환되지 않는가?
- [ ] LLM이 후보에 없는 `book_id`(예: `"B999"`)나 깨진 JSON을 반환하도록 강제했을 때, 재시도 후 정상적으로 `source="fallback"`(규칙 기반 3권)으로 전환되는가?
- [ ] LLM 추천 이유에 실제 DB와 다른 저자/청구기호/유튜브 URL/적합도 % 등이 포함되지 않도록 차단되는가?
- [ ] `goal` 일치 도서가 3권 미만일 때 `allow_goal_relaxation=false`면 `GOAL_COVERAGE_INSUFFICIENT`가 반환되고, `true`면 유사 목적 도서가 포함되는가?
- [ ] `already_read` 등으로 `exclude_book_ids`가 누적되어 3권 미만만 남았을 때 `NO_MORE_BOOKS`가 반환되는가?
- [ ] `music` URL이 전부 비활성이거나 태그 교집합이 0일 때에도 `GET /v1/books/{book_id}`가 에러 없이 `music: null`을 반환해 서가 이동을 막지 않는가?
- [ ] 전체 추천 API 응답 시간이 도서관 네트워크 기준 허용 범위(목표 3~8초 이내)에 들어오는가?
- [ ] 저장소 및 API 응답 어디에도 LLM API 키나 사용자 개인정보가 노출되지 않는가?

