package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.PrototypeLayout

private val genres = listOf(
    Choice("소설", "fiction"), Choice("에세이", "essay"),
    Choice("인문·교양", "humanities"), Choice("상관없음", "any")
)

internal fun genreCaption(value: String): String =
    genres.firstOrNull { it.value == value }?.caption.orEmpty()

@Composable
internal fun PrototypeLayout.GenreScreen(model: BookMoodViewModel) {
    QuestionScreen(
        2, "어떤 장르가 끌리나요?", "오늘 읽고 싶은 책의 장르를 골라 주세요.",
        genres, model.genre, { model.genre = it }, model::back, model::advanceQuestion
    )
}
