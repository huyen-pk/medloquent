#!/usr/bin/env python3
"""CLI for the synthetic pipeline components.

Usage examples:
  python synthetic/cli.py extract --outdir testData/synthetic
  python synthetic/cli.py tts --manifest testData/synthetic/manifest.csv
    python synthetic/cli.py augment --in-dir testData/synthetic/audio \
            --out-dir testData/synthetic/audio_aug
    python synthetic/cli.py asr --in-dir testData/synthetic/audio_aug \
            --out-dir testData/synthetic/predictions
    python synthetic/cli.py eval --manifest testData/synthetic/manifest.csv \
            --preds-dir testData/synthetic/predictions
  python synthetic/cli.py run-all
"""

from __future__ import annotations

import argparse
import glob
import os
from typing import List


def find_sample_manifests(root: str) -> List[str]:
    """Find per-sample manifest files under a synthetic output root."""
    pattern = os.path.join(root, "*", "manifest.csv")
    return sorted(glob.glob(pattern))


def find_sample_step_dirs(root: str, step_name: str) -> List[str]:
    """Find per-sample step directories under a synthetic output root."""
    pattern = os.path.join(root, "*", step_name)
    return sorted(path for path in glob.glob(pattern) if os.path.isdir(path))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="synthetic-cli")
    subs = p.add_subparsers(dest="cmd")

    # extract
    e = subs.add_parser("extract", help="Extract transcripts from Synthea/FHIR")
    e.add_argument("--input", "-i", help="Input folder or FHIR JSON file")
    e.add_argument("--outdir", "-o", default="testData/synthetic")
    e.add_argument("--format", choices=("csv", "jsonl", "both"), default="csv")
    e.add_argument("--batch-size", type=int, default=1)

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
    ra = subs.add_parser(
        "run-all", help="Run end-to-end pipeline using sensible defaults"
    )
    ra.add_argument("--out-root", default="testData/synthetic")
    ra.add_argument("--batch-size", type=int, default=1)

    return p


def handle_extract(args: argparse.Namespace) -> int:
    """Run the extraction stage."""
    from synthetic.pipeline.extractor import run_extract

    run_extract(
        getattr(args, "input", None),
        args.outdir,
        args.format,
        args.batch_size,
    )
    return 0


def handle_tts(args: argparse.Namespace) -> int:
    """Run TTS directly or across discovered sample folders."""
    from synthetic.pipeline.tts import run_tts

    sample_manifests = find_sample_manifests(os.path.dirname(args.manifest))
    if sample_manifests:
        step_name = os.path.basename(args.out_dir)
        for sample_manifest in sample_manifests:
            sample_root = os.path.dirname(sample_manifest)
            run_tts(
                sample_manifest,
                os.path.join(sample_root, step_name),
                args.force_fallback,
            )
        return 0

    run_tts(args.manifest, args.out_dir, args.force_fallback)
    return 0


def handle_augment(args: argparse.Namespace) -> int:
    """Run augmentation directly or across discovered sample folders."""
    from synthetic.pipeline.augmenter import run_augment

    sample_inputs = find_sample_step_dirs(
        os.path.dirname(args.in_dir),
        os.path.basename(args.in_dir),
    )
    if sample_inputs:
        step_name = os.path.basename(args.out_dir)
        for sample_input in sample_inputs:
            sample_root = os.path.dirname(sample_input)
            run_augment(
                sample_input,
                os.path.join(sample_root, step_name),
                args.snr,
                args.speeds,
            )
        return 0

    run_augment(args.in_dir, args.out_dir, args.snr, args.speeds)
    return 0


def handle_asr(args: argparse.Namespace) -> int:
    """Run ASR directly or across discovered sample folders."""
    from synthetic.pipeline.asr_runner import run_asr

    sample_inputs = find_sample_step_dirs(
        os.path.dirname(args.in_dir),
        os.path.basename(args.in_dir),
    )
    if sample_inputs:
        step_name = os.path.basename(args.out_dir)
        for sample_input in sample_inputs:
            sample_root = os.path.dirname(sample_input)
            run_asr(
                sample_input,
                os.path.join(sample_root, step_name),
                os.path.join(sample_root, "manifest.csv"),
            )
        return 0

    run_asr(args.in_dir, args.out_dir, args.manifest)
    return 0


def handle_eval(args: argparse.Namespace) -> int:
    """Run evaluation directly or across discovered sample folders."""
    from synthetic.pipeline.evaluator import run_eval

    sample_preds = find_sample_step_dirs(
        os.path.dirname(args.preds_dir),
        os.path.basename(args.preds_dir),
    )
    if sample_preds:
        out_name = os.path.basename(args.out_file)
        for sample_pred_dir in sample_preds:
            sample_root = os.path.dirname(sample_pred_dir)
            run_eval(
                os.path.join(sample_root, "manifest.csv"),
                sample_pred_dir,
                out_file=os.path.join(sample_root, out_name),
            )

    run_eval(args.manifest, args.preds_dir, out_file=args.out_file)
    return 0


def handle_run_all(args: argparse.Namespace) -> int:
    """Run the full synthetic pipeline one sample at a time."""
    from synthetic.pipeline.extractor import run_extract
    from synthetic.pipeline.tts import run_tts
    from synthetic.pipeline.augmenter import run_augment
    from synthetic.pipeline.asr_runner import run_asr
    from synthetic.pipeline.evaluator import run_eval

    root = args.out_root
    rows = run_extract(None, root, batch_size=args.batch_size)
    for row in rows:
        record_id = row.get("id")
        if not isinstance(record_id, str) or not record_id:
            continue

        sample_root = os.path.join(root, record_id)
        sample_manifest = os.path.join(sample_root, "manifest.csv")
        sample_audio = os.path.join(sample_root, "audio")
        sample_audio_aug = os.path.join(sample_root, "audio_aug")
        sample_predictions = os.path.join(sample_root, "predictions")
        sample_metrics = os.path.join(sample_root, "eval_metrics.json")

        run_tts(sample_manifest, sample_audio)
        run_augment(
            sample_audio,
            sample_audio_aug,
            [20.0, 10.0, 0.0],
            [1.0],
        )
        run_asr(sample_audio_aug, sample_predictions, sample_manifest)
        run_eval(
            sample_manifest,
            sample_predictions,
            out_file=sample_metrics,
        )

    run_eval(
        os.path.join(root, "manifest.csv"),
        os.path.join(root, "predictions"),
        out_file=os.path.join(root, "eval_metrics.json"),
    )
    return 0


def main(argv: List[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    cmd = getattr(args, "cmd", None)
    if not isinstance(cmd, str):
        p.print_help()
        return 2

    handlers = {
        "extract": handle_extract,
        "tts": handle_tts,
        "augment": handle_augment,
        "asr": handle_asr,
        "eval": handle_eval,
        "run-all": handle_run_all,
    }
    handler = handlers.get(cmd)
    if handler is not None:
        return handler(args)

    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
