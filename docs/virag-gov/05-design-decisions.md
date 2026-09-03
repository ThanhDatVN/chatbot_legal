# 05 — Design Analysis (Architecture Decision Records)

> Document 04 describes what the system **is**. This document explains **why it
> is that way, which alternatives were considered, and what it costs**.
>
> Each decision follows: **Context → Options → Decision → Consequences (good
> *and* bad) → Revisit trigger**. An ADR without a downside section is an
> incomplete ADR.

---

## 0. Founding design principles

Every ADR below derives from these seven. When two principles conflict, the
lower number wins.

| # | Principle | Meaning |
|--:|-----------|---------|
| **P1** | **A silent wrong answer is worse than no answer** | Every mechanism must favour making errors detectable over hiding them |
| **P2** | **Time is mandatory, not optional** | `as_of` accompanies every query, every cache key, every citation |
| **P3** | **Cite to the Clause or do not speak** | No pin-point evidence, no conclusion |
| **P4** | **Legal decisions must be explainable** | The rule engine names its rule; the LLM is never the final arbiter |
| **P5** | **Data is immutable** | Never edit, never delete; only append new versions |
| **P6** | **Degrade gracefully, never crash** | Missing Qdrant/Redis/models → quality drops, the system still runs |
| **P7** | **Reproducible** | Same input + same corpus hash → same retrieval result |

---

## ADR-001 — Positioning: a system that determines the applicable provision, not a QA chatbot

**Context.** The original deliverables list describes a RAG chatbot with
citations. Both input analyses (A, B) conclude that this square is crowded and
non-differentiating.

**Options.**

| Option | Pros | Cons |
|--------|------|------|
| A. RAG chatbot with citations | Fast, low technical risk | No differentiation; does not address the temporal risk |
| B. Version-aware + conflict-aware system | Real research contribution; matches the legal reality | ~3× complexity; requires a multi-version corpus |
| C. Change Monitor only (drop chat) | Highly differentiated | Loses the most natural user interface |

**Decision.** Option **B**, with chat as one of four modules.

**Good consequences.** Falsifiable research questions (RQ1–RQ3). New metrics
(LAA, TVA, VMR). Faithful to the actual legal constraints.

**Bad consequences.** Substantially more work. Requires a multi-version corpus
which **does not yet exist** — the crawled corpus is mostly the latest version
of each document. This is **risk R-D02** in document 07.

**Revisit trigger.** If after Phase 2 fewer than 10% of documents have ≥2
versions in the corpus, either expand the historical crawl or narrow RQ2 to the
subset that does have enough versions.

---

## ADR-002 — Chunk on legal structure: parent = Article, child = Clause

**Context.** P3 requires citation to the Clause. Token-window chunking cuts
across Clauses and destroys that.

**Options.**

| Option | Citable to | Problem |
|--------|-----------|---------|
| A. Fixed 512-token window, 64 overlap | Page | Cuts mid-Clause; the citation is meaningless |
| B. Semantic chunking (embedding boundaries) | Undefined | Boundaries do not coincide with legal boundaries |
| C. One Article = one chunk | Article | Chunks too long; the Clause is diluted in the embedding |
| D. **Parent = Article, child = Clause** | **Clause** | Requires a reliable structure parser |

**Decision.** Option **D**. Embed and retrieve the **child**; hand the **parent**
to the LLM.

**Core reason.** A Clause is usually meaningless once separated from the
Article's opening sentence:

> "The following cases are exempt from tax: 1. … 2. …"

Clause 2 alone **does not carry the information "exempt from tax"**. Score the
Clause (the unit the user asks about), read the Article (enough context to
reason).

**Good consequences.** High Citation Precision. Article Recall and Clause Recall
become separately measurable. This is the `use_parent_expansion` variable in the
ablation.

**Bad consequences.** Entirely dependent on parser quality. On poor scans/OCR the
structure is unrecoverable → falls back to passage chunks, and citation degrades
to "Passage N". The **parse success rate must be measured as a first-class data
metric** (document 06 §5).

**Mitigation.** Where no Article is found, the citation label reads *"Passage N
— <instrument number>"* rather than inventing an Article number. Crude beats
wrong.

> ⚠️ **Known defects in the current scaffold** (see
> [12 — Defect register](12-defect-register.md), D-06):
>
> 1. **Unit mismatch.** `chunking.py:130` writes
>    `article_text[: parent_max_tokens * 8]` — a **token** budget multiplied by 8
>    and applied as a **character** limit. The two units are not
>    interchangeable; the bound must be computed on tokens.
> 2. **Tail truncation drops the retrieved clause.** The slice keeps the head of
>    a long Article and discards the tail. A Khoản near the end of a long Điều is
>    therefore **removed from the parent context by the very step meant to supply
>    its context** — parent expansion silently deletes the clause that retrieval
>    just selected. The fix is a window centred on the retrieved child, not a
>    head slice.
> 3. **No stable anchors.** Chunks carry `page_number` but no character offsets
>    or bounding boxes, and no hash binding to the authoritative artifact, so a
>    citation cannot be pinned to an exact span in the source PDF.
>    `docs/large-data-processing-plan.md:150` already specifies
>    "physical page, bbox, character offsets, source hash" as the target.

---

## ADR-003 — Qdrant instead of pgvector

**Context.** Document B proposes pgvector for the early stage — reasonable
operationally. But P2 requires filtering by validity.

**The decisive technical problem.** Filtering **after** retrieving top-k
**shrinks the result set**:

```text
Request the 30 nearest neighbours
   → receive 30 chunks, mostly from current-law documents
     (their language is closer to the question)
   → filter by as_of = 2021-06-15
   → 2 chunks remain
```

Recall@10 collapses with no warning.

**Options.**

| Option | Filter location | Result |
|--------|-----------------|--------|
| A. pgvector + `WHERE` after ORDER BY | After top-k | Top-k shrinks — **unacceptable** |
| B. pgvector + fetch top-500 then filter | After, compensated by large k | Wasteful; still no guarantee |
| C. pgvector + partial indexes per year | Before | Index explosion; cannot express open intervals |
| D. **Qdrant + payload filter** | **During traversal** | Top-k stays top-k |

**Decision.** Option **D**. Dates are stored as **integer days-since-epoch**
(`effective_from_days` / `effective_to_days`) with sentinels for unknown bounds,
because integer range filters are fully supported and fast on every backend.

**Good consequences.** The temporal filter is **semantically correct at the
retrieval level**. Payload indexes on 5 fields make additional filtering by tax
domain and legal tier essentially free.

**Bad consequences.** One more service in compose. Relational metadata still
lives in PostgreSQL → **two sources of truth** requiring synchronisation.
Mitigation: the Qdrant payload holds only the fields **used for filtering**;
canonical content lives in `ChunkStore` + PostgreSQL, and `chunk_id` is the sole
join key.

**Revisit trigger.** Beyond ~5 million chunks or if sharding is needed, consider
Milvus. If the time axis were abandoned entirely (it will not be), pgvector
suffices.

---

## ADR-004 — Hybrid BM25 + dense, fused with RRF

**Context.** Two query types coexist in this domain:

| User type | Typical query | Winner |
|-----------|---------------|--------|
| Tax specialist | `"Điều 9 Luật 48/2024/QH15"` | BM25 dominates |
| Operational accountant | `"software export what tax rate"` | Dense dominates |

A system with only one half breaks on half the traffic.

**Fusion options.**

| Option | Problem |
|--------|---------|
| A. Weighted score addition | BM25 scores (unbounded) and cosine ([-1,1]) are **not on the same scale**; requires per-corpus recalibration |
| B. Min-max normalise then add | Outlier-sensitive; one anomalously high chunk distorts everything |
| C. **RRF** — `score(d) = Σᵢ wᵢ / (k + rankᵢ(d))` | Uses **ranks only**, not scores → no calibration needed |

**Decision.** **RRF** with `k = 60`, weights `[1 − dense_weight, dense_weight]`,
`dense_weight = 0.5` by default.

**Good consequences.** No parameter needs retuning when the corpus or the
embedding model changes. Stable.

**Bad consequences.** RRF discards information about the **margin** between
ranks — a clearly dominant chunk and a marginally better one are treated
identically. Accepted: the cross-encoder in the next stage restores fine
ordering.

---

## ADR-005 — Write BM25 and the Vietnamese tokenizer in-house

**Context.** `rank_bm25`, Elasticsearch and OpenSearch all exist.

**The problem.** Default tokenizers **destroy exactly the highest-value tokens**:

| String | Generic tokenizer | Must preserve |
|--------|-------------------|---------------|
| `48/2024/QH15` | `48`, `2024`, `qh15` | `vb:48/2024/qh15` |
| `10%` | `10` | `pct:10%` |
| `Điều 9` | `điều`, `9` | `ref:điều9` |
| `giá trị gia tăng` | 4 loose unigrams | + bigrams `giá_trị`, `trị_gia`, `gia_tăng` |

The first three rows are the **highest-precision queries** a professional user
can supply. Losing them forfeits the sparse branch's biggest advantage.

**Options.**

| Option | Downside |
|--------|----------|
| A. `rank_bm25` + preprocessing | Still requires writing the tokenizer; adds a dependency for the easy part |
| B. Elasticsearch + custom analyzer | Another JVM service; far too heavy for ~10⁵ chunks |
| C. **In-house Okapi BM25 + domain tokenizer** | Must be tested by us |

**Decision.** **C**. ~200 lines, index persisted as JSON so it is diffable and
reproducible (P7).

**Bad consequences.** We own the correctness of the IDF formula and length
normalisation → **unit tests against known worked examples are mandatory**.

---

## ADR-006 — Cross-encoder reranking after fusion, over top-20

**Context.** Bi-encoders encode query and passage **independently**, so they
cannot distinguish "rate is 10%" (answers "what rate?") from "rate is 0%" (does
not).

**Decision.** `BAAI/bge-reranker-v2-m3` over the **post-RRF top-20**, not the
full candidate list.

**Reason for that position.** A cross-encoder costs roughly an order of
magnitude more than a bi-encoder. Twenty pairs keeps P95 inside the 8-second
budget; two hundred does not.

**Bad consequences.** If the correct chunk falls outside the post-RRF top-20 the
reranker **cannot rescue it**. Therefore `top_k_sparse` and `top_k_dense`
(30/30) must be wide enough — a parameter to measure, not to guess.

---

## ADR-007 — Time: hard filter when known, graded score when unknown

**Context.** This is the project's **most important design decision**, and it
collides head-on with an uncomfortable data fact:

> **160 of 698 (22.9%)** crawled documents have **no `effective_date`** in the
> portal metadata.

**Options.**

| Option | Consequence |
|--------|-------------|
| A. No date = treat as in force | 160 unverified documents enter **every** answer |
| B. No date = discard | Loses **23% of the corpus**; Recall collapses |
| C. **Hard-filter when both bounds known; down-weight when missing; always show status** | More complex, but honest |

**Decision.** **C**, concretely:

```text
in_force(from, to, as_of):
    from and as_of < from  → False
    to   and as_of > to    → False
    otherwise              → True     (unknown bound ⇒ not excluded)

validity_score:
    1.00  in force, BOTH bounds known
    0.70  in force, ONE bound missing
    0.50  no bound known
    0.25  out of force but adjacent (≤ 365 days)
    0.00  out of force, far
```

Plus a **safety valve**: if the temporal filter empties the candidate set, the
system **falls back to the unfiltered set** and logs it, rather than returning
nothing. Returning nothing because of missing metadata is a worse failure than
returning a flagged result.

**Good consequences.** The 23% is not lost. Uncertainty is **surfaced** rather
than hidden — a 🟡 light whenever an `UNKNOWN` document is involved.

**Bad consequences.** TVA **cannot reach 1.0** on the portion of the corpus
lacking dates. That is a limitation of the data, not the model — and the report
must say so, splitting TVA into two figures: over the whole set, and over the
subset with complete date metadata.

**Follow-on work.** Backfilling effective dates for those 160 documents from the
Official Gazette is the **highest-priority data task** (document 06 §12).

---

## ADR-008 — A composite score with legal hierarchy

**Context.** The real situation:

```text
similarity:  Official Letter = 0.92   |   Law = 0.89
```

Choosing the Official Letter is **legally wrong**, regardless of score.

**Decision.**

```text
Score = α·Semantic + β·Authority + γ·Temporal + δ·Specificity + ε·CitationQuality
        0.55         0.15          0.20         0.07           0.03
```

**How the weights were chosen — and their limitation.** Four constraints shape
the numbers:

1. `α` must dominate — otherwise the system returns correctly-tiered but
   irrelevant documents.
2. `γ > β` — being wrong about time is more dangerous than being wrong about
   tier (a Circular in force beats a Law that has been replaced).
3. `β` must be large enough to overturn the typical semantic gap between an
   Official Letter (tier 9, authority = 0) and a Law (tier 2, authority =
   0.875): `0.15 × 0.875 ≈ 0.131`, enough to flip a post-normalisation semantic
   gap of ~0.13.
4. `δ` and `ε` are tie-breakers only.

> ⚠️ **Honest status:** this weight set is **derived from constraints, not
> optimised on data**. It is a reasonable starting point, not an experimental
> result. Calibration plan: a coarse grid search on the dev set
> (`α ∈ {0.45, 0.55, 0.65}`, `γ ∈ {0.15, 0.20, 0.25}`), selected by LAA, with a
> sensitivity analysis reported. See
> [document 09 §7](09-evaluation-plan.md).

**Bad consequences.** Five hyperparameters are five chances to overfit the dev
set. Mitigation: tune only 2 (`α`, `γ`), hold the other 3 fixed, and report the
default-weight result alongside the tuned one.

---

## ADR-009 — The rule engine decides conflicts; the LLM only detects them

**Context.** P4. A decision that "Circular B beats Circular A" must be
defensible before a tax authority. "The model thought so" is not a
justification.

**Options.**

| Option | Accuracy | Explainable | Reproducible |
|--------|----------|-------------|--------------|
| A. LLM decides | Possibly high | ✗ | ✗ |
| B. LLM decides + is asked to explain | High | The explanation **may be post-hoc rationalisation** | ✗ |
| C. **Rule engine decides; LLM only nominates** | To be measured | ✓ named rule | ✓ |

**Decision.** **C**. Six rules in order: Temporal → Lex superior → Amendment →
Formal-vs-guidance → Lex specialis → Lex posterior. When no rule applies,
return **`winner = None`** and state that expert review is required.

**Why abstention is a feature.** Implicit repeal is a question lawyers still
argue about. A system that confidently adjudicates it is exceeding the certainty
of the field itself.

**Bad consequences.** Lower coverage — many cases fall into "not adjudicated".
This is a deliberate trade under P1. Tracked metrics: `CRA` (accuracy when a
decision is made) **and** `Coverage` (share of cases receiving a decision) —
report **both**, because a rule engine that is 100% accurate on 5% of cases is
useless.

---

## ADR-010 — Immutable, bitemporal versioning

**Context.** The crawler runs on a schedule and will re-download the same
document.

**The rejected anti-pattern:**

```text
DELETE old document → INSERT new document
```

Destroys: issued citations · answer history · version links · embeddings.

**Decision.**

```text
Normalise text → SHA-256
   ├── hash matches    → no-op (ingest is idempotent)
   └── hash differs    → close the old version (superseded_at = now) → append new
```

Two time axes: **valid time** (`effective_from/to`) and **transaction time**
(`ingested_at/superseded_at`).

**Why both are needed.** The audit question *"what did the system know on
2025-01-03?"* is answerable only with transaction time. If a user disputes an
answer given six months ago, the knowledge state at that moment must be
reconstructible.

**Bad consequences.** Data only grows. A long-term retention policy is needed.
Estimate: 13k documents × ~2 versions/year × 5 years ≈ 130k version rows —
not a concern at this scale.

---

## ADR-011 — `legal_status` at Clause level, not document level

**Context.**

```text
Circular B: "Amends Khoản 2 Điều 3 of Circular A"
```

`{"document_status": "amended"}` on all of Circular A says **all four Articles
are suspect**, when in reality **one Clause** changed.

**Decision.** Status attaches at chunk (Clause) level, with 9 values:

```text
ACTIVE · PARTIALLY_AMENDED · PARTIALLY_REPEALED · REPLACED
EXPIRED · SUSPENDED · NOT_YET_EFFECTIVE · SUPERSEDED · UNKNOWN
```

**Bad consequences.** Deriving Clause-level status requires resolving the
pointer "Khoản 2 Điều 3" in the amending text to the right `chunk_id` — a
non-trivial entity-linking problem. When it cannot be resolved, fall back to
Article level, then document level, and **record which granularity was used**.

---

## ADR-012 — LangGraph state machine, not a function chain

**Context.** The flow has 3 early exits (`blocked`, `clarify`, `refuse`) and 1
bounded loop (`regenerate`, at most once).

**Decision.** A state machine where each node is a pure function over state.

**Reason.** Nested if/else makes it **impossible to test branches
independently**. For a system whose "refusal branch" is a first-class safety
feature (P1), an untestable refusal branch is unacceptable.

**Bad consequences.** One more dependency and one more mental model. For a new
team member LangGraph is a learning cost. Mitigation: every node is a plain
Python function, directly callable and testable without the graph.

---

## ADR-013 — Claude Opus 5, streaming, prompt caching

**Decision.**

| Setting | Value | Reason |
|---------|-------|--------|
| Model | `claude-opus-5` | Long-horizon reasoning; good Vietnamese; 1M context |
| Thinking | `{"type": "adaptive"}` | The default for the current model line |
| Effort | `medium` (Q&A) / `high` (conflict) | Conflicts need multi-step reasoning |
| Streaming | Mandatory | Early first token; avoids timeouts |
| Prompt caching | System + citation contract | Cuts cost on the stable prefix |
| Prefill | **Not used** | Rejected on the current model line |

**The critical caching detail.** Caching is a **prefix match**: one changed byte
anywhere in the prefix invalidates everything after it. Hence the mandatory
order:

```text
[fixed system + citation contract]   ← cache_control here
[retrieved context]                   ← variable
[question + as_of]                    ← most variable
```

Putting `as_of` or a timestamp in the system prompt **disables caching entirely**
with no error raised. Verify via `usage.cache_read_input_tokens`.

**Bad consequences.** Single-vendor dependency. Mitigation: the
`generation/llm.py` layer has an abstract interface plus an extractive fallback
backend for offline operation; swapping vendors means replacing one layer.

---

## ADR-014 — The `[Sn]` citation contract with two-step verification

**Context.** P3. Citations must be machine-checkable, not taken on faith.

**Decision.** Context is numbered `[S1] … [Sn]`, each block carrying its citation
label, validity interval and legal tier. The model must attach `[Sn]` to **every
normative assertion**.

Verification in **two steps**, and the order matters:

| Step | Checks | Catches | Cost |
|-----:|--------|---------|------|
| 1 | Does `[Sn]` exist in the context we sent? | **Wholly fabricated citations** | ~0, deterministic |
| 2 | Does the sentence carrying `[Sn]` follow from that chunk? | Content-mismatched citations | LLM/NLI |

Step 1 is **mechanical and deterministic** — it catches the most dangerous
failure class without any model. Only what passes step 1 incurs step 2's cost.

**Bad consequences.** The format constraint makes answers read less naturally.
Accepted: the target users are professionals who need evidence more than prose.

---

## ADR-015 — The semantic cache key **must** include `as_of`

**Context.** A semantic cache groups similar questions.

**The trap.** Two questions:

```text
"What is the VAT rate for transport services?"  as_of = 2026-09-03
"What is the VAT rate for transport services?"  as_of = 2021-06-15
```

have **nearly identical embeddings**. If the cache key rests on the question
alone, the second receives the first's cached answer — **the cache becomes a
source of temporal misgrounding**, and worse: this failure **bypasses the entire
temporal filtering pipeline** that was built.

**Decision.** Key = `hash(normalised question ‖ as_of ‖ config_name)`. The
semantic tier only compares within the **same `as_of` bucket**.

**Invalidation.** When a `change_event` touches a `document_id` appearing in a
cached answer's citations, drop that cache entry.

**Note.** This is a textbook case of a harmless optimisation in ordinary systems
becoming a safety defect in a legal one.

---

## ADR-016 — Graceful degradation at every layer

**Context.** P6 plus a practical constraint: deliverable 8 requires
`docker compose up` to work **on the reviewer's machine**, which may have no
GPU, no model cache and no API key.

**Decision.** Every heavy component has a substitute backend:

| Component | Primary | Fallback | What is lost |
|-----------|---------|----------|--------------|
| Embedding | BGE-M3 | `HashingEmbedder` (deterministic char/word n-grams) | Semantics; lexical retained |
| Reranker | bge-reranker-v2-m3 | `LexicalReranker` | Ranking precision |
| Vector store | Qdrant | `NumpyVectorStore` (linear scan) | Speed at scale |
| LLM | `claude-opus-5` | Extractive generation from context | Fluency; citations retained |
| DB | PostgreSQL | SQLite | Concurrency |
| Cache | Redis | Skipped | Cost, latency |

**Mandatory rule.** Every reported measurement **must record the backend used**.
A benchmark table produced with `HashingEmbedder` that does not say so is a
**false report**.

**Bad consequences.** More code paths, more latent bugs. Mitigation:
`SearchFilters.matches()` (the in-memory version) and the Qdrant filter must be
cross-tested so they cannot drift apart.

---

## ADR-017 — Plain HTML/JS frontend, not Next.js (v1)

**Context.** Document B proposes Next.js. Deliverable 8 requires **one command**.

**Analysis.** Next.js adds: a Node runtime in the image, a build step, ~1–3
minutes of build time, and a new class of failure ("where do I install `npm`?").
In exchange: routing, SSR, a component ecosystem — **none of which** is needed
for 4 tabs and a dashboard.

**Decision.** Plain HTML + JS served statically by FastAPI. SSE consumed with
the native `EventSource`.

**Revisit trigger.** When user authentication, business profiles and
notifications arrive — that is Phase 4. At that point Next.js earns its cost.

---

## ADR-018 — Dependency graph in PostgreSQL, not Neo4j (v1)

**Context.** Document B proposes Neo4j.

**Scale analysis.** ~13k documents, each declaring ~2–8 explicit edges →
estimated 30–100k edges. Required queries: `incoming(X)`, `outgoing(X)`, and BFS
to **depth ≤ 3**. A table with an index on `target_instrument` handles this in
milliseconds.

**Decision.** A `legal_relations` table plus BFS in application code, bounded by
depth.

**When Neo4j would win.** Variable-length path queries, cycle detection, graph
algorithms (PageRank over a citation network). None of these appear in v1.

**Bad consequences.** If Phase 3 expands into complex multi-hop impact analysis,
a migration becomes necessary. Mitigation: `LegalGraph` is an abstraction;
swapping the backend does not touch call sites.

---

## ADR-019 — Confidence as a three-light signal derived from observable evidence

**Context.** The temptation: display `Confidence = 87.5%`.

**The problem.** That number is meaningless. LLMs are **poorly calibrated** — a
self-reported probability does not match the empirical frequency of being right.
Displaying it systematically **miscommunicates**, and in the legal domain
miscommunicating certainty is a safety defect.

**Decision.** Three levels derived from **measurable signals**, not from the
model:

| Level | Condition (all must hold) |
|-------|---------------------------|
| 🟢 Clear legal basis | `as_of` explicit · every citation `ACTIVE` at `as_of` · no unresolved conflict · citation coverage ≥ 0.8 |
| 🟡 Needs more information | `as_of` inferred · **or** an `UNKNOWN` document present · **or** a conflict that was resolved |
| 🔴 Needs expert review | No `as_of` · **or** unresolved conflict · **or** the highest basis found is only an Official Letter · **or** coverage < 0.6 |

Always accompanied by a **stated reason**, e.g. *"The result depends on the date
the transaction arose."*

**Good consequences.** The light is **reproducible** and **auditable** — the same
input yields the same colour, and the reason is explainable.

---

## ADR-020 — Four-tier legal diff, LLM last

**Decision.** `Hash → Text diff → Embedding → LLM`.

**The primary reason is not cost but reproducibility.** Tiers 1–3 are
deterministic: rerunning yields **the same** result. Only what reaches tier 4 is
stochastic. A "what did the new regulation change" report that produces
different output on two runs is unusable for legal purposes.

**Bad consequences.** Aligning Articles across versions (tier 3) is hard when a
document renumbers. Accepted with a low-confidence `MOVED` label.

---

## ADR-021 — Refusal as a first-class behaviour with its own metric

**Context.** Most RAG systems optimise for "always produce something".

**Decision.** Three exits: `blocked` (guardrail), `clarify` (missing date),
`refuse` (insufficient evidence). Each carries its own eval label.

**Measured by a matrix, not a single number:**

| | Should answer | Should decline |
|--|---------------|----------------|
| **Answered** | ✅ | ❌ **over-confident** — most dangerous |
| **Declined** | ❌ over-cautious | ✅ |

Report **both** Abstention Accuracy **and** Over-confidence Rate. A system that
declines everything has Hallucination Rate = 0 and is entirely useless —
reporting one number alone would reward that behaviour.

---

## ADR-022 — Modular monolith, not microservices

**Decision.** One FastAPI process with clear module boundaries.

**Reason.** Microservices trade network latency, deployment complexity and
debugging difficulty for independent scaling and team autonomy — **neither of
which** a one-person, one-server project needs.

**The exit is pre-planned.** Correctly placed module boundaries will cut into
services later: `ingest` (batch, CPU-heavy) and `api` (long-running, light) are
the first two extraction candidates.

---

## ADR-023 — Implement the RAGAS metrics in-house rather than using the `ragas` package

**Context.** Deliverable 9 requires a "full RAGAS report".

**Options.**

| Option | Pros | Cons |
|--------|------|------|
| A. The `ragas` package | Reference standard, uncontroversial | Pulls a heavy LangChain dependency chain with tight version pins; hard to pin the judge for reproducibility |
| B. **Implement from the definitions** | Control over judge, prompts, self-consistency; no dependency conflicts | We must prove the implementation is correct |

**Decision.** **B**, with three mandatory constraints so the results carry
weight:

1. Record the formulas and judge prompts in `reports/judge-prompts/`.
2. Calibrate against **30 hand-scored items**; report the human ↔ judge Spearman
   correlation. **ρ < 0.7 ⇒ not usable.**
3. Keep the `ragas` package as an optional extra; if installable, run it as a
   cross-check and report both columns.

**Bad consequences.** The burden of proof is ours. Without step 2, an in-house
RAGAS number is no more convincing than a fabricated one.

---

## ADR-024 — Scope authority: the September dossier governs the immediate project

**Context.** Two document sets disagree about scope, and both claim authority.

| | August design set | September dossier |
|--|-------------------|-------------------|
| Location | `docs/design/00-08` | `docs/virag-gov/` |
| Authority claim | `00-design-index.md` §7 names the **PRD as the source of truth** for "Why / scope / success" | `08-implementation-plan.md` treats the **11 deliverables as the contract** |
| Scope | Multi-tenant case workspace: uploads, calculators, review workflows, retention, **40 requirements** | 9-week project: Qdrant, plain HTML/JS, no case workspace |

Verified: `docs/design/00-design-index.md:117–120` does state
`Why / scope / success -> PRD`, and `docs/design/01-product-requirements.md`
contains exactly **40** `R-xx` requirements. The conflict is real, not
apparent.

**Options.**

| Option | Consequence |
|--------|-------------|
| A. PRD governs | The immediate project balloons to a multi-tenant product; the 11 deliverables slip indefinitely |
| B. Dossier governs, PRD discarded | Loses genuine product design work that remains valid |
| C. **Dossier governs the immediate project; PRD becomes the post-delivery roadmap** | Two clear horizons; nothing is lost |

**Decision.** Option **C**.

1. The **September dossier is the source of truth for the immediate project**.
   Its contract is the 11 deliverables.
2. The **PRD remains the source of truth for the product roadmap** after those
   deliverables pass their gates.
3. `docs/design/00-design-index.md` §7 is hereby **scoped**: "PRD is the source
   of truth for scope" applies to the **product**, not to the immediate
   9-week project.

**Explicitly deferred from the immediate contract** (moved to the roadmap, not
rejected):

| Deferred | Belongs to |
|----------|-----------|
| Tenant isolation, matters/case workspace | Roadmap phase 1 |
| Document upload by users | Roadmap phase 1 |
| **Deterministic VAT calculators** | Roadmap phase 2 |
| Review / approval workflow | Roadmap phase 2 |
| Export, retention policy | Roadmap phase 2 |
| Alerts, enterprise authentication | Roadmap phase 3 |

**Explicitly retained in the immediate contract:** Ask, Time Machine, Change
Monitor, Conflict Explorer, citation verification, guardrails, the evaluation
suite, Docker, deployment.

**Good consequences.** No further ambiguity about what "done" means. The
calculator question — previously undecided between the two document sets — is
now settled: **deferred**.

**Bad consequences.** The PRD's 40 requirements are not traceable to code in
this project, so PRD-based traceability reporting is not available until the
roadmap phase begins. Accepted.

**Revisit trigger.** After deliverable 11 passes, reopen the PRD as the
governing document and re-baseline.

---

## 24. Rejected designs

Recorded so nobody proposes them again without new information.

| Design | Why rejected |
|--------|--------------|
| Index only the latest consolidated document (VBHN) | Destroys the ability to answer questions about the past — the central problem |
| Fine-tune an LLM on the tax corpus | Knowledge frozen in weights; not updatable; not citable; not auditable |
| Let the LLM decide conflicts and explain itself | An explanation generated **after** the decision may be rationalisation, not the actual reason |
| Show confidence as a percentage | LLMs are poorly calibrated; miscommunicates certainty |
| Fixed token-window chunking | Breaks Article/Clause structure → loses pin-point citation |
| Filter by time after retrieving top-k | Shrinks the result set; Recall collapses silently |
| Semantic cache without `as_of` in the key | Turns the cache into a source of temporal misgrounding |
| Use News / User Content as corpus sources | Not legal sources; not verifiable |
| Automatically compute the tax owed | Out of v1 scope; high liability; needs a deterministic tool, not an LLM |

---

## 25. Traceability matrix: principles → decisions

| | P1 silent error | P2 time | P3 citation | P4 explainable | P5 immutable | P6 degrade | P7 reproducible |
|--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| ADR-002 chunking | | | ● | | | | |
| ADR-003 Qdrant | | ● | | | | | |
| ADR-005 in-house BM25 | | | | | | | ● |
| ADR-007 temporal | ● | ● | | | | ● | |
| ADR-008 ranking | | ● | | ● | | | |
| ADR-009 rule engine | ● | | | ● | | | ● |
| ADR-010 versioning | | ● | ● | ● | ● | | |
| ADR-011 clause status | | ● | ● | | | | |
| ADR-014 citation | ● | | ● | ● | | | ● |
| ADR-015 cache key | ● | ● | | | | | |
| ADR-016 fallbacks | | | | | | ● | |
| ADR-019 confidence light | ● | | | ● | | | ● |
| ADR-020 four-tier diff | | | | ● | | | ● |
| ADR-021 refusal | ● | | | | | | |

No row is empty — every decision traces to at least one principle. No column is
empty — every principle is realised by at least one decision.

---

**Previous:** [04 — System architecture](04-system-architecture.md)
**Next:** [06 — Data and data pipeline](06-data-pipeline.md)
