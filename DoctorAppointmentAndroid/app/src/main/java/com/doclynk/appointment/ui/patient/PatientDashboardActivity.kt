package com.doclynk.appointment.ui.patient

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import com.doclynk.appointment.databinding.ActivityPatientDashboardBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.ui.auth.LoginActivity
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.doclynk.appointment.viewmodel.PatientDashboardViewModel
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class PatientDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPatientDashboardBinding
    private lateinit var appointmentAdapter: PatientAppointmentAdapter
    private lateinit var token: String

    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: PatientDashboardViewModel by viewModels {
        AppViewModelFactory(patientRepository = appContainer.patientRepository)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPatientDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupRecyclerView()
        setupButtons()
        observeUiState()
        loadSessionAndAppointments()
    }

    private fun setupRecyclerView() {
        appointmentAdapter = PatientAppointmentAdapter(
            onCancelClick = { appointment ->
                viewModel.cancelAppointment(token, appointment.id)
            }
        )
        binding.recyclerAppointments.apply {
            layoutManager = LinearLayoutManager(this@PatientDashboardActivity)
            adapter = appointmentAdapter
        }
    }

    private fun setupButtons() {
        binding.btnBookAppointment.setOnClickListener {
            startActivity(Intent(this, BookAppointmentActivity::class.java))
        }

        binding.btnLogout.setOnClickListener {
            lifecycleScope.launch {
                appContainer.sessionManager.clearSession()
                startActivity(Intent(this@PatientDashboardActivity, LoginActivity::class.java))
                finish()
            }
        }
    }

    private fun loadSessionAndAppointments() {
        lifecycleScope.launch {
            val session = appContainer.sessionManager.sessionFlow.first()
            token = session.token
            viewModel.loadAppointments(token)
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.loading) View.VISIBLE else View.GONE
                    binding.emptyView.visibility = if (!state.loading && state.appointments.isEmpty()) View.VISIBLE else View.GONE
                    appointmentAdapter.submitList(state.appointments)
                    binding.recyclerAppointments.scheduleLayoutAnimation()

                    state.errorMessage?.let {
                        Snackbar.make(binding.root, it, Snackbar.LENGTH_LONG).show()
                        viewModel.clearMessages()
                    }

                    state.infoMessage?.let {
                        Snackbar.make(binding.root, it, Snackbar.LENGTH_SHORT).show()
                        viewModel.clearMessages()
                    }
                }
            }
        }
    }
}
