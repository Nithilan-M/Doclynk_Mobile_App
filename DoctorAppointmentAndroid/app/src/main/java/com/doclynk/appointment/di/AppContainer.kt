package com.doclynk.appointment.di

import android.content.Context
import com.doclynk.appointment.data.api.RetrofitClient
import com.doclynk.appointment.data.repository.AdminRepository
import com.doclynk.appointment.data.repository.AuthRepository
import com.doclynk.appointment.data.repository.DoctorRepository
import com.doclynk.appointment.data.repository.PatientRepository
import com.doclynk.appointment.data.repository.SessionManager

class AppContainer(context: Context) {
    val sessionManager = SessionManager(context)
    private val apiService = RetrofitClient.apiService

    val authRepository = AuthRepository(apiService)
    val patientRepository = PatientRepository(apiService)
    val doctorRepository = DoctorRepository(apiService)
    val adminRepository = AdminRepository(apiService)
}
