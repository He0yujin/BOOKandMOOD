package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import androidx.compose.ui.text.style.TextAlign
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.Palette
import com.bookmood.app.PrototypeLayout

@Composable
internal fun PrototypeLayout.LoadingScreen(model: BookMoodViewModel) {
    header()
    surface(761, 261, 398, 400, Palette.Mint, 185)
    eyes(820, 975.8, 377, 121.36, 151.7)
    val problem = model.problem
    label(
        if (problem == null) "어울리는 책을 찾고 있어요" else "추천을 완료하지 못했어요",
        300, 710, 1320, 102, 68, bold = true, align = TextAlign.Center
    )
    val detail = when (problem?.code) {
        null -> "선택한 독서 목적과 장르, 분량을 살펴보고 있어요."
        "NETWORK_ERROR" -> "서버 연결을 확인하고 다시 시도해 주세요."
        else -> problem?.message.orEmpty()
    }
    label(detail, 240, 815, 1440, 88, 32, Palette.Muted, align = TextAlign.Center, lines = 2)
    if (problem == null) {
        repeat(3) { ellipse(900 + it * 44, 936, 20, 20, if (it == 0) Palette.Teal else Palette.Sage) }
        return
    }
    button("이전", 652, 966, 200, primary = false, action = model::back)
    val allowRelated = problem.code == "GOAL_COVERAGE_INSUFFICIENT"
    if (problem.code != "NO_MORE_BOOKS") {
        button(if (allowRelated) "비슷한 목적도 보기" else "다시 시도", 892, 966, 376) {
            model.retryRecommendations(relaxGoal = allowRelated)
        }
    }
}
