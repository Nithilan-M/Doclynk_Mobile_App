package com.doclynk.appointment.data.model

import com.google.gson.annotations.SerializedName

data class Doctor(
    val id: Int,
    val name: String,
    val email: String,
    @SerializedName("specialty")
    val specialization: String? = null
)
