#!/usr/bin/env python3
"""ASR runner component (reusable).

For smoke tests this exposes `run_asr` which will create a
predictions.jsonl file. Real ASR integrations (Vosk/onnx/whisper) can be
plugged into this component later.
"""

import argparse
import csv
import glob
import json
import os
import subprocess
import tempfile
import urllib.request
import wave
import zipfile
from typing import Dict, List, Optional
from typing import Any

_HAS_VOSK = False
_HAS_WHISPER = False
try:
    import vosk

    _HAS_VOSK = True
except Exception:
    _HAS_VOSK = False

try:
    import whisper

    _HAS_WHISPER = True
except Exception:
    _HAS_WHISPER = False


def load_manifest(manifest_path: str) -> Dict[str, str]:
    d: Dict[str, str] = {}
    if not os.path.exists(manifest_path):
        return d
    with open(manifest_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            d[row["id"]] = row.get("text", "")
    return d


def find_audio_files(in_dir: str) -> List[str]:
    paths: List[str] = glob.glob(
        os.path.join(in_dir, "**", "*.wav"), recursive=True
    )
    return sorted(paths)


def download_and_extract_vosk(model_url: str, dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        zpath = os.path.join(td, "model.zip")
        print(f"Downloading Vosk model from {model_url}...")
        urllib.request.urlretrieve(model_url, zpath)
        print("Extracting model...")
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(dest_dir)


def ensure_16k_mono(src: str) -> str:
    # If the file is already 16k mono PCM WAV, return it unchanged.
    # Otherwise use ffmpeg to convert it.
    try:
        with wave.open(src, "rb") as wf:
            channels = wf.getnchannels()
            sr = wf.getframerate()
            sampwidth = wf.getsampwidth()
            if channels == 1 and sr == 16000 and sampwidth == 2:
                return src
    except Exception:
        pass

    # convert using ffmpeg
    out = os.path.splitext(src)[0] + ".16k.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src,
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "wav",
        out,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return out
    except Exception:
        return src


def resolve_engine() -> Optional[str]:
    if _HAS_VOSK:
        return "vosk"
    if _HAS_WHISPER:
        return "whisper"
    return None


def ensure_vosk_model_available(model_path: str, model_url: str) -> None:
    if os.path.exists(model_path):
        return
    print("Vosk model not found, downloading to:", model_path)
    download_and_extract_vosk(model_url, os.path.dirname(model_path))


def load_whisper_model(engine: Optional[str]) -> Any | None:
    if engine != "whisper":
        return None
    return whisper.load_model("tiny")


def transcribe_with_vosk(audio_path: str, model_path: str) -> str:
    try:
        wav_path = ensure_16k_mono(audio_path)
        model = vosk.Model(model_path)
        with wave.open(wav_path, "rb") as wav_file:
            recognizer = vosk.KaldiRecognizer(model, wav_file.getframerate())
            while True:
                data = wav_file.readframes(4000)
                if not data:
                    break
                recognizer.AcceptWaveform(data)
        parsed = json.loads(recognizer.FinalResult())
        text = parsed.get("text", "")
        return text if isinstance(text, str) else ""
    except Exception as exc:
        print("Vosk transcription failed:", exc)
        return ""


def transcribe_with_whisper(whisper_model: Any, audio_path: str) -> str:
    try:
        result = whisper_model.transcribe(audio_path)
        text = result.get("text", "")
        return text if isinstance(text, str) else ""
    except Exception as exc:
        print("Whisper transcription failed:", exc)
        return ""


def prediction_for_file(
    engine: Optional[str],
    whisper_model: Any | None,
    vosk_model_path: str,
    audio_path: str,
    fallback: str,
) -> str:
    if engine == "vosk":
        return transcribe_with_vosk(audio_path, vosk_model_path) or fallback
    if engine == "whisper" and whisper_model is not None:
        return transcribe_with_whisper(whisper_model, audio_path) or fallback
    return fallback


def run_asr(
    in_dir: str, out_dir: str, manifest: str = "testData/synthetic/manifest.csv"
) -> str:
    os.makedirs(out_dir, exist_ok=True)
    manifest_map = load_manifest(manifest)

    audio_files = find_audio_files(in_dir)
    out_path = os.path.join(out_dir, "predictions.jsonl")
    engine = resolve_engine()

    # prepare vosk model if needed
    vosk_model_path = os.environ.get(
        "VOSK_MODEL_DIR", "models/vosk-model-small-en-us-0.15"
    )
    vosk_model_url = os.environ.get(
        "VOSK_MODEL_URL",
        "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
    )
    if engine == "vosk":
        ensure_vosk_model_available(vosk_model_path, vosk_model_url)

    whisper_model = load_whisper_model(engine)

    with open(out_path, "w", encoding="utf-8") as out:
        for pth in audio_files:
            basename = os.path.splitext(os.path.basename(pth))[0]
            _id = basename.split("_")[0]
            ref = manifest_map.get(_id, "")
            pred_text = prediction_for_file(
                engine,
                whisper_model,
                vosk_model_path,
                pth,
                ref,
            )

            rec = {"id": _id, "audio": pth, "prediction": pred_text}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out_path


def main(argv: List[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--in-dir",
        required=True,
        help="augmented audio dir (e.g., testData/synthetic/audio_aug)",
    )
    p.add_argument("--out-dir", required=True, help="predictions out dir")
    p.add_argument(
        "--manifest",
        default="testData/synthetic/manifest.csv",
        help="manifest with references",
    )
    args = p.parse_args(argv)
    path = run_asr(args.in_dir, args.out_dir, args.manifest)
    print("Wrote predictions:", path)


if __name__ == "__main__":
    main()
