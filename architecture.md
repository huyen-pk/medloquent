# MedLoquent architecture

You’re essentially designing a **fully offline, privacy-preserving clinical AI system** with **edge inference + federated learning + low-bandwidth coordination (LoRa)**. That combination is unusual but tractable if you structure it as a layered, device-centric architecture.

Below is a precise, implementation-oriented breakdown.

---

# 1) High-Level System Architecture

### Core principles

- **Edge-first**: all inference and document generation runs locally
- **Data sovereignty**: no raw patient data leaves device
- **Intermittent coordination**: LoRa used only for model updates/metadata
- **Modular pipelines**: ASR → NLP structuring → EHR formatting

### Logical layers

```
[Audio Input Layer]
   ↓
[Streaming ASR Engine (on-device)]
   ↓
[Clinical NLP Pipeline]
   ↓
[EHR Structuring Engine]
   ↓
[Local Storage (compliant format)]
   ↓
[FL Client + Feature Extractor]
   ↓
[LoRa Communication Layer]
```

---

# 2) Cross-Platform App (Kotlin iOS + Android)

### Recommended approach

Use **Kotlin Multiplatform Mobile (KMM)**:

- **Shared (Kotlin)**
    - ASR orchestration
    - NLP pipeline logic
    - FL client
    - encryption / storage abstraction
- **Platform-specific**
    - Audio capture (AVFoundation / Android AudioRecord)
    - Hardware acceleration (NNAPI / Core ML delegate)

### Modules

```
shared/
 ├── asr/
 ├── nlp/
 ├── ehr/
 ├── fl/
 ├── storage/
 └── crypto/

androidApp/
iosApp/
```

### Key libraries

- **ONNX Runtime Mobile** (cross-platform inference)
- **TensorFlow Lite** (fallback / hardware acceleration)
- **SQLCipher** (encrypted SQLite)

---

# 3) Local Inference Stack (Fully Offline)

## 3.1 Speech-to-Text (ASR)

### Requirements

- Streaming + batch
- Medical vocabulary adaptation
- Low-latency (<300 ms chunk processing)

### Options

- MedGemma (quantized)
- Whisper (quantized, small/medium variants)
- Vosk (lighter, less accurate)
- Custom Conformer (optimized)

### Architecture

```
Audio Stream → Chunking (1–2 sec)
             → Feature Extraction (MFCC / log-mel)
             → ASR Model (ONNX/TFLite)
             → Incremental Decoder
```

### Optimization

- INT8 quantization
- CPU-first fallback (GPU optional)
- Sliding window inference

---

## 3.2 Clinical NLP Pipeline

### Stages

```
Raw Transcript
   ↓
Medical NER
   ↓
Entity Linking (SNOMED / ICD-10)
   ↓
Section Classification
   ↓
Structured Representation (JSON)
```

### Models (all local)

- DistilBERT / MiniLM (quantized)
- CRF layer for entity tagging (optional)

---

## 3.3 EHR Document Generator

### Output formats (EU compliant)

- **HL7 FHIR (R4)** → primary format
- Optional: CDA

### Pipeline

```
Structured JSON
   ↓
FHIR Mapper
   ↓
Resources:
   - Patient
   - Encounter
   - Observation
   - Condition
   ↓
Bundle (stored locally)
```

### Storage

- Encrypted SQLite (SQLCipher)
- File-based FHIR bundles (JSON)

---

# 4) Federated Learning (On Device)

## 4.1 Design Goals

- No raw data leaves device
- Minimal bandwidth usage
- Robust to sparse connectivity

---

## 4.2 Feature Extraction Strategy

Instead of sharing gradients from raw models:

```
Local Data
   ↓
Feature Extractor (frozen layers)
   ↓
Embeddings / Gradients
   ↓
Layer-wise updates
```

### Why

- Reduces communication payload
- Adds privacy layer
- Enables LoRa feasibility

---

## 4.3 Layer-Wise Aggregation

Split model into:

```
[Base Layers] (frozen or slowly updated)
[Mid Layers] (periodic updates)
[Top Layers] (frequent updates)
```

### Aggregation scheme

- Top layers → frequent LoRa updates
- Mid layers → occasional updates
- Base layers → rarely updated (manual sync)

### Algorithm

- Federated Averaging (FedAvg)
- Layer-wise learning rates
- Sparse updates (Top-K gradients)

---

## 4.4 FL Client Pipeline

```
Local Training Loop:
   - Load local dataset
   - Fine-tune top layers
   - Extract gradients
   - Compress (quantize + sparsify)

   ↓

Send via LoRa (when available)
```

---

# 5) LoRa Communication Layer

## Constraints

- Extremely low bandwidth (~0.3–50 kbps)
- High latency
- Packet size limits

---

## Strategy

### 5.1 What gets transmitted

- Model deltas only
- Highly compressed:
    - Quantized (INT8 / INT4)
    - Sparse (Top-K)
    - Possibly hashed

### 5.2 Communication model

```
Device → LoRa Gateway → Aggregator Node
                           ↓
                    Global Model Update
                           ↓
                  Broadcast back via LoRa
```

### 5.3 Scheduling

- Opportunistic sync
- Night-time batching
- Priority queues:
    - Critical updates (small)
    - Bulk updates (rare)

---

# 6) Privacy & Compliance (EU Context)

### Requirements (GDPR-aligned)

- Data never leaves device (default)
- Explicit consent for FL participation
- Right to delete data locally

### Implementation

- End-to-end encryption (AES-256)
- Secure enclave / keystore usage
- Differential privacy (optional):
    - Add noise to gradients

---

# 7) End-to-End Flow

### Real-time transcription

```
Doctor speaks
   ↓
Streaming ASR
   ↓
Live transcript UI
   ↓
NLP structuring (incremental)
   ↓
Draft EHR sections
```

---

### Final document generation

```
Recording ends
   ↓
Full ASR pass (higher accuracy)
   ↓
NLP refinement
   ↓
FHIR document generation
   ↓
Encrypted local storage
```

---

### Federated learning cycle

```
Idle device
   ↓
Local training
   ↓
Feature extraction
   ↓
Layer-wise compression
   ↓
LoRa transmission
```

---

# 8) Key Engineering Challenges

### 1. Model size vs device constraints

- Solution: aggressive quantization + pruning

### 2. ASR accuracy in medical domain

- Solution: domain-adapted fine-tuning via FL

### 3. LoRa bottleneck

- Solution: layer-wise + sparse updates

### 4. Cross-platform ML consistency

- Solution: ONNX as canonical format

---

# 9) Suggested Tech Stack Summary

| Component | Tech |
| --- | --- |
| App | Kotlin Multiplatform |
| ASR | Whisper (quantized ONNX) |
| NLP | DistilBERT (TFLite/ONNX) |
| Storage | SQLCipher + FHIR JSON |
| FL | Custom FedAvg (layer-wise) |
| Communication | LoRaWAN |
| Security | OS keystore + AES |

---

# 10) Optional Enhancements

- On-device vector DB for patient history retrieval
- Clinical decision support (offline rules + ML)
- Incremental personalization per doctor
- Secure USB export of EHR bundles