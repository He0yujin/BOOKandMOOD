package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.PrototypeLayout

private val lengths = listOf(
    Choice("짧은 책", 1, "단편 또는 짧은 분량"),
    Choice("긴 책", 2, "장편 또는 긴 분량")
)

@Composable
internal fun PrototypeLayout.LengthScreen(model: BookMoodViewModel) {
    QuestionScreen(
        3, "어느 정도 길이의 책을 원하나요?", "오늘 읽기 편한 분량을 골라 주세요.",
        if (model.genre in listOf("essay", "humanities")) {
            listOf(Choice("짧은 책", 1, "274쪽 이하"), Choice("긴 책", 2, "275쪽 이상"))
        } else {
            lengths
        }, model.depth, { model.depth = it }, model::back, model::advanceQuestion
    )
}
