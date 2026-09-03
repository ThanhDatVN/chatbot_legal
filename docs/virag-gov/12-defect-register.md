# 12 — Defect Register

> Tracked defects in the `virag/` scaffold, established by code review on
> 2026-09-03 and verified line by line against the source.
>
> **Every defect here must be closed before the module it affects is promoted
> from "reference scaffold" to working code.** The register is the gate.

**Status legend:** ⬜ open · 🟨 in progress · ✅ closed · ⏸️ deferred with reason

---

## 1. Summary

| Severity | Count | Meaning |
|----------|------:|---------|
| 🔴 Blocker | 6 | Produces legally wrong output or invalidates evidence |
| 🟠 Major | 6 | Breaks a documented promise of the design |
| 🟡 Minor | 4 | Correctness or consistency issue with bounded impact |

**Total: 17 defects. 8 closed (D-02, D-09, D-12, D-13, D-14, D-15, D-16, D-17).**

D-01…D-12 were raised by code review on 2026-09-03.
**D-13…D-16 were raised by the G0 measurement run** — see
[`reports/G0-REPORT.md`](../../reports/G0-REPORT.md). D-17 is the environment
defect, now fixed.

---

## 2. Register

### 🔴 D-01 — Manifest reader has no reviewer-promotion gate

| | |
|--|--|
| **Location** | `virag/ingest/manifest.py:97` |
| **Status** | ⬜ open |
| **Severity** | 🔴 Blocker |

**Observed.** The reader filters only on `fetch_status == "fetched"`. It never
inspects `quarantine_status`, which is `"pending_human_review"` on every crawled
record.

**Why it matters.** The crawler's own manifests carry the notice:

> "Không index vào RAG trước khi reviewer xác nhận số hiệu, ngày, checksum và
> quan hệ hiệu lực."
> *(Do not index into RAG before a reviewer has confirmed the number, date,
> checksum and validity relations.)*

The current code ingests unreviewed quarantine material straight into Silver and
Gold, violating the acquisition design's central control.

**Fix.** Add an explicit promotion state to the ingest path. Only records marked
reviewed may enter Gold; everything else is visible in Silver but excluded from
the index, and the count of each state is reported in
`reports/data-quality.json`.

---

### ✅ D-02 — Wrong artifact hash bound to the document

| | |
|--|--|
| **Location** | `virag/ingest/manifest.py` |
| **Status** | ✅ **closed 2026-09-03** |
| **Severity** | 🔴 Blocker |

**Observed.** `sha256=record.get("response_sha256")` is read from the
`source_page` record, so the stored hash is the **HTML portal page**. The
`official_attachment` records carry their own `response_sha256` for the **signed
PDF** — the authoritative artifact — and that hash is discarded.

**Why it matters.** Citations claim to be traceable to a checksummed copy of the
authoritative source. As written, they are traceable to a checksum of a web page
that may change with any portal redesign.

**Fix applied.** `DocumentMeta.artifact_sha256` now carries the signed
attachment's hash, bound in `load_manifest` from the `official_attachment`
record; `sha256` keeps the page hash as provenance. Verified on
`shard-0001`: the two hashes are distinct and correctly sourced.
Regression: `tests/test_virag_manifest.py::TestArtifactHashBinding`.

---

### 🔴 D-03 — Parent truncation deletes the retrieved clause

| | |
|--|--|
| **Location** | `virag/ingest/chunking.py:130` |
| **Status** | ⬜ open |
| **Severity** | 🔴 Blocker |

**Observed.** `text=article_text[: settings.parent_max_tokens * 8]`

Two distinct faults in one line:

1. **Unit mismatch.** `parent_max_tokens` is a **token** budget; multiplying by
   8 and slicing produces a **character** bound. The units are not
   interchangeable.
2. **Head slice discards the tail.** A Khoản near the end of a long Điều is cut
   out of the parent text — so **parent expansion removes the very clause that
   retrieval selected**, which is the exact opposite of its purpose (ADR-002).

**Why it matters.** The model is handed context that does not contain the
provision it is supposed to be reasoning about, while the citation label still
points at that provision.

**Fix.** Window the parent around the retrieved child rather than slicing from
the head, and compute the bound in tokens.

---

### 🔴 D-04 — Conflict "winner" presented as adjudication

| | |
|--|--|
| **Location** | `virag/legal/conflict.py` |
| **Status** | ⬜ open |
| **Severity** | 🔴 Blocker |

**Observed.** Conflict detection rests on unvalidated lexical Jaccard overlap,
hand-written marker phrases and date comparison. `_mentions_amendment` merely
checks whether an instrument number appears near an amendment cue in the text.

**Why it matters.** ADR-009 promises that a decision is legal adjudication
carrying a named rule. The current heuristics do not support that claim.

**Fix.** Until relations are extracted and **accepted by a reviewer**, the engine
must emit **proposals**, not decisions: `winner_chunk_id` stays `None` and the
UI shows a 🔴 "needs expert review" light. Only conflicts backed by an accepted
`AMENDS`/`REPLACES`/`REPEALS` relation, or by a temporal/hierarchical fact, may
be presented as resolved.

---

### 🟠 D-05 — Transaction-time query not implemented

| | |
|--|--|
| **Location** | `virag/store/db.py:433` |
| **Status** | ⬜ open |
| **Severity** | 🟠 Major |

**Observed.** `version_as_of(engine, document_id, as_of)` filters on
`effective_from` / `effective_to` only. The table stores `ingested_at` and
`superseded_at`, but nothing queries them.

**Why it matters.** ADR-010 and document 04 §5 promise the audit query *"what did
the system know on date X?"*. That query cannot currently be expressed.

**Fix.** Add an `as_known_at` parameter; filter valid time **and** transaction
time. Add a regression test that reconstructs a historical answer.

---

### 🟠 D-06 — Consolidated documents hard-coded to tier 7

| | |
|--|--|
| **Location** | `virag/legal/authority.py:113` |
| **Status** | ⬜ open |
| **Severity** | 🟠 Major |

**Observed.** Any instrument number matching `VBHN` returns tier 7
unconditionally.

**Why it matters.** Document 06 §7.4 states a Consolidated Document must inherit
the authority of the instrument it consolidates. A consolidated **Law** is
currently ranked as a Circular — five tiers too low — which the authority
component of the score then acts on.

**Impact is not hypothetical:** 141 of 698 documents (20.2%) are VBHN.

**Fix.** Parse the organ code after the `VBHN-` prefix and map it to the
underlying tier; fall back to tier 7 only when the code is unrecognised.

---

### 🟠 D-07 — Clause status copied from document metadata

| | |
|--|--|
| **Location** | `virag/ingest/chunking.py` (`legal_status=meta.legal_status`) |
| **Status** | ⬜ open |
| **Severity** | 🟠 Major |

**Observed.** Every chunk inherits the document-level `legal_status`, which is
`UNKNOWN` for all documents at ingest time.

**Why it matters.** ADR-011 is entirely about clause-level status. As written,
the field exists but carries no information, so partial-amendment handling
(conflict type 5.4) cannot function.

**Fix.** Derive status per clause from accepted amendment relations, with a
recorded granularity marker when the pointer cannot be resolved below Article
level.

---

### 🟠 D-08 — Temporal midpoint inference is silent

| | |
|--|--|
| **Location** | `virag/legal/temporal.py` |
| **Status** | ⬜ open |
| **Severity** | 🟠 Major |

**Observed.** A bare year becomes `YYYY-06-30`; a quarter or month becomes day
15 of the middle month. The `TemporalContext.source` field records `"inferred"`,
but the collapse of an interval to a point is not surfaced further.

**Why it matters.** If a rule changed inside the stated interval — the common
case for a tax year — the midpoint selects one side of the change arbitrarily,
and the answer is presented with normal confidence.

**Fix.** Represent the inferred period as an **interval**, not a point. If any
retrieved provision's validity boundary falls inside that interval, force the 🟡
light and state that the answer depends on the exact date.

---

### ✅ D-09 — Application dependencies undeclared

| | |
|--|--|
| **Location** | `pyproject.toml` |
| **Status** | ✅ **closed 2026-09-03** |
| **Severity** | 🟠 Major |

**Observed.** Declared dependencies are `pypdf`, `truststore`, `pytest`, `ruff`.
The scaffold imports `numpy`, `sqlalchemy`, `qdrant-client`,
`sentence-transformers`, `fastapi`, `redis`, `langgraph`, `python-docx`,
`pytesseract` and `pymupdf`.

**Why it matters.** The setup path documented in the README installs
`requirements-dev.lock`, which cannot import a single scaffold module.

**Fix applied.** `pyproject.toml` now declares four groups: base (acquisition
tools only), `dev`, `app` (numpy, sqlalchemy, fastapi, uvicorn, redis,
qdrant-client, langgraph, anthropic, python-docx), `ml`
(sentence-transformers) and `ocr` (pytesseract, pymupdf, pillow). The
acquisition tools remain installable without the ML stack, preserving ADR-016.

---

### 🟡 D-10 — NumPy vector store has no upsert semantics

| | |
|--|--|
| **Location** | `virag/index/vector_store.py` (`NumpyVectorStore.upsert`) |
| **Status** | ⬜ open |
| **Severity** | 🟡 Minor |

**Observed.** `upsert` appends via `vstack` and `extend` without deduplicating on
`chunk_id`. Re-ingesting the same chunk produces two rows with the same id.

**Why it matters.** ADR-016 promises the fallback behaves like Qdrant. Qdrant
overwrites by point id; NumPy duplicates. Recall and ranking then differ between
the two backends, so a fallback run is not comparable to a real run even after
accounting for the encoder.

**Fix.** Maintain an id → row index map; overwrite in place on repeat.

---

### 🟡 D-11 — Divergent identity semantics between vector backends

| | |
|--|--|
| **Location** | `virag/index/vector_store.py` (`_point_id`) |
| **Status** | ⬜ open |
| **Severity** | 🟡 Minor |

**Observed.** `NumpyVectorStore` keys on the `chunk_id` string;
`QdrantVectorStore` keys on `int(chunk_id[:15], 16)` — 60 bits derived from a
16-hex-character id.

**Why it matters.** Collision probability at this corpus size is negligible, but
the two stores do not share an identity model, which is the root cause of D-10
and makes cross-backend comparison unsound.

**Fix.** Use one identity function for both, or key Qdrant by UUID derived from
the full `chunk_id`.

---

### ✅ D-12 — Crawler buffers whole responses in memory

| | |
|--|--|
| **Location** | `tools/legal_crawler.py` |
| **Status** | ✅ **closed 2026-09-03** |
| **Severity** | 🟡 Minor (🔴 before any further large crawl) |

**Observed.** `subprocess.run(..., capture_output=True)` collects the full body,
then `len(completed.stdout)` checks the size limit — after the whole payload is
already resident.

**Why it matters.** `docs/large-data-processing-plan.md:123–125` already
mandates the correct pattern: stream in 1–8 MiB blocks to a `.partial` file
while updating SHA-256, verify magic/EOF/hash, `fsync`, then atomic-rename into
a content-addressed path.

**Severity note.** Low impact on the 600 documents already fetched; **blocking**
before crawling shards 0008–0131.

**Fix applied.** Implemented exactly the pattern the large-data plan specifies:

* `SafeFetcher.fetch_to_file()` streams the body to a `.partial` sibling in
  1 MiB blocks while advancing the SHA-256 and byte count, so a multi-megabyte
  PDF is never resident whole.
* `Content-Length` is checked **before** the transfer and re-checked after, so
  an oversize body is refused up front and a short read is refused at the end.
* `fsync` then `os.replace()` - the rename is atomic, so a crash can never
  leave a truncated file where a complete one is expected.
* `verify_pdf()` checks magic bytes and the `%%EOF` trailer before the file is
  accepted; a failure unlinks the file.
* The curl fallback now writes via `--output` instead of `capture_output`, so
  the payload no longer passes through the parent process.
* `write_bytes` on the attachment path is gone.

Regression: `tests/test_crawler_streaming.py` - 9 tests covering incremental
hashing across block boundaries, the byte cap, declared-length rejection, short
reads, mid-stream failure leaving no `.partial`, and truncated-PDF detection.

**This unblocks crawling shards 0008–0131.**

---

### ✅ D-13 — `effective_date` carries the literal string "Công báo"

| | |
|--|--|
| **Location** | Portal metadata, propagated through `virag/ingest/manifest.py` |
| **Status** | ✅ **closed 2026-09-03** |
| **Severity** | 🔴 Blocker |
| **Raised by** | G0 measurement |

**Observed.** **152 of 819 documents** have `metadata.effective_date` set to the
literal label `"Công báo"` rather than a date.

**Why it matters.** Any code testing `if effective_date:` treats this as a
**present** date. During the G0 run this exact mistake made an intermediate tool
report 97.3% date completeness against a true figure of 78.8% — a 19-point
error, in the direction that hides risk.

`manifest.py` currently routes the value through `parse_vn_date()`, which
returns `None` for unparseable input, so ingest happens to be safe **by
accident**. Nothing enforces it.

**Fix applied.** `virag/legal/temporal.classify_portal_date()` returns
`(iso_date, quality)` where quality is `valid` / `malformed` / `absent`.
`DocumentMeta` gained `effective_date_quality` and `expiration_date_quality`, set
at the manifest boundary. Measured on `shard-0001`: 91 valid, 9 malformed.
Regression: `tests/test_virag_temporal.py::TestPortalDateClassification`,
including an explicit assertion that a naive truthiness test would have
accepted the label.

---

### ✅ D-14 — Relation extraction misses 69% of amendment links

| | |
|--|--|
| **Location** | `virag/legal/relations.py` |
| **Status** | ✅ **closed 2026-09-03** |
| **Severity** | 🔴 Blocker |
| **Raised by** | G0 measurement |

**Observed.** The extractor matches instrument numbers only
(`\d{1,4}/\d{4}/XX`). Vietnamese instruments overwhelmingly cite their targets
**by name**:

```text
"Luật số 149/2025/QH15 ... sửa đổi, bổ sung một số điều của
 Luật Thuế giá trị gia tăng"           <- no target number anywhere
```

Measured over the corpus: **59 links resolvable by number, 134 by name** — the
number-only path finds **31%** of them.

**Why it matters.** The dependency graph drives change detection, impact
analysis, clause-level status (D-07) and conflict adjudication (ADR-009).
Missing two-thirds of the edges makes all four unreliable.

**Fix applied.** `relations.py` now matches on both axes: instrument number
(including year-less VBHN numbers) **and** normalised subject name, where a
subject counts only if the name *starts* with a legal-type word. `LegalGraph`
gained a subject index, `LegalRelation` gained `target_subject` and `matched_by`
for auditing, and `resolution_stats()` reports the split.

Measured on the corpus after the fix:

| | Before (number only) | After |
|--|---------------------:|------:|
| Resolved edges | 248 | **316** |
| VAT Law 48/2024/QH15 incoming | **0** | **15** |
| Invoices Decree 123/2020/NĐ-CP incoming | 0 | 3 |
| Resolution rate | 31% | **57.9%** |

The VAT Law - the single most important instrument in the v1 scope - had **zero**
resolvable incoming edges before this fix; all 15 are cited by name.

Two further bugs were caught by the new regression tests and fixed:
duplicate edges when a target was cited by both number and name in one phrase,
and a self-edge when a document restated its own number.
Regression: `tests/test_virag_legal_relations.py`.

---

### ✅ D-15 — Measurement tool reported a misleading OCR metric

| | |
|--|--|
| **Location** | `tools/trial_parse_pdfs.py` |
| **Status** | ✅ **closed 2026-09-03** |
| **Severity** | 🟠 Major |
| **Raised by** | G0 measurement |

**Observed.** The trial reported *"% pages needing OCR: 0.0%"*. That counted
pages **actually OCR'd** — zero, because OCR was unavailable — not pages
**below the text threshold**, which is **21%**.

**Why it matters.** The metric read as "no OCR needed" while the real figure was
that **52% of documents had no extractable text at all**. A measurement tool that
under-reports a blocker is worse than no measurement.

**Fix applied.** The report now separates two figures: `pages_needing_ocr`
(pages below the text threshold — the burden) and `pages_ocr_applied` with an
`ocr_coverage_pct`. On the expanded corpus the corrected metric reads **34.5%
of pages need OCR, 0% coverage** — where the old metric said "0.0% needing
OCR".

---

### ✅ D-16 — Parse metric does not separate main instruments from annexes

| | |
|--|--|
| **Location** | `tools/trial_parse_pdfs.py` |
| **Status** | ✅ **closed 2026-09-03** |
| **Severity** | 🟡 Minor |
| **Raised by** | G0 measurement |

**Observed.** Attachments are numbered `-1`, `-2`, `-3`… where `-1` is the
instrument and higher ordinals are annexes. The trial scored all of them
together.

An annex of forms and tables legitimately contains no `Điều`. Counting it as a
parse failure understated parser quality by roughly **22 points** (70.8% mixed
versus 92.3% on main instruments).

**Fix applied.** Rows carry `attachment_ordinal`, `is_main_instrument` and
`has_text_layer`; the report emits four populations (all / text-bearing /
main-instruments / annexes) and gates only on main instruments with a text
layer. On n=120 the gated population reads **88.9%** against **20.0%** for
annexes — confirming the two must not be pooled.

---

### ✅ D-17 — `pyproject.toml` invalid, blocking ruff

| | |
|--|--|
| **Location** | `pyproject.toml:27` |
| **Status** | ✅ **closed 2026-09-03** |
| **Severity** | 🟠 Major |

**Observed.** `select = ["E", "F", "I", "B", "UP", "SIM"]y` — a stray `y`
prevented ruff from reading its configuration.

**Fix applied.** Character removed, trailing newline added. Verified:
`ruff check tools tests` → *All checks passed*; `pytest -q` → **39 passed**.

---

## 3. Gate mapping

Which defects must close before which gate:

| Gate | Must be closed |
|------|----------------|
| **G0** (before Phase 1 ingest) | ~~D-13~~ ✅ ~~D-14~~ ✅ ~~D-15~~ ✅ ~~D-16~~ ✅ — **only OCR (B-1) remains** |
| **G1** (index built, before RAG work) | D-01, D-02, D-03, D-06, D-07, D-09, D-10, D-11 |
| **G2** (RAG reliable) | D-05, D-08 |
| **G3/G4** (evaluation published) | D-04 (or conflicts demoted to proposals) |
| Before crawling shards 0008–0131 | ~~D-12~~ ✅ **cleared** |

### 3.1 G0 blockers not tracked as code defects

Two G0 findings are supply problems, not code defects, and are tracked in
[`reports/G0-REPORT.md`](../../reports/G0-REPORT.md) §5:

| ID | Blocker | Evidence |
|----|---------|----------|
| **B-1** | Image-only PDFs; Tesseract not installed | **Worse after the tax crawl: 54.2% of documents, 34.5% of pages** (1,771/5,134). A 77-page Decree yielded 76 characters. Two escapes tested and rejected: Official Gazette substitution (0.2% overlap) and PyMuPDF (0 of 26 rescued) |
| ~~**B-2**~~ ✅ | ~~Version chains yield exactly 50 TaxTime probes~~ **RESOLVED** | The tax-priority crawl took the corpus from 819 to 1,580 documents; tax chains 25 → **101**, probes 50 → **149** (3.0× margin) |

---

## 4. Defects introduced by documentation, now corrected

| ID | Issue | Resolution |
|----|-------|------------|
| DOC-01 | "Month 1 is already complete" contradicted the missing-components table | Corrected in [B §27](B-product-direction.md) — only weeks 1–2 are complete |
| DOC-02 | PRD and dossier both claimed scope authority | Resolved by [ADR-024](05-design-decisions.md) — dossier governs the project, PRD governs the roadmap |
| DOC-03 | Documentation line count misreported as ~14,800 | Actual: 35 files, 19,461 lines excluding `data/` |

---

**Previous:** [11 — Compliance, ethics and limits](11-compliance-and-ethics.md)
**Back to the index:** [00 — Index](00-index.md)
