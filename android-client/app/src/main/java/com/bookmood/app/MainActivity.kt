package com.bookmood.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.bookmood.app.navigation.TemiNavigationController

class MainActivity : ComponentActivity() {
    private val model: BookMoodViewModel by viewModels()
    private var robot: TemiNavigationController? = null
    private val temiLauncherPackages = listOf("com.roboteam.teamy.usa", "com.roboteam.teamy.china")

    private fun packageInstalled(packageName: String): Boolean = runCatching {
        packageManager.getApplicationInfo(packageName, 0)
    }.isSuccess

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        hideSystemBars()

        if (BuildConfig.BOOK_MOOD_BASE_URL.isNotBlank()) {
            model.configureServer(BuildConfig.BOOK_MOOD_BASE_URL)
        }
        // The SDK has no service to bind to on the Android emulator.
        if (temiLauncherPackages.any(::packageInstalled)) {
            robot = TemiNavigationController(BuildConfig.STANDBY_POI, model::onNavigationEvent)
            model.attachRobot(robot)
        }
        setContent {
            BackHandler(enabled = model.screen != Screen.WELCOME) { model.back() }
            BookMoodApp(model)
        }
    }

    override fun onStart() {
        super.onStart()
        robot?.start()
    }

    override fun onDestroy() {
        robot?.close()
        model.attachRobot(null)
        super.onDestroy()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemBars()
    }

    private fun hideSystemBars() {
        WindowCompat.getInsetsController(window, window.decorView).apply {
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            hide(WindowInsetsCompat.Type.systemBars())
        }
    }
}
