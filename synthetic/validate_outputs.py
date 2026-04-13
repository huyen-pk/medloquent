#!/usr/bin/env python3
"""Simple validator for generated Synthea + synthetic outputs.

Checks for presence of FHIR bundles, a pipeline manifest, and an
eval metrics JSON file. Exits non-zero on failures.
"""
import glob
import json
import os
import sys


def fail(msg: str, code: int = 1) -> None:
    print("ERROR:", msg)
    sys.exit(code)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) < 2:
        print("Usage: validate_outputs.py <synthea_fhir_dir> <synthetic_output_dir>")
        return 2

    fhir_dir, synth_dir = argv[0], argv[1]

    # Find FHIR JSON bundles
    fhir_files = glob.glob(os.path.join(fhir_dir, "*.json"))
    if not fhir_files:
        fail(f"no FHIR JSON files found in {fhir_dir}")
    print(f"Found {len(fhir_files)} FHIR files in {fhir_dir}")

    manifest = os.path.join(synth_dir, "manifest.csv")
    if not os.path.exists(manifest):
        fail(f"manifest missing: {manifest}")
    print("Found manifest:", manifest)

    metrics = os.path.join(synth_dir, "eval_metrics.json")
    if not os.path.exists(metrics):
        print("Warning: eval metrics not found (pipeline may have skipped eval):", metrics)
        return 0

    try:
        with open(metrics, "r", encoding="utf-8") as fh:
            json.load(fh)
        print("Eval metrics present and valid JSON:", metrics)
    except Exception as exc:
        fail(f"invalid eval metrics JSON: {exc}")

    print("Validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
