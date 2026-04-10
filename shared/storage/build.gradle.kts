plugins {
    alias(libs.plugins.androidLibrary)
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.kotlinSerialization)
}

kotlin {
    jvmToolchain(21)

    androidTarget()
    iosX64()
    iosArm64()
    iosSimulatorArm64()

    sourceSets {
        commonMain.dependencies {
            implementation(project(":shared:core"))
            api(project(":shared:crypto"))
            api(project(":shared:ehr"))
            api(libs.kotlinx.serialization.json)
            implementation(libs.okio)
        }
    }
}

android {
    namespace = "com.medloquent.shared.storage"
    compileSdk = 35

    defaultConfig {
        minSdk = 29
    }
}
