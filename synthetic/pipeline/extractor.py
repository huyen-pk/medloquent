#!/usr/bin/env python3
"""Extraction component for the synthetic pipeline.

Provides `run_extract(...)` which implements the previous extractor script
but in a reusable function-oriented component.
"""

import argparse
import csv
import json
import os
import sys
import uuid
from typing import Any, Dict, List, Optional


def extract_text_from_resource(res: Dict[str, Any]) -> Optional[str]:
    if not isinstance(res, dict):
        return None
    # Common FHIR narrative
    if "text" in res:
        t = res["text"]
        if isinstance(t, dict):
            if "div" in t and isinstance(t["div"], str):
                return t["div"]
            if "status" in t and isinstance(t["status"], str):
                return t["status"]
        if isinstance(t, str):
            return t
    # Common fields
    for k in ("note", "narrative", "summary", "comment", "valueString", "description"):
        if k in res:
            v = res[k]
            if isinstance(v, str):
                return v
            if isinstance(v, list) and v:
                first = v[0]
                if isinstance(first, dict) and "text" in first:
                    return first["text"]
                if isinstance(first, str):
                    return first
    # Observation common value
    if res.get("resourceType") == "Observation" and "valueString" in res:
        return res["valueString"]
    return None


def write_manifest(outdir: str, rows: List[Dict[str, Any]], fmt: str = "csv") -> None:
    os.makedirs(outdir, exist_ok=True)
    if fmt in ("csv", "both"):
        csv_path = os.path.join(outdir, "manifest.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "text", "metadata"])
            writer.writeheader()
            for r in rows:
                writer.writerow({"id": r["id"], "text": r["text"], "metadata": json.dumps(r.get("metadata", {}), ensure_ascii=False)})
        print("Wrote:", csv_path)
    if fmt in ("jsonl", "both"):
        jpath = os.path.join(outdir, "transcripts.jsonl")
        with open(jpath, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print("Wrote:", jpath)


def run_extract(input_path: Optional[str], outdir: str = "testData/synthetic", fmt: str = "csv") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if input_path:
        if os.path.isdir(input_path):
            for root, _, files in os.walk(input_path):
                for fn in files:
                    if fn.endswith(".json"):
                        path = os.path.join(root, fn)
                        try:
                            with open(path, "r", encoding="utf-8") as fh:
                                data = json.load(fh)
                                # Handle bundles
                                if isinstance(data, dict) and data.get("resourceType") == "Bundle":
                                    for e in data.get("entry", []):
                                        res = e.get("resource", {})
                                        t = extract_text_from_resource(res)
                                        if t:
                                            rows.append({"id": str(uuid.uuid4()), "text": t, "metadata": {"source": path}})
                                else:
                                    t = extract_text_from_resource(data)
                                    if t:
                                        rows.append({"id": str(uuid.uuid4()), "text": t, "metadata": {"source": path}})
                        except Exception as e:
                            print("warn: failed to parse", path, e, file=sys.stderr)
        else:
            try:
                with open(input_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, dict) and data.get("resourceType") == "Bundle":
                        for e in data.get("entry", []):
                            res = e.get("resource", {})
                            t = extract_text_from_resource(res)
                            if t:
                                rows.append({"id": str(uuid.uuid4()), "text": t, "metadata": {"source": input_path}})
                    else:
                        t = extract_text_from_resource(data)
                        if t:
                            rows.append({"id": str(uuid.uuid4()), "text": t, "metadata": {"source": input_path}})
            except Exception as e:
                print("warn: could not read input", e, file=sys.stderr)

    if not rows:
        # demo single sample
        rows = [{"id": "sample-1", "text": "Patient John Doe, age 45, presented with chest pain and shortness of breath.", "metadata": {"age": 45, "gender": "M", "condition": "chest pain"}}]

    write_manifest(outdir, rows, fmt)
    return rows


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", "-i", help="Input Synthea folder or FHIR JSON file (optional)")
    p.add_argument("--outdir", "-o", default="testData/synthetic", help="Output dir (default: testData/synthetic)")
    p.add_argument("--format", choices=("csv", "jsonl", "both"), default="csv")
    args = p.parse_args(argv)
    run_extract(args.input, args.outdir, args.format)


if __name__ == "__main__":
    main()
