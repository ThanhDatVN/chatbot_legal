#!/usr/bin/env python3
"""Measure the corpus properties that gate G0.

Three questions decide whether the project's central research claim is testable:

1.  How many legal instruments exist in the corpus in **two or more legal
    states** (an original plus an amending or consolidating instrument)?
    Below the gate threshold, RQ2 and the whole ``TaxTime`` task family cannot
    be validated - see docs/virag-gov/07-risk-analysis.md, R-D02.
2.  What share of documents carry an ``effective_date``?
3.  How are document types and authority tiers distributed?

Version chains are detected two ways, because Vietnamese instruments cite their
targets **by name far more often than by number**:

    "Luật số 149/2025/QH15 ... sửa đổi, bổ sung một số điều của
     Luật Thuế giá trị gia tăng"        <- name reference, no number

A number-only regex misses these entirely, so this tool matches on both the
normalised instrument number and the normalised subject name.

Output is a JSON report; nothing is written into the corpus.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- instrument numbers ----------------------------------------------------
INSTRUMENT_RE = re.compile(
    r"\b(\d{1,4}\s*/\s*(?:19|20)\d{2}\s*/\s*[A-ZĐ][A-ZĐ0-9\-]{1,20})\b"
)
# VBHN numbers frequently omit the year: "67/VBHN-NĐ-BCT", "66/VBHN-TT-BCT".
VBHN_RE = re.compile(r"\b(\d{1,4}\s*/\s*(?:(?:19|20)\d{2}\s*/\s*)?VBHN[A-ZĐ0-9\-]*)\b")

# --- role cues -------------------------------------------------------------
AMEND_CUE = re.compile(r"sửa\s*đổi|bổ\s*sung", re.IGNORECASE)
CONSOLIDATE_CUE = re.compile(r"hợp\s*nhất", re.IGNORECASE)
REPEAL_CUE = re.compile(r"bãi\s*bỏ|thay\s*thế", re.IGNORECASE)

# "... một số điều của X" / "... hợp nhất X"
AFTER_CUA = re.compile(
    r"(?:sửa\s*đổi[^:]{0,40}?của|bổ\s*sung[^:]{0,40}?của)\s+(.+)$", re.IGNORECASE
)
AFTER_HOPNHAT = re.compile(r"hợp\s*nhất\s+(.+)$", re.IGNORECASE)

# A legal subject worth indexing, e.g. "Luật Thuế giá trị gia tăng".
SUBJECT_RE = re.compile(
    r"((?:Bộ\s*luật|Luật|Pháp\s*lệnh|Nghị\s*định|Nghị\s*quyết|Thông\s*tư|Quyết\s*định)"
    r"[^,;.:]{4,120})",
    re.IGNORECASE,
)

TAX_TERMS = (
    "thue",
    "hoa don",
    "gia tri gia tang",
    "thu nhap doanh nghiep",
    "thu nhap ca nhan",
    "tieu thu dac biet",
    "quan ly thue",
    "hai quan",
    "le phi",
    "phi",
)


# The portal leaks a section label into the date field on a large minority of
# records, so "non-empty" is not the same as "is a date".  See D-13.
DATE_RE = re.compile(r"^\s*\d{1,2}[/-]\d{1,2}[/-]\d{4}\s*$|^\s*\d{4}-\d{2}-\d{2}\s*$")


def is_real_date(value: str | None) -> bool:
    return bool(value) and bool(DATE_RE.match(value))


def fold(text: str) -> str:
    """Lowercase, strip Vietnamese diacritics, collapse whitespace."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    stripped = stripped.replace("đ", "d")
    return re.sub(r"\s+", " ", stripped).strip()


def norm_number(number: str) -> str:
    return re.sub(r"\s+", "", number).upper()


def is_tax_related(text: str) -> bool:
    folded = fold(text)
    return any(term in folded for term in TAX_TERMS)


@dataclass
class Doc:
    document_id: str
    instrument_number: str | None
    document_type: str | None
    title: str
    promulgation_date: str | None
    effective_date: str | None
    source: str | None
    shard: str
    role: str = "base"  # base | amending | consolidating
    subject: str = ""  # normalised subject name, for name-based matching
    targets_by_number: set[str] = field(default_factory=set)
    targets_by_name: set[str] = field(default_factory=set)


def extract_subject(title: str, document_type: str | None) -> str:
    """The normalised name of the instrument **itself**, for name matching.

    The subject is only valid when the name after the colon *starts* with a
    legal-type word, i.e. the instrument has a name of its own:

        "Luật số 48/2024/QH15 của Quốc hội: Luật Thuế giá trị gia tăng"
            -> "luat thue gia tri gia tang"                        (own name)

    A document that merely *implements* another one has no name of its own, and
    naming it after its target would make it absorb every link aimed at that
    target:

        "Nghị định số 181/2025/NĐ-CP ...: Quy định chi tiết thi hành một số
         điều của Luật Thuế giá trị gia tăng"
            -> ""   (identity is its number; NOT the VAT Law)

    Getting this wrong inflates the version-chain count, which is the G0 gate.
    """
    if not title:
        return ""
    tail = title.split(":", 1)[1].strip() if ":" in title else title.strip()
    match = SUBJECT_RE.match(tail)  # match, not search: must start with the type
    if match:
        return fold(match.group(1))
    return ""


def extract_targets(title: str) -> tuple[set[str], set[str]]:
    """Instruments this document acts upon, by number and by name."""
    numbers: set[str] = set()
    names: set[str] = set()
    if not title:
        return numbers, names

    for pattern in (INSTRUMENT_RE, VBHN_RE):
        numbers.update(norm_number(m) for m in pattern.findall(title))

    segment = None
    match = AFTER_CUA.search(title)
    if match:
        segment = match.group(1)
    else:
        match = AFTER_HOPNHAT.search(title)
        if match:
            segment = match.group(1)

    if segment:
        # "Luật A, Luật B và Luật C" -> three separate targets.
        for part in re.split(r",|\bvà\b", segment):
            found = SUBJECT_RE.search(part)
            if found:
                names.add(fold(found.group(1)))
    return numbers, names


def classify_role(title: str, document_type: str | None) -> str:
    folded_type = fold(document_type or "")
    if "hop nhat" in folded_type or CONSOLIDATE_CUE.search(title or ""):
        return "consolidating"
    if AMEND_CUE.search(title or ""):
        return "amending"
    return "base"


def load_documents(crawl_root: Path) -> dict[str, Doc]:
    """One record per document_id, taking the richest metadata seen."""
    docs: dict[str, Doc] = {}
    manifests = sorted(crawl_root.glob("**/manifest.jsonl"))

    for manifest in manifests:
        shard = manifest.parent.name
        with manifest.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("record_type") != "source_page":
                    continue
                if record.get("fetch_status") != "fetched":
                    continue

                document_id = record.get("document_id")
                if not document_id:
                    continue

                portal = record.get("metadata") or {}
                title = record.get("title") or portal.get("summary") or ""
                doc = Doc(
                    document_id=document_id,
                    instrument_number=portal.get("instrument_number")
                    or record.get("instrument_number"),
                    document_type=portal.get("document_type"),
                    title=title,
                    promulgation_date=portal.get("promulgation_date"),
                    effective_date=portal.get("effective_date"),
                    source=record.get("source"),
                    shard=shard,
                )
                existing = docs.get(document_id)
                # Prefer the record carrying more metadata.
                if existing is None or (
                    (is_real_date(doc.effective_date) and not is_real_date(existing.effective_date))
                    or (len(doc.title) > len(existing.title))
                ):
                    docs[document_id] = doc

    for doc in docs.values():
        doc.role = classify_role(doc.title, doc.document_type)
        doc.subject = extract_subject(doc.title, doc.document_type)
        doc.targets_by_number, doc.targets_by_name = extract_targets(doc.title)

    return docs


def analyse(docs: dict[str, Doc]) -> dict:
    by_number: dict[str, Doc] = {}
    by_subject: dict[str, list[Doc]] = defaultdict(list)
    for doc in docs.values():
        if doc.instrument_number:
            by_number[norm_number(doc.instrument_number)] = doc
        if doc.subject:
            by_subject[doc.subject].append(doc)

    # base instrument -> set of instruments that amend/consolidate it
    chains: dict[str, set[str]] = defaultdict(set)
    resolved_by_number = 0
    resolved_by_name = 0
    dangling = 0

    for doc in docs.values():
        if doc.role == "base":
            continue
        matched = False

        for number in doc.targets_by_number:
            target = by_number.get(number)
            if target is not None and target.document_id != doc.document_id:
                chains[target.document_id].add(doc.document_id)
                resolved_by_number += 1
                matched = True

        for name in doc.targets_by_name:
            for target in by_subject.get(name, []):
                if target.document_id == doc.document_id:
                    continue
                if target.role != "base":
                    continue
                chains[target.document_id].add(doc.document_id)
                resolved_by_name += 1
                matched = True

        if not matched and (doc.targets_by_number or doc.targets_by_name):
            dangling += 1

    # The same instrument is crawled under several document_ids across runs, so
    # count *distinct instruments* acting on a base, not distinct records.
    def distinct_instruments(base_id: str, derived_ids: set[str]) -> list[str]:
        seen: dict[str, str] = {}
        base_number = norm_number(docs[base_id].instrument_number or "")
        for derived_id in sorted(derived_ids):
            key = norm_number(docs[derived_id].instrument_number or derived_id)
            if key == base_number:  # a record of the base itself
                continue
            seen.setdefault(key, derived_id)
        return list(seen.values())

    # A base instrument is also crawled under several document_ids, so collapse
    # bases by instrument number and union the instruments acting on them.
    by_base_number: dict[str, tuple[str, dict[str, str]]] = {}
    for base_id, derived in chains.items():
        base_key = norm_number(docs[base_id].instrument_number or base_id)
        representative, merged = by_base_number.setdefault(base_key, (base_id, {}))
        for derived_id in distinct_instruments(base_id, derived):
            merged.setdefault(
                norm_number(docs[derived_id].instrument_number or derived_id),
                derived_id,
            )
        # Keep the representative whose record carries a usable date.
        if not is_real_date(docs[representative].effective_date) and is_real_date(
            docs[base_id].effective_date
        ):
            by_base_number[base_key] = (base_id, merged)

    multi_version = {
        representative: list(merged.values())
        for representative, merged in by_base_number.values()
        if merged
    }
    tax_multi_version = {
        base_id: derived
        for base_id, derived in multi_version.items()
        if is_tax_related(docs[base_id].title)
    }

    with_date = sum(1 for d in docs.values() if is_real_date(d.effective_date))
    malformed = sorted(
        {d.effective_date for d in docs.values() if d.effective_date and not is_real_date(d.effective_date)}
    )
    malformed_count = sum(
        1 for d in docs.values() if d.effective_date and not is_real_date(d.effective_date)
    )
    roles = Counter(d.role for d in docs.values())
    types = Counter((d.document_type or "unknown") for d in docs.values())

    return {
        "documents_total": len(docs),
        "effective_date": {
            "present": with_date,
            "missing": len(docs) - with_date,
            "present_pct": round(100 * with_date / max(1, len(docs)), 1),
            "malformed": malformed_count,
            "malformed_values": malformed[:10],
        },
        "roles": dict(roles),
        "document_types": dict(types.most_common()),
        "version_chains": {
            "base_instruments_with_2plus_states": len(multi_version),
            "tax_related_subset": len(tax_multi_version),
            "links_resolved_by_number": resolved_by_number,
            "links_resolved_by_name": resolved_by_name,
            "amending_or_consolidating_with_unresolved_target": dangling,
        },
        "_chains": multi_version,
        "_tax_chains": tax_multi_version,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crawl-root", default=str(REPO_ROOT / "data" / "crawl"))
    parser.add_argument("--out", default=str(REPO_ROOT / "reports" / "g0-corpus-versions.json"))
    parser.add_argument("--gate", type=int, default=60, help="G0 threshold")
    parser.add_argument("--examples", type=int, default=10)
    args = parser.parse_args()

    crawl_root = Path(args.crawl_root)
    if not crawl_root.exists():
        print(f"crawl root not found: {crawl_root}", file=sys.stderr)
        return 2

    docs = load_documents(crawl_root)
    result = analyse(docs)

    result.pop("_chains")
    tax_chains = result.pop("_tax_chains")

    examples = []
    for base_id, derived in sorted(
        tax_chains.items(), key=lambda kv: len(kv[1]), reverse=True
    )[: args.examples]:
        examples.append(
            {
                "base": {
                    "document_id": base_id,
                    "instrument_number": docs[base_id].instrument_number,
                    "title": docs[base_id].title[:160],
                    "effective_date": docs[base_id].effective_date,
                },
                "derived": [
                    {
                        "document_id": d,
                        "instrument_number": docs[d].instrument_number,
                        "role": docs[d].role,
                        "title": docs[d].title[:160],
                    }
                    for d in derived
                ],
            }
        )
    result["examples"] = examples

    gate = result["version_chains"]["base_instruments_with_2plus_states"]
    tax_gate = result["version_chains"]["tax_related_subset"]
    result["gate"] = {
        "threshold": args.gate,
        "observed_all_domains": gate,
        "observed_tax_related": tax_gate,
        "passes_all_domains": gate >= args.gate,
        "passes_tax_related": tax_gate >= args.gate,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"documents                       : {result['documents_total']}")
    print(
        f"effective_date present          : {result['effective_date']['present']}"
        f" ({result['effective_date']['present_pct']}%)"
    )
    print(f"roles                           : {result['roles']}")
    vc = result["version_chains"]
    print(f"base instruments with 2+ states : {vc['base_instruments_with_2plus_states']}")
    print(f"  of which tax-related          : {vc['tax_related_subset']}")
    print(f"  links resolved by number      : {vc['links_resolved_by_number']}")
    print(f"  links resolved by name        : {vc['links_resolved_by_name']}")
    print(f"  unresolved targets            : {vc['amending_or_consolidating_with_unresolved_target']}")
    print(f"G0 threshold {args.gate}: all-domains={'PASS' if gate >= args.gate else 'FAIL'}"
          f"  tax-related={'PASS' if tax_gate >= args.gate else 'FAIL'}")
    print(f"report -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
