package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import com.bookmood.app.Palette
import com.bookmood.app.PrototypeLayout

internal data class Choice<T>(val caption: String, val value: T, val subtitle: String? = null)

@Composable
internal fun <T> PrototypeLayout.QuestionScreen(
    index: Int, title: String, hint: String, choices: List<Choice<T>>, selected: T?,
    onChoice: (T) -> Unit, onBack: () -> Unit, onNext: () -> Unit
) {
    header("질문  $index / 3")
    title(title, hint)
    repeat(3) {
        surface(148 + it * 75, 370, 60, 8, if (it < index) Palette.Teal else Palette.Sage, 4)
    }
    choices.forEachIndexed { position, choice ->
        option(
            choice.caption, 148 + position % 2 * 830, 450 + position / 2 * 248,
            choice.value == selected, { onChoice(choice.value) }, choice.subtitle
        )
    }
    footerRule()
    button("이전", 146, 1058, 200, false, action = onBack)
    button(if (index == 3) "추천 받기" else "다음으로", 1410, 1058, 364, enabled = selected != null, action = onNext)
}
