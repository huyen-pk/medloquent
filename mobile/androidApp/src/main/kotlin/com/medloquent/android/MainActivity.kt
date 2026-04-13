package com.medloquent.android

import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.medloquent.shared.app.MedLoquentApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            MedLoquentApp(
                storageRoot = filesDir.absolutePath,
                deviceId = buildDeviceId(),
                onShareBundle = ::shareBundle,
            )
        }
    }

    private fun buildDeviceId(): String = listOfNotNull(Build.MANUFACTURER, Build.MODEL)
        .joinToString(separator = "-")
        .lowercase()
        .replace(' ', '-')
        .ifBlank { "android-edge" }

    private fun shareBundle(bundleJson: String) {
        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = "application/fhir+json"
            putExtra(Intent.EXTRA_SUBJECT, "MedLoquent FHIR Bundle")
            putExtra(Intent.EXTRA_TEXT, bundleJson)
        }

        startActivity(Intent.createChooser(shareIntent, "Share FHIR bundle"))
    }
}
