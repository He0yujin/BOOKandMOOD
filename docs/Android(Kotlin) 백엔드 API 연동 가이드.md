# Android(Kotlin) 백엔드 API 연동 가이드

프론트(Android Studio) 프로젝트가 생성되면 아래 3개 파일을 앱 패키지(`com.bookmood.app.network`)에 복사해 넣고 호출하시면 됩니다.

* `network/BookMoodModels.kt` — 요청/응답 데이터 모델
* `network/BookMoodApiService.kt` — Retrofit2 API 인터페이스
* `network/BookMoodClient.kt` — 네트워크 호출 & 오류 코드(`INVALID_INPUT`, `NO_MORE_BOOKS` 등) 자동 파싱 래퍼

---

## 1. Android Studio 설정 (2곳)

### ① `app/build.gradle.kts` 의존성 추가
```kotlin
dependencies {
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
```

### ② `app/src/main/AndroidManifest.xml` 권한 추가
로컬 개발 서버(`http://...`) 통신을 위해 `INTERNET` 권한과 `usesCleartextTraffic="true"`를 추가합니다.
```xml
<uses-permission android:name="android.permission.INTERNET" />

<application
    android:usesCleartextTraffic="true"
    ...>
```

---

## 2. 서버 주소(`BASE_URL`) 연결 규칙

* **노트북 Android Studio 에뮬레이터로 테스트할 때:** 기본값 `http://10.0.2.2:8000/` 그대로 사용
* **실제 TEMI 기기(같은 Wi-Fi)에서 테스트할 때:** 앱 시작 시 1회 호출
  ```kotlin
  BookMoodClient.setBaseUrl("http://192.168.x.x:8000/")
  ```

---

## 3. 화면별 호출 예시

### ① 문진 완료 후 추천 3권 받기 (`S03 → S04 → S05`)
```kotlin
val request = RecommendationRequestDto(
    sessionId = sessionId, // 앱 시작 시 UUID.randomUUID().toString() 생성
    answers = SurveyAnswersDto(
        goal = "refresh",   // comfort | rest | refresh | motivate
        genre = "fiction",  // fiction | essay | humanities | any
        depth = 1           // 1(단편) | 2(장편)
    )
)

when (val result = BookMoodClient.getRecommendations(request)) {
    is ApiResult.Success -> {
        val books = result.data.recommendations // 3권 리스트 (bookId, reason, book)
    }
    is ApiResult.Error -> {
        // result.code: "INVALID_INPUT", "GOAL_COVERAGE_INSUFFICIENT", "NO_MORE_BOOKS", "NETWORK_ERROR"
    }
}
```

### ② 도서 상세 + 매칭 음악 QR 조회 (`S05 → S07`)
```kotlin
when (val result = BookMoodClient.getBookDetail(selectedBookId)) {
    is ApiResult.Success -> {
        val book = result.data.book   // title, author, summary, callNumber, shelfLabel, poiId
        val music = result.data.music // music?.youtubeUrl 로 QR 코드 생성 (null이면 음악 영역 숨김)
    }
    is ApiResult.Error -> { /* 안내 처리 */ }
}
```
