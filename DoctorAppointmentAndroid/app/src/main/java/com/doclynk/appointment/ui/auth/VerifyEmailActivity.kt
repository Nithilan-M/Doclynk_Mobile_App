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
        setupClickListeners()
        observeUiState()
    }

    private fun setupClickListeners() {
        binding.btnVerifyOtp.setOnClickListener {
            val otp = binding.etOtp.text.toString().trim()
            if (otp.length < 4) {
                Toast.makeText(this, "Enter the OTP sent to your email", Toast.LENGTH_SHORT).show()
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
                        Toast.makeText(this@VerifyEmailActivity, it, Toast.LENGTH_LONG).show()
                        viewModel.clearMessage()
                    }

                    state.successMessage?.let {
                        Toast.makeText(this@VerifyEmailActivity, it, Toast.LENGTH_SHORT).show()
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
