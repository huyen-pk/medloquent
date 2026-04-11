#!/usr/bin/env bash
set -euo pipefail

# Commit-msg hook: enforce a simple Conventional Commits pattern
msgfile="$1"
msg=$(sed -n '1p' "$msgfile" || true)

if ! echo "$msg" | grep -Eq '^(feat|fix|docs|style|refactor|perf|test|chore|ci)(\([^)]+\))?: .+'; then
  echo "ERROR: Commit message does not follow Conventional Commits." >&2
  echo "Format: <type>(optional-scope): <short description>" >&2
  echo "Example: feat(ui): add dark-mode toggle" >&2
  exit 1
fi

exit 0
