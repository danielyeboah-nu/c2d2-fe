package com.c2d2.atak.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import com.atakmap.android.maps.MapView
import com.atakmap.coremap.log.Log
import com.c2d2.atak.api.BackendApi
import kotlinx.coroutines.*

/**
 * Background service that periodically pushes the device's own GPS position
 * and any queued readiness updates to the C2D2 backend.
 *
 * Position sync interval: every 30 seconds while the service is running.
 * The service is started/stopped by C2D2MapComponent.
 */
class BackendSyncService : Service() {

    companion object {
        const val TAG              = "C2D2SyncService"
        const val EXTRA_TOKEN      = "token"
        const val EXTRA_TAK_UID    = "tak_uid"
        const val SYNC_INTERVAL_MS = 30_000L
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var syncJob: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val token  = intent?.getStringExtra(EXTRA_TOKEN)  ?: return START_NOT_STICKY
        val takUid = intent.getStringExtra(EXTRA_TAK_UID) ?: return START_NOT_STICKY

        syncJob?.cancel()
        syncJob = scope.launch { positionLoop(token, takUid) }
        Log.d(TAG, "Sync service started (uid=$takUid)")
        return START_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        Log.d(TAG, "Sync service stopped")
        super.onDestroy()
    }

    // ── Position loop ─────────────────────────────────────────────────────────

    private suspend fun positionLoop(token: String, takUid: String) {
        val api = BackendApi(token)
        while (isActive) {
            try {
                pushPosition(api, takUid)
            } catch (e: Exception) {
                Log.w(TAG, "Position push failed: ${e.message}")
            }
            delay(SYNC_INTERVAL_MS)
        }
    }

    private fun pushPosition(api: BackendApi, takUid: String) {
        val mapView = MapView.getMapView() ?: return
        val self    = mapView.selfMarker    ?: return
        val gp      = self.point            ?: return

        api.postPosition(
            BackendApi.PositionPayload(
                tak_uid            = takUid,
                lat                = gp.latitude,
                lon                = gp.longitude,
                mgrs_grid          = null,  // TODO: convert via MGRS library if available
                operational_status = "available",
            )
        )
        Log.d(TAG, "Position pushed: (${gp.latitude}, ${gp.longitude})")
    }
}
