package com.doclynk.appointment.ui.admin

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.doclynk.appointment.data.model.AdminUser
import com.doclynk.appointment.databinding.ItemAdminUserBinding

class AdminUserAdapter(
    private val onToggleAdmin: (AdminUser) -> Unit,
    private val onDelete: (AdminUser) -> Unit
) : ListAdapter<AdminUser, AdminUserAdapter.AdminUserViewHolder>(DiffCallback) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): AdminUserViewHolder {
        val binding = ItemAdminUserBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return AdminUserViewHolder(binding)
    }

    override fun onBindViewHolder(holder: AdminUserViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class AdminUserViewHolder(
        private val binding: ItemAdminUserBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(item: AdminUser) {
            binding.tvUserName.text = item.name
            binding.tvUserEmail.text = item.email
            binding.tvRole.text = if (item.is_admin) "System Admin" else item.role.replaceFirstChar { it.uppercase() }

            binding.btnToggleAdmin.text = if (item.is_admin) "Revoke Admin" else "Grant Admin"
            binding.btnToggleAdmin.setOnClickListener { onToggleAdmin(item) }
            binding.btnDelete.setOnClickListener { onDelete(item) }
        }
    }

    private companion object {
        val DiffCallback = object : DiffUtil.ItemCallback<AdminUser>() {
            override fun areItemsTheSame(oldItem: AdminUser, newItem: AdminUser): Boolean {
                return oldItem.id == newItem.id
            }

            override fun areContentsTheSame(oldItem: AdminUser, newItem: AdminUser): Boolean {
                return oldItem == newItem
            }
        }
    }
}
