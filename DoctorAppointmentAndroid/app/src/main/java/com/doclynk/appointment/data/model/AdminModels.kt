package com.doclynk.appointment.data.model

data class AdminStats(
    val total_users: Int = 0,
    val total_doctors: Int = 0,
    val total_patients: Int = 0,
    val total_admins: Int = 0,
    val total_appointments: Int = 0,
    val pending_appointments: Int = 0,
    val approved_appointments: Int = 0,
    val rejected_appointments: Int = 0
)

data class AdminDashboardResponse(
    val stats: AdminStats,
    val recent_users: List<AdminUser> = emptyList(),
    val recent_appointments: List<AdminAppointment> = emptyList()
)

data class AdminUser(
    val id: Int,
    val name: String,
    val email: String,
    val role: String,
    val is_admin: Boolean = false,
    val email_verified: Boolean = true,
    val auth_provider: String = "email"
)

data class AdminAppointment(
    val id: Int,
    val patient_id: Int,
    val doctor_id: Int,
    val patient_name: String,
    val doctor_name: String,
    val patient_email: String? = null,
    val doctor_email: String? = null,
    val date: String,
    val time_slot: String,
    val reason: String,
    val status: String
)

data class ToggleAdminRequest(
    val user_id: Int
)
