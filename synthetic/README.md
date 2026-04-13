Synthetic data generator
========================

Small, local pipeline for converting Synthea/FHIR text → synthetic audio → augmentations → ASR predictions → metrics.

Quick start
-----------

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-full.txt
```

2. Run an end-to-end smoke sequence (creates files under `testData/synthetic`):

```bash
# Unified CLI (preferred):
python synthetic/cli.py extract --outdir testData/synthetic --batch-size 3
python synthetic/cli.py tts --manifest testData/synthetic/manifest.csv --voice af_heart
python synthetic/cli.py augment --in-dir testData/synthetic/audio --out-dir testData/synthetic/audio_aug
python synthetic/cli.py asr --in-dir testData/synthetic/audio_aug --out-dir testData/synthetic/predictions
python synthetic/cli.py eval --manifest testData/synthetic/manifest.csv --preds-dir testData/synthetic/predictions --out-file testData/synthetic/metrics.json

# Or call components directly via the package (also supported):
python -c "from synthetic.pipeline.extractor import run_extract; run_extract(None, 'testData/synthetic', batch_size=3)"
python -c "from synthetic.pipeline.tts import run_tts; run_tts('testData/synthetic/manifest.csv', 'testData/synthetic/audio', voice='af_heart')"
python -c "from synthetic.pipeline.augmenter import run_augment; run_augment('testData/synthetic/audio', 'testData/synthetic/audio_aug', [20,10,0], [1.0])"
python -c "from synthetic.pipeline.asr_runner import run_asr; run_asr('testData/synthetic/audio_aug', 'testData/synthetic/predictions')"
python -c "from synthetic.pipeline.evaluator import run_eval; run_eval('testData/synthetic/manifest.csv', 'testData/synthetic/predictions', out_file='testData/synthetic/metrics.json')"
```

Notes
-----
- All synthetic artifacts live under `testData/synthetic` by default.
- Batch commands loop over per-sample folders under `testData/synthetic/<id>`.
- Use `--batch-size` with `extract` or `run-all` to create multiple demo samples.
- Each sample folder contains step-local outputs such as `manifest.csv`, `audio/`, `audio_aug/`, `predictions/`, and `eval_metrics.json` for easier inspection.
- The TTS stage defaults to Kokoro on ONNX Runtime and will download the selected model artifact and voice into the Hugging Face cache on first use unless `--no-download` is set.
- Extracted FHIR XHTML is normalized to speech-friendly plain text before phonemization, so the TTS stage can handle raw narrative bundles without changing the extractor schema.
- The pipeline fails fast if Kokoro or ASR dependencies are missing; there is no fake-audio fallback.
