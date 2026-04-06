package com.doclynk.appointment.data.repository

import android.util.Log
import com.doclynk.appointment.data.model.ApiResult
import kotlinx.coroutines.delay
import org.json.JSONObject
import retrofit2.Response
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

open class BaseRepository {
    private val maxNetworkRetries = 1
    private val TAG = "DocLynk-API"

    suspend fun <T> safeApiCall(apiCall: suspend () -> Response<T>): ApiResult<T> {
        var attempt = 0
        val maxServerRetries = 12 // Give Render up to ~60 seconds to wake up (12 attempts * 5 sec)

        while (true) {
            try {
                val response = apiCall()
                Log.d(TAG, "📊 Response code: ${response.code()} | URL: ${response.raw().request.url}")

                if (response.isSuccessful) {
                    val data = response.body()
                    return if (data != null) {
                        ApiResult.Success(data)
                    } else {
                        ApiResult.Error("Empty response from server")
                    }
                } else if (response.code() in listOf(502, 503, 504) && attempt < maxServerRetries) {
                    Log.w(TAG, "⚠️ Server waking up (${response.code()}). Retrying attempt ${attempt + 1}/$maxServerRetries")
                    attempt++
                    delay(5000L) // Wait 5 seconds to let Render start
                    continue
                } else {
                    val errorBody = response.errorBody()?.string().orEmpty()
                    Log.e(TAG, "❌ Error ${response.code()}: $errorBody")

                    val parsedMessage = parseBackendMessage(errorBody)
                    val userMessage = mapHttpError(response.code(), parsedMessage)
                    return ApiResult.Error(userMessage)
                }
            } catch (e: Exception) {
                Log.e(TAG, "🔥 Exception: ${e.javaClass.simpleName} – ${e.message}")
                if (shouldRetry(e, attempt)) {
                    attempt++
                    delay(3000L)
                    continue
                }
                return ApiResult.Error(mapNetworkError(e))
            }
        }
    }

    /**
     * Maps well-known HTTP status codes to user-friendly messages.
     * Falls back to the backend message when available.
     */
    private fun mapHttpError(code: Int, backendMessage: String): String {
        return when (code) {
            400 -> if (backendMessage.isNotBlank()) backendMessage else "Bad request. Please check your input."
            401 -> if (backendMessage.isNotBlank()) backendMessage else "Unauthorized. Please log in again."
            403 -> "Access denied. You don't have permission for this action."
            404 -> "Endpoint not found (404). The requested URL does not exist on the server."
            405 -> "Method not allowed (405). The server does not accept this request method for this endpoint."
            409 -> if (backendMessage.isNotBlank()) backendMessage else "Conflict. This resource may already exist."
            422 -> if (backendMessage.isNotBlank()) backendMessage else "Invalid data submitted."
            429 -> "Too many requests. Please wait a moment and try again."
            500 -> "Internal server error. Please try again later."
            502 -> "Server is starting up or temporarily unavailable (502). Please wait 30-60 seconds and retry."
            503 -> "Server is under maintenance (503). Please try again shortly."
            504 -> "Server gateway timeout (504). The server took too long to respond."
            else -> if (backendMessage.isNotBlank()) backendMessage else "Request failed with code $code"
        }
    }

    private fun shouldRetry(e: Exception, attempt: Int): Boolean {
        if (attempt >= maxNetworkRetries) return false
        return e is SocketTimeoutException || e is ConnectException
    }

    private fun mapNetworkError(e: Exception): String {
        return when (e) {
            is SocketTimeoutException ->
                "Server is taking too long to respond. It may be waking up — please try again in 30 seconds."
            is ConnectException ->
                "Unable to connect to server. Check your internet connection and try again."
            is UnknownHostException ->
                "Server not reachable. Please verify network connectivity."
            is IOException ->
                "Network error occurred. Please try again."
            else -> e.message ?: "Unknown error occurred"
        }
    }

    private fun parseBackendMessage(errorBody: String): String {
        if (errorBody.isBlank()) return ""
        return try {
            val json = JSONObject(errorBody)
            // Try common field names used by backends
            json.optString("message", "")
                .ifBlank { json.optString("error", "") }
                .ifBlank { json.optString("detail", "") }
                .ifBlank { errorBody }
        } catch (_: Exception) {
            errorBody
        }
    }
}
