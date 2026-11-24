package com.bookmood.app.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.Palette
import com.bookmood.app.PrototypeLayout
import com.bookmood.app.cover
import com.bookmood.app.network.RecommendationItemDto
import com.bookmood.app.softPress

@Composable
internal fun PrototypeLayout.RecommendationsScreen(model: BookMoodViewModel) {
    header("추천 도서")
    title("오늘 이 책은 어때요?", "책을 선택하면 추천 이유와 함께 들을 음악을 볼 수 있어요.")
    model.recommendations.forEachIndexed { index, item ->
        recommendationCard(item, index, model::coverUrl) { model.chooseBook(item) }
    }
    footerRule()
    button("이전", 146, 1058, 200, false, action = model::back)
    button("다시 추천받기", 1410, 1058, 364, false, action = model::showRerecommend)
}

@Composable
private fun PrototypeLayout.recommendationCard(
    item: RecommendationItemDto, index: Int, coverUrl: (String) -> String?, onChoose: () -> Unit
) {
    val book = item.book ?: return
    val interactionSource = remember { MutableInteractionSource() }
    Box(
        position(147 + index * 552, 397, 524, 564)
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                role = Role.Button,
                onClick = onChoose
            )
            .softPress(interactionSource, pressedScale = 0.98f)
            .clip(RoundedCornerShape(units(24)))
            .background(Palette.Cream)
    ) {
        cover(book.title, book.author, coverUrl(book.coverPath), coverColor(index), 38, 35, false)
        label(book.title, 38, 282, 450, 64, 45, bold = true)
        label(book.author, 39, 354, 448, 49, 26, Palette.Muted)
        surface(38, 420, 448, 2, Palette.Line)
        label(book.shortSummary, 38, 447, 440, 108, 29, lines = 3)
    }
}
