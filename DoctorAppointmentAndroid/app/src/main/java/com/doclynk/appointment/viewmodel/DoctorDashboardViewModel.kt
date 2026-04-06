package com.doclynk.appointment.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.model.Appointment
import com.doclynk.appointment.data.repository.DoctorRepository
import com.doclynk.appointment.data.repository.SessionManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

data class DoctorDashboardUiState(
    val isLoading: Boolean = false,
    val appointments: List<Appointment> = emptyList(),
    val errorMessage: String? = null,
    val successMessage: String? = null
)

class DoctorDashboardViewModel(
    private val doctorRepository: DoctorRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(DoctorDashboardUiState())
    val uiState: StateFlow<DoctorDashboardUiState> = _uiState.asStateFlow()

    fun fetchAppointments() {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            when (val result = doctorRepository.getAppointments(token)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        appointments = result.data
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = result.message)
                }
            }
        }
    }

    fun updateStatus(appointmentId: Int, status: String) {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            when (val result = doctorRepository.updateStatus(token, appointmentId, status)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(successMessage = result.data.message)
                    fetchAppointments()
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
            when (val result = doctorRepository.deleteAppointment(token, appointmentId)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(successMessage = result.data.message)
                    fetchAppointments()
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

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(errorMessage = null, successMessage = null)
    }
}
