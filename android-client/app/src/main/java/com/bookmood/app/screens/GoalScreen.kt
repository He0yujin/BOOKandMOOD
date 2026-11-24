package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.PrototypeLayout

private val goals = listOf(
    Choice("위로와 공감을 얻고 싶어요", "comfort"),
    Choice("편안하게 쉬고 싶어요", "rest"),
    Choice("기분을 전환하고 싶어요", "refresh"),
    Choice("동기부여와 용기를 얻고 싶어요", "motivate")
)

@Composable
internal fun PrototypeLayout.GoalScreen(model: BookMoodViewModel) {
    QuestionScreen(
        1, "책을 통해 어떤 시간을 보내고 싶나요?", "지금 마음에 가장 가까운 답을 골라 주세요.",
        goals, model.goal, { model.goal = it }, model::back, model::advanceQuestion
    )
}
