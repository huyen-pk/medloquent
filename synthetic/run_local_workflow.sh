#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") [-p N] [--venv PATH] [--skip-deps]

Runs Synthea locally and then the synthetic pipeline (no Docker).

Options:
  -p, --patients N    Number of Synthea patients to generate (default: 1)
  --venv PATH         Path to Python virtualenv to use/create (default: .venv in repo root)
  --skip-deps         Skip installing Python dependencies (useful if already installed)
  -h, --help          Show this help message
EOF
}

PATIENTS=1
VENV_PATH=""
SKIP_DEPS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--patients)
      PATIENTS="$2"
      shift 2
      ;;
    --venv)
      VENV_PATH="$2"
      shift 2
      ;;
    --skip-deps)
      SKIP_DEPS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use provided venv path, otherwise prefer Python 3.11 and create a .venv3.11
if [[ -n "$VENV_PATH" ]]; then
  # User explicitly provided a venv path
  if [[ ! -d "$VENV_PATH" ]]; then
    echo "Creating Python venv at $VENV_PATH"
    python3 -m venv "$VENV_PATH"
  fi
  PYTHON="$VENV_PATH/bin/python"
  echo "Using virtualenv python: $PYTHON"
else
  # Prefer conda/mamba. We'll create a local conda prefix env at $REPO_ROOT/.conda-env
  CONDA_BIN=""
  if command -v mamba >/dev/null 2>&1; then
    CONDA_BIN="$(command -v mamba)"
  elif command -v conda >/dev/null 2>&1; then
    CONDA_BIN="$(command -v conda)"
  elif [[ -x "$REPO_ROOT/miniconda/bin/conda" ]]; then
    CONDA_BIN="$REPO_ROOT/miniconda/bin/conda"
  fi

  if [[ -z "$CONDA_BIN" ]]; then
    echo "No conda/mamba found. Installing Miniforge locally into $REPO_ROOT/miniconda..."
    TMP_INSTALL="/tmp/miniforge_installer.sh"
    curl -sSL -o "$TMP_INSTALL" "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
    bash "$TMP_INSTALL" -b -p "$REPO_ROOT/miniconda"
    rm -f "$TMP_INSTALL"
    CONDA_BIN="$REPO_ROOT/miniconda/bin/conda"
  fi

  CONDA_PREFIX="$REPO_ROOT/.conda-env"
  if [[ ! -d "$CONDA_PREFIX" ]]; then
    echo "Creating conda prefix env at $CONDA_PREFIX (python=3.11)..."
    "$CONDA_BIN" create --yes --prefix "$CONDA_PREFIX" -c conda-forge python=3.11 pip
  else
    echo "Using existing conda prefix env at $CONDA_PREFIX"
  fi

  PYTHON="$CONDA_PREFIX/bin/python"
  echo "Using conda python: $PYTHON"
fi

if [[ $SKIP_DEPS -eq 0 ]]; then
  echo "Installing Python dependencies (this may take a long time)..."
  "$PYTHON" -m pip install --upgrade pip setuptools wheel
  "$PYTHON" -m pip install --no-cache-dir -r "$REPO_ROOT/synthetic/requirements-full.txt"
else
  echo "Skipping dependency installation (--skip-deps)"
fi

# Verify Synthea launcher
SYNTH_DIR="$REPO_ROOT/testData/synthea"
if [[ ! -d "$SYNTH_DIR" ]]; then
  echo "Error: Synthea directory not found at $SYNTH_DIR" >&2
  echo "Either clone Synthea into testData/synthea or build the synthea image via Docker Compose." >&2
  exit 2
fi

if [[ ! -x "$SYNTH_DIR/run_synthea" ]]; then
  chmod +x "$SYNTH_DIR/run_synthea" || true
fi

# If FHIR output already exists, skip running Synthea to save time.
FHIR_DIR="$SYNTH_DIR/output/fhir"
echo "Running Synthea (patients=$PATIENTS) to produce FHIR bundles..."
pushd "$SYNTH_DIR" >/dev/null
./run_synthea -p "$PATIENTS" --exporter.fhir.export=true
popd >/dev/null

if [[ ! -d "$FHIR_DIR" || -z "$(ls -A "$FHIR_DIR" 2>/dev/null)" ]]; then
  echo "Synthea did not produce FHIR output at $FHIR_DIR" >&2
  exit 3
fi

SYNTH_OUT="$REPO_ROOT/testData/synthetic"
mkdir -p "$SYNTH_OUT"

echo "Running extraction..."
(cd "$REPO_ROOT" && "$PYTHON" -m synthetic.cli extract --input "$FHIR_DIR" --outdir "$SYNTH_OUT")

MANIFEST="$SYNTH_OUT/manifest.csv"
if [[ ! -f "$MANIFEST" ]]; then
  echo "Manifest not found at $MANIFEST" >&2
  exit 4
fi

echo "Running TTS (Coqui TTS)..."
(cd "$REPO_ROOT" && "$PYTHON" -m synthetic.cli tts --manifest "$MANIFEST" --out-dir "$SYNTH_OUT/audio")

echo "Running augment..."
(cd "$REPO_ROOT" && "$PYTHON" -m synthetic.cli augment --in-dir "$SYNTH_OUT/audio" --out-dir "$SYNTH_OUT/audio_aug")

echo "Running ASR..."
(cd "$REPO_ROOT" && "$PYTHON" -m synthetic.cli asr --in-dir "$SYNTH_OUT/audio_aug" --out-dir "$SYNTH_OUT/predictions" --manifest "$MANIFEST")

echo "Running Eval..."
(cd "$REPO_ROOT" && "$PYTHON" -m synthetic.cli eval --manifest "$MANIFEST" --preds-dir "$SYNTH_OUT/predictions" --out-file "$SYNTH_OUT/eval_metrics.json")

echo "Validating outputs..."
(cd "$REPO_ROOT" && "$PYTHON" synthetic/validate_outputs.py "$FHIR_DIR" "$SYNTH_OUT")

echo "Workflow completed successfully. Outputs under $SYNTH_OUT"
exit 0
