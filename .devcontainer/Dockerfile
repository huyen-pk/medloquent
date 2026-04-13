FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GRADLE_VERSION=8.10.2

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        openjdk-21-jdk \
        openssh-client \
        rsync \
        ruby-full \
        unzip \
        zip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" -o /tmp/gradle.zip \
    && mkdir -p /opt/gradle \
    && unzip -q /tmp/gradle.zip -d /opt/gradle \
    && ln -s "/opt/gradle/gradle-${GRADLE_VERSION}/bin/gradle" /usr/local/bin/gradle \
    && rm /tmp/gradle.zip

ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH=${PATH}:${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools

# Install HL7 FHIR Validator CLI (validator_cli.jar) and a small wrapper
RUN curl -fsSL -o /usr/local/bin/validator_cli.jar "https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar" \
    && chmod 644 /usr/local/bin/validator_cli.jar \
    && printf '%s\n' '#!/usr/bin/env bash' 'java -jar /usr/local/bin/validator_cli.jar "$@"' > /usr/local/bin/fhir-validator \
    && chmod +x /usr/local/bin/fhir-validator

# Install Android command-line tools and basic SDK packages so the container
# can provide the Android SDK out-of-the-box. Note: the devcontainer
# `post-create.sh` will also populate a mounted SDK volume at runtime if
# necessary.
ARG ANDROID_CMDLINE_TOOLS_REVISION=13114758
RUN mkdir -p /opt/android-sdk/cmdline-tools \
        && curl -fsSL "https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_CMDLINE_TOOLS_REVISION}_latest.zip" -o /tmp/cmdline-tools.zip \
        && unzip -q /tmp/cmdline-tools.zip -d /opt/android-sdk/cmdline-tools \
        && rm -f /tmp/cmdline-tools.zip \
        && mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest || true \
        && chmod -R a+rX /opt/android-sdk || true

# Install common Android packages and accept licenses. This installs into
# the image layer; if a runtime-mounted SDK volume is used, the devcontainer
# `post-create.sh` will run inside the container and ensure the mounted
# volume is populated as needed.
RUN if [ -x /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager ]; then \
            yes | /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk --licenses || true; \
            /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk "platform-tools" "platforms;android-35" "build-tools;34.0.0"; \
        else \
            echo "sdkmanager not available; post-create.sh will populate SDK at container start"; \
        fi