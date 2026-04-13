# Synthea + Synthetic Pipeline Compose

This Compose file provides an end-to-end local orchestration that:

- Runs the vendored Synthea launcher (testData/synthea) to emit FHIR bundles.
- Runs the Python synthetic pipeline (`synthetic/cli.py`) to extract text, synthesize audio using Kokoro on ONNX Runtime, run ASR (Vosk/Whisper), and evaluate.
- Runs a small validator to check FHIR files, the pipeline manifest, and eval metrics.

Quickstart (from repository root):

```bash
# Build images and run the full workflow (Synthea is cloned at image build time)
docker compose -f synthetic/compose.yaml up --build

# Or run just the Synthea generator:
docker compose -f synthetic/compose.yaml up --build synthea

# Or run pipeline after synthea has produced data:
docker compose -f synthetic/compose.yaml up --build pipeline

# Bring everything down and remove volumes when done:
docker compose -f synthetic/compose.yaml down -v
```

Notes:
- The pipeline image installs the full `requirements-full.txt` (Kokoro ONNX Runtime, Misaki phonemization, Vosk, and related libs). There is no deterministic TTS/ASR fallback anymore.
- The first pipeline run downloads the selected Kokoro model artifact and voice into the `hf_cache` named volume unless they are already cached.
- The `synthea` image builds the vendored `testData/synthea` project during image build; the first build may download Gradle dependencies and take several minutes.
- Outputs are persisted in Docker named volumes `synthea_output` and `synthetic_output`; the Hugging Face cache is persisted in `hf_cache`.
