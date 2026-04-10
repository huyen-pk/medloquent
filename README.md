# MedLoquent

MedLoquent is a Kotlin Multiplatform mobile application scaffold for fully offline medical dictation, clinical NLP structuring, FHIR bundle generation, encrypted local persistence, federated learning, and LoRa-ready synchronization.

## Architecture

The implementation follows the reference architecture in architecture.md:

- Edge-first inference pipeline: seeded audio capture -> offline ASR normalization -> clinical NLP -> FHIR bundle generation
- FHIR-first storage: bundle generation and local JSON persistence behind a storage abstraction
- Privacy-first learning: top-layer feature deltas only, queued locally for intermittent low-bandwidth sync
- Kotlin Multiplatform shared runtime with Android and iOS entry points

## Project structure

- androidApp: Android launcher application
- iosApp: SwiftUI host shell for the generated iOS framework
- shared/core: shared clinical and federated learning models
- shared/audio: audio capture contract and seeded offline capture implementation
- shared/asr: offline ASR orchestration and medical abbreviation normalization
- shared/nlp: rule-based clinical entity extraction and note structuring
- shared/ehr: FHIR R4 bundle mapper and JSON formatter
- shared/crypto: envelope codec abstraction with a demo codec for local development
- shared/storage: encrypted bundle persistence abstraction
- shared/fl: on-device layer-wise federated update preparation
- shared/lora: LoRa packet queue abstraction
- shared/app: Compose Multiplatform UI and workflow coordinator

## Build notes

This workspace does not include a Gradle wrapper. The Android build was validated locally on Linux with Gradle 8.10.2, Android SDK Platform 35, and JDK 21. To build locally:

1. Install Gradle 8.10 or newer and JDK 21.
2. Run `gradle wrapper` from the repository root if you want to commit the wrapper.
3. Set `sdk.dir` in `local.properties` or export `ANDROID_HOME` and `ANDROID_SDK_ROOT` to a working Android SDK installation.
4. Build Android with `./gradlew :androidApp:assembleDebug` once the wrapper exists.
5. Generate the shared iOS framework with `./gradlew :shared:app:assembleXCFramework` and attach it to an Xcode project in iosApp.

## Dev container

The repository now includes a VS Code dev container in `.devcontainer/` for Kotlin Multiplatform and Android work.

- The container installs JDK 17, Gradle 8.10.2, SSH and rsync tooling, and Android command-line tooling.
- Android SDK components are installed by `.devcontainer/post-create.sh` into a persisted volume.
- Xcode does not run inside a Linux container. The supported workflow is to use the container for shared code and Android work, then bridge to a remote macOS machine for Xcode.

### Remote macOS bridge

1. Copy `.devcontainer/remote-mac.env.example` to your shell environment or load the variables manually.
2. Ensure the remote macOS machine has Xcode installed and SSH access enabled.
3. Optionally install XcodeGen on the remote Mac if you want `iosApp/project.yml` to generate `iosApp/MedLoquent.xcodeproj` automatically.
4. From inside the dev container, run `scripts/remote-xcode.sh open` to sync the repo and open the project in Xcode on the remote Mac.
5. Run `scripts/remote-xcode.sh build` to sync and execute `xcodebuild` remotely.

The remote build script assumes a macOS host because iOS compilation and Xcode are Apple-only toolchains.

## Production hardening

The module boundaries are production-oriented, but several runtime adapters are intentionally conservative scaffolds:

- Replace DemoEnvelopeCodec with Android Keystore and iOS Keychain or Secure Enclave backed AES-GCM.
- Replace SeededAudioCaptureEngine with AudioRecord and AVAudioEngine capture implementations.
- Replace OfflineMedicalAsrEngine internals with ONNX Runtime Mobile or TensorFlow Lite model invocation.
- Replace JsonFileClinicalRecordStore with SQLCipher-backed structured storage if record indexing is required.
- Replace InMemoryLoraSyncTransport with a real LoRaWAN transport and packet retry policy.
