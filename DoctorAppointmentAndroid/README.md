# DocLynk Android (Kotlin)

Doctor Appointment Booking Android app built with MVVM, Retrofit, Coroutines, StateFlow, and Material Design 3.

## Features

- Authentication: Login and Register (doctor/patient role)
- Session persistence using DataStore
- Patient:
  - View appointments
  - Book appointment (doctor, date, available slot, reason)
  - Cancel appointment
- Doctor:
  - View all appointments
  - Approve/Reject appointment
  - Delete appointment
- API error handling with a common repository pattern
- RecyclerView-based lists and loading/empty/error states

## Tech Stack

- Kotlin + AndroidX
- MVVM architecture
- Retrofit + Gson + OkHttp logging
- Kotlin Coroutines + StateFlow
- DataStore preferences
- Material Design 3
- Navigation component graph (`res/navigation/nav_graph.xml`)

## Project Structure

```
app/src/main/java/com/doclynk/appointment/
  data/
    api/
    model/
    repository/
  ui/
    auth/
    patient/
    doctor/
  viewmodel/
```

## API Endpoints Integrated

- `POST /api/login`
- `POST /api/register`
- `GET /api/patient/appointments`
- `GET /api/doctors`
- `GET /api/check_availability?doctor_id=&date=`
- `POST /api/appointment/book`
- `POST /api/appointment/update_status`
- `DELETE /api/appointment/delete`

Also included for doctor role listing:
- `GET /api/doctor/appointments`

## Base URL

Set in `app/build.gradle.kts` as:

```kotlin
buildConfigField("String", "BASE_URL", "\"http://10.0.2.2:5000/\"")
```

- `10.0.2.2` is the Android emulator alias for host `localhost`.
- If using a real device, replace with your computer LAN IP.

## Sample Request/Response Handling

### Login request

```kotlin
@POST("api/login")
suspend fun login(@Body body: LoginRequest): Response<AuthResponse>
```

```kotlin
when (val result = authRepository.login(email, password)) {
    is ApiResult.Success -> {
        val user = result.data.user
        // save DataStore session and route by role
    }
    is ApiResult.Error -> {
        // show error toast/snackbar
    }
}
```

### Book appointment request

```kotlin
apiService.bookAppointment(
    token = "Bearer $token",
    body = BookAppointmentRequest(
        doctor_id = doctorId,
        date = date,
        time_slot = timeSlot,
        reason = reason
    )
)
```

## Important Notes

- Ensure Flask API returns JSON fields matching model names.
- If your API wraps data inside another key, update model classes accordingly.
- Navigation graph is included in `res/navigation/nav_graph.xml` and can be expanded to fully fragment-based navigation if needed.

## Run Instructions

1. Open `DoctorAppointmentAndroid` folder in Android Studio.
2. Let Gradle sync and download dependencies.
3. Start Flask backend on port `5000`.
4. Run app on emulator/device.
5. Login/Register and test patient/doctor flows.
