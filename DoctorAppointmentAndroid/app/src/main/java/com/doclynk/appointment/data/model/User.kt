package com.doclynk.appointment.data.model

data class User(
    val id: Int,
    val name: String,
    val email: String,
    val role: String,
    val token: String? = null
)
