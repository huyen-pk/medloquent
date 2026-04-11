"""Synthetic data pipeline components.

Public components:
- extractor: extract transcripts from Synthea/FHIR
- tts: generate audio from text
- augmenter: audio augmentation utilities
- asr_runner: ASR inference runner
- evaluator: ASR evaluation utilities

This package contains the implementation; lightweight CLI wrappers live
under `synthetic/scripts/` for backward compatibility.
"""

__all__ = ["extractor", "tts", "augmenter", "asr_runner", "evaluator"]
