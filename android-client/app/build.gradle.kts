plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

val backendUrl = providers.gradleProperty("bookMoodBaseUrl").orElse("http://10.0.2.2:8000/")
val standbyPoi = providers.gradleProperty("bookMoodStandbyPoi").orElse("HOME_STANDBY")
fun buildConfigString(value: String) = "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

android {
    namespace = "com.bookmood.app"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.bookmood.app"
        minSdk = 23
        targetSdk = 32
        versionCode = 1
        versionName = "1.0"
        buildConfigField("String", "BOOK_MOOD_BASE_URL", buildConfigString(backendUrl.get()))
        buildConfigField("String", "STANDBY_POI", buildConfigString(standbyPoi.get()))
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

android.sourceSets.named("main") {
    kotlin.directories += "../network"
}

dependencies {
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.compose.foundation:foundation:1.10.4")
    implementation("androidx.compose.ui:ui:1.10.4")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.google.zxing:core:3.5.3")
    implementation("com.robotemi:sdk:1.138.0")
}
