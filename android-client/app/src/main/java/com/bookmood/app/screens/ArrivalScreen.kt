package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.Palette
import com.bookmood.app.PrototypeLayout

@Composable
internal fun PrototypeLayout.ArrivalScreen(model: BookMoodViewModel) {
    header("서가 안내")
    title("서가에 도착했어요", "책등 아래쪽의 청구기호를 확인해 주세요.")
    surface(147, 422, 1627, 490, Palette.Mint, 30)
    label("청구기호", 215, 488, 1470, 56, 32, Palette.Dark, true)
    val book = model.detail?.book
    val callNumber = book?.callNumber.orEmpty()
    val size = if (callNumber.length > 22) 78 else 115
    label(callNumber, 211, 586, 1470, 155, size, Palette.Dark, true)
    label(book?.shelfLabel.orEmpty(), 216, 770, 1460, 62, 31, Palette.Muted)
    footerRule()
    button("안내 종료", 1410, 1058, 364, action = model::endGuide)
}
