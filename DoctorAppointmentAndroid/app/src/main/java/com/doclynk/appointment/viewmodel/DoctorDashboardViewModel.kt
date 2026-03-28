package com.doclynk.appointment.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.model.Appointment
import com.doclynk.appointment.data.repository.DoctorRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DoctorDashboardUiState(
    val loading: Boolean = false,
    val appointments: List<Appointment> = emptyList(),
    val errorMessage: String? = null,
    val infoMessage: String? = null
)

class DoctorDashboardViewModel(
    private val doctorRepository: DoctorRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(DoctorDashboardUiState())
    val uiState: StateFlow<DoctorDashboardUiState> = _uiState.asStateFlow()

    fun loadAppointments(token: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, errorMessage = null)
            when (val result = doctorRepository.getAppointments(token)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        appointments = result.data
                    )
                }

                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(loading = false, errorMessage = result.message)
                }
            }
        }
    }

    fun updateStatus(token: String, appointmentId: Int, status: String) {
        viewModelScope.launch {
            when (val result = doctorRepository.updateStatus(token, appointmentId, status)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(infoMessage = result.data.message)
                    loadAppointments(token)
                }

                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(errorMessage = result.message)
                }
            }
        }
    }

    fun deleteAppointment(token: String, appointmentId: Int) {
        viewModelScope.launch {
            when (val result = doctorRepository.deleteAppointment(token, appointmentId)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(infoMessage = result.data.message)
                    loadAppointments(token)
                }

                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(errorMessage = result.message)
                }
            }
        }
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(errorMessage = null, infoMessage = null)
    }
}
