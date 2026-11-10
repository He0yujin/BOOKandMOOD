package com.bookmood.app.network

import com.google.gson.Gson
import okhttp3.OkHttpClient
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(
        val code: String,
        val message: String,
        val details: Map<String, Any>? = null
    ) : ApiResult<Nothing>()
}

object BookMoodClient {
    // - Android Studio 에뮬레이터에서 내 PC 로컬 서버 접속 시: "http://10.0.2.2:8000/"
    // - 실제 TEMI 기기에서 같은 Wi-Fi 내 맥북 접속 시: "http://<맥북IP>:8000/"
    private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000/"

    private val gson = Gson()

    private val okHttpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)   // LLM 추천 응답 대기 시간 고려
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    @Volatile
    private var currentBaseUrl: String = DEFAULT_BASE_URL

    @Volatile
    private var service: BookMoodApiService = buildService(DEFAULT_BASE_URL)

    private fun buildService(baseUrl: String): BookMoodApiService {
        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        return Retrofit.Builder()
            .baseUrl(normalized)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
            .create(BookMoodApiService::class.java)
    }

    fun setBaseUrl(baseUrl: String) {
        currentBaseUrl = baseUrl
        service = buildService(baseUrl)
    }

    suspend fun getRecommendations(
        request: RecommendationRequestDto
    ): ApiResult<RecommendationResponseDto> = safeCall {
        service.getRecommendations(request)
    }

    suspend fun getBookDetail(
        bookId: String
    ): ApiResult<BookDetailResponseDto> = safeCall {
        service.getBookDetail(bookId)
    }

    suspend fun recordEvent(
        request: EventRequestDto
    ): ApiResult<EventResponseDto> = safeCall {
        service.recordEvent(request)
    }

    suspend fun recordEvaluation(
        request: EvaluationRequestDto
    ): ApiResult<EvaluationResponseDto> = safeCall {
        service.recordEvaluation(request)
    }

    private suspend fun <T> safeCall(
        call: suspend () -> Response<T>
    ): ApiResult<T> {
        return try {
            val response = call()
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) {
                    ApiResult.Success(body)
                } else {
                    ApiResult.Error("EMPTY_RESPONSE", "서버 응답 본문이 비어 있습니다.")
                }
            } else {
                val errJson = response.errorBody()?.string()
                val parsed = try {
                    gson.fromJson(errJson, ApiErrorResponseDto::class.java)
                } catch (_: Exception) {
                    null
                }
                if (parsed != null) {
                    ApiResult.Error(
                        code = parsed.error.code,
                        message = parsed.error.message,
                        details = parsed.error.details
                    )
                } else {
                    ApiResult.Error("HTTP_${response.code()}", "요청 처리에 실패했습니다.")
                }
            }
        } catch (e: Exception) {
            ApiResult.Error("NETWORK_ERROR", e.localizedMessage ?: "서버에 연결할 수 없습니다.")
        }
    }
}
