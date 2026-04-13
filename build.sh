#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd)"
MOBILE_DIR="$ROOT_DIR/mobile"
MOBILE_GRADLE="$MOBILE_DIR/gradlew"

usage() {
  cat <<'EOF'
Usage:
  bash ./build.sh build [gradle args...]
  bash ./build.sh harness-check [gradle args...]
  bash ./build.sh mobile <gradle args...>

Commands:
  build          Run the mobile Gradle build, then any optional submodule build scripts.
  harness-check  Run Kotlin/iOS mobile harness checks, then any optional submodule harness scripts.
  mobile         Pass arguments directly to mobile/gradlew.

Optional submodule scripts:
  If a submodule exposes an executable build.sh, it will be called with the
  same high-level command after the mobile build completes.
EOF
}

run_mobile_gradle() {
  (
    cd "$MOBILE_DIR"
    bash "$MOBILE_GRADLE" "$@"
  )
}

run_optional_submodule_scripts() {
  local command="$1"
  shift || true

  # Detect whether caller requested skipping harness via Gradle property
  local skip_harness=false
  for _arg in "$@"; do
    case "${_arg}" in
      -PskipHarness*|*skipHarness=*)
        skip_harness=true
        break
        ;;
    esac
  done
  if [[ -n "${SKIP_HARNESS:-}" ]]; then
    skip_harness=true
  fi

  local scripts=(
    "$ROOT_DIR/synthetic/build.sh"
  )

  local script
  for script in "${scripts[@]}"; do
    if [[ -x "$script" ]]; then
      # When running a top-level build, run each submodule's harness-check first
      # unless a skip was explicitly requested.
      if [[ "$command" == "build" && "$skip_harness" == false ]]; then
        "$script" harness-check "$@"
      fi

      "$script" "$command" "$@"
    fi
  done
}

if [[ ! -f "$MOBILE_GRADLE" ]]; then
  echo "Expected mobile Gradle wrapper at $MOBILE_GRADLE" >&2
  exit 1
fi

command_name="${1:-}"
if [[ -z "$command_name" ]]; then
  usage
  exit 1
fi
shift

case "$command_name" in
  build)
    run_mobile_gradle build "$@"
    run_optional_submodule_scripts build "$@"
    ;;
  harness-check|harnessCheck)
    run_mobile_gradle harnessCheck "$@"
    run_optional_submodule_scripts harness-check "$@"
    ;;
  mobile)
    if [[ $# -eq 0 ]]; then
      usage
      exit 1
    fi
    run_mobile_gradle "$@"
    ;;
  *)
    usage
    exit 1
    ;;
esac