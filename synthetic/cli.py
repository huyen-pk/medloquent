#!/usr/bin/env python3
"""CLI for the synthetic pipeline components.

Usage examples:
  python synthetic/cli.py extract --outdir testData/synthetic
  python synthetic/cli.py tts --manifest testData/synthetic/manifest.csv
  python synthetic/cli.py augment --in-dir testData/synthetic/audio --out-dir testData/synthetic/audio_aug
  python synthetic/cli.py asr --in-dir testData/synthetic/audio_aug --out-dir testData/synthetic/predictions
  python synthetic/cli.py eval --manifest testData/synthetic/manifest.csv --preds-dir testData/synthetic/predictions
  python synthetic/cli.py run-all
"""

from __future__ import annotations

import argparse
import sys
from typing import List


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="synthetic-cli")
    subs = p.add_subparsers(dest="cmd")

    # extract
    e = subs.add_parser("extract", help="Extract transcripts from Synthea/FHIR")
    e.add_argument("--input", "-i", help="Input folder or FHIR JSON file")
    e.add_argument("--outdir", "-o", default="testData/synthetic")
    e.add_argument("--format", choices=("csv", "jsonl", "both"), default="csv")

    # tts
    t = subs.add_parser("tts", help="Run TTS to generate audio")
    t.add_argument("--manifest", default="testData/synthetic/manifest.csv")
    t.add_argument("--out-dir", default="testData/synthetic/audio")
    t.add_argument("--force-fallback", action="store_true")

    # augment
    a = subs.add_parser("augment", help="Create augmented audio variants")
    a.add_argument("--in-dir", required=True)
    a.add_argument("--out-dir", required=True)
    a.add_argument("--snr", nargs="*", type=float, default=[20.0, 10.0, 0.0])
    a.add_argument("--speeds", nargs="*", type=float, default=[1.0])

    # asr
    r = subs.add_parser("asr", help="Run ASR on audio and produce predictions")
    r.add_argument("--in-dir", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--manifest", default="testData/synthetic/manifest.csv")

    # eval
    v = subs.add_parser("eval", help="Evaluate predictions against manifest")
    v.add_argument("--manifest", required=True)
    v.add_argument("--preds-dir", required=True)
    v.add_argument("--out-file", default="testData/synthetic/metrics.json")

    # run-all
    ra = subs.add_parser("run-all", help="Run end-to-end pipeline using sensible defaults")
    ra.add_argument("--out-root", default="testData/synthetic")

    return p


def main(argv: List[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    cmd = getattr(args, "cmd", None)

    # lazy import components to keep CLI lightweight if not used
    if cmd == "extract":
        from synthetic.pipeline.extractor import run_extract

        run_extract(getattr(args, "input", None), args.outdir, args.format)
        return 0
    if cmd == "tts":
        from synthetic.pipeline.tts import run_tts

        run_tts(args.manifest, args.out_dir, args.force_fallback)
        return 0
    if cmd == "augment":
        from synthetic.pipeline.augmenter import run_augment

        run_augment(args.in_dir, args.out_dir, args.snr, args.speeds)
        return 0
    if cmd == "asr":
        from synthetic.pipeline.asr_runner import run_asr

        run_asr(args.in_dir, args.out_dir, args.manifest)
        return 0
    if cmd == "eval":
        from synthetic.pipeline.evaluator import run_eval

        run_eval(args.manifest, args.preds_dir, out_file=args.out_file)
        return 0
    if cmd == "run-all":
        from synthetic.pipeline.extractor import run_extract
        from synthetic.pipeline.tts import run_tts
        from synthetic.pipeline.augmenter import run_augment
        from synthetic.pipeline.asr_runner import run_asr
        from synthetic.pipeline.evaluator import run_eval

        root = args.out_root
        run_extract(None, root)
        run_tts(f"{root}/manifest.csv", f"{root}/audio")
        run_augment(f"{root}/audio", f"{root}/audio_aug", [20.0, 10.0, 0.0], [1.0])
        run_asr(f"{root}/audio_aug", f"{root}/predictions", f"{root}/manifest.csv")
        run_eval(f"{root}/manifest.csv", f"{root}/predictions", out_file=f"{root}/metrics.json")
        return 0

    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
