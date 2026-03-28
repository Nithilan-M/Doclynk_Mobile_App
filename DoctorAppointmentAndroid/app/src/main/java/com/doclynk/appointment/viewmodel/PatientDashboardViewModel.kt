package com.doclynk.appointment.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.model.Appointment
import com.doclynk.appointment.data.repository.PatientRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PatientDashboardUiState(
    val loading: Boolean = false,
    val appointments: List<Appointment> = emptyList(),
    val errorMessage: String? = null,
    val infoMessage: String? = null
)

class PatientDashboardViewModel(
    private val patientRepository: PatientRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(PatientDashboardUiState())
    val uiState: StateFlow<PatientDashboardUiState> = _uiState.asStateFlow()

    fun loadAppointments(token: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, errorMessage = null)
            when (val result = patientRepository.getAppointments(token)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        appointments = result.data
                    )
                }

                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        errorMessage = result.message
                    )
                }
            }
        }
    }

    fun cancelAppointment(token: String, appointmentId: Int) {
        viewModelScope.launch {
            when (val result = patientRepository.cancelAppointment(token, appointmentId)) {
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
