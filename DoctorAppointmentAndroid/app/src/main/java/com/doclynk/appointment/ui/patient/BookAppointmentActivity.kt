package com.doclynk.appointment.ui.patient

import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.doclynk.appointment.R
import com.doclynk.appointment.databinding.ActivityBookingBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.doclynk.appointment.viewmodel.BookingViewModel
import com.google.android.material.chip.Chip
import com.google.android.material.datepicker.MaterialDatePicker
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class BookAppointmentActivity : AppCompatActivity() {

    private lateinit var binding: ActivityBookingBinding
    private var selectedDate: String = ""
    private var selectedDoctorId: Int? = null
    private var selectedSlot: String = ""

    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: BookingViewModel by viewModels {
        AppViewModelFactory(
            patientRepository = appContainer.patientRepository,
            sessionManager = appContainer.sessionManager
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBookingBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupViews()
        observeUiState()
        viewModel.loadDoctors()
    }

    private fun setupViews() {
        binding.btnBack.setOnClickListener {
            finish()
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        binding.spinnerDoctors.setOnItemClickListener { _, _, position, _ ->
            selectedDoctorId = viewModel.uiState.value.doctors.getOrNull(position)?.id
        }

        binding.btnPickDate.setOnClickListener {
            showDatePicker()
        }

        binding.btnFetchSlots.setOnClickListener {
            val doctorId = selectedDoctorId
            if (doctorId == null || selectedDate.isBlank()) {
                Snackbar.make(binding.root, "Choose doctor and date first", Snackbar.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            viewModel.loadAvailableSlots(doctorId, selectedDate)
        }

        binding.chipGroupSlots.setOnCheckedStateChangeListener { group, checkedIds ->
            if (checkedIds.isNotEmpty()) {
                val chip = group.findViewById<Chip>(checkedIds.first())
                selectedSlot = chip?.text.toString()
            } else {
                selectedSlot = ""
            }
        }

        binding.btnConfirmBooking.setOnClickListener {
            val doctorId = selectedDoctorId
            val reason = binding.etReason.text.toString().trim()

            if (doctorId == null || selectedDate.isBlank() || selectedSlot.isBlank() || reason.isBlank()) {
                Snackbar.make(binding.root, "Complete all fields to book", Snackbar.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            viewModel.bookAppointment(doctorId, selectedDate, selectedSlot, reason)
        }
    }

    private fun showDatePicker() {
        val datePicker = MaterialDatePicker.Builder.datePicker()
            .setTitleText("Select Appointment Date")
            .setSelection(MaterialDatePicker.todayInUtcMilliseconds())
            .build()

        datePicker.addOnPositiveButtonClickListener { selection ->
            val formatter = SimpleDateFormat("yyyy-MM-dd", Locale.US)
            selectedDate = formatter.format(Date(selection))
            binding.tvSelectedDate.text = "Selected: $selectedDate"
            binding.tvSelectedDate.setTextColor(ContextCompat.getColor(this, R.color.brand_primary))
        }

        datePicker.show(supportFragmentManager, "MATERIAL_DATE_PICKER")
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE

                    // Update Doctors
                    if (state.doctors.isNotEmpty() && binding.spinnerDoctors.adapter == null) {
                        val doctorNames = state.doctors.map { "Dr. ${it.name} - ${it.specialization ?: "Specialist"}" }
                        val adapter = ArrayAdapter(
                            this@BookAppointmentActivity,
                            android.R.layout.simple_dropdown_item_1line,
                            doctorNames
                        )
                        binding.spinnerDoctors.setAdapter(adapter)
                    }

                    // Update Slots
                    if (state.slots.isNotEmpty()) {
                        binding.llTimeSlots.visibility = View.VISIBLE
                        binding.chipGroupSlots.removeAllViews()
                        state.slots.forEach { slotTime ->
                            val chip = Chip(this@BookAppointmentActivity).apply {
                                text = slotTime
                                isCheckable = true
                                isClickable = true
                                chipBackgroundColor = ContextCompat.getColorStateList(this@BookAppointmentActivity, R.color.brand_background)
                                setTextColor(ContextCompat.getColor(this@BookAppointmentActivity, R.color.brand_text_primary))
                            }
                            binding.chipGroupSlots.addView(chip)
                        }
                    } else {
                        // Clear if empty check is returned successful but no slots
                        binding.chipGroupSlots.removeAllViews()
                    }

                    // Handle Messages
                    state.errorMessage?.let {
                        Snackbar.make(binding.root, it, Snackbar.LENGTH_LONG)
                            .setBackgroundTint(resources.getColor(android.R.color.holo_red_dark, theme))
                            .show()
                        viewModel.clearMessages()
                    }

                    state.successMessage?.let {
                        Snackbar.make(binding.root, it, Snackbar.LENGTH_SHORT)
                            .setBackgroundTint(resources.getColor(android.R.color.holo_green_dark, theme))
                            .show()
                        viewModel.clearMessages()
                        finish()
                        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
                    }
                }
            }
        }
    }

    override fun onBackPressed() {
        super.onBackPressed()
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
    }
}
