package com.bookmood.app.navigation

import android.os.Looper
import android.util.Log
import com.robotemi.sdk.Robot
import com.robotemi.sdk.listeners.OnGoToLocationStatusChangedListener
import com.robotemi.sdk.listeners.OnRobotReadyListener

/**
 * BOOK & MOOD / temi V1 navigation controller.
 *
 * Integration contract:
 *  - Create ONE instance for the active app session (not once per recomposition).
 *  - call start() in Activity.onStart(), close() in Activity.onStop().
 *  - call goToBookShelf(book.poiId) ONLY after the user presses the move button.
 *  - call returnToHome() ONLY after the user finishes the guide/evaluation.
 *  - Register actual temi POIs (including the standby POI) before testing movement.
 *  - Methods are called from Android's main thread.
 *  - Never issue navigation commands from an emulator or before SDK readiness.
 *
 * This class intentionally does NOT speak or play audio in the library.
 */
class TemiNavigationController(
    private val standbyPoiId: String = "HOME_STANDBY",
    private val onStateChanged: (NavigationEvent) -> Unit
) : OnRobotReadyListener, OnGoToLocationStatusChangedListener {

    enum class State {
        NOT_READY, IDLE, STARTING, MOVING, ARRIVED,
        RETURNING, HOME_ARRIVED, CANCELLED, FAILED
    }

    data class NavigationEvent(
        val state: State,
        val poiId: String? = null,
        val message: String = "",
        val descriptionId: Int? = null
    )

    private val robot: Robot = Robot.getInstance()
    private var registered = false
    private var ready = false
    private var activePoi: String? = null
    private var returningHome = false
    private var cancelRequested = false

    var currentState: State = State.NOT_READY
        private set

    /** Subscribe to temi callbacks. Call from Activity.onStart(). */
    fun start() {
        requireMainThread()
        if (registered) return
        robot.addOnRobotReadyListener(this)
        robot.addOnGoToLocationStatusChangedListener(this)
        registered = true
        emit(State.NOT_READY, message = "테미 연결을 확인하고 있습니다.")
    }

    /** Unsubscribe to avoid stale callbacks. Does NOT cancel ongoing movement. */
    fun close() {
        requireMainThread()
        if (!registered) return
        robot.removeOnRobotReadyListener(this)
        robot.removeOnGoToLocationStatusChangedListener(this)
        registered = false
        ready = false
        // Never start a new movement here. The owner must explicitly decide
        // what to do if it is leaving while temi is moving.
    }

    override fun onRobotReady(isReady: Boolean) {
        requireMainThread()
        ready = isReady
        if (!isReady) {
            activePoi = null
            returningHome = false
            cancelRequested = false
            emit(State.NOT_READY, message = "테미 연결이 끊어졌습니다.")
        } else if (activePoi == null) {
            emit(State.IDLE, message = "이동할 준비가 되었습니다.")
        }
    }

    /** Retrieve map POI names after temi is ready; helpful when mapping shelves. */
    fun getSavedPoiNames(): List<String> {
        requireMainThread()
        return if (ready) robot.locations.toList() else emptyList()
    }

    /**
     * Start shelf navigation. Returns false when readiness, name or state
     * validation fails. 'true' means a request was sent, NOT arrival.
     */
    fun goToBookShelf(poiId: String): Boolean = sendMove(poiId, isReturn = false)

    /**
     * Stop an ongoing navigation request. The ABORT callback can follow;
     * its reason will be mapped to CANCELLED rather than FAILED.
     */
    fun cancelMovement(): Boolean {
        requireMainThread()
        if (!ready || activePoi == null) return false
        cancelRequested = true
        return try {
            robot.stopMovement()
            true
        } catch (e: Exception) {
            cancelRequested = false
            emit(if (returningHome) State.RETURNING else State.MOVING, activePoi, "이동 중단 요청 실패: ${e.message.orEmpty()}")
            false
        }
    }

    /** Return to the service standby POI, NOT the charging station. */
    fun returnToHome(): Boolean = sendMove(standbyPoiId, isReturn = true)

    private fun sendMove(poiId: String, isReturn: Boolean): Boolean {
        requireMainThread()
        if (!registered || !ready) {
            emit(State.NOT_READY, poiId, "테미가 연결된 뒤 이동할 수 있습니다.")
            return false
        }
        val destination = poiId.trim()
        if (destination.isEmpty() || destination !in robot.locations) {
            emit(State.FAILED, destination, "테미 지도에 등록되지 않은 목적지입니다: $destination")
            return false
        }
        // Do not overwrite an in-progress request or initiate two movements.
        if (activePoi != null) {
            Log.w(TAG, "Move rejected; active=$activePoi, new=$destination")
            return false
        }
        activePoi = destination
        returningHome = isReturn
        cancelRequested = false
        emit(if (isReturn) State.RETURNING else State.STARTING,
            destination,
            if (isReturn) "대기 장소로 복귀를 시작합니다." else "서가로 이동을 시작합니다.")
        return try {
            robot.goTo(destination)
            true
        } catch (e: Exception) {
            activePoi = null
            returningHome = false
            emit(State.FAILED, destination, "이동 요청 실패: ${e.message.orEmpty()}")
            false
        }
    }

    override fun onGoToLocationStatusChanged(
        location: String,
        status: String,
        descriptionId: Int,
        description: String
    ) {
        requireMainThread()
        val target = activePoi ?: return
        if (location != target) return
        Log.d(TAG, "POI=$location status=$status id=$descriptionId $description")
        when (status) {
            OnGoToLocationStatusChangedListener.START,
            OnGoToLocationStatusChangedListener.CALCULATING -> {
                emit(if (returningHome) State.RETURNING else State.STARTING,
                    target, if (returningHome) "복귀 경로를 확인하고 있습니다." else "이동 경로를 확인하고 있습니다.",
                    descriptionId)
            }
            OnGoToLocationStatusChangedListener.GOING,
            OnGoToLocationStatusChangedListener.REPOSING -> {
                emit(if (returningHome) State.RETURNING else State.MOVING,
                    target, if (returningHome) "대기 장소로 복귀 중입니다." else "서가로 이동 중입니다.",
                    descriptionId)
            }
            OnGoToLocationStatusChangedListener.COMPLETE -> {
                val wasReturning = returningHome
                clearActive()
                emit(if (wasReturning) State.HOME_ARRIVED else State.ARRIVED,
                    target, if (wasReturning) "대기 장소로 복귀했습니다." else "서가에 도착했습니다.",
                    descriptionId)
            }
            OnGoToLocationStatusChangedListener.ABORT -> {
                val wasCancelled = cancelRequested
                clearActive()
                emit(if (wasCancelled) State.CANCELLED else State.FAILED,
                    target,
                    if (wasCancelled) "이동을 취소했습니다." else "이동을 완료하지 못했습니다: $description",
                    descriptionId)
            }
        }
    }

    private fun clearActive() {
        activePoi = null
        returningHome = false
        cancelRequested = false
    }

    private fun emit(
        state: State,
        poiId: String? = activePoi,
        message: String = "",
        descriptionId: Int? = null
    ) {
        currentState = state
        onStateChanged(NavigationEvent(state, poiId, message, descriptionId))
    }

    private fun requireMainThread() {
        check(Looper.myLooper() == Looper.getMainLooper()) {
            "TemiNavigationController must be called on the Android main thread"
        }
    }

    companion object {
        private const val TAG = "BookMoodTemiNav"
    }
}
