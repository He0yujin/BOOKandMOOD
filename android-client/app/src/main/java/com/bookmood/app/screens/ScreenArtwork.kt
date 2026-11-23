package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import com.bookmood.app.Palette
import com.bookmood.app.PrototypeLayout

private val coverColors = listOf(Palette.Teal, Palette.Purple, Palette.Rust)

internal fun coverColor(index: Int) = coverColors[index % coverColors.size]

@Composable
internal fun PrototypeLayout.eyes(
    left: Number,
    right: Number,
    top: Number,
    width: Number,
    height: Number,
    pupilOffsetX: Float = 0f
) {
    val w = width.toFloat()
    val h = height.toFloat()
    val y = top.toFloat()
    for (x in listOf(left.toFloat(), right.toFloat())) {
        val gazeX = x + pupilOffsetX
        ellipse(x, y, w, h, Palette.Cream)
        ellipse(gazeX + w * .324f, y + h * .314f, w * .493f, h * .492f, Palette.Teal)
        ellipse(gazeX + w * .432f, y + h * .368f, w * .135f, w * .135f, Palette.Cream)
    }
}
