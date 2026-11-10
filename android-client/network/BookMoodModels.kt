package com.bookmood.app.network

import com.google.gson.annotations.SerializedName

// 1. 문진 3문항 응답 (Q1 독서 목적, Q2 도서 유형, Q3 독서 깊이)
data class SurveyAnswersDto(
    @SerializedName("goal") val goal: String,     // "comfort" | "rest" | "refresh" | "motivate"
    @SerializedName("genre") val genre: String,   // "fiction" | "essay" | "humanities" | "any"
    @SerializedName("depth") val depth: Int       // 1 (단편) | 2 (장편)
)

// 2. 추천 요청 (POST /v1/recommendations)
data class RecommendationRequestDto(
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("answers") val answers: SurveyAnswersDto,
    @SerializedName("exclude_book_ids") val excludeBookIds: List<String> = emptyList(),
    @SerializedName("feedback_type") val feedbackType: String? = null,
    @SerializedName("allow_goal_relaxation") val allowGoalRelaxation: Boolean = false
)

// 3. 추천 결과 카드용 도서 요약
data class BookSummaryDto(
    @SerializedName("title") val title: String,
    @SerializedName("author") val author: String,
    @SerializedName("genre") val genre: String,
    @SerializedName("depth") val depth: Int,
    @SerializedName("cover_path") val coverPath: String
)

data class RecommendationItemDto(
    @SerializedName("book_id") val bookId: String,
    @SerializedName("reason") val reason: String,
    @SerializedName("book") val book: BookSummaryDto?
)

// 4. 추천 응답 (POST /v1/recommendations)
data class RecommendationResponseDto(
    @SerializedName("status") val status: String,
    @SerializedName("source") val source: String, // "llm" | "fallback"
    @SerializedName("catalog_version") val catalogVersion: String,
    @SerializedName("recommendations") val recommendations: List<RecommendationItemDto>
)

// 5. 도서 상세 정보 (GET /v1/books/{book_id})
data class BookDetailDto(
    @SerializedName("book_id") val bookId: String,
    @SerializedName("title") val title: String,
    @SerializedName("author") val author: String,
    @SerializedName("genre") val genre: String,
    @SerializedName("summary") val summary: String,
    @SerializedName("themes") val themes: List<String>,
    @SerializedName("mood_tags") val moodTags: List<String>,
    @SerializedName("goal_tags") val goalTags: List<String>,
    @SerializedName("depth") val depth: Int,
    @SerializedName("depth_reason") val depthReason: String,
    @SerializedName("page_count") val pageCount: Int?,
    @SerializedName("call_number") val callNumber: String,
    @SerializedName("shelf_label") val shelfLabel: String,
    @SerializedName("poi_id") val poiId: String,
    @SerializedName("cover_path") val coverPath: String
)

// 6. 매칭 음악 플레이리스트 (QR 연결용)
data class MusicDto(
    @SerializedName("music_id") val musicId: String,
    @SerializedName("title") val title: String,
    @SerializedName("style") val style: String,
    @SerializedName("mood_tags") val moodTags: List<String>,
    @SerializedName("youtube_url") val youtubeUrl: String
)

data class BookDetailResponseDto(
    @SerializedName("status") val status: String,
    @SerializedName("book") val book: BookDetailDto,
    @SerializedName("music") val music: MusicDto?
)

// 7. 사용자 행동 이벤트 로그 (POST /v1/events)
data class EventRequestDto(
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("event_type") val eventType: String,
    @SerializedName("book_id") val bookId: String? = null,
    @SerializedName("music_id") val musicId: String? = null,
    @SerializedName("metadata") val metadata: Map<String, Any> = emptyMap()
)

data class EventResponseDto(
    @SerializedName("status") val status: String,
    @SerializedName("event_id") val eventId: Int
)

// 8. 서비스 종료 평가 (POST /v1/evaluations)
data class EvaluationRequestDto(
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("top3_satisfied") val top3Satisfied: Boolean,
    @SerializedName("reason_score") val reasonScore: Int,
    @SerializedName("music_helpful_score") val musicHelpfulScore: Int? = null,
    @SerializedName("usability_score") val usabilityScore: Int,
    @SerializedName("used_rerecommend") val usedRerecommend: Boolean = false
)

data class EvaluationResponseDto(
    @SerializedName("status") val status: String,
    @SerializedName("evaluation_id") val evaluationId: Int
)

// 9. 백엔드 표준 오류 응답
data class ApiErrorDetailDto(
    @SerializedName("code") val code: String,
    @SerializedName("message") val message: String,
    @SerializedName("details") val details: Map<String, Any>? = null
)

data class ApiErrorResponseDto(
    @SerializedName("status") val status: String,
    @SerializedName("error") val error: ApiErrorDetailDto
)
