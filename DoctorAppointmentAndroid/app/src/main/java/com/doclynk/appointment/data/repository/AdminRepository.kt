package com.doclynk.appointment.data.repository

import com.doclynk.appointment.data.api.ApiService
import com.doclynk.appointment.data.model.AdminAppointment
import com.doclynk.appointment.data.model.AdminDashboardResponse
import com.doclynk.appointment.data.model.AdminUser
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.model.MessageResponse
import com.doclynk.appointment.data.model.ToggleAdminRequest
import com.doclynk.appointment.data.model.UpdateStatusRequest

class AdminRepository(private val apiService: ApiService) : BaseRepository() {

    suspend fun getDashboard(token: String): ApiResult<AdminDashboardResponse> {
        return safeApiCall { apiService.getAdminDashboard("Bearer $token") }
    }

    suspend fun getUsers(token: String): ApiResult<List<AdminUser>> {
        return safeApiCall { apiService.getAdminUsers("Bearer $token") }
    }

    suspend fun toggleAdmin(token: String, userId: Int): ApiResult<MessageResponse> {
        return safeApiCall {
            apiService.toggleAdminStatus(
                token = "Bearer $token",
                body = ToggleAdminRequest(user_id = userId)
            )
        }
    }

    suspend fun deleteUser(token: String, userId: Int): ApiResult<MessageResponse> {
        return safeApiCall { apiService.deleteUser("Bearer $token", userId = userId) }
    }

    suspend fun getAppointments(token: String): ApiResult<List<AdminAppointment>> {
        return safeApiCall { apiService.getAdminAppointments("Bearer $token") }
    }

    suspend fun updateAppointmentStatus(
        token: String,
        appointmentId: Int,
        status: String
    ): ApiResult<MessageResponse> {
        return safeApiCall {
            apiService.updateAdminAppointmentStatus(
                token = "Bearer $token",
                body = UpdateStatusRequest(appointment_id = appointmentId, status = status)
            )
        }
    }

    suspend fun deleteAppointment(token: String, appointmentId: Int): ApiResult<MessageResponse> {
        return safeApiCall { apiService.deleteAdminAppointment("Bearer $token", appointmentId = appointmentId) }
    }

    suspend fun seedDoctorAppointments(token: String): ApiResult<MessageResponse> {
        return safeApiCall { apiService.seedDoctorAppointments("Bearer $token") }
    }
}
