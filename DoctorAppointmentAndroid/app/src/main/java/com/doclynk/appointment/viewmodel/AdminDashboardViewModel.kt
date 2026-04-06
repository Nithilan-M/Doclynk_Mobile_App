package com.doclynk.appointment.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doclynk.appointment.data.model.AdminAppointment
import com.doclynk.appointment.data.model.AdminStats
import com.doclynk.appointment.data.model.AdminUser
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.repository.AdminRepository
import com.doclynk.appointment.data.repository.SessionManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

data class AdminDashboardUiState(
    val isLoading: Boolean = false,
    val adminName: String = "Admin",
    val stats: AdminStats = AdminStats(),
    val users: List<AdminUser> = emptyList(),
    val appointments: List<AdminAppointment> = emptyList(),
    val errorMessage: String? = null,
    val successMessage: String? = null
)

class AdminDashboardViewModel(
    private val adminRepository: AdminRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(AdminDashboardUiState())
    val uiState: StateFlow<AdminDashboardUiState> = _uiState.asStateFlow()

    fun setAdminName(name: String) {
        _uiState.value = _uiState.value.copy(adminName = name)
    }

    fun loadAll() {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)

            val dashboardResult = adminRepository.getDashboard(token)
            val usersResult = adminRepository.getUsers(token)
            val appointmentsResult = adminRepository.getAppointments(token)

            val nextState = _uiState.value.copy(isLoading = false)

            _uiState.value = when {
                dashboardResult is ApiResult.Error -> nextState.copy(errorMessage = dashboardResult.message)
                usersResult is ApiResult.Error -> nextState.copy(errorMessage = usersResult.message)
                appointmentsResult is ApiResult.Error -> nextState.copy(errorMessage = appointmentsResult.message)
                else -> nextState.copy(
                    stats = (dashboardResult as ApiResult.Success).data.stats,
                    users = (usersResult as ApiResult.Success).data,
                    appointments = (appointmentsResult as ApiResult.Success).data
                )
            }
        }
    }

    fun toggleAdmin(userId: Int) {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            when (val result = adminRepository.toggleAdmin(token, userId)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(successMessage = result.data.message)
                    loadAll()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(errorMessage = result.message)
                }
            }
        }
    }

    fun deleteUser(userId: Int) {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            when (val result = adminRepository.deleteUser(token, userId)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(successMessage = result.data.message)
                    loadAll()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(errorMessage = result.message)
                }
            }
        }
    }

    fun updateAppointmentStatus(appointmentId: Int, status: String) {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            when (val result = adminRepository.updateAppointmentStatus(token, appointmentId, status)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(successMessage = result.data.message)
                    loadAll()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(errorMessage = result.message)
                }
            }
        }
    }

    fun deleteAppointment(appointmentId: Int) {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            when (val result = adminRepository.deleteAppointment(token, appointmentId)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(successMessage = result.data.message)
                    loadAll()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(errorMessage = result.message)
                }
            }
        }
    }

    fun seedDoctorAppointments() {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            when (val result = adminRepository.seedDoctorAppointments(token)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(successMessage = result.data.message)
                    loadAll()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(errorMessage = result.message)
                }
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            sessionManager.clearSession()
        }
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(errorMessage = null, successMessage = null)
    }
}
