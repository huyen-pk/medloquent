#!/usr/bin/env bash
set -euo pipefail

# Download and run detekt CLI with project detekt.yml configuration.
DETEKT_VERSION="1.23.1"
JAR_DIR=".gradle/detekt"
JAR_PATH="$JAR_DIR/detekt-cli-$DETEKT_VERSION-all.jar"

if [ ! -f "$JAR_PATH" ]; then
  mkdir -p "$JAR_DIR"
  if command -v curl >/dev/null 2>&1; then
    echo "Downloading detekt-cli $DETEKT_VERSION..."
    curl -fsSL -o "$JAR_PATH" "https://repo1.maven.org/maven2/io/gitlab/arturbosch/detekt-cli/$DETEKT_VERSION/detekt-cli-$DETEKT_VERSION-all.jar" || { echo "failed to download detekt-cli" >&2; rm -f "$JAR_PATH"; exit 2; }
  elif command -v wget >/dev/null 2>&1; then
    echo "Downloading detekt-cli $DETEKT_VERSION..."
    wget -q -O "$JAR_PATH" "https://repo1.maven.org/maven2/io/gitlab/arturbosch/detekt-cli/$DETEKT_VERSION/detekt-cli-$DETEKT_VERSION-all.jar" || { echo "failed to download detekt-cli" >&2; rm -f "$JAR_PATH"; exit 2; }
  else
    echo "curl or wget is required to download detekt-cli" >&2
    exit 2
  fi
fi

if ! command -v java >/dev/null 2>&1; then
  echo "java not found; cannot run detekt-cli" >&2
  exit 2
fi

echo "Running detekt checks..."
java -jar "$JAR_PATH" --input androidApp,shared --config detekt.yml || exit $?

echo "detekt checks passed"
exit 0
