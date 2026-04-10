package com.medloquent.shared.app

import androidx.compose.ui.window.ComposeUIViewController
import platform.Foundation.NSUUID
import platform.Foundation.NSTemporaryDirectory

class MedLoquentIosHost {
    fun rootViewController() = ComposeUIViewController {
        MedLoquentApp(
            storageRoot = NSTemporaryDirectory(),
            deviceId = NSUUID().UUIDString(),
        )
    }
}

fun MainViewController() = MedLoquentIosHost().rootViewController()
