# Evaluation plan — clinical dictation → EHR

Purpose
-------
This document defines a concise, actionable test & evaluation plan for the end‑to‑end pipeline: audio capture → on‑device ASR → clinical NLP → FHIR generation → encrypted persistence + federated learning + LoRa sync. Use this for engineering, data science experiments, and CI gating.

Goals & success metrics
----------------------
- ASR accuracy: WER < 15% on clinical testset; medical‑term recall ≥ 90% (tunable).  
- NLP: NER/entity linking micro/macro F1 ≥ 0.85; section classification accuracy ≥ 90%.  
- FHIR: 99% schema‑valid bundles (validator `error` = 0) and completeness ≥ 95% for required clinical fields.  
- FL & comms: per‑sync payload ≤ target (example 5 KB) and sync success rate ≥ 95%; rounds‑to‑converge within budgeted rounds.  
- Privacy: membership‑inference AUC close to random or meet an agreed epsilon for DP.  
- Resource: inference latency per chunk ≤ 300 ms; memory and battery within device constraints (target device profiles defined separately).

Datasets & data strategy
------------------------
- Synthetic & FHIR: `Synthea` (use `testData/synthea`); use generated FHIR bundles for mapping and schema tests.  
- NER / gold labels: request access to `i2b2`/`n2c2` where needed; otherwise curate clinician‑annotated holdouts.  
- EHR distributional tests: `MIMIC` / `eICU` (DUA required) for mapping edge cases and real note structure.  
- Acoustic robustness: mix `Common Voice`, `VCTK`, `LibriSpeech` and TTS‑generated clinical audio (use `LJSpeech` / `LibriTTS`) to synthesize clinical dictation.  
- Storage: validate using `FHIR R4` official examples and `Synthea` bundles.

Test types (what to run)
-----------------------
1. Unit/component tests (fast, CI):
   - Tokenizer, model IO, deterministic NER outputs for fixed inputs.  
   - FHIR mapper functions: mapping rules produce expected resource fields from canned transcripts.

2. Model evaluation (offline):
   - ASR: compute WER, CER, medical‑term recall, per‑speaker and per‑noise SNR buckets.  
   - NLP: compute precision/recall/F1 for NER; entity linking accuracy against gold IDs (SNOMED/ICD).  
   - Model regression tests for quantized artifacts (accuracy tolerance thresholds).

3. Integration / E2E tests:
   - Audio file → ASR → NLP → FHIR bundle generation → `fhir-validator` check; compare to ground truth bundles for structural and content correctness.  
   - Fail CI on any `OperationOutcome` with severity `error`.

4. Federated Learning (simulation):
   - Use a simulator (Flower or custom) to run heterogenous-client experiments with configurable client counts, participation rates, and data skew.
   - Record communication bytes per round, rounds‑to‑converge, and final model quality on holdout.  
   - Ablation: Top‑K sparsity levels, quantization bits (INT8/INT4), layer‑wise update policy.

5. Privacy & adversarial tests:
   - Membership inference: train attack models on released model snapshots/deltas. Measure AUC and attack advantage.  
   - Gradient/embedding inversion: attempt reconstruction from compressed/quantized deltas. Report reconstruction MSE or overlap with ground truth.  
   - DP sweeps: vary noise levels (epsilon) and measure utility vs privacy.

6. LoRa / comms tests:
   - Simulate LoRa link budgets (payload size, fragmentation, loss, latency).  
   - Validate retry/backoff policies, queueing, and prioritized update types (top layers vs base layers).  
   - Measure end‑to‑end time from local training → gateway aggregation → device apply.

7. Performance & resource benchmarking:
   - Latency: cold/warm model load and per‑chunk inference (ms).  
   - Memory: heap and native usage during inference and local training.  
   - Energy: energy per inference (where measurable).  
   - Profile with representative device images and emulator/device farm.

8. Security & compliance checks:
   - Keystore integration: test key generation, encryption/decryption, rotation, and secure deletion.  
   - Consent & deletion flows: verify user opt‑in/out and local data deletion (complete) paths.  
   - Transport & storage encryption: validate AES‑GCM envelope, key lifecycle, and retrieval.

Experiment design & statistics
----------------------------
- A/B tests: compare model variants or compression strategies with statistical significance testing (bootstrap CIs, t‑tests where appropriate).  
- Ablations: quantization and sparsity impact on accuracy and payload.  
- Reporting: produce concise tables with metrics, CIs, and sample sizes. Include per‑device/profile breakdowns.

Test harness & automation
------------------------
- Components to build:  
  - `inference-runner` container for ONNX/TFLite evaluation (reproducible runtime).  
  - `eval-scripts` (Python) to compute WER/F1 and produce summaries.  
  - `fl-simulator` harness (Flower or custom) for federated experiments.  
  - `lora-sim` small simulator for constrained transport testing.  
- CI gates: unit tests + small model smoke tests on PRs; nightly larger runs (FL sim, privacy sweep).  
- Artifacts: store evaluation datasets, `outcome.json` from `fhir-validator`, and model artifacts with checksums.

Device & environment considerations
---------------------------------
- Use the devcontainer (`.devcontainer/Dockerfile`) for reproducible host‑side tooling (Synthea generation, `fhir-validator`).  
- Use an emulator/device farm for energy/latency profiling; record device make/model, OS version, and hardware acceleration availability.

Reporting & release gating
-------------------------
- Dashboards: daily/nightly metrics (WER, F1, payload size, sync success).  
- Gate for production: defined numeric thresholds for ASR/NLP/FHIR validation and privacy bounds.  
- Artifacts for audit: `outcome.json`, dataset provenance (checksums), and ADRs for irreversible decisions.

Timeline (suggested)
--------------------
- Week 0–1: finalize metrics, seed datasets, scaffold `inference-runner` and `eval-scripts`.  
- Week 1–2: Synthea → TTS pipeline, baseline ASR/NLP evaluations, and `fhir-validator` smoke tests.  
- Week 2–4: FL simulator + LoRa PoC and payload measurement.  
- Week 4–6: privacy attack suite and DP sweeps; CI integration and dashboards.

Quick commands (examples)
-------------------------
- Generate synthetic data (Synthea):
```
cd testData/synthea
./run_synthea -p 10 --exporter.fhir.export=true
```
- Validate a generated FHIR file with the installed validator (devcontainer):
```
fhir-validator testData/synthea/output/fhir/*.json -version 4.0.1 -output testData/synthea/output/validation-outcome.json
```

Next actions
------------
- I can scaffold the `inference-runner` container + `eval-scripts` (Python) and add a small CI job that runs the Synthea → validate smoke test.  
- Or I can implement the FL + LoRa PoC harness first. Choose which to start.

Document created by the evaluation planning workflow — use as a living checklist and update as experiments progress.
