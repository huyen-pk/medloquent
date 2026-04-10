# iOS host shell

The Kotlin Multiplatform shared UI exposes MainViewController in shared/app/src/iosMain/kotlin/com/medloquent/shared/app/MainViewController.kt.

To finish the iOS packaging step in Xcode:

1. Build the shared framework with `./gradlew :shared:app:assembleXCFramework`.
2. Create or open an Xcode iOS App target in this directory.
3. Add the generated MedLoquentShared framework to the project.
4. Use MedLoquentApp.swift and MedLoquentRootView.swift as the SwiftUI host.
5. Ensure Info.plist is attached to the target and the microphone permission string is preserved.

The repository also includes `iosApp/project.yml` for XcodeGen. On a macOS machine with XcodeGen installed, run `xcodegen generate --spec iosApp/project.yml` to create `iosApp/MedLoquent.xcodeproj`.

If you are working from the Linux dev container, use `scripts/remote-xcode.sh open` or `scripts/remote-xcode.sh build` to sync to a remote macOS machine and drive Xcode there.
