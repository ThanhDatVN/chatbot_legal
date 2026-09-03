# ViRAG-Gov — Research, Design and Implementation Dossier

**Project code:** ViRAG-Gov
**Product name:** Vietnam Tax Legal Intelligence Assistant
**Dossier version:** 1.0 — 2026-09-03
**Status:** Design complete, production code not yet implemented

---

## 0. The positioning statement

> **The system does not look for "the latest law". It determines *which
> provision actually applies* to a specific situation, at a specific point in
> time, in a landscape of amended, replaced, overlapping documents of differing
> legal force.**

That sentence is the line between an ordinary RAG chatbot and a legal
intelligence system. This entire dossier exists to defend that line at the
level of design, data, model and measurement.

---

## 1. Reading order

### 1.1 Direction documents (read first for context)

| # | Document | Content |
|---|----------|---------|
| A | [Research direction](A-research-direction.md) | Research framing, existing benchmarks, 7 conflict types, the LAA metric |
| B | [Product direction](B-product-direction.md) | Platform positioning, 4 modules, data architecture, UX, roadmap |

Unedited originals are archived in [`_source/`](_source/README.md) (Vietnamese).

### 1.2 Main dossier

| # | Document | Answers | Audience |
|---|----------|---------|----------|
| 01 | [Problem analysis](01-problem-analysis.md) | What is the real problem? Why does plain RAG fail? | Everyone |
| 02 | [Related work & research gap](02-related-work.md) | Who has done what? What is our contribution? | Research, reviewers |
| 03 | [VietTaxBench](03-benchmark-viettaxbench.md) | What do we measure? How do we measure it correctly? | Research, ML |
| 04 | [System architecture](04-system-architecture.md) | What are the parts and how do they fit? | Engineers |
| 05 | [**Design decisions** (ADRs)](05-design-decisions.md) | Why this design? What alternatives? What does it cost? | Engineers, reviewers |
| 06 | [Data and data pipeline](06-data-pipeline.md) | Where does the data come from? Can we trust it? | Data engineers |
| 07 | [**Risk analysis**](07-risk-analysis.md) | What can go wrong? How do we detect it early? | Everyone |
| 08 | [Implementation plan](08-implementation-plan.md) | What first, what next, when done? | Management, everyone |
| 09 | [Evaluation & experiment plan](09-evaluation-plan.md) | How do we prove the system is good? | Research, ML |
| 10 | [Setup & operations guide](10-operations-guide.md) | How do I run this? | Engineers, reviewers |
| 11 | [Compliance, ethics and limits](11-compliance-and-ethics.md) | Where are the boundaries? | Everyone |
| 12 | [**Defect register**](12-defect-register.md) | What is broken in the scaffold, and which gate blocks on it? | Engineers |

### 1.3 Pre-existing foundation documents in this repository

> These predate this dossier and are **still in Vietnamese**.

- [`docs/de-an-tong-the.md`](../de-an-tong-the.md) — overall proposal
- [`docs/design/00-design-index.md`](../design/00-design-index.md) — design set 00–08
- [`docs/source-register.md`](../source-register.md) — verified source register
- [`docs/crawl-tax-law-10y.md`](../crawl-tax-law-10y.md) — 10-year corpus
- [`docs/large-data-processing-plan.md`](../large-data-processing-plan.md) — large-data processing plan

---

## 2. Reading paths by role

| If you are | Read in this order |
|------------|--------------------|
| **Reviewer / examiner** | 01 → 03 → 05 → 09 → 07 |
| **Engineer about to write code** | 04 → 05 → 06 → 08 → 10 |
| **Data engineer** | 06 → 07 §3 → 08 Phase 1 |
| **Researcher / thesis author** | A → 02 → 03 → 09 |
| **You have 20 minutes** | 01 §1, §2.3, §7, §13 → 05 §0 → 07 §10 |

---

## 3. Map to the 11 required deliverables

| # | Deliverable | Defined in | Artifact when complete |
|---|-------------|------------|------------------------|
| 1 | Problem statement & success metric | 01, 03 | `docs/PROBLEM_STATEMENT.md` |
| 2 | Dataset / data pipeline | 06 | `virag/ingest/*`, `reports/data-quality.json`, `docs/DATA_PIPELINE.md` |
| 3 | Baseline model | 09 §2 | Configuration `A-bm25-baseline` |
| 4 | Method / main model | 04, 09 §2 | Configuration `E-full-temporal-legal` |
| 5 | Benchmark table | 03, 09 | `reports/benchmark.md`, `reports/ablation.json` |
| 6 | Error analysis | 09 §8 | `reports/hallucination-analysis.md` (20 cases) |
| 7 | English README + architecture diagram | 04 | `README.md` (EN), `docs/architecture.svg` |
| 8 | Runs with one command | 10 | `docker compose up` |
| 9 | Model card / eval report | 09, 11 | `docs/MODEL_CARD.md`, `docs/EVAL_REPORT.md` |
| 10 | Demo video ≤3 minutes | 08 Phase 5 | `docs/DEMO_SCRIPT.md` + recording |
| 11 | Deploy / demo link | 08 Phase 5, 10 §10 | `docs/DEPLOYMENT.md` + public URL |

> **Honest note:** deliverables 10 and 11 require human action (screen
> recording, cloud credentials). This dossier prepares the script, the configs
> and the checklists; pressing the button belongs to the project owner.

---

## 4. Current state of the repository

**Last updated: 2026-09-03, after the tax-priority crawl and G0 Revision 2.**

| Component | Status | Notes |
|-----------|--------|-------|
| Development environment | ✅ **Working** | Python 3.11.9 + `.venv` |
| Data acquisition (`tools/`) | ✅ **Working** | 12 tools; **82 tests pass**; ruff clean |
| Raw corpus (Bronze) | ✅ **Present** | **2,225 PDFs / 6.24 GiB**, full checksums |
| Tax-priority crawl | ✅ **Complete** | 756/757 documents, 864/897 attachments (96.3%) |
| **G0 gate** | ⚠️ **1 of 2 blockers cleared** | [`reports/G0-REPORT.md`](../../reports/G0-REPORT.md) rev 2 |
|   B-2 version-chain margin | ✅ **RESOLVED** | TaxTime probes 50 → **149** (3.0× margin) |
|   B-1 OCR | ❌ **open, and larger** | **34.5% of pages** have no text layer |
| Parser gates | ✅ **All 3 pass** | 88.9% / 83.7% / 91.2% on n=120 |
| **Defect register** | ⚠️ **8 of 17 closed** | [12](12-defect-register.md) |
| `virag/` ingest modules | ⚠️ **Executed, 0 crashes** | 120 real PDFs, no failures |
| `virag/` remaining modules | ⚠️ **Reference scaffold** | Never run |
| Silver + Gold layers | ⬜ Not implemented | Blocked on B-1 and D-01/D-03 |
| RAG layer | ⬜ Not implemented | Phase 2 |
| Evaluation & benchmark | ⬜ Not implemented | Phase 4 |
| Docker / deploy | ⬜ Not implemented | Docker daemon stopped |

**Measurement boundary.** The table below is **measured**. Everything else in
this dossier remains a design target until a gate report says otherwise.

| Measured | Rev 1 (819 docs) | **Rev 2 (1,580 docs)** |
|----------|-----------------:|----------------------:|
| Distinct documents | 819 | **1,580** |
| Usable `effective_date` | 78.8% | **82.6%** |
| Instruments with ≥2 legal states | 32 | **108** |
|   tax-related | 25 | **101** |
| **TaxTime probes** (requirement 50) | 50 | **149** ✅ |
| Amendment links resolved by **name** | 69% | 56% (239 of 423) |
| Parser — docs with ≥1 Article | 92.3% (n=13) | **88.9%** (n=45) ✅ |
| Parser — Articles yielding a Clause | 77.3% | **83.7%** ✅ |
| Parser — chunks citable at Clause | 88.8% | **91.2%** ✅ |
| **Pages with no text layer** | 21.3% | **34.5%** ❌ |

---

## 5. Where the project actually stands

**One blocker left.** The tax-priority crawl closed B-2 and confirmed the
parser; only OCR stands between the corpus and Phase 1.

### What the crawl proved

Selecting the queue's own `direct_tax_title` class — 757 documents instead of
all 12,239 remaining — took the corpus from 819 to 1,580 documents and
multiplied every version metric:

- tax version chains **25 → 101**
- TaxTime probes **50 → 149**, a **3.0× margin** over the benchmark requirement
- **R-D02 is closed**: the central research contribution is now testable

The run was also an unplanned field test of **D-12**. It was killed mid-download;
the in-flight file stayed `.partial` and was **never promoted to `.pdf`**, at
exactly 2 MiB — two clean streaming blocks. No truncated file masqueraded as
complete, and the resume pass recovered the remainder without overwriting the
partial shard.

### The one blocker

**B-1 — OCR.** 54.2% of documents and **34.5% of pages** carry no extractable
text, up from 21.3%: the government-portal tax documents are more scan-heavy
than the earlier sample. Two software escapes were tested and rejected —
Official Gazette substitution (0.2% instrument overlap) and PyMuPDF (0 of 26
documents rescued). Tesseract plus the `vie` traineddata is required;
`winget --scope user` reports no applicable installer.

### Next actions

1. Install Tesseract + `vie`, re-run the parser trial with OCR (**B-1**).
2. Close **D-01** (reviewer-promotion gate) and **D-03** (parent-window
   truncation) — both required for **G1**.
3. Backfill `effective_date` for the 275 records still unusable.
4. Then begin Phase 1 ingest.

---

## 6. Shared conventions

### 6.1 Terminology

Vietnamese legal terms are kept in Vietnamese where they are data values in the
system (citation labels, document types), with an English gloss on first use.

| Vietnamese | English | Note |
|------------|---------|------|
| VBQPPL | Legal Normative Document | The binding category |
| Luật | Law | Authority tier 2 |
| Nghị định | Decree | Tier 5 |
| Thông tư | Circular | Tier 7 |
| Công văn | Official Letter | Tier 9 — **not** binding law |
| Văn bản hợp nhất (VBHN) | Consolidated Document | A convenience view, not a legal source |
| Công báo | Official Gazette | The authoritative publication |
| Điều / Khoản / Điểm | Article / Clause / Point | The three mandatory citation levels |
| `as_of` | Date of the taxable event | The date that determines applicable law |

| Abbreviation | Meaning |
|--------------|---------|
| **LAA** | Legal Applicability Accuracy |
| **TVA** | Temporal Version Accuracy |
| **VMR** | Version Mixing Rate |
| ASR | Attack Success Rate (prompt injection) |
| CRA | Conflict Resolution Accuracy |

### 6.2 Formats

Dates: ISO `YYYY-MM-DD` in storage, `DD/MM/YYYY` in the UI.
Risk IDs: `R-<group><number>`, e.g. `R-D01`.
Design decision IDs: `ADR-<number>`.

### 6.3 The seven founding design principles

Full text in [05 §0](05-design-decisions.md).

| # | Principle |
|--:|-----------|
| P1 | A silent wrong answer is worse than no answer |
| P2 | Time is mandatory, not optional |
| P3 | Cite to the clause or do not speak |
| P4 | Legal decisions must be explainable |
| P5 | Data is immutable |
| P6 | Degrade gracefully, never crash |
| P7 | Reproducible |

### 6.4 Five non-negotiable rules

1. No date means no confident answer — the system must ask.
2. No citation to Article/Clause/Point means no assertion.
3. Never let the LLM adjudicate a conflict — a rule engine decides; the LLM
   only nominates candidates.
4. An Official Letter never outranks a Law.
5. Output is reference information, not legal advice.

---

## 7. Three numbers to remember

| Number | Meaning | Source |
|--------|---------|--------|
| **22.9%** | Share of crawled documents **missing an effective date** — the ceiling on TVA is set by data, not by the model | [06 §1.4](06-data-pipeline.md) |
| **307 / 9** | Circulars versus Laws in the corpus — quantitative proof that ranking needs an authority component | [06 §1.3](06-data-pipeline.md) |
| **19/22** | Laws whose effective date matches between portal metadata and the Official Gazette PDF — the verification process works and needs to scale | [06 §1.5](06-data-pipeline.md) |

---

## 8. Language note

This dossier is written in English. The **system itself operates in
Vietnamese** — user questions, retrieved legal text, generated answers and
citation labels are all Vietnamese, because Vietnamese tax law exists only in
Vietnamese. Examples in these documents therefore show Vietnamese strings with
English glosses where meaning matters.
