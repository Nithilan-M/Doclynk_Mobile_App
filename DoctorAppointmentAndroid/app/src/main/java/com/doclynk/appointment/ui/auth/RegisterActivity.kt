package com.doclynk.appointment.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.doclynk.appointment.R
import com.doclynk.appointment.databinding.ActivityRegisterBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.doclynk.appointment.viewmodel.AuthViewModel
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

class RegisterActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRegisterBinding

    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: AuthViewModel by viewModels {
        AppViewModelFactory(
            authRepository = appContainer.authRepository,
            sessionManager = appContainer.sessionManager
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Select Patient by default
        binding.rgRole.check(R.id.rbPatient)
        
        val slideFadeIn = android.view.animation.AnimationUtils.loadAnimation(this, R.anim.slide_fade_in)
        binding.root.startAnimation(slideFadeIn)
        
        setupClickListeners()
        observeUiState()
    }

    private fun setupClickListeners() {
        binding.btnRegister.setOnTouchListener { view, event ->
            when (event.action) {
                android.view.MotionEvent.ACTION_DOWN -> {
                    view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, R.anim.btn_press))
                }
                android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> {
                    view.startAnimation(android.view.animation.AnimationUtils.loadAnimation(this, R.anim.btn_release))
                }
            }
            false
        }

        binding.btnRegister.setOnClickListener {
            val name = binding.etName.text.toString().trim()
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            val role = if (binding.rgRole.checkedRadioButtonId == R.id.rbDoctor) "doctor" else "patient"

            if (name.isBlank() || email.isBlank() || password.length < 6) {
                Snackbar.make(binding.root, "Enter valid details (password min 6 chars)", Snackbar.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            viewModel.startRegistrationEmailVerification(
                name = name,
                email = email,
                password = password,
                role = role,
                onOtpSent = { verifiedEmail, verificationToken ->
                    val intent = Intent(this, VerifyEmailActivity::class.java).apply {
                        putExtra(VerifyEmailActivity.EXTRA_EMAIL, verifiedEmail)
                        putExtra(VerifyEmailActivity.EXTRA_VERIFICATION_TOKEN, verificationToken)
                    }
                    startActivity(intent)
                    overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
                    finish()
                }
            )
        }

        binding.btnGoLogin.setOnClickListener {
            finish()
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }
    }

    override fun onBackPressed() {
        super.onBackPressed()
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    binding.btnRegister.isEnabled = !state.isLoading

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
}
