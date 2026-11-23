package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.Palette
import com.bookmood.app.PrototypeLayout
import com.bookmood.app.cover
import com.bookmood.app.musicQr
import com.bookmood.app.network.BookDetailResponseDto
import com.bookmood.app.playableMusicLink

@Composable
internal fun PrototypeLayout.BookDetailScreen(model: BookMoodViewModel) {
    header("책과 음악", accented = true)
    label("이 책과 함께 잠시 쉬어 가세요", 128, 159, 1664, 99, 66, bold = true)
    label("책이 마음에 들면 TEMI가 서가까지 안내해요.", 130, 260, 1662, 62, 31, Palette.Muted)
    surface(128, 358, 1080, 627, Palette.Cream, 25)
    surface(1238, 358, 554, 627, Palette.Cream, 25)
    label("책", 166, 384, 220, 50, 28, Palette.Dark, true)
    label("음악", 1278, 384, 220, 50, 28, Palette.Dark, true)
    val data = model.detail
    if (data != null) {
        val selectedIndex = model.recommendations.indexOfFirst { it.bookId == data.book.bookId }.coerceAtLeast(0)
        detailData(data, coverColor(selectedIndex), model)
    } else {
        val message = model.problem?.let {
            if (it.code == "NETWORK_ERROR") "서버에 연결할 수 없어요." else it.message
        } ?: "책 정보를 불러오고 있어요."
        label(message, 190, 495, 940, 106, 36, Palette.Muted, lines = 2)
        if (model.problem != null) button("다시 시도", 190, 650, 320, action = model::retryDetail)
    }
    button("다른 책 선택", 128, 1042, 295, false, action = model::back)
    button("서가로 가기", 1428, 1042, 364, enabled = data != null, action = model::startShelf)
}

@Composable
private fun PrototypeLayout.detailData(data: BookDetailResponseDto, color: Color, model: BookMoodViewModel) {
    val book = data.book
    cover(book.title, book.author, model.coverUrl(book.coverPath), color, 166, 450, true)
    label(book.title, 458, 418, 710, 90, 59, bold = true)
    val genre = genreCaption(book.genre)
    label(listOf(book.author, genre).filter(String::isNotBlank).joinToString("  ·  "), 460, 513, 708, 57, 30, Palette.Muted)
    if (book.themes.isNotEmpty()) {
        surface(458, 580, 403, 55, Palette.Pale, 25)
        label(book.themes.take(3).joinToString(" · "), 475, 584, 370, 50, 27, Palette.Dark, true)
    }
    label("책 소개", 460, 661, 706, 47, 29, Palette.Dark, true)
    label(book.summary, 460, 711, 702, 124, 29, lineSpacing = 1.42f, scroll = true)
    label("추천 이유", 460, 838, 706, 45, 29, Palette.Dark, true)
    label(model.selected?.reason.orEmpty(), 460, 887, 702, 88, 29, lineSpacing = 1.42f, scroll = true)
    val music = data.music
    if (music == null) {
        label("함께 들을 음악을 찾지 못했어요.", 1278, 448, 462, 100, 30, Palette.Muted, lines = 2)
        return
    }
    label(music.title, 1278, 435, 470, 62, 42, bold = true)
    label(music.style, 1278, 506, 470, 54, 28, Palette.Muted)
    val link = music.youtubeUrl.playableMusicLink()
    surface(1363, 578, 304, 304, Palette.Pale, 22)
    if (link == null) {
        label("음악 링크 준비 중", 1368, 696, 294, 63, 29, Palette.Dark, true, TextAlign.Center)
    } else {
        musicQr(link, 1363, 578, 304) { model.onQrShown(music.musicId) }
        label("휴대폰으로 스캔해 음악 듣기", 1265, 912, 500, 60, 27, Palette.Muted, align = TextAlign.Center)
    }
}
