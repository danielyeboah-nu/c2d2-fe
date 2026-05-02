package com.c2d2.atak

import android.content.Context
import android.content.Intent
import com.atakmap.android.maps.MapView
import com.atakmap.android.maps.MapComponent
import com.atakmap.coremap.log.Log
import transapps.maps.plugin.lifecycle.Lifecycle
import transapps.mapi.MapView as TransMapView

/**
 * Plugin lifecycle entry point — declared in AndroidManifest.xml as:
 *   <meta-data android:name="com.atakmap.app.COMPONENTS"
 *              android:value="com.c2d2.atak.C2D2PluginLifecycle"/>
 *
 * ATAK instantiates this class via reflection and calls the lifecycle hooks.
 */
class C2D2PluginLifecycle : Lifecycle {

    companion object { const val TAG = "C2D2Lifecycle" }

    private lateinit var component: C2D2MapComponent
    private lateinit var context:   Context

    override fun onCreate(ctx: Context, intent: Intent, transView: TransMapView) {
        context   = ctx
        component = C2D2MapComponent()
        Log.d(TAG, "Plugin onCreate")
        val mapView = MapView.getMapView()
        component.onCreate(ctx, intent, mapView)
    }

    override fun onStart() {}
    override fun onPause() {}
    override fun onResume() {}
    override fun onStop()  {}

    override fun onDestroy() {
        Log.d(TAG, "Plugin onDestroy")
        val mapView = MapView.getMapView()
        component.onDestroyImpl(context, mapView)
    }

    override fun onFinish() {}
}
