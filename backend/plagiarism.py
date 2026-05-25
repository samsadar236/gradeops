"""Plagiarism flagging via sentence-embedding similarity.

The brief calls for flagging "highly similar logic structures across
papers." We do this on the OCR transcripts (not the raw images) because:
  - handwriting varies even when reasoning is copied, so image similarity
    is the wrong signal
  - transcripts capture the LOGIC the student used
  - embedding similarity catches paraphrases that string matching misses

This is a background worker. It is intentionally simple: O(n^2) cosine
similarity, with a threshold check. For real exam scale (thousands of
papers per exam) you would FAISS-index the embeddings.
"""
from __future__ import annotations

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from .config import settings


_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def find_similar_pairs(
    transcripts: list[tuple[int, str]],
    threshold: float | None = None,
) -> list[tuple[int, int, float]]:
    """Return all (crop_a_id, crop_b_id, similarity) tuples above the threshold.

    transcripts: list of (crop_id, transcript_text) tuples.
    """
    if len(transcripts) < 2:
        return []

    threshold = threshold if threshold is not None else settings.plagiarism_threshold
    ids = [t[0] for t in transcripts]
    texts = [t[1] or "" for t in transcripts]

    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    sim = cosine_similarity(embeddings)
    pairs: list[tuple[int, int, float]] = []
    n = len(ids)
    for i in range(n):
        for j in range(i + 1, n):
            s = float(sim[i, j])
            if s >= threshold:
                # Always store with a < b for the uniqueness constraint
                a, b = sorted((ids[i], ids[j]))
                pairs.append((a, b, s))
    pairs.sort(key=lambda p: p[2], reverse=True)
    return pairs
