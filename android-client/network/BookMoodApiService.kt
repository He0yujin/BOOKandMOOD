package com.bookmood.app.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface BookMoodApiService {

    @POST("v1/recommendations")
    suspend fun getRecommendations(
        @Body request: RecommendationRequestDto
    ): Response<RecommendationResponseDto>

    @GET("v1/books/{book_id}")
    suspend fun getBookDetail(
        @Path("book_id") bookId: String
    ): Response<BookDetailResponseDto>

    @POST("v1/events")
    suspend fun recordEvent(
        @Body request: EventRequestDto
    ): Response<EventResponseDto>

    @POST("v1/evaluations")
    suspend fun recordEvaluation(
        @Body request: EvaluationRequestDto
    ): Response<EvaluationResponseDto>
}
