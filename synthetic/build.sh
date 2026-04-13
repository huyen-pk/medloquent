#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd)"

usage() {
  cat <<'EOF'
Usage:
  bash synthetic/build.sh build
  bash synthetic/build.sh harness-check

This script is invoked by the repository dispatcher as an
optional submodule hook. It provides a lightweight `build` no-op
and a `harness-check` that validates Python syntax and optionally
runs `ruff`, `mypy`, and `pytest` when available on PATH.
EOF
}

command_name="${1:-}"
case "$command_name" in
  build)
    echo "synthetic: no build steps defined; skipping"
    ;;
  harness-check|harnessCheck)
    echo "synthetic: running harness checks"

    # Ensure we operate from the synthetic module root
    cd "$ROOT_DIR"

    # Choose a Python executable
    if command -v python3 >/dev/null 2>&1; then
      PYTHON="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
      PYTHON="$(command -v python)"
    else
      echo "synthetic: python not found; skipping harness checks" >&2
      exit 0
    fi

    echo "synthetic: using Python at $PYTHON"

    # Syntax check using the stdlib compileall
    echo "synthetic: running syntax check (compileall)"
    if ! "$PYTHON" -m compileall -q .; then
      echo "synthetic: syntax check failed" >&2
      exit 1
    fi

    # Run ruff if available
    if command -v ruff >/dev/null 2>&1; then
      echo "synthetic: running ruff"
      if ! ruff check .; then
        echo "synthetic: ruff reported issues" >&2
        exit 1
      fi
    fi

    # Run mypy if available
    if command -v mypy >/dev/null 2>&1; then
      echo "synthetic: running mypy"
      if ! mypy .; then
        echo "synthetic: mypy reported issues" >&2
        exit 1
      fi
    fi

    # Run pytest if available
    if command -v pytest >/dev/null 2>&1; then
      echo "synthetic: running pytest"
      if ! pytest -q; then
        echo "synthetic: pytest failed" >&2
        exit 1
      fi
    fi

    echo "synthetic: harness checks passed"
    ;;
  *)
    usage
    exit 1
    ;;
esac
