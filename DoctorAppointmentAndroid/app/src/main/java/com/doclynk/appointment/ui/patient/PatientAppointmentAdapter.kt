package com.doclynk.appointment.ui.patient

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.doclynk.appointment.data.model.Appointment
import com.doclynk.appointment.databinding.ItemPatientAppointmentBinding

class PatientAppointmentAdapter(
    private val onCancelClick: (Appointment) -> Unit
) : ListAdapter<Appointment, PatientAppointmentAdapter.AppointmentViewHolder>(DiffCallback) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): AppointmentViewHolder {
        val binding = ItemPatientAppointmentBinding.inflate(
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
        private val binding: ItemPatientAppointmentBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(item: Appointment) {
            binding.tvDoctorName.text = item.doctorName
            binding.tvDateTime.text = "${item.date} | ${item.timeSlot}"
            binding.tvReason.text = item.reason
            binding.tvStatus.text = item.status

            binding.btnCancel.setOnClickListener {
                onCancelClick(item)
            }
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
