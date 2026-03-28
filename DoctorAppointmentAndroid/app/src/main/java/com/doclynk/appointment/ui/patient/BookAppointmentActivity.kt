package com.doclynk.appointment.ui.patient

import android.app.DatePickerDialog
import android.os.Bundle
import android.widget.AdapterView
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.doclynk.appointment.databinding.ActivityBookingBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.doclynk.appointment.viewmodel.BookingViewModel
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

class BookAppointmentActivity : AppCompatActivity() {

    private lateinit var binding: ActivityBookingBinding
    private lateinit var token: String
    private var selectedDate: String = ""
    private var selectedDoctorId: Int? = null
    private var cachedDoctorIds: List<Int> = emptyList()
    private var cachedSlots: List<String> = emptyList()

    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: BookingViewModel by viewModels {
        AppViewModelFactory(patientRepository = appContainer.patientRepository)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBookingBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupViews()
        observeUiState()
        loadSessionAndDoctors()
    }

    private fun setupViews() {
        binding.spinnerDoctors.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                selectedDoctorId = viewModel.uiState.value.doctors.getOrNull(position)?.id
            }

            override fun onNothingSelected(parent: AdapterView<*>?) {
                selectedDoctorId = null
            }
        }

        binding.btnPickDate.setOnClickListener {
            showDatePicker()
        }

        binding.btnFetchSlots.setOnClickListener {
            val doctorId = selectedDoctorId
            if (doctorId == null || selectedDate.isBlank()) {
                Toast.makeText(this, "Choose doctor and date", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            viewModel.loadAvailableSlots(token, doctorId, selectedDate)
        }

        binding.btnConfirmBooking.setOnClickListener {
            val doctorId = selectedDoctorId
            val slotPosition = binding.spinnerSlots.selectedItemPosition
            val reason = binding.etReason.text.toString().trim()

            if (doctorId == null || slotPosition < 0 || selectedDate.isBlank() || reason.isBlank()) {
                Toast.makeText(this, "Complete all fields", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val slot = viewModel.uiState.value.slots[slotPosition]
            viewModel.bookAppointment(token, doctorId, selectedDate, slot, reason)
        }
    }

    private fun showDatePicker() {
        val calendar = Calendar.getInstance()
        DatePickerDialog(
            this,
            { _, year, month, dayOfMonth ->
                calendar.set(year, month, dayOfMonth)
                selectedDate = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(calendar.time)
                binding.tvSelectedDate.text = selectedDate
            },
            calendar.get(Calendar.YEAR),
            calendar.get(Calendar.MONTH),
            calendar.get(Calendar.DAY_OF_MONTH)
        ).show()
    }

    private fun loadSessionAndDoctors() {
        lifecycleScope.launch {
            val session = appContainer.sessionManager.sessionFlow.first()
            token = session.token
            viewModel.loadDoctors(token)
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.isIndeterminate = true
                    binding.progressBar.visibility = if (state.loading) View.VISIBLE else View.GONE

                    val doctorIds = state.doctors.map { it.id }
                    if (doctorIds != cachedDoctorIds) {
                        val oldDoctorId = selectedDoctorId
                        val doctorNames = state.doctors.map { "Dr. ${it.name} (${it.email})" }
                        binding.spinnerDoctors.adapter = ArrayAdapter(
                            this@BookAppointmentActivity,
                            android.R.layout.simple_spinner_dropdown_item,
                            doctorNames
                        )
                        val selectedIndex = state.doctors.indexOfFirst { it.id == oldDoctorId }
                            .takeIf { it >= 0 } ?: 0
                        if (state.doctors.isNotEmpty()) {
                            binding.spinnerDoctors.setSelection(selectedIndex, false)
                            selectedDoctorId = state.doctors[selectedIndex].id
                        }
                        cachedDoctorIds = doctorIds
                    }

                    if (state.slots != cachedSlots) {
                        binding.spinnerSlots.adapter = ArrayAdapter(
                            this@BookAppointmentActivity,
                            android.R.layout.simple_spinner_dropdown_item,
                            state.slots
                        )
                        cachedSlots = state.slots
                    }

                    state.errorMessage?.let {
                        Toast.makeText(this@BookAppointmentActivity, it, Toast.LENGTH_LONG).show()
                        viewModel.clearMessages()
                    }

                    state.successMessage?.let {
                        Toast.makeText(this@BookAppointmentActivity, it, Toast.LENGTH_SHORT).show()
                        finish()
                    }
                }
            }
        }
    }
}
