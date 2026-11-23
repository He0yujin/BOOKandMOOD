package com.bookmood.app.screens

import androidx.compose.runtime.Composable
import com.bookmood.app.BookMoodViewModel
import com.bookmood.app.PrototypeLayout
import com.bookmood.app.Screen

@Composable
internal fun PrototypeLayout.RecommendAgainScreen(model: BookMoodViewModel) {
    header("다시 추천받기")
    title("어떤 점을 바꾸고 싶나요?", "원하는 항목을 고르면 해당 질문으로 돌아가요.")
    option("독서 목적", 148, 430, true, { model.edit(Screen.GOAL) }, actionOnly = true, height = 204)
    option("책의 장르", 978, 430, false, { model.edit(Screen.GENRE) }, actionOnly = true, height = 204)
    option("책의 길이", 148, 674, false, { model.edit(Screen.LENGTH) }, actionOnly = true, height = 204)
    option("같은 조건으로 다시 추천", 978, 674, false, model::recommendAgain, actionOnly = true, height = 204)
    footerRule()
    button("이전", 146, 1058, 200, false, action = model::back)
}
