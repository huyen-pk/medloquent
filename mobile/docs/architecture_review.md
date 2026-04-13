# Architecture review — MedLoquent

Summary
-------
- Project: Edge‑first, privacy‑preserving clinical dictation system with on‑device ASR/NLP, FHIR bundle generation, encrypted local storage, and federated learning over constrained links (LoRa). See the canonical reference in [architecture.md](architecture.md) and the project overview in [README.md](README.md).
- Primary platform choices: Kotlin Multiplatform (KMM) for shared logic, ONNX/TFLite for model runtime, FHIR R4 for clinical data interchange, and SQLCipher for encrypted local storage.

Key decisions (state & recommendation)
-------------------------------------
- Shared‑platform strategy: Keep KMM for core ASR/NLP/FL code. Enforce thin, well‑tested platform adapters for audio capture, hardware acceleration delegates, and keystore integration.
- Model runtime: Use ONNX Runtime Mobile as the canonical artifact and provide TFLite as a hardware‑accelerated fallback. Produce quantized INT8 (and INT4 where viable) builds for device targets.
- Federated learning over LoRa: Adopt layer‑wise FedAvg with Top‑K sparse + quantized updates. Implement a gateway/aggregator that performs secure aggregation and retransmits global deltas to devices.
- Data & storage: Canonicalize on FHIR R4 bundles for export/import and persist bundles in SQLCipher. Keep a single canonical bundle format for interchange and audits.
- Operational scope: Start as a modular monolith (shared KMM + platform shells) and delay microservice decomposition until team size/operational maturity justifies it.

Strengths (keep)
-----------------
- Privacy‑first default: architecture explicitly designed to keep raw data on device.
- Clear module boundaries: `:shared` modules (asr, nlp, ehr, fl, lora, storage) align with responsibilities in [settings.gradle.kts](settings.gradle.kts).
- Practical tech choices: ONNX/TFLite + SQLCipher are appropriate for offline device constraints.
- Dev ergonomics: devcontainer + remote macOS bridge in [README.md](README.md) support cross‑platform development.

Risks & gaps (priority)
-----------------------
- LoRa bandwidth and latency are severe constraints — requires validation of compression, sparsity, and scheduling assumptions; no aggregator PoC exists yet.
- Missing production security integration: Demo envelope codec and placeholder keystore usage must be replaced with Android Keystore / iOS Keychain / Secure Enclave flows.
- Operational/CI hygiene: no committed Gradle wrapper and no automated validation gates for FHIR bundles or model artifacts.
- Documentation / ADRs: key irreversible choices (FL protocol, quantization format, aggregator topology) are not yet documented as ADRs or SLOs.

Concrete, prioritized recommendations
-----------------------------------
1. Immediate (low friction)
   - Commit a Gradle wrapper and add CI jobs to build `:shared` and `:androidApp` (assembleDebug).  
   - Add a smoke test that runs Synthea → validate FHIR bundle with the HAPI/HL7 validator (devcontainer has a validator installed).
2. PoC (next):
   - Build a minimal LoRa gateway/aggregator PoC (HTTP server that accepts compressed deltas, runs secure aggregation, emits a global delta). Measure bytes/round and end‑to‑end latency.  
3. Security (must):
   - Replace DemoEnvelopeCodec with platform keystore backed AES‑GCM and implement key rotation and deletion flows.  
4. Models & tooling:
   - Standardize ONNX as canonical artifact; publish quantized (INT8) builds and add parity/accuracy regression tests.  
5. Docs & process:
   - Record ADRs for FL protocol, model artifact format, and LoRa aggregator topology. Define success metrics and release gates.

What NOT to build yet
---------------------
- Do not split into many independent microservices early — keep modular monolith to reduce operational overhead.  
- Do not over‑engineer a full service mesh or always‑on device streaming for LoRa scenarios; prioritize batched, compressed updates.

Suggested immediate next steps (3–4 day cadence)
-----------------------------------------------
1. Commit Gradle wrapper + CI job skeleton.  
2. Create three ADRs (FL protocol, quantization & model artifact, keystore/envelope policy).  
3. Implement LoRa aggregator PoC and run measurements with synthetic clients.  
4. Replace DemoEnvelopeCodec with keystore‑backed AES‑GCM (platform PRs).

Files & references
------------------
- Architecture reference: [architecture.md](architecture.md)  
- Project readme & build notes: [README.md](README.md)  
- Module list: [settings.gradle.kts](settings.gradle.kts)  
- Root plugin file: [build.gradle.kts](build.gradle.kts)

---

Document created by repository assist — concise architecture review and prioritized next actions.
