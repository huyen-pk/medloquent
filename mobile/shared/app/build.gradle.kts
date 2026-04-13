plugins {
    alias(libs.plugins.androidLibrary)
    alias(libs.plugins.composeCompiler)
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.kotlinMultiplatform)
}

kotlin {
    jvmToolchain(21)

    androidTarget()

    val iosTargets = listOf(
        iosX64(),
        iosArm64(),
        iosSimulatorArm64(),
    )

    iosTargets.forEach { target ->
        target.binaries.framework {
            baseName = "MedLoquentShared"
            isStatic = true
        }
    }

    sourceSets {
        commonMain.dependencies {
            implementation(project(":shared:asr"))
            implementation(project(":shared:audio"))
            implementation(project(":shared:core"))
            implementation(project(":shared:crypto"))
            implementation(project(":shared:ehr"))
            implementation(project(":shared:fl"))
            implementation(project(":shared:lora"))
            implementation(project(":shared:nlp"))
            implementation(project(":shared:storage"))
            implementation(compose.foundation)
            implementation(compose.material3)
            implementation(compose.runtime)
            implementation(compose.ui)
            implementation(libs.kotlinx.coroutines.core)
        }
        commonTest.dependencies {
            implementation(kotlin("test"))
        }
    }
}

android {
    namespace = "com.medloquent.shared.app"
    compileSdk = 35

    defaultConfig {
        minSdk = 29
    }
}
