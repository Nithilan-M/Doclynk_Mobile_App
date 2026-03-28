package com.doclynk.appointment.data.api

import com.doclynk.appointment.data.model.Appointment
import com.doclynk.appointment.data.model.AdminAppointment
import com.doclynk.appointment.data.model.AdminDashboardResponse
import com.doclynk.appointment.data.model.AdminUser
import com.doclynk.appointment.data.model.AuthResponse
import com.doclynk.appointment.data.model.BookAppointmentRequest
import com.doclynk.appointment.data.model.Doctor
import com.doclynk.appointment.data.model.ForgotPasswordRequest
import com.doclynk.appointment.data.model.LoginRequest
import com.doclynk.appointment.data.model.MessageResponse
import com.doclynk.appointment.data.model.RegisterRequest
import com.doclynk.appointment.data.model.RegisterOtpInitResponse
import com.doclynk.appointment.data.model.RegisterOtpRequest
import com.doclynk.appointment.data.model.ResetPasswordRequest
import com.doclynk.appointment.data.model.ResendRegisterOtpRequest
import com.doclynk.appointment.data.model.SlotsResponse
import com.doclynk.appointment.data.model.ToggleAdminRequest
import com.doclynk.appointment.data.model.UpdateStatusRequest
import com.doclynk.appointment.data.model.VerifyRegisterOtpRequest
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

interface ApiService {
    @POST("api/login")
    suspend fun login(@Body body: LoginRequest): Response<AuthResponse>

    @POST("api/register")
    suspend fun register(@Body body: RegisterRequest): Response<AuthResponse>

    @POST("api/register/send_otp")
    suspend fun sendRegisterOtp(@Body body: RegisterOtpRequest): Response<RegisterOtpInitResponse>

    @POST("api/register/verify_otp")
    suspend fun verifyRegisterOtp(@Body body: VerifyRegisterOtpRequest): Response<AuthResponse>

    @POST("api/register/resend_otp")
    suspend fun resendRegisterOtp(@Body body: ResendRegisterOtpRequest): Response<MessageResponse>

    @POST("api/password/forgot")
    suspend fun forgotPassword(@Body body: ForgotPasswordRequest): Response<MessageResponse>

    @POST("api/password/reset")
    suspend fun resetPassword(@Body body: ResetPasswordRequest): Response<MessageResponse>

    @GET("api/patient/appointments")
    suspend fun getPatientAppointments(@Header("Authorization") token: String): Response<List<Appointment>>

    @GET("api/doctor/appointments")
    suspend fun getDoctorAppointments(@Header("Authorization") token: String): Response<List<Appointment>>

    @GET("api/doctors")
    suspend fun getDoctors(@Header("Authorization") token: String): Response<List<Doctor>>

    @GET("api/check_availability")
    suspend fun getAvailableSlots(
        @Header("Authorization") token: String,
        @Query("doctor_id") doctorId: Int,
        @Query("date") date: String
    ): Response<SlotsResponse>

    @POST("api/appointment/book")
    suspend fun bookAppointment(
        @Header("Authorization") token: String,
        @Body body: BookAppointmentRequest
    ): Response<MessageResponse>

    @POST("api/appointment/update_status")
    suspend fun updateAppointmentStatus(
        @Header("Authorization") token: String,
        @Body body: UpdateStatusRequest
    ): Response<MessageResponse>

    @DELETE("api/appointment/delete")
    suspend fun deleteAppointment(
        @Header("Authorization") token: String,
        @Query("appointment_id") appointmentId: Int
    ): Response<MessageResponse>

    @GET("api/admin/dashboard")
    suspend fun getAdminDashboard(@Header("Authorization") token: String): Response<AdminDashboardResponse>

    @GET("api/admin/users")
    suspend fun getAdminUsers(@Header("Authorization") token: String): Response<List<AdminUser>>

    @POST("api/admin/users/toggle_admin")
    suspend fun toggleAdminStatus(
        @Header("Authorization") token: String,
        @Body body: ToggleAdminRequest
    ): Response<MessageResponse>

    @DELETE("api/admin/users/delete")
    suspend fun deleteUser(
        @Header("Authorization") token: String,
        @Query("user_id") userId: Int
    ): Response<MessageResponse>

    @GET("api/admin/appointments")
    suspend fun getAdminAppointments(@Header("Authorization") token: String): Response<List<AdminAppointment>>

    @POST("api/admin/appointments/update_status")
    suspend fun updateAdminAppointmentStatus(
        @Header("Authorization") token: String,
        @Body body: UpdateStatusRequest
    ): Response<MessageResponse>

    @DELETE("api/admin/appointments/delete")
    suspend fun deleteAdminAppointment(
        @Header("Authorization") token: String,
        @Query("appointment_id") appointmentId: Int
    ): Response<MessageResponse>

    @POST("api/admin/seed_doctor_appointments")
    suspend fun seedDoctorAppointments(@Header("Authorization") token: String): Response<MessageResponse>
}
