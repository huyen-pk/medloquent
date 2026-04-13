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
from itertools import cycle
from typing import Any, Dict, List, Optional


def extract_text_from_narrative(text_field: Any) -> Optional[str]:
    """Extract text from a FHIR narrative-like field.

    The `text_field` may be a dict with keys like `div` or `status`, or a
    plain string. Returns the first found textual value or `None`.

    Args:
        text_field: Value to inspect for narrative text.

    Returns:
        Extracted text string or `None` if none found.
    """
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
    """Attempt to extract human-readable text from common resource fields.

    Looks through a set of known keys (note, narrative, summary, comment,
    valueString, description) and returns the first text found.

    Args:
        res: Resource dictionary to inspect.

    Returns:
        Extracted text string or `None` if none found.
    """
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
    """Extract a best-effort text string from a FHIR resource dict.

    Checks narrative fields, common textual fields, and Observation
    `valueString` as a fallback.

    Args:
        res: Resource dictionary to extract from.

    Returns:
        Extracted text string or `None`.
    """
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
    """Append a standardized row dict containing extracted text.

    Args:
        rows: List to append the row to.
        text: Extracted text content.
        source: Source identifier (e.g., filename) for provenance.
    """
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
    """Extract rows from a parsed JSON object or bundle.

    If `data` is a FHIR Bundle, each `entry.resource` is inspected; otherwise
    `data` is treated as a single resource.

    Args:
        data: Parsed JSON data (resource or bundle).
        source: Source identifier for provenance.
        rows: List to append extracted rows to.
    """
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
    """Load a JSON file and append any extracted rows to `rows`.

    Args:
        path: Path to the JSON file.
        rows: List to append extracted rows to.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    append_rows_from_data(data, path, rows)


def process_input_path(input_path: str, rows: List[Dict[str, Any]]) -> None:
    """Process either a single JSON file or a directory of JSON files.

    Non-JSON files are skipped; parse errors are reported to stderr.

    Args:
        input_path: File or directory path to process.
        rows: List to append extracted rows to.
    """
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


def demo_rows(batch_size: int = 1) -> List[Dict[str, Any]]:
    """Return deterministic example rows for demo/testing.

    This is used as a fallback when no input data yields extracted rows.

    Args:
        batch_size: Number of demo rows to generate.

    Returns:
        List of demo row dictionaries.
    """
    templates = [
        {
            "text": (
                "Patient John Doe, age 45, presented with chest pain "
                "and shortness of breath."
            ),
            "metadata": {
                "age": 45,
                "gender": "M",
                "condition": "chest pain",
                "source": "demo",
            },
        },
        {
            "text": (
                "Patient Jane Smith, age 62, reported dizziness, "
                "headache, and intermittent blurred vision."
            ),
            "metadata": {
                "age": 62,
                "gender": "F",
                "condition": "dizziness",
                "source": "demo",
            },
        },
        {
            "text": (
                "Patient Alex Johnson, age 29, arrived with fever, "
                "productive cough, and mild dehydration."
            ),
            "metadata": {
                "age": 29,
                "gender": "X",
                "condition": "fever",
                "source": "demo",
            },
        },
    ]
    rows: List[Dict[str, Any]] = []
    safe_batch_size = max(1, batch_size)
    for index, template in zip(range(safe_batch_size), cycle(templates)):
        metadata = template.get("metadata", {})
        rows.append(
            {
                "id": f"sample-{index + 1}",
                "text": template["text"],
                "metadata": (
                    dict(metadata) if isinstance(metadata, dict) else {}
                ),
            }
        )
    return rows


def write_sample_outputs(outdir: str, rows: List[Dict[str, Any]]) -> None:
    """Create per-sample directories with text and metadata files.

    Args:
        outdir: Root output directory.
        rows: Extracted rows containing `id`, `text`, and `metadata`.
    """
    for r in rows:
        rid = r.get("id")
        if not rid:
            continue
        sample_dir = os.path.join(outdir, rid)
        os.makedirs(sample_dir, exist_ok=True)
        text_path = os.path.join(sample_dir, "text.txt")
        try:
            with open(text_path, "w", encoding="utf-8") as fh:
                fh.write(r.get("text", ""))
        except Exception:
            pass
        meta_path = os.path.join(sample_dir, "metadata.json")
        try:
            with open(meta_path, "w", encoding="utf-8") as fh:
                json.dump(
                    r.get("metadata", {}),
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass
        manifest_path = os.path.join(sample_dir, "manifest.csv")
        try:
            with open(
                manifest_path,
                "w",
                newline="",
                encoding="utf-8",
            ) as fh:
                writer = csv.DictWriter(
                    fh,
                    fieldnames=["id", "text", "metadata"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "id": rid,
                        "text": r.get("text", ""),
                        "metadata": json.dumps(
                            r.get("metadata", {}),
                            ensure_ascii=False,
                        ),
                    }
                )
        except Exception:
            pass


def write_manifest(
    outdir: str, rows: List[Dict[str, Any]], fmt: str = "csv"
) -> None:
    """Write extracted rows to manifest files in CSV and/or JSONL formats.

    Args:
        outdir: Output directory to create and write files into.
        rows: List of row dicts with keys `id`, `text`, and `metadata`.
        fmt: One of "csv", "jsonl", or "both" to control outputs.
    """
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
    # Create per-sample files for downstream steps
    write_sample_outputs(outdir, rows)


def run_extract(
    input_path: Optional[str],
    outdir: str = "testData/synthetic",
    fmt: str = "csv",
    batch_size: int = 1,
) -> List[Dict[str, Any]]:
    """High-level extraction entrypoint.

    Processes `input_path` (file or directory), writes a manifest to
    `outdir`, and returns the list of extracted rows. If no rows are
    extracted a demo row set is used instead.

    Args:
        input_path: Optional path to a JSON file or directory to process.
        outdir: Directory to write manifest files into.
        fmt: Output format choice (csv/jsonl/both).
        batch_size: Number of demo rows to generate when no input is provided.

    Returns:
        List of extracted row dictionaries.
    """
    rows: List[Dict[str, Any]] = []
    if input_path:
        process_input_path(input_path, rows)

    if not rows:
        rows = demo_rows(batch_size)

    write_manifest(outdir, rows, fmt)
    return rows


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entrypoint for the extractor component.

    Parses CLI args and invokes `run_extract`.
    """
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
    p.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="number of demo samples to generate when no input is provided",
    )
    args = p.parse_args(argv)
    run_extract(args.input, args.outdir, args.format, args.batch_size)


if __name__ == "__main__":
    main()
