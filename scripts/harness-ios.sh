#!/usr/bin/env bash
set -euo pipefail

# Run SwiftLint on staged iOS files if swiftlint is available
changed=$(git diff --cached --name-only --relative || true)
if ! echo "$changed" | grep -qE '^iosApp/'; then
  exit 0
fi


if command -v swiftlint >/dev/null 2>&1; then
  # Use strict mode to treat warnings as errors so thresholds fail the build
  swiftlint lint --path iosApp --config .swiftlint.yml --strict || { echo "SwiftLint failed" >&2; exit 1; }
else
  echo "swiftlint not found; running heuristic swift checks" >&2
  if command -v python3 >/dev/null 2>&1; then
    python3 scripts/harness-swift-check.py || { echo "swift heuristic checks failed" >&2; exit 1; }
  elif command -v python >/dev/null 2>&1; then
    python scripts/harness-swift-check.py || { echo "swift heuristic checks failed" >&2; exit 1; }
  else
    echo "python not found; skipping swift harness checks" >&2
  fi
fi

exit 0
