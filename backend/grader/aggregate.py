"""Aggregate scores across multiple grading passes.

We deliberately keep median, max, AND std-dev:
  - median is the "fair" provisional score (less sensitive to outliers)
  - max is the conservative-in-student's-favor choice (Paper 2's primary)
  - std-dev is the routing signal for the review queue (highest variance first)

Paper 2 found no reliable threshold for fully-automated low-confidence
skipping. So std-dev is used here as a SORTING signal, not a SKIP signal —
every grade still goes to a human, but high-std-dev ones go to the front
of the queue.
"""
from __future__ import annotations

import statistics


def aggregate_scores(passes: list[dict]) -> dict:
    """Given N pass dicts (each with 'score'), produce summary stats."""
    scores = [float(p.get("score", 0.0)) for p in passes if "score" in p]
    if not scores:
        return {
            "median": 0.0, "max_score": 0.0, "min_score": 0.0,
            "std_dev": 0.0, "n_passes": 0,
        }
    return {
        "median": float(statistics.median(scores)),
        "max_score": float(max(scores)),
        "min_score": float(min(scores)),
        "std_dev": float(statistics.pstdev(scores)) if len(scores) > 1 else 0.0,
        "n_passes": len(scores),
    }
