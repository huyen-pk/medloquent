#!/usr/bin/env python3
"""Evaluation component for the synthetic pipeline.

Provides `run_eval(...)` which computes WER and simple medical-term
recall/precision and writes a JSON metrics file.
"""

import argparse
import csv
import json
import os
from collections import Counter
from typing import Any, Dict, List, Optional

try:
    from jiwer import wer  # type: ignore
except Exception:
    wer = None


def load_manifest(manifest: str) -> Dict[str, str]:
    m: Dict[str, str] = {}
    if not os.path.exists(manifest):
        return m
    with open(manifest, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            m[row["id"]] = row.get("text", "")
    return m


def load_predictions(preds_path: str) -> List[Dict[str, Any]]:
    preds: List[Dict[str, Any]] = []
    if not os.path.exists(preds_path):
        return preds
    with open(preds_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            preds.append(json.loads(line))
    return preds


def simple_wer(ref: str, hyp: str) -> float:
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


def run_eval(manifest: str, preds_dir: str, preds_file: str = "predictions.jsonl", terms: str = "synthetic/terms/medical_terms.txt", out_file: str = "testData/synthetic/metrics.json") -> str:
    manifest_map = load_manifest(manifest)
    preds_path = os.path.join(preds_dir, preds_file)
    preds = load_predictions(preds_path)

    term_list: List[str] = []
    if os.path.exists(terms):
        with open(terms, encoding="utf-8") as f:
            for l in f:
                t = l.strip()
                if t:
                    term_list.append(t.lower())

    wer_scores: List[float] = []
    term_tp: Counter = Counter()
    term_fn: Counter = Counter()
    term_fp: Counter = Counter()

    for r in preds:
        _id = r.get("id")
        ref = manifest_map.get(_id, "")
        hyp = r.get("prediction", "")
        if wer:
            score = wer(ref, hyp)
        else:
            score = simple_wer(ref, hyp)
        wer_scores.append(score)

        ref_low = ref.lower()
        hyp_low = hyp.lower()
        for t in term_list:
            in_ref = t in ref_low
            in_hyp = t in hyp_low
            if in_ref and in_hyp:
                term_tp[t] += 1
            elif in_ref and not in_hyp:
                term_fn[t] += 1
            elif (not in_ref) and in_hyp:
                term_fp[t] += 1

    metrics: Dict[str, Any] = {
        "samples": len(wer_scores),
        "avg_wer": sum(wer_scores) / max(1, len(wer_scores)),
        "term_counts": {"tp": sum(term_tp.values()), "fn": sum(term_fn.values()), "fp": sum(term_fp.values())},
        "per_term": {},
    }

    for t in set(list(term_tp.keys()) + list(term_fn.keys()) + list(term_fp.keys())):
        tp = term_tp[t]
        fn = term_fn[t]
        fp = term_fp[t]
        prec = tp / (tp + fp) if (tp + fp) > 0 else None
        rec = tp / (tp + fn) if (tp + fn) > 0 else None
        metrics["per_term"][t] = {"tp": tp, "fn": fn, "fp": fp, "precision": prec, "recall": rec}

    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    return out_file


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--preds-dir", required=True)
    p.add_argument("--preds-file", default="predictions.jsonl", help="predictions filename inside --preds-dir")
    p.add_argument("--terms", default="synthetic/terms/medical_terms.txt", help="medical terms file")
    p.add_argument("--out-file", default="testData/synthetic/metrics.json", help="metrics output path")
    args = p.parse_args(argv)
    path = run_eval(args.manifest, args.preds_dir, args.preds_file, args.terms, args.out_file)
    print("Wrote metrics:", path)


if __name__ == "__main__":
    main()
