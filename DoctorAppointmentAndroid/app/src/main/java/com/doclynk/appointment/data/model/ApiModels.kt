package com.doclynk.appointment.data.model

data class LoginRequest(
    val email: String,
    val password: String
)

data class RegisterRequest(
    val name: String,
    val email: String,
    val password: String,
    val role: String
)

data class RegisterOtpRequest(
    val name: String,
    val email: String,
    val password: String,
    val role: String
)

data class VerifyRegisterOtpRequest(
    val email: String,
    val otp: String,
    val verification_token: String
)

data class ResendRegisterOtpRequest(
    val verification_token: String
)

data class ForgotPasswordRequest(
    val email: String
)

data class ResetPasswordRequest(
    val email: String,
    val otp: String,
    val new_password: String
)

data class AuthResponse(
    val message: String,
    val user: User
)

data class SlotsResponse(
    val available_slots: List<String>
)

data class BookAppointmentRequest(
    val doctor_id: Int,
    val date: String,
    val time_slot: String,
    val reason: String
)

data class UpdateStatusRequest(
    val appointment_id: Int,
    val status: String
)

data class MessageResponse(
    val message: String
)

data class RegisterOtpInitResponse(
    val message: String,
    val email: String,
    val verification_token: String
)
