FROM openjdk:17-jdk-slim

# Allow overriding the Synthea source repository and branch at build time.
ARG REPO_URL=https://github.com/synthetichealth/synthea.git
ARG BRANCH=main

WORKDIR /opt

# Basic tooling for Git/Gradle
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl unzip procps ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Clone Synthea at build time into /opt/synthea (shallow clone).
RUN rm -rf /opt/synthea \
    && git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" /opt/synthea || git clone --depth 1 "${REPO_URL}" /opt/synthea

WORKDIR /opt/synthea
RUN chmod +x ./gradlew ./run_synthea || true
# Optionally assemble during image build to cache dependencies; allow failure.
RUN ./gradlew assemble --no-daemon || true

ENTRYPOINT ["./run_synthea"]
