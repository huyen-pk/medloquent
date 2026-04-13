#!/usr/bin/env python3
"""Evaluation component for the synthetic pipeline.

Provides `run_eval(...)` which computes WER and simple medical-term
recall/precision and writes a JSON metrics file.
"""

import argparse
import csv
import glob
import json
import os
from collections import Counter
from collections.abc import Callable
from typing import Any, Dict, List

wer: Callable[[str, str], float] | None
try:
    from jiwer import wer as jiwer_wer

    wer = jiwer_wer
except Exception:
    wer = None


def load_manifest(manifest: str) -> Dict[str, str]:
    """Load a CSV manifest mapping ids to reference text.

    Args:
        manifest: Path to the CSV manifest file.

    Returns:
        Dict mapping record id to reference text. Missing files return
        an empty dict.
    """
    m: Dict[str, str] = {}
    if not os.path.exists(manifest):
        return m
    with open(manifest, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            m[row["id"]] = row.get("text") or ""
    return m


def load_predictions(preds_path: str) -> List[Dict[str, Any]]:
    """Load predictions from a JSONL file.

    Args:
        preds_path: Path to a JSONL file where each line is a JSON object.

    Returns:
        List of parsed JSON objects (dictionaries).
    """
    preds: List[Dict[str, Any]] = []
    if not os.path.exists(preds_path):
        return preds
    with open(preds_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            preds.append(json.loads(line))
    return preds


def resolve_prediction_files(preds_dir: str, preds_file: str) -> List[str]:
    """Resolve prediction files from either a flat or per-sample layout.

    Args:
        preds_dir: Predictions directory passed to the evaluator.
        preds_file: Predictions filename to look for.

    Returns:
        A list of matching prediction file paths.
    """
    direct_path = os.path.join(preds_dir, preds_file)
    if os.path.exists(direct_path):
        return [direct_path]

    root_dir = os.path.dirname(preds_dir)
    step_dir = os.path.basename(preds_dir)
    pattern = os.path.join(root_dir, "*", step_dir, preds_file)
    return sorted(glob.glob(pattern))


def load_terms(terms_path: str) -> List[str]:
    """Load medical terms from a text file, one term per line.

    Returns a list of lowercase terms. Missing files return an empty list.
    """
    if not os.path.exists(terms_path):
        return []

    term_list: List[str] = []
    with open(terms_path, encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if text:
                term_list.append(text.lower())
    return term_list


def simple_wer(ref: str, hyp: str) -> float:
    """Compute a simple word error rate (WER) between reference and hypo.

    This implements a basic Levenshtein edit-distance based WER.

    Args:
        ref: Reference string.
        hyp: Hypothesis string.

    Returns:
        WER as edits / max(1, number of reference words).
    """
    a = ref.split()
    b = hyp.split()
    n = len(a)
    m = len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    edits = dp[n][m]
    return edits / max(1, n)


def score_prediction(ref: str, hyp: str) -> float:
    """Score a single prediction using jiwer.wer if available, else fallback.

    Args:
        ref: Reference string.
        hyp: Hypothesis string.

    Returns:
        WER score as a float.
    """
    if wer is not None:
        return wer(ref, hyp)
    return simple_wer(ref, hyp)


def update_term_counts(
    terms: List[str],
    ref_low: str,
    hyp_low: str,
    term_tp: Counter[str],
    term_fn: Counter[str],
    term_fp: Counter[str],
) -> None:
    """Update per-term true/false positive/negative counters.

    Args:
        terms: List of lowercase terms to check.
        ref_low: Lowercased reference text.
        hyp_low: Lowercased hypothesis text.
        term_tp: Counter for true positives.
        term_fn: Counter for false negatives.
        term_fp: Counter for false positives.
    """
    for term in terms:
        in_ref = term in ref_low
        in_hyp = term in hyp_low
        if in_ref and in_hyp:
            term_tp[term] += 1
        elif in_ref and not in_hyp:
            term_fn[term] += 1
        elif (not in_ref) and in_hyp:
            term_fp[term] += 1


def build_metrics(
    wer_scores: List[float],
    term_tp: Counter[str],
    term_fn: Counter[str],
    term_fp: Counter[str],
) -> Dict[str, Any]:
    """Aggregate WER scores and term counts into a metrics dict.

    Args:
        wer_scores: List of per-sample WER floats.
        term_tp: Counter of true positives per term.
        term_fn: Counter of false negatives per term.
        term_fp: Counter of false positives per term.

    Returns:
        A dictionary containing overall and per-term metrics.
    """
    metrics: Dict[str, Any] = {
        "samples": len(wer_scores),
        "avg_wer": sum(wer_scores) / max(1, len(wer_scores)),
        "term_counts": {
            "tp": sum(term_tp.values()),
            "fn": sum(term_fn.values()),
            "fp": sum(term_fp.values()),
        },
        "per_term": {},
    }

    for term in set(term_tp) | set(term_fn) | set(term_fp):
        tp = term_tp[term]
        fn = term_fn[term]
        fp = term_fp[term]
        precision = tp / (tp + fp) if (tp + fp) > 0 else None
        recall = tp / (tp + fn) if (tp + fn) > 0 else None
        metrics["per_term"][term] = {
            "tp": tp,
            "fn": fn,
            "fp": fp,
            "precision": precision,
            "recall": recall,
        }

    return metrics


def run_eval(
    manifest: str,
    preds_dir: str,
    preds_file: str = "predictions.jsonl",
    terms: str = "synthetic/terms/medical_terms.txt",
    out_file: str = "testData/synthetic/eval_metrics.json",
) -> str:
    """Compute evaluation metrics (WER and term precision/recall).

    Args:
        manifest: Path to CSV manifest mapping ids to reference text.
        preds_dir: Directory containing the predictions file.
        preds_file: Filename of the predictions JSONL inside `preds_dir`.
        terms: Path to a file containing medical terms (one per line).
        out_file: Path to write the JSON metrics file to.

    Returns:
        Path to the written metrics JSON file.
    """
    manifest_map = load_manifest(manifest)
    term_list = load_terms(terms)
    pred_paths = resolve_prediction_files(preds_dir, preds_file)

    wer_scores: List[float] = []
    term_tp: Counter[str] = Counter()
    term_fn: Counter[str] = Counter()
    term_fp: Counter[str] = Counter()

    for preds_path in pred_paths:
        preds = load_predictions(preds_path)
        for r in preds:
            record_id = r.get("id")
            if not isinstance(record_id, str):
                continue
            ref = manifest_map.get(record_id, "")
            prediction = r.get("prediction")
            hyp = prediction if isinstance(prediction, str) else ""
            wer_scores.append(score_prediction(ref, hyp))
            update_term_counts(
                term_list,
                ref.lower(),
                hyp.lower(),
                term_tp,
                term_fn,
                term_fp,
            )

    metrics = build_metrics(wer_scores, term_tp, term_fn, term_fp)

    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    return out_file


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for the evaluator component.

    Parses CLI args and invokes `run_eval`.
    """
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--preds-dir", required=True)
    p.add_argument(
        "--preds-file",
        default="predictions.jsonl",
        help="predictions filename inside --preds-dir",
    )
    p.add_argument(
        "--terms",
        default="synthetic/terms/medical_terms.txt",
        help="medical terms file",
    )
    p.add_argument(
        "--out-file",
        default="testData/synthetic/eval_metrics.json",
        help="metrics output path",
    )
    args = p.parse_args(argv)
    path = run_eval(
        args.manifest,
        args.preds_dir,
        args.preds_file,
        args.terms,
        args.out_file,
    )
    print("Wrote metrics:", path)


if __name__ == "__main__":
    main()
