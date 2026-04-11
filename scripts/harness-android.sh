#!/usr/bin/env bash
set -euo pipefail

# Run lightweight Android/Kotlin checks if Android-related files are staged.
changed=$(git diff --cached --name-only --relative || true)
if ! echo "$changed" | grep -qE '^(androidApp|shared|core|nlp|asr|audio|storage)/'; then
  exit 0
fi

if [ ! -f "./gradlew" ] && [ ! -x "./gradlew" ]; then
  echo "gradlew not found; skipping Android checks" >&2
  # still attempt detekt fallback
else
  # Try running detekt wrapper first (downloads detekt-cli if needed). If detekt fails or is unavailable,
  # fall back to a heuristic Kotlin checker.
  if bash scripts/harness-detekt.sh; then
    echo "detekt OK"
  else
    echo "detekt not available or reported issues; running Kotlin heuristic fallback"
    if command -v python3 >/dev/null 2>&1; then
      python3 scripts/harness-kotlin-check.py || { echo "kotlin checks failed" >&2; exit 1; }
    elif command -v python >/dev/null 2>&1; then
      python scripts/harness-kotlin-check.py || { echo "kotlin checks failed" >&2; exit 1; }
    else
      echo "Python not found; cannot run kotlin heuristic checks" >&2
    fi
  fi

  # Prefer ktlint tasks if present, fall back to Android lint if available
  if ./gradlew help --task ktlintFormat >/dev/null 2>&1; then
    ./gradlew ktlintFormat || { echo "ktlintFormat failed" >&2; exit 1; }
  elif ./gradlew help --task ktlintCheck >/dev/null 2>&1; then
    ./gradlew ktlintCheck || { echo "ktlintCheck failed" >&2; exit 1; }
  elif ./gradlew help --task :androidApp:lintDebug >/dev/null 2>&1; then
    ./gradlew :androidApp:lintDebug || { echo "Android lint failed" >&2; exit 1; }
  elif ./gradlew help --task lint >/dev/null 2>&1; then
    ./gradlew lint || { echo "Project lint failed" >&2; exit 1; }
  else
    echo "No Android/Kotlin lint tasks found; consider adding ktlint or detekt. Skipping Gradle lint checks." >&2
  fi
fi

exit 0
