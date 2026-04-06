package com.doclynk.appointment.data.api

import android.util.Log
import com.doclynk.appointment.BuildConfig
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
    private const val TAG = "DocLynk-API"
    private const val BASE_URL = "https://doclynk-mobile-app-backend.onrender.com/"

    private val loggingInterceptor = HttpLoggingInterceptor { message ->
        Log.d(TAG, message)
    }.apply {
        level = if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor.Level.BODY
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
    }

    /** Interceptor that logs the full request URL and response status for every call */
    private val urlLoggingInterceptor = Interceptor { chain ->
        val request = chain.request()
        Log.d(TAG, "➡️  REQUEST: ${request.method} ${request.url}")
        Log.d(TAG, "   Content-Type: ${request.body?.contentType()}")

        val startMs = System.currentTimeMillis()
        val response = chain.proceed(request)
        val durationMs = System.currentTimeMillis() - startMs

        Log.d(TAG, "⬅️  RESPONSE: ${response.code} ${response.message} (${durationMs}ms)")
        Log.d(TAG, "   URL: ${response.request.url}")

        response
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(urlLoggingInterceptor)
        .addInterceptor(loggingInterceptor)
        .retryOnConnectionFailure(true)
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .callTimeout(120, TimeUnit.SECONDS)
        .build()

    val apiService: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .client(okHttpClient)
            .build()
            .create(ApiService::class.java)
    }
}
