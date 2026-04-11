FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GRADLE_VERSION=8.10.2

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        openjdk-17-jdk \
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
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=${PATH}:${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools

# Install HL7 FHIR Validator CLI (validator_cli.jar) and a small wrapper
RUN curl -fsSL -o /usr/local/bin/validator_cli.jar "https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar" \
    && chmod 644 /usr/local/bin/validator_cli.jar \
    && printf '%s\n' '#!/usr/bin/env bash' 'java -jar /usr/local/bin/validator_cli.jar "$@"' > /usr/local/bin/fhir-validator \
    && chmod +x /usr/local/bin/fhir-validator