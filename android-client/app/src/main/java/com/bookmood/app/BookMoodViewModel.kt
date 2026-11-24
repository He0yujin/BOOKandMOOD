package com.bookmood.app

import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bookmood.app.navigation.TemiNavigationController
import com.bookmood.app.navigation.TemiNavigationController.State
import com.bookmood.app.network.ApiResult
import com.bookmood.app.network.BookDetailResponseDto
import com.bookmood.app.network.BookMoodClient
import com.bookmood.app.network.EventRequestDto
import com.bookmood.app.network.RecommendationItemDto
import com.bookmood.app.network.RecommendationRequestDto
import com.bookmood.app.network.SurveyAnswersDto
import java.net.URI
import java.util.UUID
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

internal enum class Screen {
    WELCOME, GOAL, GENRE, LENGTH, LOADING, RECOMMENDATIONS, RECOMMEND_AGAIN,
    DETAIL, NAVIGATION, ARRIVAL, FINISH
}

internal class BookMoodViewModel : ViewModel() {
    var screen by mutableStateOf(Screen.WELCOME)
        private set
    var goal by mutableStateOf<String?>(null)
    var genre by mutableStateOf<String?>(null)
    var depth by mutableStateOf<Int?>(null)
    var recommendations by mutableStateOf(emptyList<RecommendationItemDto>())
        private set
    var selected by mutableStateOf<RecommendationItemDto?>(null)
        private set
    var detail by mutableStateOf<BookDetailResponseDto?>(null)
        private set
    var problem by mutableStateOf<ApiResult.Error?>(null)
        private set
    var navigationState by mutableStateOf(State.NOT_READY)
        private set
    var navigationMessage by mutableStateOf("")
        private set
    var stopping by mutableStateOf(false)
        private set

    private var sessionId = ""
    private var robot: TemiNavigationController? = null
    private var pending: Job? = null
    private var lastRequest: RecommendationRequestDto? = null
    private var lastSuccessfulRequest: RecommendationRequestDto? = null
    private var editQuestion: Screen? = null
    private var editOriginAnswers: SurveyAnswersDto? = null
    private var returnPending = false
    private var navigationLogged = false
    private var serverBase = BuildConfig.BOOK_MOOD_BASE_URL
    private val loggedMusic = mutableSetOf<Pair<String, String>>()

    fun configureServer(url: String) {
        val normalized = if (url.endsWith("/")) url else "$url/"
        BookMoodClient.setBaseUrl(normalized)
        serverBase = normalized
    }

    fun coverUrl(path: String): String? =
        path.takeIf(String::isNotBlank)?.let { raw ->
            runCatching { URI(serverBase).resolve(raw).toString() }.getOrNull()
                ?.takeIf { it.startsWith("https://") || it.startsWith("http://") }
        }

    fun attachRobot(controller: TemiNavigationController?) {
        robot = controller
    }

    fun start() {
        reset()
        sessionId = UUID.randomUUID().toString()
        screen = Screen.GOAL
    }

    fun advanceQuestion() {
        val active = screen
        when {
            active == Screen.GOAL && goal == null -> return
            active == Screen.GENRE && genre == null -> return
            active == Screen.LENGTH && depth == null -> return
        }
        if (editQuestion == active || active == Screen.LENGTH) {
            requestRecommendations()
        } else {
            screen = when (active) {
                Screen.GOAL -> Screen.GENRE
                Screen.GENRE -> Screen.LENGTH
                else -> active
            }
        }
    }

    fun showRerecommend() {
        problem = null
        screen = Screen.RECOMMEND_AGAIN
    }

    fun edit(which: Screen) {
        editOriginAnswers = answers()
        editQuestion = which
        screen = which
    }

    fun recommendAgain() {
        val previous = lastSuccessfulRequest ?: return
        executeRecommendations(previous.copy(
            excludeBookIds = recommendations.map { it.bookId },
            feedbackType = null
        ))
    }

    fun retryRecommendations(relaxGoal: Boolean = false) {
        lastRequest?.let {
            executeRecommendations(it.copy(allowGoalRelaxation = relaxGoal || it.allowGoalRelaxation))
        }
    }

    private fun answers(): SurveyAnswersDto? {
        return SurveyAnswersDto(goal ?: return null, genre ?: return null, depth ?: return null)
    }

    private fun requestRecommendations() {
        val answers = answers() ?: return
        val feedback = when (editQuestion) {
            Screen.GOAL -> "different_mood"
            Screen.GENRE -> "different_genre"
            else -> null
        }
        executeRecommendations(
            RecommendationRequestDto(
                sessionId = sessionId,
                answers = answers,
                feedbackType = feedback
            )
        )
    }

    private fun executeRecommendations(request: RecommendationRequestDto) {
        pending?.cancel()
        lastRequest = request
        problem = null
        screen = Screen.LOADING
        pending = viewModelScope.launch {
            when (val result = BookMoodClient.getRecommendations(request)) {
                is ApiResult.Success -> {
                    val cards = result.data.recommendations.filter { it.book != null }
                    if (cards.size != 3) {
                        problem = ApiResult.Error("INCOMPLETE", "추천 도서 정보를 모두 받지 못했어요.")
                    } else {
                        lastSuccessfulRequest = request
                        recommendations = cards
                        editQuestion = null
                        editOriginAnswers = null
                        screen = Screen.RECOMMENDATIONS
                    }
                }
                is ApiResult.Error -> problem = result
            }
        }
    }

    fun chooseBook(item: RecommendationItemDto) {
        pending?.cancel()
        selected = item
        detail = null
        problem = null
        screen = Screen.DETAIL
        pending = viewModelScope.launch {
            when (val result = BookMoodClient.getBookDetail(item.bookId)) {
                is ApiResult.Success -> {
                    detail = result.data
                    log("book_selected")
                }
                is ApiResult.Error -> problem = result
            }
        }
    }

    fun retryDetail() {
        selected?.let(::chooseBook)
    }

    fun onQrShown(musicId: String) {
        val bookId = selected?.bookId ?: return
        if (loggedMusic.add(bookId to musicId)) log("qr_displayed", musicId)
    }

    fun startShelf() {
        val poiId = detail?.book?.poiId ?: return
        screen = Screen.NAVIGATION
        navigationLogged = false
        stopping = false
        navigationState = State.STARTING
        val controller = robot
        if (controller == null) {
            onNavigationEvent(TemiNavigationController.NavigationEvent(
                State.NOT_READY, poiId, "테미 실기기에 연결한 뒤 서가 안내를 시작할 수 있어요."
            ))
            return
        }
        if (controller.goToBookShelf(poiId)) {
            navigationLogged = true
            log("nav_started")
        } else if (navigationState == State.STARTING) {
            navigationState = State.FAILED
            navigationMessage = "이전 이동 상태를 확인한 뒤 다시 시도해 주세요."
        }
    }

    fun stopNavigation() {
        if (stopping || navigationState !in setOf(State.STARTING, State.MOVING)) return
        stopping = true
        if (robot?.cancelMovement() != true) stopping = false
    }

    fun endGuide() {
        screen = Screen.FINISH
        returnHome()
    }

    fun returnHome() {
        if (returnPending) return
        val controller = robot
        if (controller == null) {
            navigationState = State.NOT_READY
            navigationMessage = "테미 실기기에 연결해 주세요."
            return
        }
        returnPending = true
        if (!controller.returnToHome()) {
            returnPending = false
            if (navigationState == State.ARRIVED || navigationState == State.RETURNING) {
                navigationState = State.FAILED
                navigationMessage = "복귀를 시작하지 못했어요. 다시 시도해 주세요."
            }
        }
    }

    fun onNavigationEvent(event: TemiNavigationController.NavigationEvent) {
        if (screen != Screen.NAVIGATION && screen != Screen.FINISH) return
        // Readiness notifications can arrive while displaying a terminal state.
        if (event.state == State.IDLE) return
        navigationState = event.state
        navigationMessage = event.message
        when (event.state) {
            State.ARRIVED -> {
                stopping = false
                log("nav_arrived")
                screen = Screen.ARRIVAL
            }
            State.HOME_ARRIVED -> {
                returnPending = false
                log("returned_home")
            }
            State.FAILED, State.NOT_READY, State.CANCELLED -> {
                stopping = false
                returnPending = false
                if (event.state != State.CANCELLED && (screen == Screen.NAVIGATION || navigationLogged)) {
                    log("nav_failed", metadata = mapOf(
                        "poi_id" to event.poiId.orEmpty(),
                        "message" to event.message
                    ))
                }
                navigationLogged = false
            }
            else -> Unit
        }
    }

    fun finish() {
        if (returnPending) return
        reset()
    }

    fun back() {
        when (screen) {
            Screen.GOAL, Screen.GENRE, Screen.LENGTH -> {
                val active = screen
                if (editQuestion != null) {
                    restoreAnswers()
                    screen = Screen.RECOMMEND_AGAIN
                } else if (active == Screen.GOAL) {
                    reset()
                } else {
                    screen = if (active == Screen.GENRE) Screen.GOAL else Screen.GENRE
                }
            }
            Screen.LOADING -> {
                pending?.cancel()
                pending = null
                problem = null
                if (recommendations.isNotEmpty()) {
                    restoreAnswers()
                    screen = Screen.RECOMMEND_AGAIN
                } else {
                    screen = Screen.LENGTH
                }
            }
            Screen.RECOMMENDATIONS -> screen = Screen.LENGTH
            Screen.RECOMMEND_AGAIN -> screen = Screen.RECOMMENDATIONS
            Screen.DETAIL -> {
                pending?.cancel()
                problem = null
                screen = Screen.RECOMMENDATIONS
            }
            Screen.NAVIGATION -> {
                if (navigationState in setOf(State.CANCELLED, State.FAILED, State.NOT_READY) && !stopping) {
                    screen = Screen.DETAIL
                } else {
                    stopNavigation()
                }
            }
            Screen.ARRIVAL, Screen.FINISH, Screen.WELCOME -> Unit
        }
    }

    private fun restoreAnswers() {
        editOriginAnswers?.let {
            goal = it.goal
            genre = it.genre
            depth = it.depth
        }
        editOriginAnswers = null
        editQuestion = null
    }

    private fun reset() {
        pending?.cancel()
        pending = null
        goal = null
        genre = null
        depth = null
        recommendations = emptyList()
        detail = null
        selected = null
        lastRequest = null
        lastSuccessfulRequest = null
        problem = null
        editQuestion = null
        editOriginAnswers = null
        sessionId = ""
        navigationMessage = ""
        navigationLogged = false
        returnPending = false
        stopping = false
        loggedMusic.clear()
        screen = Screen.WELCOME
    }

    private fun log(event: String, musicId: String? = null, metadata: Map<String, Any> = emptyMap()) {
        if (sessionId.isBlank()) return
        val payload = EventRequestDto(sessionId, event, selected?.bookId, musicId, metadata)
        viewModelScope.launch { BookMoodClient.recordEvent(payload) }
    }
}

internal fun String?.playableMusicLink(): String? {
    val raw = this ?: return null
    val url = Uri.parse(raw)
    val host = url.host?.lowercase() ?: return null
    if (url.scheme != "https" || host !in setOf("www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be")) return null
    val video = if (host == "youtu.be") url.lastPathSegment else url.getQueryParameter("v")
    val playlist = url.getQueryParameter("list")
    return raw.takeIf {
        video?.matches(Regex("[A-Za-z0-9_-]{11}")) == true ||
            (!playlist.isNullOrBlank() && playlist.matches(Regex("[A-Za-z0-9_-]{10,}")))
    }
}
