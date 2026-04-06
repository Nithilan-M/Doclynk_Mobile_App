package com.doclynk.appointment.ui.doctor

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import com.doclynk.appointment.databinding.ActivityDoctorDashboardBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.ui.auth.LoginActivity
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.doclynk.appointment.viewmodel.DoctorDashboardViewModel
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class DoctorDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDoctorDashboardBinding
    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: DoctorDashboardViewModel by viewModels {
        AppViewModelFactory(
            doctorRepository = appContainer.doctorRepository,
            sessionManager = appContainer.sessionManager
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDoctorDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Set Name
        lifecycleScope.launch {
            val session = appContainer.sessionManager.sessionFlow.first()
            binding.tvDoctorName.text = "Dr. ${session.userName.ifBlank { "Specialist" }}"
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
        binding.recyclerAppointments.adapter = DoctorAppointmentAdapter(
            onApprove = { appointment -> viewModel.updateStatus(appointment.id, "approved") },
            onReject = { appointment -> viewModel.updateStatus(appointment.id, "rejected") },
            onDelete = { appointment -> viewModel.deleteAppointment(appointment.id) }
        )
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

                    (binding.recyclerAppointments.adapter as? DoctorAppointmentAdapter)?.submitList(state.appointments)

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
                        viewModel.fetchAppointments()
                    }
                }
            }
        }
    }
}
