package com.doclynk.appointment.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.doclynk.appointment.databinding.ActivityVerifyEmailBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.ui.admin.AdminDashboardActivity
import com.doclynk.appointment.ui.doctor.DoctorDashboardActivity
import com.doclynk.appointment.ui.patient.PatientDashboardActivity
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.doclynk.appointment.viewmodel.AuthViewModel
import kotlinx.coroutines.launch

class VerifyEmailActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_EMAIL = "extra_email"
        const val EXTRA_VERIFICATION_TOKEN = "extra_verification_token"
    }

    private lateinit var binding: ActivityVerifyEmailBinding

    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: AuthViewModel by viewModels {
        AppViewModelFactory(
            authRepository = appContainer.authRepository,
            sessionManager = appContainer.sessionManager
        )
    }

    private lateinit var email: String
    private lateinit var verificationToken: String

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityVerifyEmailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        email = intent.getStringExtra(EXTRA_EMAIL).orEmpty()
        verificationToken = intent.getStringExtra(EXTRA_VERIFICATION_TOKEN).orEmpty()

        if (email.isBlank() || verificationToken.isBlank()) {
            Toast.makeText(this, "Verification session is invalid. Please register again.", Toast.LENGTH_LONG).show()
            startActivity(Intent(this, RegisterActivity::class.java))
            finish()
            return
        }

        binding.tvEmailValue.text = email
        
        val slideFadeIn = android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.slide_fade_in)
        binding.root.startAnimation(slideFadeIn)

        setupClickListeners()
        observeUiState()
    }

    private fun setupClickListeners() {
        binding.btnVerifyOtp.setOnTouchListener { view, event ->
            when (event.action) {
                android.view.MotionEvent.ACTION_DOWN -> view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.btn_press))
                android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.btn_release))
            }
            false
        }

        binding.btnVerifyOtp.setOnClickListener {
            val otp = binding.etOtp.text.toString().trim()
            if (otp.length < 4) {
                com.google.android.material.snackbar.Snackbar.make(binding.root, "Enter the OTP sent to your email", com.google.android.material.snackbar.Snackbar.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            viewModel.verifyRegistrationOtp(email, otp, verificationToken) { role ->
                routeByRole(role)
                finish()
            }
        }

        binding.btnResendOtp.setOnClickListener {
            viewModel.resendRegistrationOtp(verificationToken)
        }

        binding.btnBackToRegister.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
            finish()
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    binding.btnVerifyOtp.isEnabled = !state.isLoading
                    binding.btnResendOtp.isEnabled = !state.isLoading

                    state.errorMessage?.let {
                        com.google.android.material.snackbar.Snackbar.make(binding.root, it, com.google.android.material.snackbar.Snackbar.LENGTH_LONG)
                            .setBackgroundTint(resources.getColor(android.R.color.holo_red_dark, theme))
                            .show()
                        viewModel.clearMessage()
                    }

                    state.successMessage?.let {
                        com.google.android.material.snackbar.Snackbar.make(binding.root, it, com.google.android.material.snackbar.Snackbar.LENGTH_SHORT)
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
    }
}
