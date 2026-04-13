# Glossary — Acronyms & Short Definitions

This file lists acronyms and short explanations used by the synthetic data pipeline.

- FHIR — Fast Healthcare Interoperability Resources: an HL7 standard for healthcare data (JSON/XML) used to model patients, observations, notes, etc.
- Synthea — Open-source synthetic patient generator that produces FHIR records and realistic clinical narratives (not an acronym; product name).
- TTS — Text-to-Speech: systems that synthesize spoken audio from text (for this pipeline, Kokoro on ONNX Runtime).
- ASR — Automatic Speech Recognition: systems that convert spoken audio back into text (e.g., Vosk, Whisper).
- WER — Word Error Rate: a metric for ASR that measures insertions/deletions/substitutions at the word level.
- CER — Character Error Rate: similar to WER but computed on characters (useful for short tokens/abbreviations).
- SNR — Signal-to-Noise Ratio: measure of signal strength vs noise level (in dB) used to create noisy test variants.
- RIR — Room Impulse Response: audio response of an acoustic space used to apply realistic reverberation by convolution.
- RTF — Run-Time Format (informal): here used to denote runtime model formats such as ONNX or TFLite.
- ONNX — Open Neural Network Exchange: a portable model format for exchanging deep learning models across frameworks.
- ONNX Runtime — Inference engine for running ONNX models efficiently on CPU/GPU.
- TFLite — TensorFlow Lite: lightweight TensorFlow runtime and model format for mobile/edge devices.
- Vosk — Offline ASR toolkit (Kaldi-based) that runs on-device and provides real-time transcriptions.
- whisper / whisper.cpp — OpenAI's Whisper model for ASR; `whisper.cpp` is an optimized C/C++ port for local inference.
- Kokoro — Lightweight neural text-to-speech model used here through ONNX Runtime and Hugging Face model snapshots.
- LJSpeech — Public single-speaker speech dataset commonly used to train TTS models (not an acronym).
- jiwer — Python package that computes WER/CER and provides common transcript normalizations.
- MFA — Montreal Forced Aligner: tool for aligning transcripts to audio at word/phone level (used for timing/analysis).
- aeneas — Lightweight forced-alignment Python library for generating word-level timestamps.
- SNOMED CT — Systematized Nomenclature of Medicine — Clinical Terms: comprehensive clinical terminology (used for medical-term matching).
- ICD — International Classification of Diseases: coding system for diagnoses and conditions (used for evaluation/term lists).
- CI — Continuous Integration: automated pipelines (e.g., GitHub Actions) that run smoke tests and validate metrics.
- CLI — Command Line Interface: e.g., `synthetic/cli.py` provides subcommands to run pipeline stages.

If you want this glossary extended with links, example commands per term, or mapping of each acronym to the exact module/function in the repo (for example: `TTS` → `synthetic/pipeline/tts.py`), tell me which mapping you prefer and I will add it.
