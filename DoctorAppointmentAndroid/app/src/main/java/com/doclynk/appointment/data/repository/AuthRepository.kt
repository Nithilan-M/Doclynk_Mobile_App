package com.doclynk.appointment.data.repository

import com.doclynk.appointment.data.api.ApiService
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.model.AuthResponse
import com.doclynk.appointment.data.model.ForgotPasswordRequest
import com.doclynk.appointment.data.model.LoginRequest
import com.doclynk.appointment.data.model.RegisterRequest
import com.doclynk.appointment.data.model.RegisterOtpInitResponse
import com.doclynk.appointment.data.model.RegisterOtpRequest
import com.doclynk.appointment.data.model.ResendRegisterOtpRequest
import com.doclynk.appointment.data.model.MessageResponse
import com.doclynk.appointment.data.model.ResetPasswordRequest
import com.doclynk.appointment.data.model.VerifyRegisterOtpRequest

class AuthRepository(private val apiService: ApiService) : BaseRepository() {
    suspend fun login(email: String, password: String): ApiResult<AuthResponse> {
        return safeApiCall {
            apiService.login(LoginRequest(email = email, password = password))
        }
    }

    suspend fun register(name: String, email: String, password: String, role: String): ApiResult<AuthResponse> {
        return safeApiCall {
            apiService.register(
                RegisterRequest(
                    name = name,
                    email = email,
                    password = password,
                    role = role
                )
            )
        }
    }

    suspend fun sendRegisterOtp(name: String, email: String, password: String, role: String): ApiResult<RegisterOtpInitResponse> {
        return safeApiCall {
            apiService.sendRegisterOtp(
                RegisterOtpRequest(
                    name = name,
                    email = email,
                    password = password,
                    role = role
                )
            )
        }
    }

    suspend fun verifyRegisterOtp(email: String, otp: String, verificationToken: String): ApiResult<AuthResponse> {
        return safeApiCall {
            apiService.verifyRegisterOtp(
                VerifyRegisterOtpRequest(
                    email = email,
                    otp = otp,
                    verification_token = verificationToken
                )
            )
        }
    }

    suspend fun resendRegisterOtp(verificationToken: String): ApiResult<MessageResponse> {
        return safeApiCall {
            apiService.resendRegisterOtp(
                ResendRegisterOtpRequest(verification_token = verificationToken)
            )
        }
    }

    suspend fun forgotPassword(email: String): ApiResult<MessageResponse> {
        return safeApiCall {
            apiService.forgotPassword(ForgotPasswordRequest(email = email))
        }
    }

    suspend fun resetPassword(email: String, otp: String, newPassword: String): ApiResult<MessageResponse> {
        return safeApiCall {
            apiService.resetPassword(
                ResetPasswordRequest(
                    email = email,
                    otp = otp,
                    new_password = newPassword
                )
            )
        }
    }
}
