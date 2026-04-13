plugins {
    alias(libs.plugins.androidApplication) apply false
    alias(libs.plugins.androidLibrary) apply false
    alias(libs.plugins.composeCompiler) apply false
    alias(libs.plugins.composeMultiplatform) apply false
    alias(libs.plugins.kotlinAndroid) apply false
    alias(libs.plugins.kotlinMultiplatform) apply false
    alias(libs.plugins.kotlinSerialization) apply false
    id("com.diffplug.spotless") version "6.21.0" apply false
    id("io.gitlab.arturbosch.detekt") version "1.23.0" apply false
}

// Harness checks: run platform-appropriate gates before build/assemble tasks.
val skipHarness: Boolean = providers.gradleProperty("skipHarness").orNull == "true"

// Apply Spotless and Detekt to subprojects so Gradle tasks (spotlessApply / detekt)
// operate across the repo instead of relying on local shell scripts.
subprojects {
    apply(plugin = "com.diffplug.spotless")
    apply(plugin = "io.gitlab.arturbosch.detekt")

    // Spotless basic configuration: format Kotlin and some misc files
    extensions.configure<com.diffplug.gradle.spotless.SpotlessExtension> {
        kotlin {
            target("**/*.kt")
            ktlint("0.48.2").userData(
                mapOf(
                    "android" to "false",
                    "max_line_length" to "80",
                )
            )
            trimTrailingWhitespace()
            endWithNewline()
        }

        format("misc") {
            target("**/*.gradle.kts", "**/*.md", "**/*.yml", "**/*.yaml")
            trimTrailingWhitespace()
            endWithNewline()
        }
    }

    // Detekt configuration: use repo-level detekt.yml
    extensions.configure<io.gitlab.arturbosch.detekt.extensions.DetektExtension> {
        buildUponDefaultConfig = true
        // Use default detekt config by default; repo-level detekt.yml can be re-enabled
        // config = files(rootProject.file("detekt.yml"))
        parallel = true
    }

    // Some detekt task implementations accept a jvmTarget on the task; configure tasks if present.
    try {
        tasks.withType(io.gitlab.arturbosch.detekt.Detekt::class.java).configureEach {
            this.jvmTarget = "19"
        }
    } catch (e: Exception) {
        // If detekt task class isn't available at configuration time, ignore; the wrapper will use defaults.
    }

    dependencies {
        // Enable detekt-formatting rules
        add("detektPlugins", "io.gitlab.arturbosch.detekt:detekt-formatting:1.23.0")
    }
}

// Python: format and check tasks (use project venv ./hf_env when available)
tasks.register("harnessFormatPython", Exec::class) {
    group = "verification"
    description = "Format python sources with black and ruff (if available)."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessFormatPython because -PskipHarness=true") }
        commandLine("bash", "-lc", "echo skipped")
    } else {
        commandLine(
            "bash",
            "-lc",
            """
            set -euo pipefail
            if [ -d ./hf_env/bin ]; then
              export PATH=\"${'$'}PWD/hf_env/bin:${'$'}PATH\"
            fi
            command -v ruff >/dev/null 2>&1 || { echo \"ruff not found\" >&2; exit 1; }
            command -v black >/dev/null 2>&1 || { echo \"black not found\" >&2; exit 1; }
            ruff check --fix .
            black .
            """.trimIndent()
        )
    }
}

tasks.register("harnessCheckPython", Exec::class) {
    group = "verification"
    description = "Run python linters/checkers (ruff, mypy)"
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessCheckPython because -PskipHarness=true") }
        commandLine("bash", "-lc", "echo skipped")
    } else {
        commandLine(
            "bash",
            "-lc",
            """
            set -euo pipefail
            if [ -d ./hf_env/bin ]; then
              export PATH=\"${'$'}PWD/hf_env/bin:${'$'}PATH\"
            fi
            command -v ruff >/dev/null 2>&1 || { echo \"ruff not found\" >&2; exit 1; }
            command -v black >/dev/null 2>&1 || { echo \"black not found\" >&2; exit 1; }
            command -v flake8 >/dev/null 2>&1 || { echo \"flake8 not found\" >&2; exit 1; }
            command -v mypy >/dev/null 2>&1 || { echo \"mypy not found\" >&2; exit 1; }
            ruff check .
            black --check .
            flake8 .
            mypy --config-file mypy.ini .
            """.trimIndent()
        )
    }
}

// Backwards-compatible harness entry that aggregates python format+check
tasks.register("harnessPython") {
    group = "verification"
    description = "Run python harness formatting and checks."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessPython because -PskipHarness=true") }
    } else {
        dependsOn("harnessFormatPython", "harnessCheckPython")
    }
}

// Kotlin/Android: use Spotless and Detekt via Gradle (fall back to running Gradle wrapper)
tasks.register("harnessFormatKotlin", Exec::class) {
    group = "verification"
    description = "Run Spotless (ktlint) to format Kotlin sources across subprojects."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessFormatKotlin because -PskipHarness=true") }
        commandLine("bash", "-lc", "echo skipped")
    } else {
        commandLine("bash", "-lc", "set -euo pipefail; ./gradlew spotlessApply")
    }
}

tasks.register("harnessCheckKotlin", Exec::class) {
    group = "verification"
    description = "Run Spotless check and Detekt across Kotlin subprojects."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessCheckKotlin because -PskipHarness=true") }
        commandLine("bash", "-lc", "echo skipped")
    } else {
        commandLine("bash", "-lc", "set -euo pipefail; ./gradlew spotlessCheck detekt")
    }
}

tasks.register("harnessAndroid") {
    group = "verification"
    description = "Run android/kotlin harness checks (format + checks)."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessAndroid because -PskipHarness=true") }
    } else {
        dependsOn("harnessFormatKotlin", "harnessCheckKotlin")
    }
}

// iOS: prefer swiftformat/swiftlint when available
tasks.register("harnessFormatIOS", Exec::class) {
    group = "verification"
    description = "Run swiftformat / swiftlint autocorrect if available."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessFormatIOS because -PskipHarness=true") }
        commandLine("bash", "-lc", "echo skipped")
    } else {
        commandLine(
            "bash",
            "-lc",
                        """
                        set -euo pipefail
                        if command -v swiftformat >/dev/null 2>&1; then
                            swiftformat .
                        else
                            echo \"swiftformat not found\"
                        fi
                        if command -v swiftlint >/dev/null 2>&1; then
                            swiftlint autocorrect
                        else
                            echo \"swiftlint not found\"
                        fi
                        """.trimIndent()
        )
    }
}

tasks.register("harnessCheckIOS", Exec::class) {
    group = "verification"
    description = "Run swiftlint lint if available."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessCheckIOS because -PskipHarness=true") }
        commandLine("bash", "-lc", "echo skipped")
    } else {
                commandLine(
                        "bash",
                        "-lc",
                        """
                        set -euo pipefail
                        if command -v swiftlint >/dev/null 2>&1; then
                            swiftlint lint
                        else
                            echo \"swiftlint not found\"
                        fi
                        """.trimIndent()
                )
    }
}

tasks.register("harnessIOS") {
    group = "verification"
    description = "Run ios harness (format + check)."
    if (skipHarness) {
        doFirst { logger.lifecycle("Skipping harnessIOS because -PskipHarness=true") }
    } else {
        dependsOn("harnessFormatIOS", "harnessCheckIOS")
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
