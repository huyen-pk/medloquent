#!/usr/bin/env python3
"""TTS component for the synthetic pipeline.

Exposes `run_tts(manifest, out_dir, force_fallback)` which reads a CSV
manifest and writes per-id WAV files. Attempts to use Coqui TTS if
installed; otherwise falls back to a deterministic tone generator for
smoke tests.
"""

import argparse
import csv
import os
import sys
from typing import Dict, List, Optional

try:
    import soundfile as sf
    import numpy as np
except Exception:
    print("Please install dependencies: soundfile, numpy", file=sys.stderr)
    raise


def write_wav(path: str, audio: "np.ndarray", sr: int = 16000) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sf.write(path, audio.astype("float32"), sr)


def fallback_tone(text: str, out_path: str, sr: int = 16000) -> None:
    duration = max(0.5, min(6.0, len(text.split()) * 0.25))
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    f = 220 + (sum(ord(c) for c in text) % 400)
    audio = 0.05 * np.sin(2 * np.pi * f * t)
    write_wav(out_path, audio, sr)


def generate_with_coqui(text: str, out_path: str) -> None:
    from TTS.api import TTS  # type: ignore

    tts = TTS()
    tts.tts_to_file(text=text, file_path=out_path)


def run_tts(manifest: str = "testData/synthetic/manifest.csv", out_dir: str = "testData/synthetic/audio", force_fallback: bool = False) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if not os.path.exists(manifest):
        raise FileNotFoundError(manifest)

    with open(manifest, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    use_coqui = False
    if not force_fallback:
        try:
            import TTS  # type: ignore
            use_coqui = True
        except Exception:
            use_coqui = False

    out_rows: List[Dict[str, str]] = []
    for r in rows:
        _id = r.get("id")
        text = r.get("text", "")
        out_path = os.path.join(out_dir, f"{_id}.wav")
        if use_coqui:
            try:
                generate_with_coqui(text, out_path)
                try:
                    data, sr = sf.read(out_path)
                    if sr != 16000:
                        import librosa

                        data_mono = data.mean(axis=1) if data.ndim > 1 else data
                        data_res = librosa.resample(data_mono, orig_sr=sr, target_sr=16000)
                        write_wav(out_path, data_res, sr=16000)
                except Exception:
                    pass
                out_rows.append({"id": _id, "audio": out_path})
                continue
            except Exception as e:
                print("coqui TTS failed — falling back:", e, file=sys.stderr)
        fallback_tone(text, out_path)
        out_rows.append({"id": _id, "audio": out_path})
    return out_rows


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="testData/synthetic/manifest.csv", help="manifest CSV")
    p.add_argument("--out-dir", default="testData/synthetic/audio", help="output audio dir")
    p.add_argument("--force-fallback", action="store_true", help="skip TTS and use tone fallback")
    args = p.parse_args(argv)
    run_tts(args.manifest, args.out_dir, args.force_fallback)


if __name__ == "__main__":
    main()
