package com.doclynk.appointment.data.repository

import android.content.Context
import androidx.datastore.preferences.core.MutablePreferences
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "session_prefs")

class SessionManager(private val context: Context) {
    private object Keys {
        val token = stringPreferencesKey("token")
        val userId = intPreferencesKey("user_id")
        val userName = stringPreferencesKey("user_name")
        val userEmail = stringPreferencesKey("user_email")
        val role = stringPreferencesKey("role")
    }

    val sessionFlow: Flow<UserSession> = context.dataStore.data.map { pref ->
        UserSession(
            token = pref[Keys.token].orEmpty(),
            userId = pref[Keys.userId] ?: -1,
            userName = pref[Keys.userName].orEmpty(),
            userEmail = pref[Keys.userEmail].orEmpty(),
            role = pref[Keys.role].orEmpty()
        )
    }

    suspend fun saveSession(session: UserSession) {
        context.dataStore.edit { pref: MutablePreferences ->
            pref[Keys.token] = session.token
            pref[Keys.userId] = session.userId
            pref[Keys.userName] = session.userName
            pref[Keys.userEmail] = session.userEmail
            pref[Keys.role] = session.role
        }
    }

    suspend fun clearSession() {
        context.dataStore.edit { it.clear() }
    }
}

data class UserSession(
    val token: String,
    val userId: Int,
    val userName: String,
    val userEmail: String,
    val role: String
)
