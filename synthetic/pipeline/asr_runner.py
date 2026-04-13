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
    """Load a CSV manifest mapping record id to reference text.

    The manifest should be a CSV with at least an `id` column and an
    optional `text` column. Missing files return an empty mapping.

    Args:
        manifest_path: Path to the CSV manifest.

    Returns:
        A dict mapping record id to text.
    """
    d: Dict[str, str] = {}
    if not os.path.exists(manifest_path):
        return d
    with open(manifest_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            d[row["id"]] = row.get("text", "")
    return d


def find_audio_files(in_dir: str) -> List[str]:
    """Find .wav audio files under a directory (recursive).

    Args:
        in_dir: Root directory to search for .wav files.

    Returns:
        Sorted list of file paths to .wav files.
    """
    paths: List[str] = glob.glob(
        os.path.join(in_dir, "**", "*.wav"), recursive=True
    )
    return sorted(paths)


def download_and_extract_vosk(model_url: str, dest_dir: str) -> None:
    """Download a zipped Vosk model and extract it to a destination.

    Args:
        model_url: URL to the zipped model.
        dest_dir: Directory to extract the model into.
    """
    os.makedirs(dest_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        zpath = os.path.join(td, "model.zip")
        print(f"Downloading Vosk model from {model_url}...")
        urllib.request.urlretrieve(model_url, zpath)
        print("Extracting model...")
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(dest_dir)


def ensure_16k_mono(src: str) -> str:
    """Ensure a WAV file is 16 kHz mono PCM, converting with ffmpeg if needed.

    If conversion succeeds this returns the path to the converted file;
    otherwise the original path is returned.

    Args:
        src: Path to the source WAV file.

    Returns:
        Path to a 16 kHz mono WAV file (may be the original file).
    """
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


def resolve_engine() -> str:
    """Pick a default ASR engine available in the environment.

    Returns "vosk" if Vosk is importable, "whisper" if Whisper is
    importable. Raises RuntimeError if no engine is available.
    """
    if _HAS_VOSK:
        return "vosk"
    if _HAS_WHISPER:
        return "whisper"
    raise RuntimeError(
        "No ASR engine available. Install 'vosk' or 'whisper' (see requirements-full.txt)"
    )


def ensure_vosk_model_available(model_path: str, model_url: str) -> None:
    """Ensure the Vosk model directory exists, downloading if missing.

    Args:
        model_path: Expected path to the model directory.
        model_url: URL to download the model zip if not present.
    """
    if os.path.exists(model_path):
        return
    print("Vosk model not found, downloading to:", model_path)
    download_and_extract_vosk(model_url, os.path.dirname(model_path))


def load_whisper_model(engine: Optional[str]) -> Any | None:
    """Load a Whisper model instance if the requested engine is 'whisper'.

    Returns the loaded model or `None` if not applicable.
    """
    if engine != "whisper":
        return None
    return whisper.load_model("tiny")


def transcribe_with_vosk(audio_path: str, model_path: str) -> str:
    """Transcribe an audio file using a Vosk model.

    Args:
        audio_path: Path to the audio file to transcribe.
        model_path: Path to the Vosk model directory.

    Returns:
        The transcribed text, or an empty string on failure.
    """
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
    """Transcribe an audio file using a loaded Whisper model.

    Args:
        whisper_model: A loaded Whisper model instance.
        audio_path: Path to the audio file to transcribe.

    Returns:
        The transcribed text, or an empty string on failure.
    """
    try:
        result = whisper_model.transcribe(audio_path)
        text = result.get("text", "")
        return text if isinstance(text, str) else ""
    except Exception as exc:
        print("Whisper transcription failed:", exc)
        return ""


def prediction_for_file(
    engine: str,
    whisper_model: Any | None,
    vosk_model_path: str,
    audio_path: str,
    fallback: str,
) -> str:
    """Return a transcription for a single audio file using the selected engine.

    If transcription fails, an empty string is returned.
    """
    if engine == "vosk":
        return transcribe_with_vosk(audio_path, vosk_model_path) or ""
    if engine == "whisper" and whisper_model is not None:
        return transcribe_with_whisper(whisper_model, audio_path) or ""
    raise RuntimeError(f"Unsupported ASR engine: {engine}")


def run_asr(
    in_dir: str, out_dir: str, manifest: str = "testData/synthetic/manifest.csv"
) -> str:
    """Run a simple ASR pass over .wav files and write predictions.

    Args:
        in_dir: Directory containing .wav files to transcribe.
        out_dir: Directory to write `predictions.jsonl` into.
        manifest: Path to a CSV manifest mapping ids to reference text.

    Returns:
        Path to the written predictions file.
    """
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
    """CLI entrypoint for ad-hoc ASR runs.

    Parses CLI arguments and invokes `run_asr`.
    """
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
