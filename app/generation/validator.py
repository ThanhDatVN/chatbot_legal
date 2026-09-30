"""Citation validation: every factual claim must be backed by evidence fetched in this request.

Checks, per claim:
  1. each cited chunk was opened with get_source in this request;
  2. each cited chunk is eligible for statements about current law;
  3. the claim's quote occurs verbatim (whitespace/case-insensitive) in a cited source;
  4. every number in the claim appears in the cited sources or their article labels;
  5. at least one cited chunk passed the retrieval relevance threshold.
Claims that fail are removed and reported; they never reach the user.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.schemas import SourceEvidence

NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


@dataclass
class DraftClaim:
    text: str
    chunk_ids: list[str]
    quote: str


@dataclass
class ValidationReport:
    kept: list[DraftClaim] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)


def loose(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[“”\"'«»]", "", text)
    return " ".join(text.split())


def numbers(text: str) -> set[str]:
    return {n.replace(".", "").replace(",", "").lstrip("0") or "0" for n in NUMBER_RE.findall(text)}


def validate_claims(claims: list[DraftClaim], fetched: dict[str, SourceEvidence], scores: dict[str, float],
                    threshold: float) -> ValidationReport:
    report = ValidationReport()
    for claim in claims:
        problem = None
        cited = [fetched.get(cid) for cid in claim.chunk_ids]
        if not claim.chunk_ids:
            problem = "no_citation"
        elif any(src is None for src in cited):
            problem = "citation_not_fetched"
        elif not all(src.eligible for src in cited):
            problem = "citation_not_current"
        elif not claim.quote.strip() or not any(loose(claim.quote) in loose(src.text) for src in cited):
            problem = "quote_not_in_source"
        else:
            allowed = set().union(*(numbers(src.text + " " + " ".join(src.section_path) + " " + src.document_number)
                                    for src in cited))
            unknown = numbers(claim.text) - allowed
            if unknown:
                problem = f"unsupported_numbers:{','.join(sorted(unknown))}"
            elif max(scores.get(cid, 0.0) for cid in claim.chunk_ids) < threshold:
                problem = "below_relevance_threshold"
        if problem:
            report.dropped.append({"claim": claim.text[:200], "chunk_ids": claim.chunk_ids, "problem": problem})
        else:
            report.kept.append(claim)
    return report
