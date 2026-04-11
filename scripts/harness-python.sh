#!/usr/bin/env bash
set -euo pipefail

# If the project virtualenv exists, prefer its tools (mypy/ruff/black)
# by prepending the venv `bin` directory to PATH so Gradle Exec sees them.
if [ -d "./hf_env/bin" ]; then
  export PATH="$PWD/hf_env/bin:$PATH"
fi

# Harness helper: run ruff and black (if installed) on python files.
# If no files are passed, prefer tracked files via git; fall back to a repo-wide find,
# excluding common generated and virtualenv directories so synthetic scripts are included.
if [ "$#" -eq 0 ]; then
  files=()
  if git rev-parse --git-dir >/dev/null 2>&1; then
    mapfile -t files < <(git ls-files "*.py" 2>/dev/null || true)
  fi
  if [ ${#files[@]} -eq 0 ]; then
    mapfile -t files < <(find . -type f -name "*.py" \
      -not -path "./.gradle/*" \
      -not -path "./build/*" \
      -not -path "./hf_env/*" \
      -not -path "./.agents/*" \
      -not -path "./.venv/*" \
      -not -path "./androidApp/build/*" \
      -not -path "*/generated/*" 2>/dev/null || true)
  fi
else
  files=("$@")
fi

py_files=()
for f in "${files[@]}"; do
  case "$f" in
    *.py)
      # skip internal examples/agent skill code that shouldn't block builds
      case "$f" in
        .agents/*) ;;
        *) py_files+=("$f") ;;
      esac ;;
  esac
done

if [ ${#py_files[@]} -eq 0 ]; then
  echo "No python files found for harness checks" >&2
  exit 0
fi

if command -v ruff >/dev/null 2>&1; then
  ruff check "${py_files[@]}" || { echo "ruff found issues" >&2; exit 1; }
else
  echo "ruff not installed; skipping ruff checks" >&2
fi

if command -v black >/dev/null 2>&1; then
  black --check "${py_files[@]}" || { echo "black would reformat files; run 'black ${py_files[*]}'" >&2; exit 1; }
else
  echo "black not installed; skipping black formatting check" >&2
fi


# Enforce strong typing with mypy (required) but skip untyped scripts and synthetic helpers
if command -v mypy >/dev/null 2>&1; then
  echo "Running mypy strict type checks (excluding scripts/, synthetic/, and .agents/)..."
  mypy_targets=()
  for f in "${py_files[@]}"; do
    case "$f" in
      ./.agents/*|.agents/*) continue ;;
      *) mypy_targets+=("$f") ;;
    esac
  done
  if [ ${#mypy_targets[@]} -eq 0 ]; then
    echo "No files to type-check with mypy; skipping mypy." >&2
  else
    mypy --config-file mypy.ini --show-error-codes "${mypy_targets[@]}" || { echo "mypy type checks failed" >&2; exit 1; }
  fi
else
  echo "ERROR: mypy not installed. Install with: python -m pip install --user mypy" >&2
  exit 1
fi

# Run extended harness checks (complexity, lengths, naming)
if command -v python3 >/dev/null 2>&1; then
  check_targets=()
  for f in "${py_files[@]}"; do
    case "$f" in
      ./.agents/*|.agents/*) continue ;;
      *) check_targets+=("$f") ;;
    esac
  done
  if [ ${#check_targets[@]} -eq 0 ]; then
    echo "No Python sources selected for extended harness checks; skipping." >&2
  else
    python3 scripts/harness-python-checks.py "${check_targets[@]}" || exit 1
  fi
elif command -v python >/dev/null 2>&1; then
  check_targets=()
  for f in "${py_files[@]}"; do
    case "$f" in
      ./scripts/*|scripts/*|./synthetic/*|synthetic/*|./.agents/*|.agents/*) continue ;;
      *) check_targets+=("$f") ;;
    esac
  done
  if [ ${#check_targets[@]} -eq 0 ]; then
    echo "No Python sources selected for extended harness checks; skipping." >&2
  else
    python scripts/harness-python-checks.py "${check_targets[@]}" || exit 1
  fi
else
  echo "python not found; skipping python harness checks" >&2
fi

exit 0
