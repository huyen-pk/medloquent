#!/usr/bin/env bash
set -euo pipefail

ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/android-sdk}"
ANDROID_API_LEVEL="${ANDROID_API_LEVEL:-35}"
ANDROID_BUILD_TOOLS="${ANDROID_BUILD_TOOLS:-35.0.0}"
ANDROID_CMDLINE_TOOLS_REVISION="${ANDROID_CMDLINE_TOOLS_REVISION:-13114758}"
ANDROID_CMDLINE_TOOLS_ZIP="commandlinetools-linux-${ANDROID_CMDLINE_TOOLS_REVISION}_latest.zip"
SDKMANAGER="${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager"

mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools"

if [[ ! -x "${SDKMANAGER}" ]]; then
    temp_zip="/tmp/${ANDROID_CMDLINE_TOOLS_ZIP}"
    curl -fsSL "https://dl.google.com/android/repository/${ANDROID_CMDLINE_TOOLS_ZIP}" -o "${temp_zip}"
    rm -rf "${ANDROID_SDK_ROOT}/cmdline-tools/latest" "${ANDROID_SDK_ROOT}/cmdline-tools/cmdline-tools"
    unzip -q "${temp_zip}" -d "${ANDROID_SDK_ROOT}/cmdline-tools"
    mv "${ANDROID_SDK_ROOT}/cmdline-tools/cmdline-tools" "${ANDROID_SDK_ROOT}/cmdline-tools/latest"
    rm -f "${temp_zip}"
fi

yes | "${SDKMANAGER}" --sdk_root="${ANDROID_SDK_ROOT}" --licenses >/dev/null || true

"${SDKMANAGER}" --sdk_root="${ANDROID_SDK_ROOT}" \
    "platform-tools" \
    "platforms;android-${ANDROID_API_LEVEL}" \
    "build-tools;${ANDROID_BUILD_TOOLS}"

echo "Android SDK is ready at ${ANDROID_SDK_ROOT}."