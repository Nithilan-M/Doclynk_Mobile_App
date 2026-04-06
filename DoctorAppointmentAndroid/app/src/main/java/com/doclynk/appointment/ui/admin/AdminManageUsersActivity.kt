package com.doclynk.appointment.ui.admin

import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import com.doclynk.appointment.databinding.ActivityAdminManageUsersBinding
import com.doclynk.appointment.di.AppContainer
import com.doclynk.appointment.viewmodel.AdminDashboardViewModel
import com.doclynk.appointment.viewmodel.AppViewModelFactory
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

class AdminManageUsersActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAdminManageUsersBinding
    private lateinit var userAdapter: AdminUserAdapter
    private val appContainer by lazy { AppContainer(applicationContext) }

    private val viewModel: AdminDashboardViewModel by viewModels {
        AppViewModelFactory(
            adminRepository = appContainer.adminRepository,
            sessionManager = appContainer.sessionManager
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAdminManageUsersBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val slideFadeIn = android.view.animation.AnimationUtils.loadAnimation(this, com.doclynk.appointment.R.anim.slide_fade_in)
        binding.root.startAnimation(slideFadeIn)

        setupUI()
        observeUiState()
        viewModel.loadAll()
    }

    private fun setupUI() {
        binding.btnBack.setOnClickListener {
            finish()
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        userAdapter = AdminUserAdapter(
            onToggleAdmin = { user -> viewModel.toggleAdmin(user.id) },
            onDelete = { user -> viewModel.deleteUser(user.id) }
        )

        binding.recyclerUsers.apply {
            layoutManager = LinearLayoutManager(this@AdminManageUsersActivity)
            adapter = userAdapter
        }
    }

    private fun observeUiState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    userAdapter.submitList(state.users)

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
