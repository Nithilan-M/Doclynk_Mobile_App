package com.doclynk.appointment.ui.admin

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
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
    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: AdminDashboardViewModel by viewModels {
        AppViewModelFactory(
            adminRepository = appContainer.adminRepository,
            sessionManager = appContainer.sessionManager
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAdminDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val slideFadeIn = android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.slide_fade_in)
        binding.root.startAnimation(slideFadeIn)

        setupClickListeners()
        observeUiState()
        loadSessionAndData()
    }

    private fun setupClickListeners() {
        binding.btnRefresh.setOnClickListener {
            viewModel.loadAll()
        }

        binding.btnSeedDoctorAppointments.setOnClickListener {
            viewModel.seedDoctorAppointments()
        }

        binding.cardManageUsers.setOnClickListener {
            startActivity(Intent(this, AdminManageUsersActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        binding.cardManageAppointments.setOnClickListener {
            startActivity(Intent(this, AdminManageAppointmentsActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        binding.btnLogout.setOnClickListener {
            viewModel.logout()
            startActivity(Intent(this@AdminDashboardActivity, LoginActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            })
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
            finish()
        }
    }

    private fun loadSessionAndData() {
        lifecycleScope.launch {
            val session = appContainer.sessionManager.sessionFlow.first()
            val adminName = if (session.userName.isBlank()) "Admin" else "${session.userName}"
            viewModel.setAdminName(adminName)
            viewModel.loadAll()
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    binding.tvAdminName.text = state.adminName
                    binding.tvStats.text =
                        "Users: ${state.stats.total_users} (Docs ${state.stats.total_doctors}, Pats ${state.stats.total_patients}, Adms ${state.stats.total_admins})\n" +
                        "Appointments: ${state.stats.total_appointments} | Pend ${state.stats.pending_appointments} | Appr ${state.stats.approved_appointments} | Rej ${state.stats.rejected_appointments}"

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
                        viewModel.loadAll() 
                    }
                }
            }
        }
    }
}
