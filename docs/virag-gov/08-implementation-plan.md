# 08 — Implementation Plan

> Written for **one person working alone**, starting from the repository's real
> state as of 2026-09-03, and treating the **11 required deliverables** as a
> non-negotiable contract.

---

## 1. The real starting point

### 1.1 What exists

| Item | Evidence |
|------|----------|
| Data acquisition tooling | 9 scripts in `tools/`, 9 test modules in `tests/` |
| Raw corpus (Bronze) | 1,355 PDFs / 4.4 GB, full checksums |
| 10-year inventory | 13,058 source records, pagination exhausted across 6 official source groups |
| Completeness audit | 600/600 pages, 726/726 PDFs, 0 errors (shards 0001–0006) |
| Effective-date verification | 19/22 Laws match the Official Gazette |
| Foundation design docs | ~400 KB (`docs/`, `docs/design/00-08`) |
| This dossier | `docs/virag-gov/` |

### 1.2 What is missing

| Missing | Effect |
|---------|--------|
| **A running environment** — no Python installed, Docker daemon not started | No line of code has been executed |
| Silver layer (parse + normalise) | No clean structured text |
| Gold layer (chunks + index) | Nothing is retrievable |
| The entire RAG layer | No question can be answered |
| The eval set | Nothing can be measured |
| Docker compose | Deliverable 8 unmet |

### 1.3 Assessment against the original roadmap

The roadmap in [document B §27](B-product-direction.md) spans four months. In
practice:

> **Month 1 (Foundation) is already complete and exceeded** — a working crawler,
> a corpus larger than most comparable projects, and full design documentation.

The plan below starts from **Month 2**, with a short Phase 0 added for standing
up the environment.

---

## 2. Five phases

```text
Phase 0  Environment & decision gate         (~3 days)
Phase 1  Silver + Gold: from PDF to index    (~2 weeks)
Phase 2  Reliable RAG: hybrid + temporal     (~2 weeks)
Phase 3  Legal Intelligence: conflict, diff  (~1.5 weeks)
Phase 4  Evaluation & submission artifacts   (~2 weeks)
Phase 5  Product & deployment                (~1 week)
```

Total: **~9 weeks** of focused work. Phases 1–2 and eval-set construction run
**partly in parallel** (see §4).

---

## 3. Phase detail

### Phase 0 — Environment & decision gate (3 days)

**Goal:** a working environment, and an answer to the make-or-break data
question **before** investing in everything else.

| # | Task | Estimate |
|--:|------|---------:|
| 0.1 | Install Python 3.11, create a venv, install dependencies | 2 h |
| 0.2 | Start Docker Desktop, confirm compose works | 1 h |
| 0.3 | Run `pytest` + `ruff` on the existing `tools/` | 1 h |
| 0.4 | Fix the syntax error in `pyproject.toml` (`select = [...]y` — a stray `y` at end of line) | 15 min |
| 0.5 | **Count documents with ≥2 versions in the corpus** | 4 h |
| 0.6 | Measure the missing-`effective_date` rate across the whole corpus (not just run v4) | 2 h |
| 0.7 | Trial-run the Article/Clause parser on 50 random PDFs, measure success rate | 4 h |

**🚦 Decision gate G0** — after 0.5 and 0.7:

| Condition | If PASS | If FAIL |
|-----------|---------|---------|
| ≥ 60 documents with ≥2 versions | Proceed to Phase 1 as planned | Build VBHN chains ([document 06 §7.3](06-data-pipeline.md)) before continuing |
| ≥ 85% of documents yield ≥1 parsed Article | Proceed to Phase 1 | Stop and fix the parser — **everything downstream depends on this** |

> Phase 0 exists so that eight weeks are not built on a false assumption.

---

### Phase 1 — Silver + Gold (2 weeks)

**Goal:** turn 1,355 PDFs into a queryable index.

| # | Task | Depends on | Estimate |
|--:|------|------------|---------:|
| 1.1 | Complete + test `ingest/extract.py` (PDF, DOCX, OCR fallback) | 0.1 | 1.5 d |
| 1.2 | Complete + test `ingest/clean.py` (NFC, headers/footers, boilerplate) | 1.1 | 1 d |
| 1.3 | Complete + test `ingest/structure.py`, meet the §5.5 thresholds of document 06 | 0.7, 1.2 | 2 d |
| 1.4 | Complete + test `ingest/chunking.py` parent–child | 1.3 | 1 d |
| 1.5 | `store/db.py`: bitemporal schema, idempotent versioning | 0.1 | 1.5 d |
| 1.6 | `legal/relations.py`: relation extraction, graph construction | 1.3 | 1 d |
| 1.7 | `index/embedder.py` + `bm25.py` + `vector_store.py` | 1.4 | 1.5 d |
| 1.8 | CLI `ingest.pipeline`: run all 600 documents of shards 0001–0006 | 1.1–1.7 | 1 d |
| 1.9 | Data Quality Engine + `reports/data-quality.json` | 1.5, 1.8 | 1 d |
| 1.10 | **Backfill effective dates** for missing documents (extend `legal_effective_dates.py`) | 1.8 | 1.5 d |

**Exit criteria:**

- [ ] ≥ 600 documents in PostgreSQL with version ids
- [ ] ≥ 85% of documents have ≥1 Article; ≥ 60% of chunks citable to the Clause
- [ ] `UNKNOWN` share < 15%
- [ ] Re-running ingest produces **0 new rows** (idempotent)
- [ ] `reports/data-quality.json` is generated

**→ Completes deliverable 2 (Dataset / data pipeline)**

---

### Phase 2 — Reliable RAG (2 weeks)

| # | Task | Estimate |
|--:|------|---------:|
| 2.1 | `retrieval/hybrid.py`: BM25 + dense + RRF | 1.5 d |
| 2.2 | Temporal filter in the Qdrant payload + safety valve | 1 d |
| 2.3 | `retrieval/rerank.py`: cross-encoder + fallback | 1 d |
| 2.4 | Composite legal score (`legal_score`) | 1 d |
| 2.5 | `legal/temporal.py`: date extraction, Temporal Clarification | 1 d |
| 2.6 | `generation/`: prompts, streaming, prompt caching, the `[Sn]` contract | 2 d |
| 2.7 | `generation/citations.py`: two-step verification | 1 d |
| 2.8 | `guardrails/`: input (injection, scope) + output (coverage, VMR, disclaimer) | 1.5 d |
| 2.9 | `cache/`: two-tier Redis, key including `as_of` | 1 d |
| 2.10 | `agent/graph.py`: the 11-node LangGraph | 1.5 d |
| 2.11 | `api/main.py`: `/api/chat` SSE + `/api/search` + `/healthz` | 1.5 d |

**Exit criteria:**

- [ ] A Vietnamese question returns a streaming answer citing to the Clause
- [ ] Changing `as_of` changes the retrieval result (verified by test)
- [ ] 100% of citations pass the mechanical check
- [ ] The second identical `(question, as_of)` hits the cache
- [ ] The cache **misses** when only `as_of` changes (mandatory regression test)

**→ Completes deliverables 3 (baseline) and 4 (method)**

---

### Phase 3 — Legal Intelligence (1.5 weeks)

| # | Task | Estimate |
|--:|------|---------:|
| 3.1 | `legal/conflict.py`: 7 types, 6-rule engine | 2 d |
| 3.2 | Four-tier legal diff | 1.5 d |
| 3.3 | Change events + `/api/changes` | 1 d |
| 3.4 | Impact analysis + `/api/impact-analysis` | 1 d |
| 3.5 | `/api/legal-rules?date=` (Time Machine) | 0.5 d |
| 3.6 | Web UI: 4 tabs + confidence light + citation panel | 2 d |
| 3.7 | Admin dashboard + `/metrics` | 1 d |
| 3.8 | `/api/feedback` + the feedback table | 0.5 d |

**Exit criteria:**

- [ ] Conflict Explorer displays the named adjudication rule
- [ ] Time Machine changes the displayed version when the date changes
- [ ] Legal diff shows Added/Modified/Removed
- [ ] The 🟢🟡🔴 light derives from observable signals (ADR-019)

---

### Phase 4 — Evaluation & submission artifacts (2 weeks)

| # | Task | Estimate |
|--:|------|---------:|
| 4.1 | Generate 120 eval questions from the corpus (source A) | 1 d |
| 4.2 | Write 50 hand-authored questions (source B) | 2 d |
| 4.3 | Write 40 adversarial questions (source C) | 1.5 d |
| 4.4 | Cross-review, compute Cohen's κ | 1 d |
| 4.5 | `eval/metrics.py`: 6 layers + LAA + TVA + VMR | 1.5 d |
| 4.6 | `eval/ragas_metrics.py` + judge calibration on 30 items | 1.5 d |
| 4.7 | `eval/ablation.py`: run the 5 configurations A–E | 1 d |
| 4.8 | The ≥20-payload injection suite + `eval/injection_suite.py` | 1 d |
| 4.9 | Analyse 20 hallucination cases, classify root causes | 1.5 d |
| 4.10 | Write `EVAL_REPORT.md`, `MODEL_CARD.md`, `benchmark.md` | 1.5 d |

**Exit criteria:**

- [ ] ≥ 200 eval questions, 100% of gold present in the corpus, κ ≥ 0.70
- [ ] A 5-configuration ablation table with confidence intervals
- [ ] A full RAGAS report with judge calibration (ρ ≥ 0.7)
- [ ] 20 hallucination cases with root-cause classification
- [ ] ASR ≤ 5% over ≥ 20 payloads
- [ ] **Every numeric table carries a backend column** (R-M09)

**→ Completes deliverables 1, 5, 6, 9**

---

### Phase 5 — Product & deployment (1 week)

| # | Task | Estimate |
|--:|------|---------:|
| 5.1 | `docker-compose.yml`: qdrant + redis + postgres + api + web | 1 d |
| 5.2 | Verify `docker compose up` on a clean machine | 0.5 d |
| 5.3 | English README + architecture diagram (SVG) | 1 d |
| 5.4 | GitHub Actions: test + lint + build | 0.5 d |
| 5.5 | Deployment configuration (2 platforms) | 1 d |
| 5.6 | Public deployment, obtain the URL | 0.5 d |
| 5.7 | Demo script + record the ≤3-minute video | 1 d |

**→ Completes deliverables 7, 8, 10, 11**

---

## 4. Critical path and parallelisation

```text
Week:   1    2    3    4    5    6    7    8    9
        │    │    │    │    │    │    │    │    │
P0  ███ │    │    │    │    │    │    │    │    │
P1      ████████ │    │    │    │    │    │    │
P2           │  ██████████  │    │    │    │    │
P3           │    │    │  ███████│    │    │    │
P4           │    │  ▓▓▓▓▓▓▓▓▓▓▓▓█████████  │   │   ← ▓ = eval-set build (parallel)
P5           │    │    │    │    │    │    │  ████
```

**Critical path:** `0.7 (parser) → 1.3 → 1.4 → 1.8 → 2.1 → 2.6 → 4.7 → 5.2`

**The most important parallelisation:** start **building the eval set (4.1–4.4)
from week 3**, as soon as the Gold layer holds data — do not wait for Phase 4.
This is the lesson of risk R-P04 (41 hours of work routinely underestimated).

**What to cut if behind schedule** (in cut order):

1. 3.4 Impact analysis
2. 3.7 Admin dashboard (keep `/metrics`)
3. 3.2 Legal diff tiers 3–4 (keep tiers 1–2)
4. 3.8 Feedback

Never cut anything belonging to deliverables 1–11.

---

## 5. Mapping to the 11 deliverables, with Definition of Done

| # | Deliverable | Phase | Definition of Done |
|--:|-------------|-------|--------------------|
| 1 | Problem statement & success metric | P4 | `docs/PROBLEM_STATEMENT.md` states the problem, 10 metrics with thresholds, LAA defined by formula |
| 2 | Dataset / data pipeline | P1 | `python -m virag.ingest.pipeline` runs Bronze → Gold; `data-quality.json` produced; corpus figures in `DATA_PIPELINE.md` |
| 3 | Baseline model | P2, P4 | `A-bm25-baseline` runs and has numbers in the ablation table |
| 4 | Method / main model | P2–P3, P4 | `E-full-temporal-legal` runs, has numbers, has an architecture description |
| 5 | Benchmark table | P4 | `reports/benchmark.md` — 5 configurations × ≥10 metrics, 95% CIs, **with a backend column** |
| 6 | Error analysis | P4 | `reports/hallucination-analysis.md` — 20 cases, root causes, real traces quoted |
| 7 | English README + diagram | P5 | `README.md` in English; `docs/architecture.svg` renders on GitHub |
| 8 | Runs with one command | P5 | `docker compose up` on a clean machine → open `localhost:8000` and ask a question |
| 9 | Model card / eval report | P4 | `MODEL_CARD.md` (limits, data, purpose) + `EVAL_REPORT.md` (full RAGAS) |
| 10 | Demo video ≤3 minutes | P5 | Video file, with the script in `DEMO_SCRIPT.md` |
| 11 | Deploy / demo link | P5 | A reachable public URL + `DEPLOYMENT.md` |

---

## 6. Decision gates

| Gate | When | Condition | If not met |
|------|------|-----------|------------|
| **G0** | End of P0 | ≥60 multi-version documents; ≥85% Article parse rate | Build VBHN chains / fix the parser before continuing |
| **G1** | End of P1 | ≥600 documents indexed; `UNKNOWN` <15%; ingest idempotent | Do not enter P2 — a wrong index makes every measurement meaningless |
| **G2** | End of P2 | Changing `as_of` changes results; 100% of citations pass the mechanical check | Fix before building new features |
| **G3** | Mid P4 | κ ≥ 0.70; judge Spearman ≥ 0.7 | Rewrite questions / fix the rubric — **never run the eval with an uncalibrated judge** |
| **G4** | End of P4 | Every result file has backend fields; no published result ran in fallback mode | Rerun with `--require-real-models` |

---

## 7. Cost estimate

### 7.1 LLM cost

| Activity | Estimated calls | Note |
|----------|----------------:|------|
| Development and experimentation | ~500 | Spread out |
| One full eval run (210 questions × 5 configurations) | 1,050 | Only configurations that use the LLM |
| RAGAS judge (210 × 5 metrics × 3 passes) | ~3,150 | Self-consistency |
| Judge calibration | ~450 | 30 items |
| Reruns (3 expected) | ×3 | After each fix |

**Cost-control measures (risk R-O03):**

1. Use `effort=medium` for Q&A, `high` only for conflict adjudication.
2. **Prompt caching** on the system prefix — most input tokens are reused.
3. Run the eval on a **50-question dev split** during development; run the
   **full 210** only at milestones.
4. Deterministic metrics (Numeric EM, Recall@K, TVA, VMR) need **no LLM** — they
   run free and unlimited.
5. Set a spending cap and monitor it; stop and review on breach.

### 7.2 Infrastructure cost

| Item | Estimate |
|------|----------|
| Development machine | Already available |
| Corpus storage | 4.4 GB — already available |
| Demo deployment | Smallest tier of a PaaS provider |

---

## 8. Working cadence

**Daily:** run `pytest` + `ruff` before ending the session.

**Weekly:**

1. Run the eval on the 50-question dev split → record in `reports/weekly/`.
2. Compare with the previous week; any metric dropping > 5 points must be
   investigated **before** new work begins.
3. Update the early-warning indicator table
   ([07 §7](07-risk-analysis.md)).
4. Record every new design decision as an ADR in
   [05](05-design-decisions.md).

**Whenever a real error is found:** turn it into a regression eval item
([07 §9](07-risk-analysis.md), step 5). The eval set must grow over time.

---

## 9. Do this now (this week)

In order, no reordering:

1. Install Python 3.11 and start Docker Desktop.
2. Fix `pyproject.toml` (the stray `y` at the end of the `select` line).
3. Run `pytest` + `ruff` on `tools/` to confirm the foundation still works.
4. **Count documents with ≥2 versions** — gate G0.
5. **Trial-run the parser on 50 PDFs** — gate G0.
6. Report the results of measurements 4 and 5 before writing any further code.

---

**Previous:** [07 — Risk analysis](07-risk-analysis.md)
**Next:** [09 — Evaluation & experiment plan](09-evaluation-plan.md)
