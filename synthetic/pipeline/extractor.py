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


def extract_text_from_narrative(text_field: Any) -> Optional[str]:
    if isinstance(text_field, dict):
        div = text_field.get("div")
        if isinstance(div, str):
            return div
        status = text_field.get("status")
        if isinstance(status, str):
            return status
    if isinstance(text_field, str):
        return text_field
    return None


def extract_text_from_common_fields(res: Dict[str, Any]) -> Optional[str]:
    for key in (
        "note",
        "narrative",
        "summary",
        "comment",
        "valueString",
        "description",
    ):
        value = res.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict):
                first_text = first.get("text")
                if isinstance(first_text, str):
                    return first_text
            if isinstance(first, str):
                return first
    return None


def extract_text_from_resource(res: Dict[str, Any]) -> Optional[str]:
    if not isinstance(res, dict):
        return None
    narrative = extract_text_from_narrative(res.get("text"))
    if narrative is not None:
        return narrative

    common_text = extract_text_from_common_fields(res)
    if common_text is not None:
        return common_text

    if res.get("resourceType") == "Observation":
        value_string = res.get("valueString")
        if isinstance(value_string, str):
            return value_string
    return None


def append_text_row(rows: List[Dict[str, Any]], text: str, source: str) -> None:
    rows.append(
        {
            "id": str(uuid.uuid4()),
            "text": text,
            "metadata": {"source": source},
        }
    )


def append_rows_from_data(
    data: Any, source: str, rows: List[Dict[str, Any]]
) -> None:
    if isinstance(data, dict) and data.get("resourceType") == "Bundle":
        for entry in data.get("entry", []):
            res = entry.get("resource", {})
            text = extract_text_from_resource(res)
            if text:
                append_text_row(rows, text, source)
        return

    text = extract_text_from_resource(data)
    if text:
        append_text_row(rows, text, source)


def process_json_file(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    append_rows_from_data(data, path, rows)


def process_input_path(input_path: str, rows: List[Dict[str, Any]]) -> None:
    if os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for filename in files:
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(root, filename)
                try:
                    process_json_file(path, rows)
                except Exception as exc:
                    print(
                        "warn: failed to parse",
                        path,
                        exc,
                        file=sys.stderr,
                    )
        return

    try:
        process_json_file(input_path, rows)
    except Exception as exc:
        print("warn: could not read input", exc, file=sys.stderr)


def demo_rows() -> List[Dict[str, Any]]:
    return [
        {
            "id": "sample-1",
            "text": (
                "Patient John Doe, age 45, presented with chest pain "
                "and shortness of breath."
            ),
            "metadata": {
                "age": 45,
                "gender": "M",
                "condition": "chest pain",
            },
        }
    ]


def write_manifest(
    outdir: str, rows: List[Dict[str, Any]], fmt: str = "csv"
) -> None:
    os.makedirs(outdir, exist_ok=True)
    if fmt in ("csv", "both"):
        csv_path = os.path.join(outdir, "manifest.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "text", "metadata"])
            writer.writeheader()
            for r in rows:
                writer.writerow(
                    {
                        "id": r["id"],
                        "text": r["text"],
                        "metadata": json.dumps(
                            r.get("metadata", {}), ensure_ascii=False
                        ),
                    }
                )
        print("Wrote:", csv_path)
    if fmt in ("jsonl", "both"):
        jpath = os.path.join(outdir, "transcripts.jsonl")
        with open(jpath, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print("Wrote:", jpath)


def run_extract(
    input_path: Optional[str],
    outdir: str = "testData/synthetic",
    fmt: str = "csv",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if input_path:
        process_input_path(input_path, rows)

    if not rows:
        rows = demo_rows()

    write_manifest(outdir, rows, fmt)
    return rows


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--input",
        "-i",
        help="Input Synthea folder or FHIR JSON file (optional)",
    )
    p.add_argument(
        "--outdir",
        "-o",
        default="testData/synthetic",
        help="Output dir (default: testData/synthetic)",
    )
    p.add_argument("--format", choices=("csv", "jsonl", "both"), default="csv")
    args = p.parse_args(argv)
    run_extract(args.input, args.outdir, args.format)


if __name__ == "__main__":
    main()
