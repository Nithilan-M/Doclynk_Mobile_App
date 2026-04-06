package com.doclynk.appointment.ui.doctor

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.doclynk.appointment.data.model.Appointment
import com.doclynk.appointment.databinding.ItemDoctorAppointmentBinding

class DoctorAppointmentAdapter(
    private val onApprove: (Appointment) -> Unit,
    private val onReject: (Appointment) -> Unit,
    private val onDelete: (Appointment) -> Unit
) : ListAdapter<Appointment, DoctorAppointmentAdapter.AppointmentViewHolder>(DiffCallback) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): AppointmentViewHolder {
        val binding = ItemDoctorAppointmentBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return AppointmentViewHolder(binding)
    }

    override fun onBindViewHolder(holder: AppointmentViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class AppointmentViewHolder(
        private val binding: ItemDoctorAppointmentBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(item: Appointment) {
            binding.tvPatientName.text = item.patientName
            binding.tvDateTime.text = "${item.date} | ${item.timeSlot}"
            binding.tvReason.text = "Reason: ${item.reason}"
            binding.tvStatus.text = item.status

            binding.btnApprove.setOnClickListener { onApprove(item) }
            binding.btnReject.setOnClickListener { onReject(item) }
            binding.btnDelete.setOnClickListener { onDelete(item) }
        }
    }

    private companion object {
        val DiffCallback = object : DiffUtil.ItemCallback<Appointment>() {
            override fun areItemsTheSame(oldItem: Appointment, newItem: Appointment): Boolean {
                return oldItem.id == newItem.id
            }

            override fun areContentsTheSame(oldItem: Appointment, newItem: Appointment): Boolean {
                return oldItem == newItem
            }
        }
    }
}
