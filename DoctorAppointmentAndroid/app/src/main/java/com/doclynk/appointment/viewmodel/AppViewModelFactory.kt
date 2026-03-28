package com.doclynk.appointment.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.doclynk.appointment.data.repository.AdminRepository
import com.doclynk.appointment.data.repository.AuthRepository
import com.doclynk.appointment.data.repository.DoctorRepository
import com.doclynk.appointment.data.repository.PatientRepository
import com.doclynk.appointment.data.repository.SessionManager

class AppViewModelFactory(
    private val authRepository: AuthRepository? = null,
    private val patientRepository: PatientRepository? = null,
    private val doctorRepository: DoctorRepository? = null,
    private val adminRepository: AdminRepository? = null,
    private val sessionManager: SessionManager? = null
) : ViewModelProvider.Factory {

    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        return when {
            modelClass.isAssignableFrom(AuthViewModel::class.java) -> {
                AuthViewModel(
                    authRepository = requireNotNull(authRepository),
                    sessionManager = requireNotNull(sessionManager)
                ) as T
            }

            modelClass.isAssignableFrom(PatientDashboardViewModel::class.java) -> {
                PatientDashboardViewModel(requireNotNull(patientRepository)) as T
            }

            modelClass.isAssignableFrom(BookingViewModel::class.java) -> {
                BookingViewModel(requireNotNull(patientRepository)) as T
            }

            modelClass.isAssignableFrom(DoctorDashboardViewModel::class.java) -> {
                DoctorDashboardViewModel(requireNotNull(doctorRepository)) as T
            }

            modelClass.isAssignableFrom(AdminDashboardViewModel::class.java) -> {
                AdminDashboardViewModel(requireNotNull(adminRepository)) as T
            }

            else -> throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
        }
    }
}
