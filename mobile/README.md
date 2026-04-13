# Mobile — MedLoquent

This directory contains the Kotlin Multiplatform mobile components for MedLoquent: Android and iOS host shells and the shared Kotlin modules that implement ASR orchestration, clinical NLP, FHIR mapping, encrypted storage adapters, and federated learning clients.

Quick start (mobile development)

1. Install JDK 21.
2. Ensure Android SDK is available: set `sdk.dir` in `mobile/local.properties` or export `ANDROID_HOME` and `ANDROID_SDK_ROOT` to a working Android SDK installation.
3. Use the repository dispatcher or run the mobile wrapper directly:

```bash
# Run the repo-level dispatcher (preferred)
bash ./build.sh build

# Or run mobile Gradle directly
bash ./mobile/gradlew :androidApp:assembleDebug
```

4. Generate the shared iOS XCFramework (on macOS):

```bash
bash ./mobile/gradlew :shared:app:assembleXCFramework
```

Dev container

The repo includes a VS Code devcontainer at `.devcontainer/` configured for Kotlin Multiplatform and Android development. The container installs JDK, Gradle, and Android command-line tools and persists the SDK in a shared volume.

Remote macOS (Xcode) bridge

Xcode does not run inside a Linux container. The supported workflow is to use the devcontainer for shared-code and Android work, then sync to a remote macOS machine for Xcode builds.

1. Copy `.devcontainer/remote-mac.env.example` to your environment and set the SSH/host variables.
2. Optionally install XcodeGen on the remote macOS host to generate the Xcode project from `mobile/iosApp/project.yml`.
3. From inside the devcontainer, run:

```bash
mobile/scripts/remote-xcode.sh open   # sync + open Xcode project remotely
mobile/scripts/remote-xcode.sh build  # sync + run xcodebuild remotely
```

Harness & formatting

- Kotlin formatting and static analysis: configured via Spotless and Detekt in `mobile/build.gradle.kts`.
- iOS: `swiftlint`/`swiftformat` are used when available on macOS.
- To skip harness checks for mobile builds, pass the Gradle property `-PskipHarness=true` when invoking the mobile build or set `SKIP_HARNESS=1` in the environment.

CI notes

- The CI workflow caches the mobile Gradle distribution and invokes the repo dispatcher or the mobile Gradle wrapper directly. See `.github/workflows/ci.yml` for details.

Further reading

- Architecture reference: `mobile/docs/architecture.md`
- Mobile build scripts and wrapper: `mobile/gradlew`, `mobile/gradle/`
