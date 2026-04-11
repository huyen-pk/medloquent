plugins {
    alias(libs.plugins.androidApplication) apply false
    alias(libs.plugins.androidLibrary) apply false
    alias(libs.plugins.composeCompiler) apply false
    alias(libs.plugins.composeMultiplatform) apply false
    alias(libs.plugins.kotlinAndroid) apply false
    alias(libs.plugins.kotlinMultiplatform) apply false
    alias(libs.plugins.kotlinSerialization) apply false
}

// Harness checks: run platform-appropriate gates before build/assemble tasks.
val skipHarness: Boolean = providers.gradleProperty("skipHarness").orNull == "true"

tasks.register("harnessPython", Exec::class) {
    group = "verification"
    description = "Run python harness checks (ruff/black) against tracked files."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessPython because -PskipHarness=true") }
        commandLine("bash", "-lc", "echo skipped")
    } else {
        commandLine("bash", "-lc", "bash scripts/harness-python.sh $(git ls-files '*.py' || true)")
    }
}

tasks.register("harnessAndroid", Exec::class) {
    group = "verification"
    description = "Run android harness checks (ktlint/detekt/gradle lint)."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessAndroid because -PskipHarness=true") }
        commandLine("bash", "-lc", "echo skipped")
    } else {
        commandLine("bash", "-lc", "bash scripts/harness-android.sh")
    }
}

tasks.register("harnessIOS", Exec::class) {
    group = "verification"
    description = "Run ios harness checks (swiftlint)."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessIOS because -PskipHarness=true") }
        commandLine("bash", "-lc", "echo skipped")
    } else {
        commandLine("bash", "-lc", "bash scripts/harness-ios.sh")
    }
}

tasks.register("harnessCheck") {
    group = "verification"
    description = "Run all harness gates (python, android, ios)."
    dependsOn("harnessPython", "harnessAndroid", "harnessIOS")
}

// Ensure assemble/build tasks depend on the harness check so gates run on regular builds.
allprojects {
    if (!skipHarness) {
        tasks.matching { it.name == "assemble" || it.name == "build" }.configureEach {
            dependsOn(rootProject.tasks.named("harnessCheck"))
        }
    }
}
