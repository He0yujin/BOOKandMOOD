# BOOK & MOOD · temi V1

Figma의 `03. Prototype · BOOK & MOOD`를 Kotlin / Jetpack Compose로 구현한 Android 앱입니다. `android-client`를 Android Studio에서 엽니다. Gradle 9.6.0, Android Gradle Plugin 9.4.1, Android SDK 37을 사용합니다.

## 앱과 서버 실행

1. 저장소의 `backend`에서 개발 서버와 샘플 SQLite DB를 준비합니다.

   ```powershell
   python -m pip install -r requirements.txt
   python scripts/seed_db.py
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. Android 에뮬레이터에서는 기본 서버 주소인 `http://10.0.2.2:8000/`를 사용합니다. 실기기에서는 `%USERPROFILE%\.gradle\gradle.properties`에 동일한 네트워크에서 테미가 접근할 수 있는 서버 주소를 입력합니다.

   ```properties
   bookMoodBaseUrl=http://192.168.0.10:8000/
   bookMoodStandbyPoi=HOME_STANDBY
   ```

3. Android Studio에서 Gradle을 동기화한 뒤, 실행 대상에서 Android 에뮬레이터 또는 ADB로 연결한 테미 V1을 선택하고 Run을 누릅니다. 명령줄 빌드는 `./gradlew.bat :app:assembleDebug`입니다.

## 화면과 데이터

- S00~S04에서 새 세션과 세 문진 답변을 수집해 추천 API에 한 번 전송합니다.
- S05~S07은 추천 목록, 재추천, 책 상세와 음악 QR입니다. 추천 이유는 추천 응답에서, 책 소개와 음악은 상세 응답에서 읽습니다. 기본 CSV의 표지 대신 책 제목과 저자가 표시된 기본 표지를 사용합니다. 샘플 YouTube URL은 실제 QR로 표시하지 않습니다.
- S08~S10은 temi의 저장된 POI와 실제 이동 상태를 사용합니다. 실기기에서 도서의 `poi_id`와 대기 장소를 지도에 동일한 이름으로 등록해야 합니다. 샘플 CSV의 `SHELF_700_TEST`·`SHELF_800_TEST`는 개발용 POI입니다.
- 서버 연결 실패, 후보 부족, 상세 조회 실패, 이동 취소와 실패, 복귀 실패에는 화면에서 다시 시도하거나 앞 화면으로 이동할 수 있습니다.

