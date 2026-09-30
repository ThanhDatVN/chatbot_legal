"""Reciprocal Rank Fusion: score(d) = Σ 1 / (k + rank_i(d)), ranks start at 1."""

from __future__ import annotations


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    for ranking in rankings:
        seen: set[str] = set()
        for rank, doc_id in enumerate(ranking, start=1):
            if doc_id in seen:
                continue  # duplicates inside one list count once, at their best rank
            seen.add(doc_id)
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(doc_id, len(first_seen))
    # ties are broken by first appearance so the result is deterministic
    return sorted(scores.items(), key=lambda item: (-item[1], first_seen[item[0]]))
