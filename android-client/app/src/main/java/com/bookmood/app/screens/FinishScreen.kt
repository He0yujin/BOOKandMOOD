package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import androidx.compose.ui.text.style.TextAlign
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.Palette
import com.bookmood.app.PrototypeLayout
import com.bookmood.app.navigation.TemiNavigationController.State

@Composable
internal fun PrototypeLayout.FinishScreen(model: BookMoodViewModel) {
    surface(1125, 0, 795, 1200, Palette.Dark)
    ellipse(1219, 324, 590, 590, Palette.Mint)
    eyes(1333, 1523, 496, 148, 185)
    label("BOOK & MOOD", 147, 103, 360, 60, 34, Palette.Dark, true)
    label("안내를 마쳤어요", 145, 332, 965, 130, 91, bold = true)
    val state = model.navigationState
    val message = when (state) {
        State.HOME_ARRIVED -> "좋은 독서 시간 보내세요.\nTEMI가 대기 장소에 도착했어요."
        State.FAILED, State.NOT_READY -> "좋은 독서 시간 보내세요.\n${model.navigationMessage}"
        else -> "좋은 독서 시간 보내세요.\nTEMI는 대기 장소로 돌아갑니다."
    }
    label(message, 148, 541, 925, 185, 42, Palette.Muted, lines = 3)
    if (state == State.FAILED || state == State.NOT_READY) {
        button("복귀 다시 시도", 147, 842, 345, action = model::returnHome)
    } else {
        button("처음으로", 147, 842, 345, enabled = state == State.HOME_ARRIVED, action = model::finish)
    }
}
