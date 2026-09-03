# 06 — Data and the Data Pipeline

> In this system the hard part is not the model. It is turning 4.4 GB of
> official-gazette PDFs into passages that can be cited down to the Clause,
> carry a trustworthy effective date, and know which version they belong to.

---

## 1. Current corpus state (real figures)

Measured on the repository as of 2026-09-03.

### 1.1 Volume

| Metric | Value |
|--------|-------|
| PDFs downloaded | **1,355 files** |
| Total PDF size | **4.4 GB** |
| Text files extracted from HTML | **1,438** |
| Records in the 10-year inventory | **13,058 source records** (≈ 13,052 semantic documents) |
| Full-text queue shards | **131 shards** |
| Shards fully audited | **6** (shards 0001–0006) |
| Time window | 2016-08-11 – 2026-08-11 |

### 1.2 Completeness audit (shards 0001–0006)

From `data/analysis/crawl-completeness-shards-0001-0006-2026-08-11.json`:

| Metric | Value |
|--------|-------|
| Documents configured | 600 |
| Source pages fetched | **600 / 600** |
| Attachment URLs expected | 726 |
| Attachment URLs fetched | **726 / 726** |
| Readable PDF pages | 33,527 |
| Hash / length / PDF-structure errors | **0** |

The audit report states its own limitations, and they matter for the design:

> - Hash/length/EOF/page-tree checks prove the **downloaded response is
>   internally complete**; they cannot prove the **publisher's scan omitted no
>   physical page**.
> - The printed page-number sequence cannot be checked reliably for image-only
>   PDFs without OCR.
> - **One Official Gazette PDF can contain several legal instruments**, so PDF
>   page count ≠ instrument page count. (Risk R-D10.)

### 1.3 Document type distribution (698 `source_page` records, run v4)

| Document type | Count | % | Tier |
|---------------|------:|--:|-----:|
| Thông tư (Circular) | 307 | 44.0% | 7 |
| Nghị định (Decree) | 162 | 23.2% | 5 |
| Văn bản hợp nhất (Consolidated) | 141 | 20.2% | (per original) |
| Nghị quyết (Resolution) | 44 | 6.3% | 2 or 5 |
| Quyết định (Decision) | 30 | 4.3% | 6 or 8 |
| Luật (Law) | 9 | 1.3% | 2 |
| Thông tư liên tịch (Joint Circular) | 3 | 0.4% | 7 |

**Three observations with design consequences:**

1. **Circulars are 44%** — the detailed implementation tier. This is where most
   quantitative figures live, so it is also where most real questions land.
2. **Only 9 Laws (1.3%)** — yet they carry the highest legal force. Under pure
   similarity ranking they would **almost never win**, swamped by 307 Circulars.
   This is quantitative evidence for ADR-008.
3. **141 Consolidated Documents (20.2%)** — both an opportunity (a natural
   multi-version source, §7.3) and a risk (confusion with originals, R-D07).

### 1.4 Temporal metadata quality

| Metric | Value |
|--------|-------|
| `source_page` records | 698 |
| With `effective_date` | 538 (**77.1%**) |
| **Missing `effective_date`** | 160 (**22.9%**) |

This is the single most important number in this document. See
[07 §3 R-D01](07-risk-analysis.md).

### 1.5 Effective-date verification against the Official Gazette

Performed on the Law-tier documents:

| Result | Count |
|--------|------:|
| Matches portal metadata | **19 / 22** |
| Conflict → quarantined | 2 |
| Image PDF, needs OCR / manual review | 1 |

The process is proven to work (`tools/legal_effective_dates.py`). What remains
is to **scale it** from 22 documents to all 160 missing dates.

---

## 2. Source Registry — do not crawl blind

### 2.1 Source tiers and trust scores

| Tier | Source type | Trust | Used in v1? |
|------|-------------|------:|:-----------:|
| 1 | Official (Official Gazette, government portal) | 1.00 | ✅ |
| 2 | Government (ministry portals) | 0.95 | ✅ |
| 3 | Commercial legal databases | 0.80 | ⛔ |
| 4 | News | 0.50 | ⛔ |
| 5 | User content | 0.20 | ⛔ |

**v1 decision:** tiers 1 and 2 only. No other source enters the corpus in any
form — not even "for reference". A legal corpus contaminated with unofficial
sources is unusable for citation purposes.

### 2.2 Six official source groups, pagination exhausted

Recorded in `data/analysis/tax-document-master-inventory-2026-08-11.json`:

- Laws / Ordinances (`law_or_ordinance`) — 235 documents
- Decrees
- Decisions
- Circulars (3 crawl passes: v1, v2, v3 — v3 exhausted 51+ pagination pages)
- Resolutions (Official Gazette)
- Consolidated Documents (Official Gazette)

**The principle applied, which must be preserved:**

> No record is excluded **merely because its title lacks a tax keyword**. Title
> keywords are used **only to schedule priority**; every record stays in the
> full-text screening queue.

This is the anti-selection-bias principle. A Decree on "foreign exchange
management" may contain an Article on a tax obligation; title filtering would
lose it permanently.

---

## 3. Medallion architecture: Bronze → Silver → Gold

```text
┌──────────────────────────────────────────────────────────────┐
│ RAW        PDF / HTML downloaded from official sources       │
├──────────────────────────────────────────────────────────────┤
│ BRONZE     Intact bytes + SHA-256 + manifest.jsonl           │
│            → data/crawl/<run>/quarantine/                    │
│            Immutable. Never edited. This is the evidence.    │
├──────────────────────────────────────────────────────────────┤
│ SILVER     Extracted + normalised text + Article/Clause tree │
│            → data/processed/<document_id>.json               │
│            Regenerable from Bronze with the same code.       │
├──────────────────────────────────────────────────────────────┤
│ GOLD       Chunks + full metadata + versions + relations     │
│            → PostgreSQL · Qdrant · BM25 · ChunkStore         │
│            This is what the system queries.                  │
└──────────────────────────────────────────────────────────────┘
```

**The critical boundary:** Bronze is **legal evidence**, checksummed and never
overwritten. Silver and Gold are **derivatives** that can be deleted and
rebuilt. If a parser bug is discovered a year from now, Silver and Gold are
rebuilt from Bronze without re-crawling 4.4 GB.

Current state: **Bronze exists**. Silver and Gold **are not built**.

---

## 4. Text extraction and OCR

### 4.1 Source selection: PDF first, HTML second

Two text sources exist per document:

| Source | Pros | Cons |
|--------|------|------|
| **Attached (signed) PDF** | The **official** text; preserves Article/Clause structure | Needs extraction; may be a scan |
| Text from portal HTML | Readily available, clean encoding | **Full of navigation boilerplate** |

Evidence for the decision — the first ~1,500 characters of a real
`quarantine/official-text/*.txt` file:

```text
… trang chủ Công báo Văn bản đăng công báo Văn bản chỉ đạo điều hành Ban hành:
13/07/2026 - Hiệu lực: … Lược đồ Thuộc tính Chia sẻ Chia sẻ lên facebook Chia sẻ
lên Zalo Chia sẻ lên Twiter Copylink Tới trang /61 Tìm kiếm … Cơ quan ban hành
Hệ thống văn bản Văn bản mới Tất cả Chủ tịch nước Quốc hội Ủy ban thường vụ
quốc hội Chính phủ Thủ tướng chính phủ BỘ CÔNG AN BỘ CÔNG THƯƠNG …
```

*(Translation: "home / Official Gazette / documents published / directive
documents / Issued: 13/07/2026 - Effective: … / Outline / Properties / Share /
Share to Facebook / Share to Zalo / … / Issuing agency / Document system / New
documents / All / President / National Assembly / …")*

**Not one word of that is normative content.** Indexed, phrases like "Bộ Tài
chính", "Chính phủ" and "Văn bản mới" become the highest-frequency n-grams in
the corpus and **destroy BM25's IDF**.

**Decision:** prefer the PDF; use HTML only when the PDF cannot be extracted,
and only through the boilerplate filter.

### 4.2 Per-page OCR fallback

```text
For each PDF page:
    text = the page's text layer
    if len(text.strip()) < 180 chars  and  OCR is available:
        ocr_text = tesseract(render(page, 300 DPI), lang="vie", --psm 4)
        if ocr_text is longer: use it, mark extraction_method="ocr"
```

**Why per page and not per document.** A 60-page Circular typically has 58
digital pages and 2 scanned annexes. OCR-ing all 60 costs 30× more and
**degrades** the 58 pages that were already fine.

**Parameters and rationale:**

| Parameter | Value | Reason |
|-----------|-------|--------|
| Chars-per-page threshold | 180 | Below this it is almost certainly an image page |
| DPI | 300 | Standard for printed-text OCR |
| `--psm 4` | Single column, variable sizes | Matches the single-column gazette layout |
| `lang` | `vie` | Mandatory — Vietnamese diacritics |

**Metric to track:** `ocr_page_count / page_count` across the corpus. Warning
threshold **> 20%** (R-D03).

### 4.3 Vietnamese normalisation

Four mandatory steps, in order:

| # | Step | Why |
|--:|------|-----|
| 1 | **NFC normalisation** | Vietnamese has **two valid Unicode spellings** for most accented vowels. Without normalisation, `"thuế"` typed two ways is two different tokens — breaking both BM25 and embeddings |
| 2 | Strip invisible characters | Soft hyphens, ZWSP, ZWNJ survive PDF extraction |
| 3 | Rejoin words broken across lines | `"thu-\nnhập"` → `"thunhập"`; the hyphen is a line-break artefact, not a real one |
| 4 | Remove repeated headers/footers | Bands such as "CÔNG BÁO/Số 440" and page numbers repeat on **every** page |

**How header/footer detection stays safe:** only the **first 3 and last 3 lines**
of each page are candidates, and a line is removed only if it appears on
**≥ 60% of pages**. The positional constraint guarantees a normative sentence
that happens to repeat mid-page is **never** deleted.

---

## 5. The Article / Clause / Point parser

### 5.1 Target tree

```text
Phần (Part) → Chương (Chapter) → Mục (Section)
            → Điều (Article) → Khoản (Clause) → Điểm (Point)
```

### 5.2 Recognition patterns

| Level | Pattern | Extra constraint |
|-------|---------|------------------|
| Part | `PHẦN (THỨ) <number/Roman>` | Must be its own line, uppercase |
| Chapter | `CHƯƠNG <Roman/number>` | — |
| Section | `MỤC <number>` | Must be its own line, uppercase |
| **Article** | `Điều <number>[a-z]. <heading>` | Supports `Điều 9a` (inserted articles) |
| **Clause** | `<number>. ` at line start | Only when inside an Article |
| **Point** | `<letter>) ` at line start | Only when inside a Clause |

### 5.3 The preservation principle

> **Any line that cannot be classified is appended to the current node's body;
> it is never dropped.**

The worst case is **citation degrading from Clause level to Article level** —
acceptable. The unacceptable case is **losing text**.

### 5.4 Handling the signature block

After `TM. CHÍNH PHỦ` / `KT. BỘ TRƯỞNG` the remainder is usually signatures and
distribution lists. But **annexes after the signature can restart Article
numbering**. The rule: skip content after the signature block, **unless** a new
`Điều <number>` line appears — at which point return to reading normative
content.

### 5.5 Parser quality metrics (measure, do not guess)

| Metric | Acceptance threshold |
|--------|----------------------|
| % of documents with ≥ 1 recognised Article | ≥ 85% |
| % of Articles with ≥ 1 recognised Clause | ≥ 70% |
| % of chunks citable to the **Clause** | ≥ 60% |
| Chunks losing text relative to the source | **0** |

This is the **Silver layer quality gate**. Failing it means no promotion to
Gold.

---

## 6. Parent–child chunking

| | Parent | Child |
|--|--------|-------|
| Unit | **Article (Điều)** | **Clause (Khoản)**, or Point if the Clause is long |
| Role | Handed to the LLM to read | Embedded and retrieved |
| Size | ≤ 1,600 tokens | ~220 tokens, 40 overlap |
| Citation label | `Điều 9 - Luật 48/2024/QH15` | `Điều 9 khoản 2 - Luật 48/2024/QH15` |

**An important detail:** each child **repeats the Article heading** at its start.
Reason: when the snippet is shown alone (search results) it remains
self-describing; and when embedded, the Article's topical context enters the
Clause's vector.

**Fallback when structure is absent:** split into 1,600-token blocks, labelled
`Passage N - <instrument number>`. **Never invent an Article number.**

---

## 7. Versioning and immutability

### 7.1 Version id

```text
version_id = <instrument number> # <SHA-256(normalised text)[:12]>
example:     48/2024/QH15#7c1e4a9b22f0
```

### 7.2 Idempotent ingest

```text
Download/read document → normalise text → SHA-256
   ├── hash already exists  → NO-OP (no row, no re-embedding)
   └── new hash             → close the open version (superseded_at = now)
                            → insert the new version
                            → write articles, chunks, relations
```

Running ingest ten times on the same data yields **the same database state**.

### 7.3 Sources of historical versions (addressing R-D02)

Three sources, in descending reliability:

| # | Source | Mechanism | Note |
|--:|--------|-----------|------|
| 1 | **Consolidated Document (VBHN) chains** | Each VBHN is a **snapshot** of the original at a point in time | 141 VBHNs in the corpus — the most natural source |
| 2 | **Reconstruction from amending instruments** | Amending texts state the old content explicitly → reconstruct the prior version | Requires an amendment-clause parser |
| 3 | Additional historical crawling | Fetch older versions from sources | The most laborious |

The repository already has `config/tax-law-consolidation-sources.json` and
`config/tax-law-legacy-consolidation-sources.json` — **the infrastructure for
source 1 is ready**.

### 7.4 A caution about Consolidated Documents (R-D07)

A Consolidated Document is a **convenience view; it does not replace the
original legal source**. Constraints:

- must be tagged `document_type = "Văn bản hợp nhất"`;
- authority tier follows the **consolidated original** (VBHN-BTC → tier 7), not
  a tier of its own;
- when cited, it must be identified as a consolidation with the original cited
  alongside.

---

## 8. Legal relation extraction

### 8.1 Documents declare their own relations

```text
"Sửa đổi, bổ sung một số điều của Luật Thuế giá trị gia tăng số 13/2008/QH12"
   (Amends and supplements several articles of VAT Law No. 13/2008/QH12)

"Bãi bỏ Thông tư số 39/2014/TT-BTC"
   (Repeals Circular No. 39/2014/TT-BTC)

"Quy định chi tiết một số điều của Luật Quản lý thuế số 38/2019/QH14"
   (Details several articles of Tax Administration Law No. 38/2019/QH14)
```

Instrument-number recognition:

```regex
\b(\d{1,4}\s*/\s*(?:19|20)\d{2}\s*/\s*[A-ZĐ][A-ZĐ0-9\-]{1,15})\b
```

### 8.2 Cue → relation table

| Relation | Cue (Vietnamese) | Confidence |
|----------|------------------|-----------:|
| `REPEALS` | bãi bỏ, hủy bỏ, chấm dứt hiệu lực | 0.90 |
| `REPLACES` | thay thế | 0.90 |
| `CONSOLIDATES` | hợp nhất | 0.90 |
| `AMENDS` | sửa đổi, bổ sung | 0.85 |
| `DETAILS` | quy định chi tiết | 0.80 |
| `GUIDES` | hướng dẫn thi hành/thực hiện | 0.75 |
| `INTERPRETS` | giải thích, trả lời về | 0.60 |
| `REFERS_TO` | (default when a number appears with no cue) | 0.40 |

### 8.3 Scan only the document head

Only the **first 20,000 characters** are scanned. Reason: the title, the
"pursuant to" recitals and the opening Articles carry essentially every
amendment declaration; the body is full of incidental cross-references that
would **flood the graph** with meaningless `REFERS_TO` edges.

### 8.4 Dangling edges are information, not errors

A document may point at an instrument number **absent from the corpus**. The
edge is still stored with `target_document_id = NULL`. It tells us what the
corpus is missing — input for the next crawl round.

---

## 9. The Data Quality Engine

Six mandatory checks before a document enters Gold:

| # | Check | Detects | Action |
|--:|-------|---------|--------|
| 1 | Missing effective date | `effective_from IS NULL` | `legal_status = UNKNOWN`, lower `validity_score`, queue for backfill |
| 2 | Invalid instrument number | Does not match the number regex | Quarantine, await manual review |
| 3 | Duplicate | Same `content_hash` | Merge, keep the richer metadata |
| 4 | Broken reference | `target_document_id IS NULL` | Record the dangling edge, **do not delete** |
| 5 | **Overlapping validity intervals** | Two versions of one document both "open" | **Raise a data-conflict warning** |
| 6 | Invalid hierarchy | Tier from the number ≠ tier from the document type | Warn, prefer the number, log it |

**Example of violation type 5:**

```text
Version A:  effective_from = 2024-01-01, effective_to = NULL
Version B:  effective_from = 2023-01-01, effective_to = NULL
```

Both claim to be "in force indefinitely" for the same document — impossible. A
validation layer must catch it.

**Output:** `reports/data-quality.json` with violation counts per check, run
after every ingest.

---

## 10. Indexes

| Index | Content | Location | Note |
|-------|---------|----------|------|
| **Qdrant** | Dense vectors + filter payload | Service | The payload **excludes** body text (halves memory on a 4 GB corpus) |
| **BM25** | Vietnamese postings | `data/index/bm25.json` | JSON so it is diffable and reproducible |
| **ChunkStore** | Full chunk + parent text | `data/index/chunks.jsonl` | The canonical text source |
| **PostgreSQL** | Versions, articles, relations, changes, feedback | Service | The canonical metadata source |

**The Qdrant payload keeps only fields used for filtering:**
`effective_from_days`, `effective_to_days`, `authority_tier`, `tax_domains`,
`document_id`, `chunk_id`, `version_id`. Dates are stored as **integer
days-since-epoch** with sentinels `-36500` / `+36500` for unknown bounds.

---

## 11. Scheduled updates

```text
Scheduler (APScheduler for the MVP)
   → Source Monitor: any new documents?
   → Download + Validate (robots, checksum)
   → Parse → Version (hash) → Diff (4 tiers) → Index
   → Change Event → Invalidate related cache → Notify
```

**Update latency target:** P50 ≤ 24 h from Official Gazette publication to
queryability.

**Idempotency key:** `(source_id, document_id, content_hash)`. Reruns create no
duplicate rows.

---

## 12. Outstanding data work (by priority)

| # | Task | Risk addressed | Priority |
|--:|------|----------------|----------|
| 1 | **Count documents with ≥2 versions** in the corpus | R-D02 | 🔴 Decision gate |
| 2 | Backfill `effective_date` for the 160 missing documents | R-D01 | 🔴 |
| 3 | Run the parser over the whole corpus, measure the four §5.5 metrics | R-D04 | 🔴 |
| 4 | Complete shard 0007 (6 source pages + 1 PDF remaining) | R-D06 | 🟠 |
| 5 | OCR the 1 image PDF in the Gazette verification set | R-D03 | 🟠 |
| 6 | Resolve the 2 quarantined effective-date conflicts | R-D05 | 🟠 |
| 7 | Build version chains from the 141 Consolidated Documents | R-D02 | 🟠 |
| 8 | Run the Data Quality Engine, export the report | R-D group | 🟠 |
| 9 | Split multi-instrument Official Gazette PDFs | R-D10 | 🟡 |
| 10 | Crawl shards 0008–0131 | Coverage | 🟡 |

**A note on task 10:** the 6 of 131 shards already completed are **enough to
build and evaluate the system** (600 documents, 33,527 pages). Expanding
coverage is Phase 5 work, not a precondition. Prioritise **metadata quality of
the 600 documents in hand** over **quantity of the 13,058 not yet processed**.

---

**Previous:** [05 — Design decisions](05-design-decisions.md)
**Next:** [07 — Risk analysis](07-risk-analysis.md)
