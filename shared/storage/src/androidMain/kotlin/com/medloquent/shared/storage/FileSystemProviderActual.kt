package com.medloquent.shared.storage

import okio.FileSystem

actual fun defaultFileSystem(): FileSystem = FileSystem.SYSTEM
