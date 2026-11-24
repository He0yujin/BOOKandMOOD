package com.bookmood.app.screens

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.keyframes
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import com.bookmood.app.Palette
import com.bookmood.app.PrototypeLayout

@Composable
internal fun PrototypeLayout.WelcomeScreen(onStart: () -> Unit) {
    surface(1030, 0, 890, 1200, Palette.Dark)
    ellipse(1110, 195, 760, 760, Palette.Teal)
    WelcomePulse()
    WelcomeEyes()
    label("BOOK & MOOD", 146, 102, 330, 60, 34, Palette.Dark, true)
    label("오늘의 기분에", 145, 302, 850, 142, 102, bold = true)
    label("어울리는 책", 145, 430, 850, 142, 102, bold = true)
    label(
        "응답에 따라 책과 음악을 추천해드릴게요.\n서가까지 함께 가요.",
        149, 620, 820, 105, 35, Palette.Muted, lines = 2
    )
    button("시작하기", 146, 880, 380, action = onStart)
}

@Composable
private fun PrototypeLayout.WelcomePulse() {
    val pulse = rememberInfiniteTransition(label = "Welcome heartbeat")
    val scale by pulse.animateFloat(
        initialValue = 1f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(keyframes {
            durationMillis = 1500
            1f at 0 using FastOutSlowInEasing
            1.075f at 145 using FastOutSlowInEasing
            1f at 320 using FastOutSlowInEasing
            1.05f at 445 using FastOutSlowInEasing
            1f at 660
        }),
        label = "Mint circle scale"
    )
    val diameter = 500f * scale
    val radius = diameter / 2f
    ellipse(1490f - radius, 571f - radius, diameter, diameter, Palette.Mint)
}

@Composable
private fun PrototypeLayout.WelcomeEyes() {
    val gaze = rememberInfiniteTransition(label = "Welcome gaze")
    val horizontalOffset by gaze.animateFloat(
        initialValue = 0f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(keyframes {
            durationMillis = 4200
            0f at 650 using FastOutSlowInEasing
            13f at 1050
            13f at 1650 using FastOutSlowInEasing
            (-13f) at 2200
            (-13f) at 2800 using FastOutSlowInEasing
            0f at 3250
        }),
        label = "Horizontal pupil offset"
    )
    eyes(1319, 1501.4, 455, 142.08, 177.6, pupilOffsetX = horizontalOffset)
}
