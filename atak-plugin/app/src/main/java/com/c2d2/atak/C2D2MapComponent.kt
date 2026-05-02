package com.c2d2.atak

import android.content.Context
import android.content.Intent
import com.atakmap.android.dropdown.DropDownMapComponent
import com.atakmap.android.ipc.AtakBroadcast
import com.atakmap.android.maps.MapView
import com.atakmap.coremap.log.Log

/**
 * ATAK MapComponent — wires the plugin's DropDownReceiver into the ATAK
 * side-panel system and registers intent filters so ATAK can open the panel.
 */
class C2D2MapComponent : DropDownMapComponent() {

    companion object { const val TAG = "C2D2MapComponent" }

    private lateinit var dropDown: C2D2DropDownReceiver

    override fun onCreate(context: Context, intent: Intent, view: MapView) {
        super.onCreate(context, intent, view)
        Log.d(TAG, "C2D2 plugin starting")

        dropDown = C2D2DropDownReceiver(view, context)

        AtakBroadcast.getInstance().registerReceiver(
            dropDown,
            AtakBroadcast.DocumentedIntentFilter(
                C2D2DropDownReceiver.SHOW_ACTION,
                "Open C2D2 panel"
            )
        )
    }

    override fun onDestroyImpl(context: Context, view: MapView) {
        AtakBroadcast.getInstance().unregisterReceiver(dropDown)
        super.onDestroyImpl(context, view)
        Log.d(TAG, "C2D2 plugin destroyed")
    }
}
