package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import androidx.compose.ui.text.style.TextAlign
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.Palette
import com.bookmood.app.PrototypeLayout
import com.bookmood.app.navigation.TemiNavigationController.State

@Composable
internal fun PrototypeLayout.NavigationScreen(model: BookMoodViewModel) {
    header("TEMI 서가 안내", accented = true)
    val state = model.navigationState
    val ended = state in setOf(State.FAILED, State.NOT_READY, State.CANCELLED)
    val status = when {
        model.stopping -> "이동을 멈추고 있어요"
        state == State.CANCELLED -> "이동 중단"
        ended -> "이동 상태 확인"
        else -> "서가 이동 중"
    }
    surface(764, 177, 392, 64, Palette.Pale, 32)
    label(status, 764, 187, 392, 48, 30, Palette.Dark, true, TextAlign.Center)
    ellipse(787, 282, 346, 346, Palette.Pale)
    ellipse(841, 336, 238, 238, Palette.Mint)
    surface(890, 385, 140, 140, Palette.Dark, 34)
    ellipse(920, 431, 19, 19, Palette.Cream)
    ellipse(981, 431, 19, 19, Palette.Cream)
    surface(943, 471, 34, 8, Palette.Cream, 4)
    listOf(678.5, 668.6, 660.9, 655.4, 652.1, 651.0, 652.1, 655.4, 660.9, 668.6, 678.5)
        .forEachIndexed { index, y -> surface(695 + 49 * index, y, 33, 7, Palette.Gold, 4) }
    val heading = when {
        state == State.CANCELLED -> "서가 안내를 중단했어요"
        ended -> "서가로 이동할 수 없어요"
        else -> "책이 있는 서가로 이동 중이에요"
    }
    label(heading, 180, 708, 1560, 103, 72, bold = true, align = TextAlign.Center)
    val message = if (ended || model.navigationMessage.startsWith("이동 중단 요청 실패")) {
        model.navigationMessage
    } else {
        "TEMI 뒤에서 천천히 따라와 주세요."
    }
    label(message, 280, 832, 1360, 110, 35, Palette.Muted, align = TextAlign.Center, lines = 2)
    if (ended) {
        button("책으로 돌아가기", 635, 959, 310, false, action = model::back)
        button("다시 시도", 975, 959, 310, action = model::startShelf)
    } else {
        button("이동 중단", 825, 959, 270, false, enabled = !model.stopping, action = model::stopNavigation)
    }
}
