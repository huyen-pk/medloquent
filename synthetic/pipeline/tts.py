#!/usr/bin/env python3
"""TTS component for the synthetic pipeline.

Exposes `run_tts(manifest, out_dir, force_fallback)` which reads a CSV
manifest and writes per-id WAV files. Attempts to use Coqui TTS if
installed; otherwise falls back to a deterministic tone generator for
smoke tests.
"""

import argparse
import csv
import math
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
        # fallback: write 16-bit PCM via wave
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            # convert float samples (-1.0..1.0) to int16
            frames = bytearray()
            for s in samples:
                v = max(-1.0, min(1.0, float(s)))
                iv = int(v * 32767.0)
                frames.extend(struct.pack("<h", iv))
            wf.writeframes(bytes(frames))


def fallback_tone(text: str, out_path: str, sr: int = 16000) -> None:
    duration = max(0.5, min(6.0, len(text.split()) * 0.25))
    nsamples = int(sr * duration)
    f = 220 + (sum(ord(c) for c in text) % 400)
    samples: List[float] = []
    for i in range(nsamples):
        t = i / sr
        samples.append(0.05 * math.sin(2 * math.pi * f * t))
    write_wav(out_path, samples, sr)


def generate_with_coqui(text: str, out_path: str) -> None:
    from TTS.api import TTS

    tts = TTS()
    tts.tts_to_file(text=text, file_path=out_path)


def coqui_available() -> bool:
    try:
        from TTS.api import TTS

        _ = TTS
        return True
    except Exception:
        return False


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


def generate_audio(text: str, out_path: str, use_coqui: bool) -> None:
    if use_coqui:
        try:
            generate_with_coqui(text, out_path)
            resample_output_to_16k(out_path)
            return
        except Exception as exc:
            print("coqui TTS failed — falling back:", exc, file=sys.stderr)

    fallback_tone(text, out_path)


def run_tts(
    manifest: str = "testData/synthetic/manifest.csv",
    out_dir: str = "testData/synthetic/audio",
    force_fallback: bool = False,
) -> List[Dict[str, str]]:
    rows: list[dict[str, str | None]] = []
    if not os.path.exists(manifest):
        raise FileNotFoundError(manifest)

    with open(manifest, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    use_coqui = not force_fallback and coqui_available()

    out_rows: List[Dict[str, str]] = []
    for r in rows:
        record_id = r.get("id") or ""
        text = r.get("text") or ""
        if not record_id:
            continue
        out_path = os.path.join(out_dir, f"{record_id}.wav")
        generate_audio(text, out_path, use_coqui)
        out_rows.append({"id": record_id, "audio": out_path})
    return out_rows


def main(argv: list[str] | None = None) -> None:
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
        "--force-fallback",
        action="store_true",
        help="skip TTS and use tone fallback",
    )
    args = p.parse_args(argv)
    run_tts(args.manifest, args.out_dir, args.force_fallback)


if __name__ == "__main__":
    main()
