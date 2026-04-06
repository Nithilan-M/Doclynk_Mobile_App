package com.doclynk.appointment.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.doclynk.appointment.databinding.ActivityLoginBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.ui.admin.AdminDashboardActivity
import com.doclynk.appointment.ui.doctor.DoctorDashboardActivity
import com.doclynk.appointment.ui.patient.PatientDashboardActivity
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.doclynk.appointment.viewmodel.AuthViewModel
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding

    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: AuthViewModel by viewModels {
        AppViewModelFactory(
            authRepository = appContainer.authRepository,
            sessionManager = appContainer.sessionManager
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val slideFadeIn = android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.slide_fade_in)
        binding.root.startAnimation(slideFadeIn)

        checkExistingSession()
        setupClickListeners()
        observeUiState()
    }

    private fun checkExistingSession() {
        lifecycleScope.launch {
            val session = appContainer.sessionManager.sessionFlow.first()
            if (session.token.isNotBlank() && session.role.isNotBlank()) {
                routeByRole(session.role)
                finish()
            }
        }
    }

    private fun setupClickListeners() {
        binding.btnLogin.setOnTouchListener { view, event ->
            when (event.action) {
                android.view.MotionEvent.ACTION_DOWN -> {
                    view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.btn_press))
                }
                android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> {
                    view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.btn_release))
                }
            }
            false
        }

        binding.btnLogin.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()

            if (email.isBlank() || password.isBlank()) {
                Snackbar.make(binding.root, "Please enter email and password", Snackbar.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            viewModel.login(email, password) { role ->
                routeByRole(role)
                finish()
            }
        }

        binding.btnGoRegister.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        binding.btnForgotPassword.setOnClickListener {
            startActivity(Intent(this, ForgotPasswordActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    binding.btnLogin.isEnabled = !state.isLoading

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
                    }
                }
            }
        }
    }

    private fun routeByRole(role: String) {
        val intent = when (role.lowercase()) {
            "doctor" -> Intent(this, DoctorDashboardActivity::class.java)
            "admin" -> Intent(this, AdminDashboardActivity::class.java)
            else -> Intent(this, PatientDashboardActivity::class.java)
        }
        startActivity(intent)
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
    }
}
