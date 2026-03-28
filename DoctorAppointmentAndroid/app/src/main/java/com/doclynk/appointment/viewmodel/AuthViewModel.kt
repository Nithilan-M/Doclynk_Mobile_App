package com.doclynk.appointment.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.repository.AuthRepository
import com.doclynk.appointment.data.repository.SessionManager
import com.doclynk.appointment.data.repository.UserSession
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AuthUiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null
)

class AuthViewModel(
    private val authRepository: AuthRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    fun login(email: String, password: String, onSuccess: (role: String) -> Unit) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            when (val result = authRepository.login(email, password)) {
                is ApiResult.Success -> {
                    val user = result.data.user
                    sessionManager.saveSession(
                        UserSession(
                            token = user.token.orEmpty(),
                            userId = user.id,
                            userName = user.name,
                            userEmail = user.email,
                            role = user.role
                        )
                    )
                    _uiState.value = AuthUiState(successMessage = "Welcome ${user.name}")
                    onSuccess(user.role)
                }

                is ApiResult.Error -> {
                    _uiState.value = AuthUiState(errorMessage = result.message)
                }
            }
        }
    }

    fun register(name: String, email: String, password: String, role: String, onSuccess: (role: String) -> Unit) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            when (val result = authRepository.register(name, email, password, role)) {
                is ApiResult.Success -> {
                    val user = result.data.user
                    sessionManager.saveSession(
                        UserSession(
                            token = user.token.orEmpty(),
                            userId = user.id,
                            userName = user.name,
                            userEmail = user.email,
                            role = user.role
                        )
                    )
                    _uiState.value = AuthUiState(successMessage = "Account created")
                    onSuccess(user.role)
                }

                is ApiResult.Error -> {
                    _uiState.value = AuthUiState(errorMessage = result.message)
                }
            }
        }
    }

    fun startRegistrationEmailVerification(
        name: String,
        email: String,
        password: String,
        role: String,
        onOtpSent: (email: String, verificationToken: String) -> Unit
    ) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            when (val result = authRepository.sendRegisterOtp(name, email, password, role)) {
                is ApiResult.Success -> {
                    _uiState.value = AuthUiState(successMessage = result.data.message)
                    onOtpSent(result.data.email, result.data.verification_token)
                }

                is ApiResult.Error -> {
                    _uiState.value = AuthUiState(errorMessage = result.message)
                }
            }
        }
    }

    fun verifyRegistrationOtp(
        email: String,
        otp: String,
        verificationToken: String,
        onSuccess: (role: String) -> Unit
    ) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            when (val result = authRepository.verifyRegisterOtp(email, otp, verificationToken)) {
                is ApiResult.Success -> {
                    val user = result.data.user
                    sessionManager.saveSession(
                        UserSession(
                            token = user.token.orEmpty(),
                            userId = user.id,
                            userName = user.name,
                            userEmail = user.email,
                            role = user.role
                        )
                    )
                    _uiState.value = AuthUiState(successMessage = result.data.message)
                    onSuccess(user.role)
                }

                is ApiResult.Error -> {
                    _uiState.value = AuthUiState(errorMessage = result.message)
                }
            }
        }
    }

    fun resendRegistrationOtp(verificationToken: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            when (val result = authRepository.resendRegisterOtp(verificationToken)) {
                is ApiResult.Success -> {
                    _uiState.value = AuthUiState(successMessage = result.data.message)
                }

                is ApiResult.Error -> {
                    _uiState.value = AuthUiState(errorMessage = result.message)
                }
            }
        }
    }

    fun forgotPassword(email: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            when (val result = authRepository.forgotPassword(email)) {
                is ApiResult.Success -> {
                    _uiState.value = AuthUiState(successMessage = result.data.message)
                }

                is ApiResult.Error -> {
                    _uiState.value = AuthUiState(errorMessage = result.message)
                }
            }
        }
    }

    fun resetPassword(email: String, otp: String, newPassword: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            when (val result = authRepository.resetPassword(email, otp, newPassword)) {
                is ApiResult.Success -> {
                    _uiState.value = AuthUiState(successMessage = result.data.message)
                    onSuccess()
                }

                is ApiResult.Error -> {
                    _uiState.value = AuthUiState(errorMessage = result.message)
                }
            }
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(errorMessage = null, successMessage = null)
    }
}
