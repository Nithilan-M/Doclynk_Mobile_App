package com.doclynk.appointment.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doclynk.appointment.data.model.ApiResult
import com.doclynk.appointment.data.model.Doctor
import com.doclynk.appointment.data.repository.PatientRepository
import com.doclynk.appointment.data.repository.SessionManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

data class BookingUiState(
    val isLoading: Boolean = false,
    val doctors: List<Doctor> = emptyList(),
    val slots: List<String> = emptyList(),
    val errorMessage: String? = null,
    val successMessage: String? = null
)

class BookingViewModel(
    private val patientRepository: PatientRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(BookingUiState())
    val uiState: StateFlow<BookingUiState> = _uiState.asStateFlow()

    fun loadDoctors() {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val result = patientRepository.getDoctors(token)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        doctors = result.data,
                        errorMessage = null
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = result.message)
                }
            }
        }
    }

    fun loadAvailableSlots(doctorId: Int, date: String) {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            _uiState.value = _uiState.value.copy(isLoading = true, slots = emptyList())
            when (val result = patientRepository.getAvailableSlots(token, doctorId, date)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        slots = result.data,
                        errorMessage = null
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = result.message)
                }
            }
        }
    }

    fun bookAppointment(doctorId: Int, date: String, timeSlot: String, reason: String) {
        viewModelScope.launch {
            val token = sessionManager.sessionFlow.first().token
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val result = patientRepository.bookAppointment(token, doctorId, date, timeSlot, reason)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = result.data.message,
                        errorMessage = null
                    )
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = result.message)
                }
            }
        }
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(errorMessage = null, successMessage = null)
    }
}
