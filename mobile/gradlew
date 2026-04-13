#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd)"
WRAPPER_PROPS="$ROOT_DIR/gradle/wrapper/gradle-wrapper.properties"
DEFAULT_DIST="https://services.gradle.org/distributions/gradle-8.10.2-bin.zip"

if [ -f "$WRAPPER_PROPS" ]; then
  distributionUrl=$(awk -F= '/^distributionUrl=/{print substr($0, index($0,$2))}' "$WRAPPER_PROPS" | tr -d '\r\n' || true)
else
  distributionUrl="$DEFAULT_DIST"
fi

distributionUrl="${distributionUrl//\\:/\:}"
distributionUrl="${distributionUrl# }"

if [ -z "$distributionUrl" ]; then
  distributionUrl="$DEFAULT_DIST"
fi

DIST_FILENAME=$(basename "$distributionUrl")
DIST_NAME="${DIST_FILENAME%.zip}"
CACHE_DIR="$ROOT_DIR/.gradle-wrapper-dists/$DIST_NAME"
GRADLE_BIN="$CACHE_DIR/bin/gradle"

if [ ! -x "$GRADLE_BIN" ]; then
  mkdir -p "$ROOT_DIR/.gradle-wrapper-dists"
  tmpdir=$(mktemp -d)
  echo "Downloading Gradle from $distributionUrl"
  curl -fsSL "$distributionUrl" -o "$tmpdir/$DIST_FILENAME"
  unzip -q "$tmpdir/$DIST_FILENAME" -d "$tmpdir"
  extracted_dir=$(find "$tmpdir" -maxdepth 1 -type d -name 'gradle-*' -print -quit)
  if [ -z "$extracted_dir" ]; then
    echo "Failed to find extracted gradle directory" >&2
    rm -rf "$tmpdir"
    exit 1
  fi
  mkdir -p "$(dirname "$CACHE_DIR")"
  mv "$extracted_dir" "$CACHE_DIR"
  rm -rf "$tmpdir"
fi

exec "$GRADLE_BIN" "$@"
