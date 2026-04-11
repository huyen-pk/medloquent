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
from typing import Dict, List


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
    paths: List[str] = glob.glob(os.path.join(in_dir, "**", "*.wav"), recursive=True)
    return sorted(paths)


def run_asr(in_dir: str, out_dir: str, manifest: str = "testData/synthetic/manifest.csv") -> str:
    os.makedirs(out_dir, exist_ok=True)
    manifest_map = load_manifest(manifest)

    audio_files = find_audio_files(in_dir)
    out_path = os.path.join(out_dir, "predictions.jsonl")
    with open(out_path, "w", encoding="utf-8") as out:
        for pth in audio_files:
            basename = os.path.splitext(os.path.basename(pth))[0]
            _id = basename.split("_")[0]
            ref = manifest_map.get(_id, "")
            # For smoke tests, emit the reference as the prediction
            pred = ref
            rec = {"id": _id, "audio": pth, "prediction": pred}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out_path


def main(argv: List[str] = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--in-dir", required=True, help="augmented audio dir (e.g., testData/synthetic/audio_aug)")
    p.add_argument("--out-dir", required=True, help="predictions out dir")
    p.add_argument("--manifest", default="testData/synthetic/manifest.csv", help="manifest with references")
    args = p.parse_args(argv)
    path = run_asr(args.in_dir, args.out_dir, args.manifest)
    print("Wrote predictions:", path)


if __name__ == "__main__":
    main()
