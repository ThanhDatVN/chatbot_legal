"""What an agent hands to the answer service before validation."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.generation.validator import DraftClaim
from app.schemas import Decision, RefusalReason


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    model: str | None = None
    requests: int = 0


@dataclass
class Draft:
    decision: Decision
    reason: RefusalReason | None
    claims: list[DraftClaim] = field(default_factory=list)
    unanswered: str | None = None
    layout: str = "grouped"  # grouped: framing line per source; prose: claims as sentences
    usage: Usage = field(default_factory=Usage)
    notes: list[str] = field(default_factory=list)
    verified_chunks: list[str] = field(default_factory=list)  # sources a gray-zone verifier confirmed
