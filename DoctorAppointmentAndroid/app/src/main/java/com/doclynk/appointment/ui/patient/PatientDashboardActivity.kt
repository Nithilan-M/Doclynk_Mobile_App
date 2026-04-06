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
    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: PatientDashboardViewModel by viewModels {
        AppViewModelFactory(
            patientRepository = appContainer.patientRepository,
            sessionManager = appContainer.sessionManager
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPatientDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Set Name
        lifecycleScope.launch {
            val session = appContainer.sessionManager.sessionFlow.first()
            binding.tvUserName.text = session.userName.ifBlank { "Patient" }
        }

        setupRecyclerView()
        setupClickListeners()
        observeUiState()
    }

    override fun onResume() {
        super.onResume()
        viewModel.fetchAppointments()
    }

    private fun setupRecyclerView() {
        binding.recyclerAppointments.layoutManager = LinearLayoutManager(this)
        binding.recyclerAppointments.adapter = PatientAppointmentAdapter { appointment ->
            viewModel.cancelAppointment(appointment.id)
        }
    }

    private fun setupClickListeners() {
        binding.btnLogout.setOnClickListener {
            viewModel.logout()
            startActivity(Intent(this, LoginActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            })
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
            finish()
        }

        binding.btnBookAppointment.setOnClickListener {
            startActivity(Intent(this, BookAppointmentActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    binding.emptyView.visibility =
                        if (!state.isLoading && state.appointments.isEmpty()) View.VISIBLE else View.GONE
                    binding.recyclerAppointments.visibility =
                        if (state.appointments.isNotEmpty()) View.VISIBLE else View.GONE

                    (binding.recyclerAppointments.adapter as? PatientAppointmentAdapter)?.submitList(state.appointments)

                    // Compute Stats
                    val safeAppointments = state.appointments
                    binding.tvTotalCount.text = safeAppointments.size.toString()
                    binding.tvApprovedCount.text = safeAppointments.count { it.status.equals("approved", ignoreCase = true) }.toString()
                    binding.tvPendingCount.text = safeAppointments.count { it.status.equals("pending", ignoreCase = true) }.toString()

                    state.errorMessage?.let {
                        Snackbar.make(binding.root, it, Snackbar.LENGTH_LONG)
                            .setBackgroundTint(resources.getColor(android.R.color.holo_red_dark, theme))
                            .show()
                        viewModel.clearMessage()
                    }

                    state.successMessage?.let {
                        Snackbar.make(binding.root, it, Snackbar.LENGTH_SHORT)
                            .setBackgroundTint(resources.getColor(android.R.color.holo_green_dark, theme))
                            .show()
                        viewModel.clearMessage()
                        viewModel.fetchAppointments() // refresh list
                    }
                }
            }
        }
    }
}
