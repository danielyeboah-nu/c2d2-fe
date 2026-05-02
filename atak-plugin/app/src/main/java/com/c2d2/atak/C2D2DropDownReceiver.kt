package com.c2d2.atak

import android.content.Context
import android.content.SharedPreferences
import android.view.LayoutInflater
import android.view.View
import android.widget.*
import com.atakmap.android.dropdown.DropDownReceiver
import com.atakmap.android.maps.MapView
import com.atakmap.coremap.log.Log
import com.c2d2.atak.api.BackendApi
import com.c2d2.atak.overlay.TeamOverlayManager
import com.c2d2.atak.service.BackendSyncService
import kotlinx.coroutines.*
import android.content.Intent

/**
 * Main side-panel UI for the C2D2 ATAK plugin.
 *
 * Tabs:
 *   1. STATUS   — log sleep hours + injury status, push readiness to backend
 *   2. TEAMS    — select a mission and load team overlay onto map
 *   3. SETTINGS — enter backend token + link device to a soldier record
 */
class C2D2DropDownReceiver(
    mapView: MapView,
    private val pluginContext: Context,
) : DropDownReceiver(mapView) {

    companion object {
        const val TAG         = "C2D2DropDown"
        const val SHOW_ACTION = "com.c2d2.atak.SHOW_PANEL"
        const val PREFS_NAME  = "c2d2_prefs"
        const val PREF_TOKEN  = "token"
        const val PREF_UID    = "tak_uid"
        const val PREF_SOLDIER_ID = "soldier_id"
    }

    private val scope   = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private val prefs: SharedPreferences =
        pluginContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    private lateinit var overlay: TeamOverlayManager
    private var api: BackendApi? = null
    private var rootView: View? = null

    // ── DropDownReceiver overrides ────────────────────────────────────────────

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != SHOW_ACTION) return
        showDropDown(
            getDropDownView(),
            HALF_WIDTH, FULL_HEIGHT,
            HALF_WIDTH, FULL_HEIGHT,
            false
        )
    }

    override fun disposeImpl() {
        scope.cancel()
        if (::overlay.isInitialized) overlay.destroy()
    }

    // ── View ──────────────────────────────────────────────────────────────────

    private fun getDropDownView(): View {
        if (rootView != null) return rootView!!

        val inflater = LayoutInflater.from(pluginContext)
        val view = inflater.inflate(R.layout.dropdown_c2d2, null)
        rootView = view

        overlay = TeamOverlayManager(pluginContext, mapView)
        setupSettingsTab(view)
        setupStatusTab(view)
        setupTeamsTab(view)
        refreshApiFromPrefs()

        return view
    }

    // ── Settings tab ─────────────────────────────────────────────────────────

    private fun setupSettingsTab(root: View) {
        val tokenField  = root.findViewById<EditText>(R.id.edit_token)
        val soldierSpinner = root.findViewById<Spinner>(R.id.spinner_soldier)
        val saveBtn     = root.findViewById<Button>(R.id.btn_save_settings)
        val statusText  = root.findViewById<TextView>(R.id.tv_settings_status)

        tokenField.setText(prefs.getString(PREF_TOKEN, ""))

        saveBtn.setOnClickListener {
            val token = tokenField.text.toString().trim()
            if (token.isEmpty()) { statusText.text = "Token required"; return@setOnClickListener }

            prefs.edit().putString(PREF_TOKEN, token).apply()
            api = BackendApi(token)
            statusText.text = "Saved. Loading soldiers…"

            scope.launch {
                try {
                    val soldiers = withContext(Dispatchers.IO) { api!!.listSoldiers() }
                    val adapter = ArrayAdapter(
                        pluginContext,
                        android.R.layout.simple_spinner_item,
                        soldiers.map { "${it.rank} ${it.name} (${it.unit ?: "—"})" }
                    )
                    adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                    soldierSpinner.adapter = adapter

                    soldierSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                        override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                            val soldier = soldiers[pos]
                            val takUid  = mapView.selfMarker?.uid ?: "UNKNOWN"
                            prefs.edit()
                                .putInt(PREF_SOLDIER_ID, soldier.id)
                                .putString(PREF_UID, takUid)
                                .apply()

                            scope.launch(Dispatchers.IO) {
                                try {
                                    api!!.linkDevice(soldier.id, takUid)
                                    withContext(Dispatchers.Main) {
                                        statusText.text = "Linked: ${soldier.rank} ${soldier.name} ↔ $takUid"
                                        startSyncService(token, takUid)
                                    }
                                } catch (e: Exception) {
                                    withContext(Dispatchers.Main) { statusText.text = "Link failed: ${e.message}" }
                                }
                            }
                        }
                        override fun onNothingSelected(p: AdapterView<*>?) {}
                    }
                    statusText.text = "${soldiers.size} soldiers loaded"
                } catch (e: Exception) {
                    statusText.text = "Error: ${e.message}"
                    Log.e(TAG, "Load soldiers failed", e)
                }
            }
        }
    }

    // ── Status / Readiness tab ────────────────────────────────────────────────

    private fun setupStatusTab(root: View) {
        val sleep24     = root.findViewById<EditText>(R.id.edit_sleep_24h)
        val sleep48     = root.findViewById<EditText>(R.id.edit_sleep_48h)
        val injurySpinner = root.findViewById<Spinner>(R.id.spinner_injury)
        val opSpinner   = root.findViewById<Spinner>(R.id.spinner_op_status)
        val submitBtn   = root.findViewById<Button>(R.id.btn_submit_readiness)
        val resultText  = root.findViewById<TextView>(R.id.tv_readiness_result)

        ArrayAdapter.createFromResource(pluginContext, R.array.injury_statuses, android.R.layout.simple_spinner_item)
            .also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item); injurySpinner.adapter = it }

        ArrayAdapter.createFromResource(pluginContext, R.array.op_statuses, android.R.layout.simple_spinner_item)
            .also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item); opSpinner.adapter = it }

        submitBtn.setOnClickListener {
            val a = api ?: run { resultText.text = "Set token in Settings first"; return@setOnClickListener }
            val takUid = prefs.getString(PREF_UID, "") ?: ""
            if (takUid.isEmpty()) { resultText.text = "Link device in Settings first"; return@setOnClickListener }

            val h24 = sleep24.text.toString().toFloatOrNull() ?: run { resultText.text = "Enter valid sleep hours"; return@setOnClickListener }
            val h48 = sleep48.text.toString().toFloatOrNull() ?: h24 * 2f

            val injuryValues = arrayOf("fit", "light_duty", "unfit")
            val opValues     = arrayOf("available", "on_mission", "rest", "casualty")
            val injury = injuryValues[injurySpinner.selectedItemPosition]
            val opStatus = opValues[opSpinner.selectedItemPosition]

            scope.launch(Dispatchers.IO) {
                try {
                    a.postReadiness(BackendApi.ReadinessPayload(takUid, h24, h48, injury))
                    // Also update position with new operational status
                    val self = mapView.selfMarker?.point
                    if (self != null) {
                        a.postPosition(BackendApi.PositionPayload(takUid, self.latitude, self.longitude, null, opStatus))
                    }
                    withContext(Dispatchers.Main) { resultText.text = "Readiness updated" }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) { resultText.text = "Error: ${e.message}" }
                }
            }
        }
    }

    // ── Teams tab ─────────────────────────────────────────────────────────────

    private fun setupTeamsTab(root: View) {
        val missionIdField = root.findViewById<EditText>(R.id.edit_mission_id)
        val loadBtn        = root.findViewById<Button>(R.id.btn_load_team)
        val clearBtn       = root.findViewById<Button>(R.id.btn_clear_overlay)
        val teamResult     = root.findViewById<TextView>(R.id.tv_team_result)

        loadBtn.setOnClickListener {
            val a = api ?: run { teamResult.text = "Set token in Settings first"; return@setOnClickListener }
            val missionId = missionIdField.text.toString().toIntOrNull()
                ?: run { teamResult.text = "Enter a valid mission ID"; return@setOnClickListener }

            scope.launch {
                try {
                    val options = withContext(Dispatchers.IO) { a.getTeamOptions(missionId) }
                    if (options.isEmpty()) { teamResult.text = "No compositions for mission $missionId"; return@launch }

                    // Show best composition (rank 1) on map
                    val best = options.minByOrNull { it.composition_rank } ?: options.first()
                    overlay.showTeam(best)

                    val summary = best.members.joinToString("\n") {
                        "• ${it.name} (${it.role}) ${(it.fit_score * 100).toInt()}%"
                    }
                    teamResult.text = "Option ${best.composition_rank} loaded:\n$summary"
                } catch (e: Exception) {
                    teamResult.text = "Error: ${e.message}"
                    Log.e(TAG, "Load team failed", e)
                }
            }
        }

        clearBtn.setOnClickListener {
            overlay.clearTeam()
            teamResult.text = "Overlay cleared"
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private fun refreshApiFromPrefs() {
        val token = prefs.getString(PREF_TOKEN, "") ?: ""
        if (token.isNotEmpty()) {
            api = BackendApi(token)
            val takUid = prefs.getString(PREF_UID, "") ?: ""
            if (takUid.isNotEmpty()) startSyncService(token, takUid)
        }
    }

    private fun startSyncService(token: String, takUid: String) {
        val intent = Intent(pluginContext, BackendSyncService::class.java).apply {
            putExtra(BackendSyncService.EXTRA_TOKEN,   token)
            putExtra(BackendSyncService.EXTRA_TAK_UID, takUid)
        }
        pluginContext.startService(intent)
    }
}
