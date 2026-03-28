package com.doclynk.appointment.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.doclynk.appointment.databinding.ActivityRegisterBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.doclynk.appointment.viewmodel.AuthViewModel
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

        setupRoleSpinner()
        setupClickListeners()
        observeUiState()
    }

    private fun setupRoleSpinner() {
        val roleAdapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            listOf("patient", "doctor")
        )
        binding.spinnerRole.adapter = roleAdapter
    }

    private fun setupClickListeners() {
        binding.btnRegister.setOnClickListener {
            val name = binding.etName.text.toString().trim()
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            val role = binding.spinnerRole.selectedItem.toString()

            if (name.isBlank() || email.isBlank() || password.length < 6) {
                Toast.makeText(this, "Enter valid details (password min 6 chars)", Toast.LENGTH_SHORT).show()
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
                    finish()
                }
            )
        }

        binding.btnGoLogin.setOnClickListener {
            finish()
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    binding.btnRegister.isEnabled = !state.isLoading

                    state.errorMessage?.let {
                        Toast.makeText(this@RegisterActivity, it, Toast.LENGTH_LONG).show()
                        viewModel.clearMessage()
                    }

                    state.successMessage?.let {
                        Toast.makeText(this@RegisterActivity, it, Toast.LENGTH_SHORT).show()
                        viewModel.clearMessage()
                    }
                }
            }
        }
    }
}
