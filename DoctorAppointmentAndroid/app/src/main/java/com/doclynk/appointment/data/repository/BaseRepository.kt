package com.doclynk.appointment.data.repository

import com.doclynk.appointment.data.model.ApiResult
import org.json.JSONObject
import retrofit2.Response

open class BaseRepository {
    suspend fun <T> safeApiCall(apiCall: suspend () -> Response<T>): ApiResult<T> {
        return try {
            val response = apiCall()
            if (response.isSuccessful) {
                val data = response.body()
                if (data != null) {
                    ApiResult.Success(data)
                } else {
                    ApiResult.Error("Empty response from server")
                }
            } else {
                val errorBody = response.errorBody()?.string().orEmpty()
                val parsedMessage = parseBackendMessage(errorBody)
                if (parsedMessage.isNotBlank()) {
                    ApiResult.Error(parsedMessage)
                } else {
                    ApiResult.Error("Request failed with code ${response.code()}")
                }
            }
        } catch (e: Exception) {
            ApiResult.Error(e.message ?: "Unknown error occurred")
        }
    }

    private fun parseBackendMessage(errorBody: String): String {
        if (errorBody.isBlank()) return ""
        return try {
            JSONObject(errorBody).optString("message", errorBody)
        } catch (_: Exception) {
            errorBody
        }
    }
}
