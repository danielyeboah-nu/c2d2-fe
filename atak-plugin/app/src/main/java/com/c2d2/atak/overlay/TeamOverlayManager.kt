package com.c2d2.atak.overlay

import android.content.Context
import android.graphics.Color
import com.atakmap.android.maps.MapGroup
import com.atakmap.android.maps.MapView
import com.atakmap.android.maps.Marker
import com.atakmap.coremap.log.Log
import com.atakmap.coremap.maps.data.GeoPoint
import com.c2d2.atak.api.BackendApi
import kotlinx.coroutines.*
import java.util.UUID

/**
 * Draws team composition members as ATAK map markers.
 *
 * Call showTeam() with a Composition from the backend to add coloured
 * markers for each team member onto the ATAK map.
 * Call clearTeam() to remove them.
 */
class TeamOverlayManager(
    private val context: Context,
    private val mapView: MapView,
) {
    companion object {
        const val TAG        = "C2D2Overlay"
        const val GROUP_NAME = "C2D2 Team"
        // CoT type: atom / friendly / ground / unit / combat
        const val MARKER_TYPE = "a-f-G-U-C"
    }

    private val scope     = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var mapGroup: MapGroup? = null

    // ── Public API ────────────────────────────────────────────────────────────

    fun showTeam(composition: BackendApi.Composition) {
        clearTeam()

        val group = MapGroup(GROUP_NAME)
        mapView.rootGroup.addGroup(group)
        mapGroup = group

        composition.members.forEachIndexed { index, member ->
            // Members don't have positions in the team API response — place them
            // near map centre with a small offset so they're visible until real
            // positions come in via position sync.
            val centre = mapView.point
            val offsetLat = centre.latitude  + (index - composition.members.size / 2) * 0.0005
            val offsetLon = centre.longitude + 0.001

            val marker = Marker(
                GeoPoint(offsetLat, offsetLon),
                UUID.randomUUID().toString()
            )
            marker.setType(MARKER_TYPE)
            marker.title = member.name
            marker.setMetaString("callsign", member.name)
            marker.setMetaString("role",     member.role)
            marker.setMetaDouble("fit_score", member.fit_score)
            member.fit_notes?.let { marker.setMetaString("fit_notes", it) }

            // Colour-code by fit score: green ≥ 0.75, amber ≥ 0.55, red < 0.55
            marker.setMetaInteger("color", when {
                member.fit_score >= 0.75 -> Color.GREEN
                member.fit_score >= 0.55 -> Color.YELLOW
                else                     -> Color.RED
            })

            group.addItem(marker)
            Log.d(TAG, "Marker added: ${member.name} role=${member.role} fit=${member.fit_score}")
        }
    }

    fun clearTeam() {
        mapGroup?.let { g ->
            mapView.rootGroup.removeGroup(g)
            mapGroup = null
        }
    }

    fun destroy() {
        clearTeam()
        scope.cancel()
    }
}
