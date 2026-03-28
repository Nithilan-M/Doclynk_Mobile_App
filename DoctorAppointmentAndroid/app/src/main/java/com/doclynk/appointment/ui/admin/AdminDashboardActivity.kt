package com.doclynk.appointment.ui.admin

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import com.doclynk.appointment.databinding.ActivityAdminDashboardBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.ui.auth.LoginActivity
import com.doclynk.appointment.viewmodel.AdminDashboardViewModel
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class AdminDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAdminDashboardBinding
    private lateinit var token: String
    private lateinit var userAdapter: AdminUserAdapter
    private lateinit var appointmentAdapter: AdminAppointmentAdapter
    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: AdminDashboardViewModel by viewModels {
        AppViewModelFactory(adminRepository = appContainer.adminRepository)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAdminDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupLists()
        setupButtons()
        observeUiState()
        loadSessionAndData()
    }

    private fun setupLists() {
        userAdapter = AdminUserAdapter(
            onToggleAdmin = { user -> viewModel.toggleAdmin(token, user.id) },
            onDelete = { user -> viewModel.deleteUser(token, user.id) }
        )
        appointmentAdapter = AdminAppointmentAdapter(
            onApprove = { appointment -> viewModel.updateAppointmentStatus(token, appointment.id, "Approved") },
            onReject = { appointment -> viewModel.updateAppointmentStatus(token, appointment.id, "Rejected") },
            onDelete = { appointment -> viewModel.deleteAppointment(token, appointment.id) }
        )

        binding.recyclerUsers.apply {
            layoutManager = LinearLayoutManager(this@AdminDashboardActivity)
            adapter = userAdapter
        }

        binding.recyclerAppointments.apply {
            layoutManager = LinearLayoutManager(this@AdminDashboardActivity)
            adapter = appointmentAdapter
        }
    }

    private fun setupButtons() {
        binding.btnRefresh.setOnClickListener {
            viewModel.loadAll(token)
        }

        binding.btnSeedDoctorAppointments.setOnClickListener {
            viewModel.seedDoctorAppointments(token)
        }

        binding.btnLogout.setOnClickListener {
            lifecycleScope.launch {
                appContainer.sessionManager.clearSession()
                startActivity(Intent(this@AdminDashboardActivity, LoginActivity::class.java))
                finish()
            }
        }
    }

    private fun loadSessionAndData() {
        lifecycleScope.launch {
            val session = appContainer.sessionManager.sessionFlow.first()
            token = session.token
            val adminName = if (session.userName.isBlank()) "Admin" else "Admin ${session.userName}"
            viewModel.setAdminName(adminName)
            viewModel.loadAll(token)
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.loading) View.VISIBLE else View.GONE
                    binding.tvAdminName.text = state.adminName
                    binding.tvStats.text =
                        "Users: ${state.stats.total_users} (Doctors ${state.stats.total_doctors}, Patients ${state.stats.total_patients}, Admins ${state.stats.total_admins})\n" +
                        "Appointments: ${state.stats.total_appointments} | Pending ${state.stats.pending_appointments} | Approved ${state.stats.approved_appointments} | Rejected ${state.stats.rejected_appointments}"

                    userAdapter.submitList(state.users)
                    appointmentAdapter.submitList(state.appointments)
                    binding.recyclerUsers.scheduleLayoutAnimation()
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
