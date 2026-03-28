package com.doclynk.appointment.ui.admin

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.doclynk.appointment.data.model.AdminAppointment
import com.doclynk.appointment.databinding.ItemAdminAppointmentBinding

class AdminAppointmentAdapter(
    private val onApprove: (AdminAppointment) -> Unit,
    private val onReject: (AdminAppointment) -> Unit,
    private val onDelete: (AdminAppointment) -> Unit
) : ListAdapter<AdminAppointment, AdminAppointmentAdapter.AdminAppointmentViewHolder>(DiffCallback) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): AdminAppointmentViewHolder {
        val binding = ItemAdminAppointmentBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return AdminAppointmentViewHolder(binding)
    }

    override fun onBindViewHolder(holder: AdminAppointmentViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class AdminAppointmentViewHolder(
        private val binding: ItemAdminAppointmentBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(item: AdminAppointment) {
            binding.tvTitle.text = "#${item.id} ${item.patient_name} -> Dr. ${item.doctor_name}"
            binding.tvMeta.text = "${item.date} | ${item.time_slot} | ${item.status}"
            binding.tvReason.text = "Reason: ${item.reason}"

            binding.btnApprove.setOnClickListener { onApprove(item) }
            binding.btnReject.setOnClickListener { onReject(item) }
            binding.btnDelete.setOnClickListener { onDelete(item) }
        }
    }

    private companion object {
        val DiffCallback = object : DiffUtil.ItemCallback<AdminAppointment>() {
            override fun areItemsTheSame(oldItem: AdminAppointment, newItem: AdminAppointment): Boolean {
                return oldItem.id == newItem.id
            }

            override fun areContentsTheSame(oldItem: AdminAppointment, newItem: AdminAppointment): Boolean {
                return oldItem == newItem
            }
        }
    }
}
