package com.doclynk.appointment.data.repository

import com.doclynk.appointment.data.api.ApiService
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.model.Appointment
import com.doclynk.appointment.data.model.BookAppointmentRequest
import com.doclynk.appointment.data.model.Doctor
import com.doclynk.appointment.data.model.MessageResponse

class PatientRepository(private val apiService: ApiService) : BaseRepository() {
    suspend fun getAppointments(token: String): ApiResult<List<Appointment>> {
        return safeApiCall { apiService.getPatientAppointments("Bearer $token") }
    }

    suspend fun getDoctors(token: String): ApiResult<List<Doctor>> {
        return safeApiCall { apiService.getDoctors("Bearer $token") }
    }

    suspend fun getAvailableSlots(token: String, doctorId: Int, date: String): ApiResult<List<String>> {
        val result = safeApiCall {
            apiService.getAvailableSlots("Bearer $token", doctorId = doctorId, date = date)
        }
        return when (result) {
            is ApiResult.Success -> ApiResult.Success(result.data.available_slots)
            is ApiResult.Error -> result
        }
    }

    suspend fun bookAppointment(
        token: String,
        doctorId: Int,
        date: String,
        timeSlot: String,
        reason: String
    ): ApiResult<MessageResponse> {
        return safeApiCall {
            apiService.bookAppointment(
                token = "Bearer $token",
                body = BookAppointmentRequest(
                    doctor_id = doctorId,
                    date = date,
                    time_slot = timeSlot,
                    reason = reason
                )
            )
        }
    }

    suspend fun cancelAppointment(token: String, appointmentId: Int): ApiResult<MessageResponse> {
        return safeApiCall {
            apiService.deleteAppointment("Bearer $token", appointmentId = appointmentId)
        }
    }
}
