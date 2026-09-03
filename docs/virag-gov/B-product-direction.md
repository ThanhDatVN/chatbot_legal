# B — Product Direction Analysis

> **Provenance:** edited from `add_details.md` (original preserved at
> [`_source/add_details.original.md`](_source/add_details.original.md), in
> Vietnamese). Every argument of the original is kept, reordered, with
> trade-off analysis added and annotations marking where the final architecture
> departs from the original proposal (see
> [05 — Design decisions](05-design-decisions.md)).

---

## 1. Product positioning

If the goal is a product that is **genuinely impressive on a CV/portfolio and
to businesses**, do not build it as:

> ❌ "A tax-law Q&A chatbot using RAG"

Position it instead as a **Tax Legal Intelligence Platform** with the data, AI
and operational architecture of a real product.

Someone reading the CV or the GitHub repository should come away with:

> **You do not merely call an LLM API and build a chatbot. You can design an AI
> system with live data, conflict handling, versioning, temporal reasoning and
> production deployment.**

**Proposed concept names:** TaxLens AI · VietTax Intelligence · TaxMind ·
TaxGraph AI · TaxScope · VTax AI.

> **Project decision:** keep **ViRAG-Gov** as the project code for the research
> side (the name used in the deliverables list) and use **Vietnam Tax Legal
> Intelligence Assistant** as the displayed product name.

### 1.1 Three value layers

```text
┌──────────────────────────────────────────────┐
│                 USER LAYER                   │
│  💬 Ask AI                                    │
│  📅 Legal Time Machine                        │
│  🔄 Regulation Change Monitor                 │
│  ⚖️ Conflict Explorer                         │
│  🔔 Personalized Tax Updates                  │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│                  AI LAYER                    │
│  Intent Detection · Temporal Reasoning       │
│  Hybrid Retrieval · Legal Knowledge Graph    │
│  Conflict Detection · Citation Validation    │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│                 DATA LAYER                   │
│  Official Sources · Crawling Pipeline        │
│  Document Processing · Version Control       │
│  PostgreSQL · Vector DB · Graph DB · Storage │
└──────────────────────────────────────────────┘
```

---

## 2. AI Tax Assistant — it does not answer immediately

The chatbot does not answer immediately. It runs a pipeline:

```text
User Question → Intent Classification → Extract Tax Type → Extract Entity Type
→ Extract Time → Check Missing Information → Clarification Question
→ Hybrid Retrieval → Version Filtering → Conflict Checking
→ Answer Generation → Citation Validation
```

**Example:** *"Does my company have to pay VAT?"*

The system recognises missing information:

```text
Entity type: Unknown · Business sector: Unknown
Time: Unknown       · Revenue: Unknown
```

Instead of hallucinating, it asks back **through UI choices**, not an open
question:

```text
🏢 Business type?              📅 When did the event occur?
   ○ Company                      ○ Now
   ○ Household business           ○ In the past (pick a date)
   ○ Individual                   ○ Not sure
```

**Why this is good UX:** the user does not need to know how to phrase a legal
question precisely. The system takes responsibility for gathering the necessary
facts instead of pushing that burden onto the user.

> **Added analysis — the trade-off:** asking back increases turn count and
> becomes irritating if overused. The control rule: ask only when the **missing
> fact changes the answer**, at most **one round**, and always offer an escape
> option ("answer under current law"). Tracked metrics: **Clarification Rate**
> (target 15–25%) and **Over-clarification Rate** (asked but the answer did not
> change — target ≤ 5%).

---

## 3. Module 1 — Legal Time Machine

The user asks: *"In 2021, which VAT rules applied to my business?"*

```text
┌─────────────────────────────────────┐
│ Applicable legal provisions         │
│  ◄──────●──────────────►            │
│ 2020   2021   2022   2023   2024    │
│ Selected: 15/06/2021                │
└─────────────────────────────────────┘
```

Backend:

```text
Question + Event Date → Legal Version Resolver
→ Find all applicable documents → Filter by effective date
→ Check amendments → Retrieve applicable version
```

The user can view: **📜 Current provision · 🔄 2021 version · 🆚 Compare changes**

---

## 4. Module 2 — Regulation Change Monitor

```text
New Circular Detected → Document Processing
→ Compare With Previous Documents → Change Extraction → Impact Analysis
```

Dashboard:

```text
🔴 3 significant changes

1. VAT
   ├── Rate adjustment
   └── Effective: 01/01/2027

2. Corporate income tax
   ├── Additional covered entities
   └── 12 business profiles may be affected

3. E-invoicing
   └── Procedure change
```

This is **Legal Change Intelligence** — the largest differentiator from an
ordinary chatbot.

---

## 5. Module 3 — "What changed?" Legal Diff

```text
┌────────────────┬────────────────┐
│ OLD VERSION    │ NEW VERSION    │
├────────────────┼────────────────┤
│ Rate 10%       │ Rate 8%        │
│ Condition A    │ Condition B    │
│ No C           │ + C added      │
└────────────────┴────────────────┘

🟢 Added   🟡 Modified   🔴 Removed
```

### 5.1 Do not LLM-diff the whole document

Tiered from cheap to expensive:

| Tier | Technique | Handles |
|-----:|-----------|---------|
| 1 | Hash comparison (normalised SHA-256) | "Unchanged" — instant, ~zero cost |
| 2 | Text diff (SequenceMatcher / Myers) | Changes inside aligned Articles |
| 3 | Embedding similarity | Articles renumbered or moved |
| 4 | LLM classification | Final semantic labelling |

Result: `UNCHANGED · MODIFIED · ADDED · REMOVED · MOVED · REPEALED`

> **Added analysis:** the tier order exists not only to save cost but to make
> results **stable**. Tiers 1–3 are **deterministic** — rerunning gives the same
> result. Only what reaches tier 4 is stochastic. If the LLM diffed the whole
> document, the entire change report would become irreproducible, and an
> irreproducible legal report is unusable.

---

## 6. Module 4 — Conflict Explorer

```text
Question → Relevant Legal Sources
   ├── Law
   ├── Decree
   ├── Circular
   └── Administrative Guidance
→ Conflict Analysis
```

UI:

```text
⚖️ Possible Regulatory Conflict

Document A  ↓  Document B

Reason:     Document B modifies Article 5 of Document A.
Resolution: Document B applies from 01/01/2025.
```

Crucially, the system **must not pretend to 100% certainty**:

```text
🟢 High Confidence   🟡 Requires Review   🔴 Potential Conflict
```

---

## 7. Personalized Tax Profile

```text
Business Type: ☑ SME
Industry:      ☑ Technology
Revenue Range: ☑ 10–50 billion VND
Location:      ☑ Vietnam
```

```text
New Regulation → Legal Impact Engine → User Profiles → Affected Users → Notification
```

> 🔔 "A new regulation may affect your business."

This turns the product from **Passive Search** into **Proactive Legal
Intelligence**.

> **Scope decision:** this feature needs a user system, notifications and a
> background queue. Assigned to **Phase 4**, out of scope for v1. See
> [08 — Implementation plan](08-implementation-plan.md).

---

## 8. Backend architecture

Do not start with complex microservices. Start with a **Modular Monolith**.

```text
Backend
├── API Layer          ├── Document Module
├── Auth Module        ├── Crawling Module
├── Chat Module        ├── Legal Version Module
├── Retrieval Module   ├── Conflict Module
                       └── Notification Module
```

After scaling:

```text
                API Gateway
   ┌────────────────┼────────────────┐
Chat API      Document API       User API
   │                │
AI Service    Processing Queue
   │                │
Retrieval     Document Workers
```

### 8.1 Proposed stack (original) versus final decision

| Layer | Original proposal | Project decision | Reason for divergence |
|-------|-------------------|------------------|-----------------------|
| Backend | FastAPI | ✅ FastAPI | — |
| AI orchestration | LangGraph / custom | ✅ LangGraph | — |
| Database | PostgreSQL | ✅ PostgreSQL | — |
| Vector | **pgvector initially** | ⚠️ **Qdrant** | The validity filter must run **during index traversal**; filtering afterwards shrinks top-k. See [ADR-003](05-design-decisions.md) |
| Graph | Neo4j | ⚠️ **PostgreSQL (relations table)** | ~13k documents, sparse edges; another DBMS is operational cost buying no capability needed in v1 |
| Queue | Celery / RabbitMQ | ⚠️ **Deferred** | v1 ingest runs in batches; no queue needed yet |
| Object Storage | MinIO / S3 | ⚠️ **Deferred** | Raw bytes already on disk with checksums |
| Frontend | Next.js | ⚠️ **Plain HTML/JS** | Keeps `docker compose up` to **one** command, no build step |
| Deployment | Docker | ✅ Docker Compose | — |

> Every divergence is a **deliberate deferral**, not a rejection. Full reasoning
> in [05 — Design decisions](05-design-decisions.md).

---

## 9. Database architecture

`documents / chunks / embeddings` alone is not enough. Design instead:

```text
Legal Document
├── Document Version
├── Article
│     └── Clause
│           └── Point
├── Legal Relations
└── Change Events
```

```sql
documents          (id, document_number, document_type, issuer, title, issue_date)
document_versions  (id, document_id, version_number, effective_from, effective_to,
                    status, source_url, content_hash)
legal_articles     (id, version_id, article_number, title, content)
legal_relations    (source_id, target_id, relation_type, confidence)
```

Relations: `AMENDS · REPEALS · REPLACES · REFERENCES · GUIDES · CONFLICTS`

---

## 10. Handling data conflicts — Immutable Versioning

When the crawler re-downloads a document, **do not**:

```text
DELETE old document → INSERT new document    ✗
```

That destroys: existing citations · answer history · legal versions ·
embeddings.

Instead:

```text
Document
├── Version 1   (never edited)
├── Version 2
└── Version 3
```

### 10.1 Hash-based duplicate detection

```text
Downloaded Document → Normalize Text → SHA-256 → Compare Hash
   ├── Same Hash      → Skip
   └── Different Hash → Create New Version
```

### 10.2 Idempotent crawling

The crawler may run today, tomorrow, next week — repeated runs **must not
create duplicates**.

```text
crawl_job_id · source_id · document_id · content_hash
```

```text
Same input + Same processing = Same result
```

### 10.3 Scheduled crawling

```text
Scheduler → Source Monitor → Detect Changes → Download → Validate
→ Queue → Parse → Version → Diff → Index → Notify
```

MVP uses **APScheduler**; production uses **Celery Beat**.

---

## 11. Source Registry — do not crawl blind

```text
Source
├── Official        Authority Score = 1.00
├── Government      Authority Score = 0.95
├── Legal Database  Authority Score = 0.80
├── News            Authority Score = 0.50
└── User Content    Authority Score = 0.20
```

Each source carries: **Authority Score · Update Frequency · Parsing Method ·
Trust Level**

This score feeds **directly into ranking**.

> **Project status:** the repository already has
> [`docs/source-register.md`](../source-register.md) and
> [`config/legal-crawl-allowlist.json`](../../config/legal-crawl-allowlist.json).
> v1 uses only `Official` and `Government` sources — News and User Content never
> enter the corpus in any form.

---

## 12. Data Pipeline — Medallion Architecture

```text
┌──────────────┐
│ RAW DATA     │  PDFs / HTML
│ BRONZE LAYER │  Raw Storage (bytes + checksum)
│ SILVER LAYER │  Parsed Docs (normalised, structured text)
│ GOLD LAYER   │  Legal Data (chunks + metadata + versions)
└──────┬───────┘
   ┌───┼───┐
PostgreSQL Vector DB Graph DB
```

This is **Data Lakehouse / Medallion Architecture** thinking.

---

## 13. Data Quality Engine

Mandatory checks:

| # | Check | Action on violation |
|--:|-------|---------------------|
| 1 | Missing effective date | Mark `UNKNOWN`, lower the temporal score |
| 2 | Invalid document number | Quarantine, await manual review |
| 3 | Duplicate document | Merge by content hash |
| 4 | Broken legal references | Record the dangling edge, do not delete |
| 5 | Overlapping validity periods | Raise a data-conflict warning |
| 6 | Invalid hierarchy | Warn, do not auto-correct |

Example of violation type 5:

```text
Version A  effective_from: 2024 → NULL
Version B  effective_from: 2023 → NULL
```

Both are "currently open" → conflict. The database needs a constraint or a
validation layer.

---

## 14. Temporal Database — Bitemporal

Every provision carries two kinds of time:

```text
VALID TIME       — when did the rule bind in the real world?
TRANSACTION TIME — when did the system learn about it?
```

```text
Law effective: 01/01/2025   |   System crawled: 05/01/2025
```

This is a strong signal to data/backend engineers.

---

## 15. Hybrid Retrieval

```text
Question
├── BM25
├── Vector Search
└── Metadata Filtering
→ Candidate Documents → Reranker
```

Separate the three search modes clearly: **Structured Search + Semantic Search
+ Keyword Search**.

---

## 16. Knowledge Graph

```text
(Document)-[:AMENDS]->(Document)
(Document)-[:REPEALS]->(Document)
(Article)-[:REFERENCES]->(Article)
(Regulation)-[:AFFECTS]->(Taxpayer)
```

Enables: `New Law → Graph Traversal → Find affected documents`

Example query: *"Which documents are affected by Circular X?"* — something pure
RAG does poorly.

---

## 17. Frontend

Do not build a single chat screen. Build:

1. **AI Chat** 2. **Explore Law** 3. **Change Monitor** 4. **Tax Timeline**
5. **Admin Data Dashboard**

### 17.1 The answer experience

```text
┌──────────────────────────────────┐
│ AI Answer                        │
│ Under the current rules...       │
│                                  │
│ [Confidence: High]               │
│ 📜 3 legal bases                  │
│ 🕒 Effective from: 01/01/2026     │
└──────────────────────────────────┘
```

Clicking the citation `Điều 5 Khoản 2` opens:

```text
Document → Chapter → Article → Clause  ← Highlight
```

With: `📅 Effective: 2026 · 🔄 Updated: Yes · ⚖️ Authority: Circular`

### 17.2 Legal Confidence UX

**Do not** display `Confidence = 87.5%` — the number misleads about precision.

Instead:

```text
🟢 Clear legal basis
🟡 May need more information
🔴 Multiple readings / needs expert review
```

With a **stated reason**:

> "The result depends on the date the transaction arose."

This is **uncertainty explanation** — more important than a number.

> **Added analysis — the mapping rule:** the three levels must not come from an
> LLM's own score (language models are poorly calibrated). They must be derived
> from **observable signals**:
>
> | Level | Condition |
> |-------|-----------|
> | 🟢 | Event date determined · every citation `ACTIVE` at that date · no conflict · citation coverage ≥ 0.8 |
> | 🟡 | Date inferred (not explicit) **or** an `UNKNOWN` document present **or** a conflict that was resolved |
> | 🔴 | No date · **or** unresolved conflict · **or** only Official Letter-tier basis · **or** coverage < 0.6 |

---

## 18. Admin Dashboard

```text
┌──────────────────┐
│ Documents: 8,241 │
│ Active:    6,120 │
│ Updated:      24 │
└──────────────────┘
```

Track: Total Documents · Active Documents · New Documents Today · Processing
Queue · Embedding Queue · Failed Crawls · Potential Conflicts · Unresolved
Legal Relations.

---

## 19. Observability

Many AI projects skip this. Track:

```text
API Latency · LLM Latency · Retrieval Latency · Reranker Latency
Crawler Failures · Queue Size · Database Errors
```

Architecture: `Application → Logs → Metrics → Tracing`
Tooling: **Prometheus · Grafana · OpenTelemetry**

---

## 20. AI Evaluation Dashboard

Do not merely deploy a chatbot — prove:

```text
Which model is better? · Which retriever works best?
Does new data improve performance?
```

| Experiment | Retrieval | Citation | Temporal | Answer |
| ---------- | --------: | -------: | -------: | -----: |
| BM25       |       71% |      65% |      60% |    72% |
| Vector     |       75% |      68% |      58% |    76% |
| Hybrid     |       84% |      79% |      82% |    86% |

> ⚠️ **The table above is illustrative data from the original document, NOT a
> measurement from this project.** The real table will live at
> `reports/benchmark.md` after running
> [09 — Evaluation plan](09-evaluation-plan.md). Do not copy this illustrative
> table into the README or any report.

Tooling: MLflow · Weights & Biases · or a custom dashboard.

---

## 21. API Design

```text
POST /chat                      GET  /changes
POST /documents                 GET  /conflicts
GET  /documents/{id}            POST /impact-analysis
GET  /documents/{id}/versions   POST /feedback
```

The critical one:

```text
GET /legal-rules?date=2022-01-01
```

This turns the system into an **API service**, not merely a chatbot.

---

## 22. Authentication and roles

| Role | Rights |
|------|--------|
| Guest | Limited question count, no long-term storage |
| Registered User | History, bookmarks, document watching |
| Enterprise | Business Profile, alerts, impact monitoring |
| Admin | Full access, data dashboard |

---

## 23. User Feedback Loop — Data Flywheel

After each answer:

```text
👍 Helpful          👎 Inaccurate
⚠️ Wrong point in time    ⚠️ Wrong legal basis
```

```text
User → Feedback → Error Dataset → Evaluation → Improve System → Better UX
```

> **Added analysis:** the two warning buttons (⚠️) matter more than the first
> two. 👎 says only "wrong" — not actionable. "Wrong point in time" and "Wrong
> legal basis" map **directly** onto TVA and Citation Precision, so each such
> response becomes **a candidate eval item with its error label already
> attached**. This is the cheapest way to grow the benchmark over time.

---

## 24. Deployment

```text
Internet → Cloudflare → Nginx → Frontend → FastAPI
   ┌────────────┼────────────┐
PostgreSQL    Redis       Worker
    │                        │
 pgvector                 Crawler → Processing
```

Early stage: one server, `docker compose` with `frontend · backend · postgres ·
redis · worker`. Then: Docker → CI/CD → Cloud.

---

## 25. CI/CD

```text
Push → Test → Lint → Build Docker → Deploy Staging
     → Integration Test → Production
```

---

## 26. Testing

| Type | Content |
|------|---------|
| **Unit** | Date parsing · Version resolver · Conflict resolver |
| **Integration** | Crawler → Parser → Database |
| **RAG Evaluation** | Question → Expected Evidence → Retrieved Evidence |
| **Regression** | Old Benchmark → Run Again → Performance Drop? |

Regression testing matters greatly for AI: a seemingly harmless prompt change
can drop TVA by 10 points with nobody noticing.

---

## 27. Four-month roadmap (original)

| Month | Content |
|-------|---------|
| **1 — Foundation** | Weeks 1–2: domain research, data sources, database schema, first crawler. Weeks 3–4: document parser, PostgreSQL, versioning, basic RAG |
| **2 — Intelligence** | Hybrid Retrieval, reranking, citation, temporal filtering, first benchmark |
| **3 — Differentiation** | Legal Knowledge Graph, Change Detection, Conflict Detection, Impact Analysis |
| **4 — Production** | Next.js UI, authentication, feedback, monitoring, Docker, CI/CD, public deployment |

> **Actual status — corrected.** Only **Month 1, weeks 1–2** is complete:
> domain research, source identification, a working crawler, 1,355 PDFs and
> 13,058 source records.
>
> **Month 1, weeks 3–4 is NOT complete.** That block called for the document
> parser, PostgreSQL, versioning and basic RAG — none of which exists
> (see [08 §1.2](08-implementation-plan.md)). An earlier revision of this
> document claimed "Month 1 is already complete"; that was wrong and is
> corrected here.
>
> Realistic position against the original roadmap: **~40% of Month 1**. The plan
> is re-baselined against the true starting point in
> [08 — Implementation plan](08-implementation-plan.md).

---

## 28. Proposed GitHub structure

```text
taxlens-ai/
├── apps/         (frontend, backend)
├── services/     (crawler, document_processor, retrieval, ai_engine)
├── packages/     (database, shared)
├── data/         (raw, processed, evaluation)
├── infrastructure/ (docker, nginx)
├── experiments/
├── docs/
└── README.md
```

The README should cover: **Problem · Architecture · Features · Data Pipeline ·
Benchmark · Evaluation · Demo · Deployment**.

> **Project decision:** keep a flatter structure (`virag/` modular monolith +
> `tools/` + `docs/` + `eval/` + `reports/`), because a multi-app monorepo only
> pays off when there really are multiple independently deployed apps. The
> structure above is the Phase 5 destination, not the starting point.

---

## 29. What makes this project strong on a CV

If the CV says only:

> *Built an AI chatbot for Vietnamese tax law using RAG.*

→ fairly ordinary.

If it says:

> **Designed and deployed a production-oriented Vietnamese Tax Legal
> Intelligence Platform featuring temporal-aware retrieval, legal document
> versioning, hybrid search, automated regulation monitoring, change detection,
> conflict analysis, and citation-grounded LLM responses.**

→ a very different impression.

### 29.1 Technical highlights by group

| Group | Content |
|-------|---------|
| **Data Engineering** | Automated crawling pipeline · Document versioning · Bitemporal data modeling · Data quality validation · Incremental indexing |
| **AI Engineering** | Hybrid RAG · Temporal-aware retrieval · Reranking · Citation validation · Hallucination detection |
| **Backend** | FastAPI · PostgreSQL · Redis · Async workers · REST APIs |
| **Data Systems** | Vector DB · Knowledge Graph · Legal dependency graph · Incremental embedding |
| **DevOps** | Docker · CI/CD · Monitoring · Logging · Production deployment |

---

## 30. The USP

If forced to pick **one sentence**:

> **"The AI does not just find the latest law — it determines exactly which
> provision applies to a specific situation at a specific point in time."**

```text
Vietnam Tax Intelligence
├── Ask              ├── Detect Changes
├── Search           ├── Resolve Conflicts
├── Time Travel      └── Monitor Updates
└── Compare Versions
```

---

## 31. Recommended build order

| Phase | Content |
|-------|---------|
| **1 — Legal Data Infrastructure** | Crawler → Parser → Versioning → Database → Index |
| **2 — Reliable Tax RAG** | Hybrid Retrieval → Temporal Filtering → Citation Validation |
| **3 — Legal Intelligence** | Change Detection → Dependency Graph → Conflict Analysis |
| **4 — Product Experience** | Chat → Timeline → Diff Viewer → Monitoring → Feedback |
| **5 — Production Engineering** | Docker → CI/CD → Monitoring → Public Deployment |

Carried this far, the product stops looking like a *"chatbot demo"* and starts
looking like a **miniature AI/data platform**.

---

**Previous:** [A — Research Direction Analysis](A-research-direction.md)
**Next:** [05 — Design decisions](05-design-decisions.md)
