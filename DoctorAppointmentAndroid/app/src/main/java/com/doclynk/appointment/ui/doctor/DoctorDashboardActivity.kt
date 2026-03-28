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
    private lateinit var appointmentAdapter: DoctorAppointmentAdapter
    private lateinit var token: String

    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: DoctorDashboardViewModel by viewModels {
        AppViewModelFactory(doctorRepository = appContainer.doctorRepository)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDoctorDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupRecyclerView()
        observeUiState()
        setupButtons()
        loadSessionAndAppointments()
    }

    private fun setupRecyclerView() {
        appointmentAdapter = DoctorAppointmentAdapter(
            onApprove = { appointment -> viewModel.updateStatus(token, appointment.id, "approved") },
            onReject = { appointment -> viewModel.updateStatus(token, appointment.id, "rejected") },
            onDelete = { appointment -> viewModel.deleteAppointment(token, appointment.id) }
        )
        binding.recyclerAppointments.apply {
            layoutManager = LinearLayoutManager(this@DoctorDashboardActivity)
            adapter = appointmentAdapter
        }
    }

    private fun setupButtons() {
        binding.btnLogout.setOnClickListener {
            lifecycleScope.launch {
                appContainer.sessionManager.clearSession()
                startActivity(Intent(this@DoctorDashboardActivity, LoginActivity::class.java))
                finish()
            }
        }
    }

    private fun loadSessionAndAppointments() {
        lifecycleScope.launch {
            val session = appContainer.sessionManager.sessionFlow.first()
            token = session.token
            val displayName = if (session.userName.isNotBlank()) "Dr. ${session.userName}" else "Doctor"
            binding.tvDoctorName.text = displayName
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
