package com.bookmood.app

import androidx.compose.runtime.Composable
import com.bookmood.app.screens.ArrivalScreen
import com.bookmood.app.screens.BookDetailScreen
import com.bookmood.app.screens.FinishScreen
import com.bookmood.app.screens.GenreScreen
import com.bookmood.app.screens.GoalScreen
import com.bookmood.app.screens.LengthScreen
import com.bookmood.app.screens.LoadingScreen
import com.bookmood.app.screens.NavigationScreen
import com.bookmood.app.screens.RecommendAgainScreen
import com.bookmood.app.screens.RecommendationsScreen
import com.bookmood.app.screens.WelcomeScreen

@Composable
internal fun BookMoodApp(model: BookMoodViewModel) {
    PrototypeCanvas {
        when (model.screen) {
            Screen.WELCOME -> WelcomeScreen(model::start)
            Screen.GOAL -> GoalScreen(model)
            Screen.GENRE -> GenreScreen(model)
            Screen.LENGTH -> LengthScreen(model)
            Screen.LOADING -> LoadingScreen(model)
            Screen.RECOMMENDATIONS -> RecommendationsScreen(model)
            Screen.RECOMMEND_AGAIN -> RecommendAgainScreen(model)
            Screen.DETAIL -> BookDetailScreen(model)
            Screen.NAVIGATION -> NavigationScreen(model)
            Screen.ARRIVAL -> ArrivalScreen(model)
            Screen.FINISH -> FinishScreen(model)
        }
    }
}
