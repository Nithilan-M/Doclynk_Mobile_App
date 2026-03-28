package com.doclynk.appointment.data.repository

import com.doclynk.appointment.data.api.ApiService
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.model.Appointment
import com.doclynk.appointment.data.model.MessageResponse
import com.doclynk.appointment.data.model.UpdateStatusRequest

class DoctorRepository(private val apiService: ApiService) : BaseRepository() {
    suspend fun getAppointments(token: String): ApiResult<List<Appointment>> {
        return safeApiCall { apiService.getDoctorAppointments("Bearer $token") }
    }

    suspend fun updateStatus(token: String, appointmentId: Int, status: String): ApiResult<MessageResponse> {
        return safeApiCall {
            apiService.updateAppointmentStatus(
                token = "Bearer $token",
                body = UpdateStatusRequest(appointment_id = appointmentId, status = status)
            )
        }
    }

    suspend fun deleteAppointment(token: String, appointmentId: Int): ApiResult<MessageResponse> {
        return safeApiCall {
            apiService.deleteAppointment("Bearer $token", appointmentId = appointmentId)
        }
    }
}
