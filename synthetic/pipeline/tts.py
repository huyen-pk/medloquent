#!/usr/bin/env python3
"""TTS component for the synthetic pipeline.

This module uses a pluggable TTS backend and currently defaults to Kokoro
running on ONNX Runtime.
"""

from __future__ import annotations

import argparse
import csv
from math import gcd
import os
import struct
import sys
import wave
from typing import Any, Dict, List, Sequence

from synthetic.pipeline.tts_backends import (
    DEFAULT_BACKEND,
    DEFAULT_MODEL_FILE,
    DEFAULT_MODEL_ID,
    DEFAULT_SPEED,
    DEFAULT_VOICE,
    SUPPORTED_BACKENDS,
    TTSBackend,
    TTSBackendConfig,
    build_tts_backend,
)


TARGET_SAMPLE_RATE = 16000
SEGMENT_PAUSE_MS = 125


def write_wav(
    path: str,
    samples: Sequence[float],
    sr: int = TARGET_SAMPLE_RATE,
) -> None:
    """Write mono WAV audio using soundfile when available."""
    try:
        import numpy as np
        import soundfile as sf

        arr = np.array(samples, dtype="float32")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sf.write(path, arr, sr, subtype="PCM_16")
        return
    except Exception:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            frames = bytearray()
            for s in samples:
                v = max(-1.0, min(1.0, float(s)))
                iv = int(v * 32767.0)
                frames.extend(struct.pack("<h", iv))
            wf.writeframes(bytes(frames))


def _to_mono_float32(samples: Sequence[float] | Any) -> Any:
    try:
        import numpy as np
    except Exception as exc:
        raise RuntimeError(
            "numpy is required for audio normalization."
        ) from exc

    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.mean(axis=1)
    return arr


def resample_audio(
    samples: Sequence[float] | Any,
    source_sr: int,
    target_sr: int = TARGET_SAMPLE_RATE,
) -> Any:
    """Resample audio while preserving the downstream ASR contract."""
    mono = _to_mono_float32(samples)
    if source_sr == target_sr:
        return mono

    try:
        from scipy import signal

        factor = gcd(source_sr, target_sr)
        up = target_sr // factor
        down = source_sr // factor
        return signal.resample_poly(mono, up, down).astype("float32")
    except Exception:
        import numpy as np

        new_length = max(1, int(round(len(mono) * target_sr / source_sr)))
        source_idx = np.linspace(0.0, 1.0, num=len(mono), endpoint=False)
        target_idx = np.linspace(0.0, 1.0, num=new_length, endpoint=False)
        return np.interp(target_idx, source_idx, mono).astype("float32")


def write_normalized_wav(
    path: str,
    samples: Sequence[float] | Any,
    sample_rate: int,
) -> None:
    """Write audio normalized to the 16 kHz mono pipeline format."""
    normalized = resample_audio(samples, sample_rate, TARGET_SAMPLE_RATE)
    write_wav(path, normalized.tolist(), sr=TARGET_SAMPLE_RATE)


def synthesize_audio(text: str, backend: TTSBackend) -> tuple[list[float], int]:
    """Produce audio samples for text using the configured backend."""
    segments = backend.prepare(text)
    if not segments:
        raise RuntimeError("No speech-ready text was produced for synthesis.")

    audio_segments = [backend.synthesize(segment) for segment in segments]
    if len(audio_segments) == 1:
        return audio_segments[0], backend.sample_rate

    try:
        import numpy as np
    except Exception as exc:
        raise RuntimeError(
            "numpy is required for audio concatenation."
        ) from exc

    pause_samples = int(
        round(backend.sample_rate * SEGMENT_PAUSE_MS / 1000.0)
    )
    pause = np.zeros(pause_samples)
    stitched: list[Any] = []
    for index, audio in enumerate(audio_segments):
        stitched.append(np.asarray(audio, dtype=np.float32))
        if index < len(audio_segments) - 1:
            stitched.append(pause)
    combined: Any = np.concatenate(stitched)
    return combined.tolist(), backend.sample_rate


def generate_audio(text: str, out_path: str, backend: TTSBackend) -> None:
    """Generate audio with the selected TTS backend and normalize to 16 kHz."""
    try:
        samples, sample_rate = synthesize_audio(text, backend)
        write_normalized_wav(out_path, samples, sample_rate)
    except Exception as exc:
        print(f"{backend.name} TTS generation failed: {exc}", file=sys.stderr)
        raise


def run_tts(
    manifest: str = "testData/synthetic/manifest.csv",
    out_dir: str = "testData/synthetic/audio",
    *,
    backend: str = DEFAULT_BACKEND,
    model_id: str = DEFAULT_MODEL_ID,
    model_path: str | None = None,
    model_file: str = DEFAULT_MODEL_FILE,
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
    allow_download: bool = True,
) -> List[Dict[str, str]]:
    """Synthesize audio for each row in a manifest CSV."""
    rows: List[Dict[str, str]] = []
    if not os.path.exists(manifest):
        raise FileNotFoundError(manifest)

    with open(manifest, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    backend_instance = build_tts_backend(
        TTSBackendConfig(
            backend=backend,
            model_id=model_id,
            model_path=model_path,
            model_file=model_file,
            voice=voice,
            speed=speed,
            allow_download=allow_download,
        )
    )

    out_rows: List[Dict[str, str]] = []
    for r in rows:
        record_id = r.get("id") or ""
        text = r.get("text") or ""
        if not record_id:
            continue
        out_path = os.path.join(out_dir, f"{record_id}.wav")
        os.makedirs(out_dir, exist_ok=True)
        generate_audio(text, out_path, backend_instance)
        out_rows.append({"id": record_id, "audio": out_path})
    return out_rows


def main(argv: List[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--manifest",
        default="testData/synthetic/manifest.csv",
        help="manifest CSV",
    )
    p.add_argument(
        "--out-dir", default="testData/synthetic/audio", help="output audio dir"
    )
    p.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        choices=SUPPORTED_BACKENDS,
        help="TTS backend to use",
    )
    p.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help="Hugging Face model id for the selected backend",
    )
    p.add_argument(
        "--model-path",
        help="Optional local snapshot path for the selected TTS backend",
    )
    p.add_argument(
        "--model-file",
        default=DEFAULT_MODEL_FILE,
        help="Relative model file path inside the snapshot",
    )
    p.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help="Voice id to use for synthesis",
    )
    p.add_argument(
        "--speed",
        type=float,
        default=DEFAULT_SPEED,
        help="Speech rate multiplier",
    )
    p.add_argument(
        "--no-download",
        action="store_true",
        help=(
            "Require the model to already exist in the local "
            "Hugging Face cache"
        ),
    )
    args = p.parse_args(argv)
    run_tts(
        args.manifest,
        args.out_dir,
        backend=args.backend,
        model_id=args.model_id,
        model_path=args.model_path,
        model_file=args.model_file,
        voice=args.voice,
        speed=args.speed,
        allow_download=not args.no_download,
    )


if __name__ == "__main__":
    main()
