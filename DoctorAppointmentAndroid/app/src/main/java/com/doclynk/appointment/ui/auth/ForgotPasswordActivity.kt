package com.doclynk.appointment.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.doclynk.appointment.databinding.ActivityForgotPasswordBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.doclynk.appointment.viewmodel.AuthViewModel
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

class ForgotPasswordActivity : AppCompatActivity() {

    private lateinit var binding: ActivityForgotPasswordBinding

    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: AuthViewModel by viewModels {
        AppViewModelFactory(
            authRepository = appContainer.authRepository,
            sessionManager = appContainer.sessionManager
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityForgotPasswordBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val slideFadeIn = android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.slide_fade_in)
        binding.root.startAnimation(slideFadeIn)

        setupClickListeners()
        observeUiState()
    }

    private fun setupClickListeners() {
        binding.btnBackToLogin.setOnClickListener {
            finish()
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        binding.btnSendResetOtp.setOnTouchListener { view, event ->
            when (event.action) {
                android.view.MotionEvent.ACTION_DOWN -> view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.btn_press))
                android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.btn_release))
            }
            false
        }

        binding.btnResetPassword.setOnTouchListener { view, event ->
            when (event.action) {
                android.view.MotionEvent.ACTION_DOWN -> view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.btn_press))
                android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.btn_release))
            }
            false
        }

        binding.btnSendResetOtp.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            if (email.isBlank()) {
                Snackbar.make(binding.root, "Enter your email", Snackbar.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            viewModel.forgotPassword(email)
        }

        binding.btnResetPassword.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            val otp = binding.etOtp.text.toString().trim()
            val newPassword = binding.etNewPassword.text.toString().trim()

            if (email.isBlank() || otp.isBlank() || newPassword.length < 6) {
                Snackbar.make(binding.root, "Enter valid details (password min 6 chars)", Snackbar.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            viewModel.resetPassword(email, otp, newPassword) {
                startActivity(Intent(this, LoginActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                })
                overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
                finish()
            }
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    binding.btnSendResetOtp.isEnabled = !state.isLoading
                    binding.btnResetPassword.isEnabled = !state.isLoading

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

    override fun onBackPressed() {
        super.onBackPressed()
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
    }
}
