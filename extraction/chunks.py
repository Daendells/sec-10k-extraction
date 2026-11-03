"""Split a filing into overlapping chunks and pick the ones that hold the financial statements."""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

QUERIES = [
    "consolidated statements of operations total net revenue net income",
    "consolidated statements of income revenues net earnings",
    "earnings per share diluted",
    "consolidated balance sheets total assets total stockholders equity",
    "cash and cash equivalents balance sheet",
]


def chunk(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    step = size - overlap
    return [text[i:i + size] for i in range(0, max(len(text) - overlap, 1), step)]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def top_chunks(chunks: list[str], queries: list[str] = QUERIES, k: int = 8, c: int = 60) -> list[str]:
    """Rank chunks for each query with BM25, fuse the rankings (reciprocal rank), return the top k in document order."""
    bm25 = BM25Okapi([_tokens(ch) for ch in chunks])
    fused: dict[int, float] = {}
    for query in queries:
        scores = bm25.get_scores(_tokens(query))
        matching = [i for i in range(len(chunks)) if scores[i] > 0]  # a chunk sharing no query word gets no vote
        for rank, idx in enumerate(sorted(matching, key=lambda i: -scores[i])[:50], start=1):
            fused[idx] = fused.get(idx, 0.0) + 1 / (c + rank)
    best = sorted(fused, key=lambda i: -fused[i])[:k]
    return [chunks[i] for i in sorted(best)]
