plugins {
    alias(libs.plugins.androidLibrary)
    alias(libs.plugins.kotlinMultiplatform)
}

kotlin {
    jvmToolchain(21)

    androidTarget()
    iosX64()
    iosArm64()
    iosSimulatorArm64()

    sourceSets {
        commonMain.dependencies {
            implementation(project(":shared:audio"))
            implementation(project(":shared:core"))
            implementation(libs.kotlinx.coroutines.core)
        }
    }
}

android {
    namespace = "com.medloquent.shared.asr"
    compileSdk = 35

    defaultConfig {
        minSdk = 29
    }
}
