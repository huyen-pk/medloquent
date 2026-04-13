# MedLoquent

MedLoquent is a Kotlin Multiplatform mobile application scaffold for fully offline medical dictation, clinical NLP structuring, FHIR bundle generation, encrypted local persistence, federated learning, and LoRa-ready synchronization.

## Architecture

The implementation follows the reference architecture in mobile/docs/architecture.md:

- Edge-first inference pipeline: seeded audio capture -> offline ASR normalization -> clinical NLP -> FHIR bundle generation
- FHIR-first storage: bundle generation and local JSON persistence behind a storage abstraction
- Privacy-first learning: top-layer feature deltas only, queued locally for intermittent low-bandwidth sync
- Kotlin Multiplatform shared runtime with Android and iOS entry points

## Project structure

- mobile/androidApp: Android launcher application
- mobile/iosApp: SwiftUI host shell for the generated iOS framework
- mobile/shared/core: shared clinical and federated learning models
- mobile/shared/audio: audio capture contract and seeded offline capture implementation
- mobile/shared/asr: offline ASR orchestration and medical abbreviation normalization
- mobile/shared/nlp: rule-based clinical entity extraction and note structuring
- mobile/shared/ehr: FHIR R4 bundle mapper and JSON formatter
- mobile/shared/crypto: envelope codec abstraction with a demo codec for local development
- mobile/shared/storage: encrypted bundle persistence abstraction
- mobile/shared/fl: on-device layer-wise federated update preparation
- mobile/shared/lora: LoRa packet queue abstraction
- mobile/shared/app: Compose Multiplatform UI and workflow coordinator

## Build notes

The mobile Gradle wrapper now lives under `mobile/`. The Android build was validated locally on Linux with Android SDK Platform 35 and JDK 21. To build locally:

1. Install JDK 21.
2. Set `sdk.dir` in `mobile/local.properties` or export `ANDROID_HOME` and `ANDROID_SDK_ROOT` to a working Android SDK installation.
3. Run the global dispatcher with `bash ./build.sh build`, or invoke mobile Gradle directly with `bash ./mobile/gradlew :androidApp:assembleDebug`.
4. Generate the shared iOS framework with `bash ./mobile/gradlew :shared:app:assembleXCFramework` and attach it to an Xcode project in `mobile/iosApp`.

## Dev container

The repository now includes a VS Code dev container in `.devcontainer/` for Kotlin Multiplatform and Android work.

- The container installs JDK 17, Gradle 8.10.2, SSH and rsync tooling, and Android command-line tooling.
- Android SDK components are installed by `.devcontainer/post-create.sh` into a persisted volume.
- Xcode does not run inside a Linux container. The supported workflow is to use the container for shared code and Android work, then bridge to a remote macOS machine for Xcode.

### Remote macOS bridge

1. Copy `.devcontainer/remote-mac.env.example` to your shell environment or load the variables manually.
2. Ensure the remote macOS machine has Xcode installed and SSH access enabled.
3. Optionally install XcodeGen on the remote Mac if you want `mobile/iosApp/project.yml` to generate `mobile/iosApp/MedLoquent.xcodeproj` automatically.
4. From inside the dev container, run `mobile/scripts/remote-xcode.sh open` to sync the repo and open the project in Xcode on the remote Mac.
5. Run `mobile/scripts/remote-xcode.sh build` to sync and execute `xcodebuild` remotely.

The remote build script assumes a macOS host because iOS compilation and Xcode are Apple-only toolchains.

## Production hardening

The module boundaries are production-oriented, but several runtime adapters are intentionally conservative scaffolds:

- Replace DemoEnvelopeCodec with Android Keystore and iOS Keychain or Secure Enclave backed AES-GCM.
- Replace SeededAudioCaptureEngine with AudioRecord and AVAudioEngine capture implementations.
- Replace OfflineMedicalAsrEngine internals with ONNX Runtime Mobile or TensorFlow Lite model invocation.
- Replace JsonFileClinicalRecordStore with SQLCipher-backed structured storage if record indexing is required.

## Pre-commit harness gates

This repository retains a lightweight pre-commit harness for quick checks (trailing whitespace, EOF fixes, YAML checks) and the `commit-msg` hook for Conventional Commits. Heavy formatting and linting are now performed by Gradle-integrated tasks (Spotless, Detekt, swiftlint, and Python formatters/checkers) instead of the previous shell scripts.

Quick setup:

1. Install pre-commit (Python):

	```bash
	python -m pip install --user pre-commit
	```

2. Install the hooks in your local repo:

	```bash
	pre-commit install
	pre-commit install --hook-type commit-msg
	```

3. Run all hooks against the repo (CI-like):

	```bash
	pre-commit run --all-files
	```

The repository wires Kotlin and iOS harness checks into the mobile Gradle lifecycle. Use the root dispatcher for whole-project orchestration.

To skip the mobile harness gates for a build, pass `-PskipHarness=true`, for example:

```bash
bash ./build.sh mobile build -PskipHarness=true
```

Note: the repository dispatcher now runs each submodule's `harness-check`
automatically before invoking a submodule `build`. Pass `-PskipHarness=true`
or set `SKIP_HARNESS=1` in the environment to bypass these forced checks.

## Pre-build harness gates

This repository uses a pre-build harness for the mobile stack: the gates run during the mobile Gradle build instead of as pre-commit hooks. The root `build.sh` dispatcher invokes that mobile harness as part of project-level build orchestration.

Run the harness locally:

```bash
# run only project-level harness checks
bash ./build.sh harness-check

# run full project build
bash ./build.sh build

# skip harness gates if necessary
bash ./build.sh mobile build -PskipHarness=true
```

Notes:

- The pre-commit configuration is retained for a small set of lightweight hooks (trailing whitespace, EOF fixer, YAML checks) and the `commit-msg` hook for Conventional Commits; heavy formatting and linting are performed via Gradle now.
- Tooling requirements:
	- Python tools (optional locally): `mypy`, `ruff`, `black`, `flake8`, `flake8-functions`, and `pep8-naming` (install with `python -m pip install --user mypy ruff black flake8 flake8-functions pep8-naming`). These checks stay repo-level and are no longer part of the mobile Gradle harness.
	- Kotlin: Spotless (ktlint) and Detekt are configured via the mobile Gradle plugins and run with `bash ./build.sh mobile spotlessApply` / `bash ./build.sh mobile detekt`.
	- iOS: `swiftlint` on macOS (install via `brew install swiftlint`) — otherwise iOS formatting/linting steps are skipped on non-macOS environments. The policy file lives at `mobile/.swiftlint.yml`.

Gate constraints enforced by the harness:

- Cyclomatic complexity ≤ 7 (per function/method)
- Function/method length ≤ 100 lines
- Class/type length ≤ 800 lines
- Function/method names:
	- Python: use snake_case (lowercase with underscores)
	- Kotlin/Swift: use CamelCaps (UpperCamelCase)
- Line length ≤ 80 characters (enforced through Black/Ruff, ktlint via Spotless, and SwiftLint where available)

How they're implemented:

- Python: `pyproject.toml` configures Black and Ruff for formatting, naming, and complexity, and `.flake8` enforces max function length for repo-level Python checks.
- Kotlin: Spotless (ktlint) and Detekt are applied across subprojects via Gradle plugin configuration (`spotlessApply`, `spotlessCheck`, `detekt`).
- Swift/iOS: `swiftformat` / `swiftlint` are preferred when available on macOS; `mobile/.swiftlint.yml` carries the complexity, size, line-length, and naming policies. On Linux the iOS steps remain a no-op when the Apple toolchain is unavailable.

Deprecated/manual scripts:

Many of the older shell and fallback scripts have been removed in favor of Gradle tasks; see Git history for reference if needed.

