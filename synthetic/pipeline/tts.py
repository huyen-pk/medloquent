#!/usr/bin/env python3
"""TTS component for the synthetic pipeline.

This module requires Coqui TTS (`TTS`) to be installed. The runtime will
fail loudly if Coqui is not available so the pipeline image must include
the full dependencies (see `requirements-full.txt`).
"""

import argparse
import csv
import os
import struct
import sys
import wave
from typing import Dict, List


# Helper write_wav: use soundfile if available, otherwise fall back to
# stdlib wave.
def write_wav(path: str, samples: List[float], sr: int = 16000) -> None:
    try:
        import soundfile as sf
        import numpy as np

        arr = np.array(samples, dtype="float32")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sf.write(path, arr, sr)
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


def generate_with_coqui(text: str, out_path: str) -> None:
    """Generate audio using the Coqui TTS library.

    Raises an exception if generation fails.
    """
    from TTS.api import TTS

    tts = TTS()
    tts.tts_to_file(text=text, file_path=out_path)


def resample_output_to_16k(out_path: str) -> None:
    try:
        import soundfile as sf

        data, sample_rate = sf.read(out_path)
    except Exception:
        return

    if sample_rate == 16000:
        return

    try:
        import librosa
    except Exception:
        write_wav(out_path, data.tolist(), sample_rate)
        return

    data_mono = data.mean(axis=1) if data.ndim > 1 else data
    data_resampled = librosa.resample(
        data_mono, orig_sr=sample_rate, target_sr=16000
    )
    write_wav(out_path, data_resampled.tolist(), sr=16000)


def generate_audio(text: str, out_path: str) -> None:
    """Produce audio for `text` using Coqui TTS. Raises on failure."""
    try:
        generate_with_coqui(text, out_path)
        resample_output_to_16k(out_path)
    except Exception as exc:
        print("Coqui TTS generation failed:", exc, file=sys.stderr)
        raise


def run_tts(
    manifest: str = "testData/synthetic/manifest.csv",
    out_dir: str = "testData/synthetic/audio",
) -> List[Dict[str, str]]:
    """Synthesize audio for each row in a manifest CSV using Coqui TTS.

    Raises a RuntimeError if Coqui is not importable.
    """
    rows: List[Dict[str, str]] = []
    if not os.path.exists(manifest):
        raise FileNotFoundError(manifest)

    with open(manifest, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    # Require Coqui TTS to be available in the runtime.
    try:
        from TTS.api import TTS  # noqa: F401
    except Exception as exc:
        raise RuntimeError(
            "Coqui TTS is not available. Ensure the pipeline image installs requirements-full.txt"
        ) from exc

    out_rows: List[Dict[str, str]] = []
    for r in rows:
        record_id = r.get("id") or ""
        text = r.get("text") or ""
        if not record_id:
            continue
        out_path = os.path.join(out_dir, f"{record_id}.wav")
        os.makedirs(out_dir, exist_ok=True)
        generate_audio(text, out_path)
        out_rows.append({"id": record_id, "audio": out_path})
    return out_rows


def main(argv: List[str] | None = None) -> None:  # type: ignore[name-defined]
    p = argparse.ArgumentParser()
    p.add_argument(
        "--manifest",
        default="testData/synthetic/manifest.csv",
        help="manifest CSV",
    )
    p.add_argument(
        "--out-dir", default="testData/synthetic/audio", help="output audio dir"
    )
    args = p.parse_args(argv)
    run_tts(args.manifest, args.out_dir)


if __name__ == "__main__":
    main()
