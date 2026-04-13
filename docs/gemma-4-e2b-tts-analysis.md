# Gemma-4-E2B-it-ONNX as TTS Backend: Analysis

## Critical Finding: FUNDAMENTAL MISMATCH

**Gemma-4-E2B-it-ONNX is NOT a Text-to-Speech (TTS) model.** It is a **speech-to-text/multimodal input** model.

### Model Capabilities
- **Input modalities**: Text, Image, Audio (E2B/E4B variants)
- **Output**: Text only
- **E2B variant specifically**:
  - For audio: ASR (transcription) and speech-to-translated-text translation
  - NOT audio generation or vocoding

### Why It Fails for TTS
TTS requires: Clinical text → model inference → **audio waveform output**
Gemma-4-E2B-it-ONNX produces: Any input → model inference → **text tokens**

This is the inverse of what's needed. Using Gemma for TTS would require:
1. Getting text output from the model (✓ possible)
2. Decoding tokens to audio (✗ requires separate vocoder)
3. No built-in audio synthesis capability (✗ missing)

## Current TTS Architecture
- **Current backend**: Coqui TTS (full synthesis pipeline)
- **Location**: `/home/huyenpk/Projects/medloquent/synthetic/pipeline/tts.py`
- **Output**: Direct WAV generation at 16kHz
- **Pipeline**: Text → Mel-spectrogram → Vocoder → Audio waveform

## Existing ONNX/Audio Infrastructure
- **Cached models**:
  - `models--onnx-community--gemma-4-E2B-it-ONNX/` (multimodal input, text output)
  - `models--NeuML--ljspeech-vits-onnx/` (vocoder/synthesis model - this is TTS-relevant!)
  - Deepseek models (7B, 67B text-only)

- **Dependencies in requirements-full.txt**:
  - ✓ onnxruntime (present)
  - ✓ huggingface-hub (present)
  - ✗ transformers (missing)
  - ✗ optimum (missing)
  - ✓ Coqui TTS (for current pipeline)

## Risk Assessment
- **Gemma-4-E2B-it-ONNX for TTS**: Not viable without external vocoder
- **Alternative high-value use**: Use Gemma for **clinical entity extraction** from transcribed text (not TTS)
- **VITs ONNX model**: Already cached - this looks like the actual TTS-capable vocoder

## Architecture Recommendation
If goal is to replace Coqui TTS with ONNX-based solutions:
1. Keep LLM (Gemma-4) separate for NLP-stage tagging/entity extraction
2. Use the cached VITs vocoder (ljspeech-vits-onnx) or similar for actual synthesis
3. Implement two-stage pipeline: Text → (LLM optional) → Vocoder → Audio

## Minimum Changes Needed (if using ONNX vocoder only)
- Replace Coqui TTS with ONNX vocoder inference
- Implement mel-spectrogram → text mapping (if not using vocoder directly)
- Keep Gemma-4 out of TTS pipeline (redirect to NLP stage instead)
