# Dataset candidates — Test & validation for clinical dictation → EHR

Purpose: collect candidate datasets and canonical links useful for testing and validating an offline, privacy-preserving clinical dictation pipeline (audio → ASR → clinical NLP → FHIR generation + FL/LoRa). Use this document to prioritize ingestion, access checks, and small smoke tests.

## Quick guidance
- Use only open or properly licensed/DUA datasets for development and CI. For datasets that require DUA (MIMIC, i2b2/n2c2, eICU), complete required training and registration before downloading.  
- Real clinical audio with paired transcripts is scarce due to PHI — plan to synthesize clinical audio from de‑identified text (Synthea, MTSamples) + TTS and mix with public speech corpora (Common Voice, VCTK) for acoustic robustness tests.  
- Prioritize: (1) FHIR conformance (Synthea), (2) NER & entity linking (i2b2/n2c2), (3) EHR mapping & downstream validation (MIMIC / eICU), (4) acoustic robustness (Common Voice, VCTK).

---

## Candidate datasets

### Synthetic / FHIR‑focused

- Synthea — https://synthetichealth.github.io/synthea/ / https://github.com/synthetichealth/synthea
  - Description: Synthetic patient generator that emits FHIR R4 bundles, demographics, encounters, and simulated clinical events. 
  - Recommended use: FHIR mapping, E2E pipeline tests, creating synthetic clinical transcripts for TTS, schema/conformance validation. 
  - Access: Open source (Apache‑2 style). No PHI.

- HL7 FHIR examples — https://www.hl7.org/fhir/
  - Description: Official FHIR examples and schema docs. Useful as authoritative validation reference.
  - Recommended use: Schema validation, example resources, ADR verification.
  - Access: Public.

### EHR / clinical notes (de‑identified; DUA/registration required)

- MIMIC (MIMIC‑IV / MIMIC‑III) — https://mimic.mit.edu/ and PhysioNet: https://physionet.org/ (e.g., https://physionet.org/content/mimiciv/)
  - Description: Large de‑identified ICU dataset including structured data and clinical notes. 
  - Recommended use: NER/entity linking tests, FHIR mapping validation (note→resource mapping), distributional checks. 
  - Access: Requires PhysioNet account, DUA and CITI training.

- eICU Collaborative Research Database — https://eicu-crd.mit.edu/  and https://physionet.org/content/eicu-crd/
  - Description: Multi‑center critical care database with notes and structured data. 
  - Recommended use: Cross‑site variability, mapping, and downstream clinical workflows tests. 
  - Access: Registration and DUA.

- i2b2 / n2c2 shared task corpora — https://www.i2b2.org/ and https://n2c2.dbmi.pitt.edu/
  - Description: Curated clinical text corpora annotated for NER, relations, de‑identification, medication extraction, etc. 
  - Recommended use: Gold‑standard NER and relation extraction evaluation; entity linking benchmarks. 
  - Access: Challenge registration / data use agreements — some tasks require application.

### Clinical transcription / templates (text)

- MTSamples — https://www.mtsamples.com/
  - Description: Public medical transcription examples and templates across specialties (text). 
  - Recommended use: Lexicon building, template extraction, synthetic audio seed material for TTS. 
  - Access: Public.

### Biomedical literature (vocabulary / lexicon)

- PubMed Central (Open Access) — https://www.ncbi.nlm.nih.gov/pmc/
  - Description: Full‑text biomedical articles (OA subset). Good for domain vocabulary and entity linking corpora (non‑patient notes). 
  - Recommended use: Vocabulary expansion, entity linking candidates (SNOMED/ICD alias mining). 
  - Access: Public for OA subset.

### Public speech corpora (acoustics & robustness)

- Mozilla Common Voice — https://commonvoice.mozilla.org/en/datasets
  - Description: Large, multilingual crowd‑sourced speech dataset with transcripts. 
  - Recommended use: Acoustic robustness pretraining, speaker diversity mixing, noise augmentation. 
  - Access: Public (license per language; typically CC0/CC BY).

- LibriSpeech — https://www.openslr.org/12/
  - Description: Clean audiobook speech with transcripts — standard ASR benchmark. 
  - Recommended use: Baseline acoustic tests and latency profiling.
  - Access: Public.

- VCTK (Edinburgh) — https://datashare.ed.ac.uk/handle/10283/2791
  - Description: Multi‑speaker English dataset with consistent recording conditions. 
  - Recommended use: Speaker variability simulation and synthetic mixing.
  - Access: Public (Edinburgh DataShare). Check license.

- VoxCeleb — https://www.robots.ox.ac.uk/~vgg/data/voxceleb/
  - Description: Large speaker identification corpus (diverse speakers). 
  - Recommended use: Speaker variability, robustness to speaker characteristics. 
  - Access: Research use; check terms.

### TTS / voice synthesis corpora (for generating clinical audio)

- LJSpeech — https://keithito.com/LJ-Speech-Dataset/
  - Description: Single‑speaker TTS corpus (13k short audio clips). 
  - Recommended use: Bootstrapping TTS for synthetic clinical audio.
  - Access: Public.

- LibriTTS — https://www.openslr.org/60/
  - Description: Multi‑speaker TTS dataset derived from LibriVox. 
  - Recommended use: Multi‑voice synthetic audio generation.
  - Access: Public.

### Other useful resources / tooling

- FHIR validators & tools — https://www.hl7.org/fhir/validation.html
  - Use to validate bundle conformance and catch mapping errors early.

### HAPI / HL7 FHIR Validator (devcontainer)

- The HL7 FHIR Validator CLI (validator_cli.jar) is installed in the devcontainer image and exposed via the `fhir-validator` wrapper. It runs the official HL7 validation engine (structure/profile conformance, invariants, terminology checks when a terminology server is provided) and emits `OperationOutcome` style reports.

- Run a quick validation inside the devcontainer (example):

```bash
# run in devcontainer shell or via `docker run` into the devcontainer image
fhir-validator input-bundle.json -version 4.0.1 -output outcome.json
``` 

- Example with terminology server (if available):

```bash
fhir-validator input-bundle.json -version 4.0.1 -tx https://tx.fhir.org -output outcome.json
``` 

- CI recommendation: fail builds on `error` severity messages; persist `outcome.json` as an artifact for audits. For fully offline CI, prepackage required Implementation Guides and ValueSets and pass them with `-ig your-ig.zip` and `-defns` flags.

- OpenSLR (dataset index) — https://www.openslr.org/
  - Central index for many speech datasets (including LibriSpeech, LibriTTS).

---

## Recommended strategy (concise)

1. Start with Synthea + HL7 FHIR examples to validate FHIR mapping and persistence flows end‑to‑end.  
2. Use i2b2/n2c2 corpora (request access) to build gold NER/entity linking test sets.  
3. Use MIMIC/eICU (after DUA) for large‑scale distributional checks and mapping edge cases.  
4. Generate synthetic clinical audio by combining Synthea/MTSamples text → TTS (LJ/LibriTTS) and mix with public speech corpora (Common Voice, VCTK) for acoustic robustness testing.  
5. For FL privacy testing, create small synthetic clients with known ground truth to run membership and inversion attack experiments (no PHI required).

## Legal & ethical checklist (quick)

- Confirm dataset license and DUA before downloading.  
- For DUA datasets (MIMIC, i2b2, eICU): complete CITI training and register accounts.  
- Treat derived data (audio synthesized from clinical text) as sensitive if based on real patient content. Prefer synthetic sources for public CI.  
- Record dataset provenance, checksums, and access steps in ingestion metadata.

## Next actions (pick one)

- I can fetch the canonical download/DUA pages and summarize access steps and registration links.  
- I can scaffold a small pipeline: `synthea -> TTS -> audio mixing -> ASR eval harness` (Python + Docker) and provide runnable scripts.  
- I can generate a short checklist and CI job templates for gating dataset ingestion and validation.

---

Document created by repository assist to support evaluation planning.
