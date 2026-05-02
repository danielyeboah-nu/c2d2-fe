package com.c2d2.atak.api

import com.c2d2.atak.BuildConfig
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

/**
 * Thin HTTP client for the C2D2 backend.
 *
 * All calls are synchronous — callers must dispatch off the main thread
 * (use BackendSyncService coroutine scope or a background thread).
 */
class BackendApi(private val token: String) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val base = BuildConfig.BACKEND_URL
    private val JSON = "application/json".toMediaType()
    private val XML  = "application/xml".toMediaType()

    // ── Auth ─────────────────────────────────────────────────────────────────

    data class LoginRequest(val email: String, val password: String)
    data class TokenResponse(val access_token: String, val token_type: String)

    fun login(email: String, password: String): TokenResponse {
        val body = gson.toJson(LoginRequest(email, password)).toRequestBody(JSON)
        return post("/api/v1/auth/login", body)
    }

    // ── Soldiers ─────────────────────────────────────────────────────────────

    data class SoldierSummary(val id: Int, val rank: String, val name: String, val unit: String?)

    fun listSoldiers(): List<SoldierSummary> {
        val json = get("/api/v1/soldiers")
        return gson.fromJson(json, object : TypeToken<List<SoldierSummary>>() {}.type)
    }

    // ── CoT / Position ────────────────────────────────────────────────────────

    data class LinkRequest(val soldier_id: Int, val tak_uid: String)
    data class PositionPayload(
        val tak_uid: String,
        val lat: Double,
        val lon: Double,
        val mgrs_grid: String?,
        val operational_status: String,
    )
    data class ReadinessPayload(
        val tak_uid: String,
        val sleep_hours_24h: Float,
        val sleep_hours_48h: Float,
        val injury_status: String,
    )

    fun linkDevice(soldierId: Int, takUid: String) {
        val body = gson.toJson(LinkRequest(soldierId, takUid)).toRequestBody(JSON)
        post<Map<String, Any>>("/api/v1/cot/link", body)
    }

    fun postPosition(payload: PositionPayload) {
        val body = gson.toJson(payload).toRequestBody(JSON)
        post<Map<String, Any>>("/api/v1/cot/position", body)
    }

    fun postReadiness(payload: ReadinessPayload) {
        val body = gson.toJson(payload).toRequestBody(JSON)
        post<Map<String, Any>>("/api/v1/cot/readiness", body)
    }

    fun postCotXml(xml: String) {
        val body = xml.toRequestBody(XML)
        val req = Request.Builder()
            .url("$base/api/v1/cot/position/raw")
            .header("Authorization", "Bearer $token")
            .post(body)
            .build()
        client.newCall(req).execute().use { /* fire and forget */ }
    }

    // ── Teams ─────────────────────────────────────────────────────────────────

    data class TeamMember(val name: String, val role: String, val fit_score: Double, val fit_notes: String?)
    data class Composition(val composition_rank: Int, val fit_score: Double, val rationale: String, val members: List<TeamMember>)
    data class TeamOptions(val mission_id: Int, val compositions: List<Composition>)

    fun getTeamOptions(missionId: Int): List<Composition> {
        val json = get("/api/v1/missions/$missionId/team-options")
        return gson.fromJson(json, object : TypeToken<List<Composition>>() {}.type)
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private fun get(path: String): String {
        val req = Request.Builder()
            .url("$base$path")
            .header("Authorization", "Bearer $token")
            .get()
            .build()
        client.newCall(req).execute().use { resp ->
            check(resp.isSuccessful) { "GET $path → ${resp.code}" }
            return resp.body!!.string()
        }
    }

    private inline fun <reified T> post(path: String, body: okhttp3.RequestBody): T {
        val req = Request.Builder()
            .url("$base$path")
            .header("Authorization", "Bearer $token")
            .post(body)
            .build()
        client.newCall(req).execute().use { resp ->
            check(resp.isSuccessful) { "POST $path → ${resp.code}" }
            return gson.fromJson(resp.body!!.string(), T::class.java)
        }
    }
}
