package com.bookmood.app

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

internal object Palette {
    val Paper = Color(0xFFF4F2ED)
    val Ink = Color(0xFF1B1F1E)
    val Muted = Color(0xFF596260)
    val Dark = Color(0xFF174746)
    val Teal = Color(0xFF1F5C5B)
    val Mint = Color(0xFFD9E6E2)
    val Pale = Color(0xFFEAF0E8)
    val Sage = Color(0xFFA7C3BE)
    val Line = Color(0xFFDCE3DF)
    val Cream = Color(0xFFFCFBF8)
    val Gold = Color(0xFFC69D52)
    val Purple = Color(0xFF665376)
    val Rust = Color(0xFF9E5548)
}

@Composable
internal fun Modifier.softPress(
    interactionSource: MutableInteractionSource,
    pressedScale: Float = 0.97f
): Modifier {
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) pressedScale else 1f,
        animationSpec = tween(durationMillis = if (pressed) 70 else 160),
        label = "Press scale"
    )

    return graphicsLayer {
        scaleX = scale
        scaleY = scale
    }
}

/** Positional units come from the 1920 × 1200 Figma artboards. */
internal class PrototypeLayout(private val scale: Float) {
    fun units(n: Number): Dp = (n.toFloat() * scale).dp

    fun position(x: Number, y: Number, width: Number, height: Number): Modifier =
        Modifier.offset(units(x), units(y)).size(units(width), units(height))

    @Composable
    fun surface(
        x: Number, y: Number, width: Number, height: Number,
        color: Color, radius: Number = 0, shape: Shape = RoundedCornerShape(units(radius))
    ) {
        Box(position(x, y, width, height).background(color, shape))
    }

    @Composable
    fun ellipse(x: Number, y: Number, width: Number, height: Number, color: Color) {
        Canvas(position(x, y, width, height)) { drawOval(color) }
    }

    @Composable
    fun label(
        text: String, x: Number, y: Number, width: Number, height: Number, font: Number,
        color: Color = Palette.Ink, bold: Boolean = false,
        align: TextAlign = TextAlign.Start, lines: Int = 1,
        lineSpacing: Float = 1.2f, scroll: Boolean = false
    ) {
        val size = font.toFloat() * scale
        val style = TextStyle(
            color = color,
            fontFamily = FontFamily.SansSerif,
            fontWeight = if (bold) FontWeight.Bold else FontWeight.Normal,
            fontSize = size.sp,
            lineHeight = (size * lineSpacing).sp,
            textAlign = align
        )
        Box(position(x, y, width, height)) {
            val area = Modifier.fillMaxSize()
            if (scroll) {
                Box(area.verticalScroll(rememberScrollState())) { BasicText(text, style = style) }
            } else {
                BasicText(text, area, style, overflow = TextOverflow.Ellipsis, maxLines = lines)
            }
        }
    }

    @Composable
    fun button(
        text: String, x: Number, y: Number, width: Number,
        primary: Boolean = true, enabled: Boolean = true, action: () -> Unit
    ) {
        val interactionSource = remember { MutableInteractionSource() }
        val shape = RoundedCornerShape(units(18))
        val bg = if (primary && enabled) Palette.Teal else Palette.Mint
        val ink = if (primary && enabled) Palette.Cream else if (enabled) Palette.Dark else Palette.Muted
        Box(
            position(x, y, width, 96)
                .clickable(
                    interactionSource = interactionSource,
                    indication = null,
                    enabled = enabled,
                    role = Role.Button,
                    onClick = action
                )
                .softPress(interactionSource)
                .clip(shape)
                .background(bg),
            contentAlignment = Alignment.Center
        ) {
            BasicText(text, style = TextStyle(
                color = ink, fontFamily = FontFamily.SansSerif,
                fontSize = (32 * scale).sp, fontWeight = FontWeight.Bold
            ))
        }
    }

    @Composable
    fun option(
        title: String, x: Int, y: Int, chosen: Boolean, onPress: () -> Unit,
        caption: String? = null, actionOnly: Boolean = false, height: Int = 216
    ) {
        val interactionSource = remember { MutableInteractionSource() }
        val shape = RoundedCornerShape(units(26))
        val base = position(x, y, 796, height)
        val input = if (actionOnly) {
            base.clickable(
                interactionSource = interactionSource,
                indication = null,
                role = Role.Button,
                onClick = onPress
            )
        } else {
            base.selectable(
                selected = chosen,
                interactionSource = interactionSource,
                indication = null,
                role = Role.RadioButton,
                onClick = onPress
            )
        }
        Box(
            input
                .softPress(interactionSource)
                .clip(shape)
                .background(if (chosen) Palette.Mint else Palette.Cream)
                .border(units(if (chosen) 4 else 2), if (chosen) Palette.Teal else Palette.Line, shape)
        ) {
            label(title, 40, 45, 671, 60, 40, bold = true)
            caption?.let { label(it, 40, 111, 680, 48, 27, Palette.Muted) }
            ellipse(726, 53, 28, 28, if (chosen) Palette.Teal else Palette.Line)
        }
    }

    @Composable
    fun header(tag: String = "", accented: Boolean = false) {
        val x = if (accented) 128 else 146
        if (accented) surface(0, 0, 1920, 14, Palette.Dark)
        label("BOOK & MOOD", x, if (accented) 55 else 71, 335, 55, if (accented) 33 else 32, Palette.Dark, true)
        if (accented) {
            label(tag, 1270, 59, 522, 46, 27, Palette.Muted, align = TextAlign.End)
        } else {
            label(tag, 1510, 77, 264, 46, 27, Palette.Muted, true)
        }
        surface(x, if (accented) 128 else 132, 1920 - x * 2, 2, Palette.Line)
    }

    @Composable
    fun title(title: String, subtitle: String) {
        label(title, 144, 182, 1650, 106, 72, bold = true)
        label(subtitle, 148, 296, 1620, 62, 32, Palette.Muted)
    }

    @Composable
    fun footerRule() = surface(146, 1018, 1628, 2, Palette.Line)
}

@Composable
internal fun PrototypeCanvas(content: @Composable PrototypeLayout.() -> Unit) {
    BoxWithConstraints(
        Modifier.fillMaxSize().background(Palette.Paper),
        contentAlignment = Alignment.Center
    ) {
        val width = minOf(maxWidth, maxHeight * 1.6f)
        val layout = PrototypeLayout(width.value / 1920f)
        Box(Modifier.size(width, width / 1.6f).aspectRatio(1.6f).clip(RoundedCornerShape(0.dp))) {
            layout.content()
        }
    }
}
