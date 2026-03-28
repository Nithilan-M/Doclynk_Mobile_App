package com.doclynk.appointment.data.model

import com.google.gson.annotations.SerializedName

data class Appointment(
    val id: Int,
    @SerializedName("doctor_id")
    val doctorId: Int,
    @SerializedName("doctor_name")
    val doctorName: String,
    @SerializedName("patient_id")
    val patientId: Int,
    @SerializedName("patient_name")
    val patientName: String,
    val date: String,
    @SerializedName("time_slot")
    val timeSlot: String,
    val reason: String,
    val status: String
)
