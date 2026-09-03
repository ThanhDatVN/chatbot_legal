# 10 — Setup and Operations Guide

> **Document status.** §1–§3 describe **what works today**. §4 onward describes
> the **target state** after the plan in document 08 is complete — those commands
> **do not work yet** because the application code is unfinished. Each section
> carries an explicit status marker so nobody runs the wrong thing and concludes
> the system is broken.

---

## 1. Environment requirements

| Component | Version | Required | Note |
|-----------|---------|:--------:|------|
| Python | 3.11+ | ✅ | Currently **not installed** on the dev machine |
| Docker Desktop | 29+ | ✅ | Installed (v29.7.2), daemon **not running** |
| Docker Compose | v2.20+ | ✅ | Available (v5.3.1) |
| RAM | 8 GB (16 GB recommended) | ✅ | The reranker needs ~2 GB |
| Free disk | 15 GB | ✅ | 4.4 GB corpus + ~3 GB models + index |
| Tesseract OCR | 5.x + `vie` | ⬜ | Only needed for scanned PDFs |
| `ANTHROPIC_API_KEY` | — | ⬜ | Without it the system runs in extractive mode |

---

## 2. Setting up the development environment  ✅ *works today*

### 2.1 Windows / PowerShell

```powershell
# 1. Install Python 3.11 if absent: winget install Python.Python.3.11

# 2. Create the virtual environment
python -m venv .venv

# 3. Install the existing dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock

# 4. Verify the foundation still runs
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check tools tests
```

> ⚠️ **Known defect.** `pyproject.toml` has a stray `y` at the end of the line
> `select = ["E", "F", "I", "B", "UP", "SIM"]y`. It must be removed before
> `ruff` can read the config file. This is task 0.4 in the
> [plan](08-implementation-plan.md).

### 2.2 Starting Docker

```powershell
# Start Docker Desktop, then check:
docker info --format '{{.ServerVersion}}'
docker compose version
```

---

## 3. Running the data-acquisition tools  ✅ *works today*

```powershell
# Dry run, downloads nothing
.\.venv\Scripts\python.exe tools\legal_crawler.py --dry-run

# Crawl one shard, downloading official PDFs
.\.venv\Scripts\python.exe tools\legal_crawler.py `
  --config config\tax-document-all-fulltext-shards-v4\shard-0001.json `
  --output data\crawl\tax-document-all-fulltext-shard-0001-YYYY-MM-DD `
  --download-official-pdfs

# Audit completeness of crawled shards
.\.venv\Scripts\python.exe tools\audit_crawl_completeness.py

# Verify effective dates against Official Gazette PDFs
.\.venv\Scripts\python.exe tools\legal_effective_dates.py
```

### 3.1 Mandatory rule when re-crawling

> If a shard stops part-way, write the missing portion into a `*-resume`
> directory. **Never overwrite the partial directory.** The Bronze layer is
> evidence and must not be edited.

A real example: shard 0007 stopped at 94/100 source pages and 108/109 PDFs. The
data was preserved as-is; the missing part must go into `shard-0007-resume`.

---

## 4. Running the whole system  ⬜ *target state*

### 4.1 One command (deliverable 8)

```bash
cp .env.example .env      # fill in ANTHROPIC_API_KEY if you have one
docker compose up
```

Open http://localhost:8000

Compose starts:

| Service | Port | Role |
|---------|-----:|------|
| `qdrant` | 6333 | Vector store |
| `redis` | 6379 | Semantic cache |
| `postgres` | 5432 | Versions, relations, changes, feedback |
| `api` | 8000 | FastAPI + web UI |
| `ingest` | — | Runs once and exits: builds the index from `data/crawl/` |

### 4.2 First run

The first start downloads the embedding and reranker models (~3 GB) into a
volume. Subsequent starts are fast.

**No network?** Set `VIRAG_EMBEDDING_BACKEND=hashing` and
`VIRAG_RERANKER_BACKEND=lexical`. The system runs, at **substantially lower
quality** — and any report produced in this mode **must record the backend**
(risk R-M09).

---

## 5. Environment variables  ⬜ *target state*

| Variable | Default | Meaning |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | — | Absent → extractive generation mode |
| `DATABASE_URL` | local SQLite | Postgres inside compose |
| `VIRAG_QDRANT_URL` | `http://localhost:6333` | |
| `VIRAG_REDIS_URL` | `redis://localhost:6379/0` | |
| `VIRAG_LLM_MODEL` | `claude-opus-5` | |
| `VIRAG_LLM_EFFORT` | `medium` | `high` for conflict adjudication |
| `VIRAG_EMBEDDING_MODEL` | `BAAI/bge-m3` | |
| `VIRAG_EMBEDDING_BACKEND` | `auto` | `auto` \| `sentence-transformers` \| `hashing` |
| `VIRAG_RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | |
| `VIRAG_RERANKER_BACKEND` | `auto` | `auto` \| `cross-encoder` \| `lexical` |
| `VIRAG_OCR_ENABLED` | `1` | |
| `VIRAG_OCR_LANGUAGE` | `vie` | |
| `VIRAG_OCR_MIN_CHARS_PER_PAGE` | `180` | Below this, OCR that page |
| `VIRAG_CACHE_SIMILARITY_THRESHOLD` | `0.94` | |
| `VIRAG_DEFAULT_AS_OF` | `today` | Set a fixed ISO date for reproducible evals |
| `VIRAG_TEMPORAL_CLARIFICATION` | `1` | Ask back when the date is missing |
| `VIRAG_MIN_CITATION_COVERAGE` | `0.6` | |
| `VIRAG_BLOCK_VERSION_MIXING` | `1` | |

---

## 6. Operational commands  ⬜ *target state*

### 6.1 Ingest

```bash
# The whole corpus
python -m virag.ingest.pipeline --crawl-root data/crawl

# One shard, limited document count (for development)
python -m virag.ingest.pipeline --include shard-0001 --limit 50

# Rerun: idempotent, creates no duplicate rows
python -m virag.ingest.pipeline --crawl-root data/crawl
```

### 6.2 Evaluation

```bash
# Build the eval set from the corpus
python -m virag.eval.build_evalset --n 210 --out eval/viettaxbench.jsonl

# Run one configuration
python -m virag.eval.run_eval --config E-full-temporal-legal --split dev

# The 5-configuration ablation table
# (for published numbers, always add --require-real-models)
python -m virag.eval.ablation --split test --require-real-models

# The prompt-injection suite
python -m virag.eval.injection_suite

# The 20-case hallucination analysis
python -m virag.eval.hallucination_analysis --n 20
```

### 6.3 Data quality

```bash
python -m virag.store.quality --out reports/data-quality.json
```

---

## 7. Testing and linting

```bash
pytest -q                          # everything
pytest tests/test_temporal.py -v   # one module
ruff check virag tools tests
ruff format virag tools tests
```

### 7.1 Four testing layers

| Layer | Content | Example |
|-------|---------|---------|
| **Unit** | Pure functions | Date parsing · version resolution · the conflict rule engine |
| **Integration** | Stage chains | Crawl → parse → DB |
| **RAG evaluation** | Retrieval | Question → expected evidence → retrieved evidence |
| **Regression** | Anti-degradation | Rerun the old benchmark, compare the numbers |

**Mandatory regression tests** (each catches an analysed failure):

- [ ] Changing `as_of` **must** change the retrieval result
- [ ] The cache **misses** when only `as_of` changes (ADR-015)
- [ ] An Official Letter never outranks a Law on the same topic (ADR-008)
- [ ] Citations outside the context are stripped 100% of the time (ADR-014 step 1)
- [ ] Two versions sharing an `article_key` are blocked (ADR-011, VMR)
- [ ] `SearchFilters.matches()` agrees with the Qdrant filter result (ADR-016)

---

## 8. Repository structure

```text
chatbot-legal-tax/
├── virag/                    # the application (modular monolith)
│   ├── settings.py           # every configuration parameter
│   ├── schemas.py            # data contracts
│   ├── legal/                # authority · temporal · relations · conflict
│   ├── ingest/               # extract · clean · structure · chunking · manifest
│   ├── store/                # bitemporal db · data quality
│   ├── index/                # embedder · bm25 · vector_store · chunk_store
│   ├── retrieval/            # hybrid · rerank
│   ├── generation/           # prompts · llm · citations
│   ├── guardrails/           # input · output · injection
│   ├── cache/                # semantic cache
│   ├── agent/                # LangGraph
│   ├── api/                  # FastAPI
│   └── eval/                 # metrics · ragas · ablation · injection
├── tools/                    # data acquisition (already working)
├── tests/
├── config/                   # allowlists, shard configs
├── data/
│   ├── crawl/                # BRONZE — immutable, checksummed
│   ├── processed/            # SILVER
│   ├── index/                # GOLD
│   └── analysis/             # audit reports
├── eval/                     # VietTaxBench + injection payloads
├── reports/                  # measurement results
├── docs/
│   └── virag-gov/            # this dossier
├── web/                      # static UI
├── docker-compose.yml
└── README.md                 # English (deliverable 7)
```

---

## 9. Troubleshooting

| Symptom | Common cause | Fix |
|---------|--------------|-----|
| `Python was not found` | Python not installed | Install Python 3.11, reopen the terminal |
| `cannot connect to docker daemon` | Docker Desktop not running | Start Docker Desktop |
| `ruff` cannot read the config | The stray `y` in `pyproject.toml` | Remove that character |
| Retrieval returns nothing | Ingest not run, or the temporal filter excluded everything | Check `chunks.jsonl`; look for the safety-valve log line |
| Answer has no citations | The model omitted `[Sn]` | Check coverage; the system regenerates once then lowers confidence |
| Unexpectedly poor results | **Running on a fallback** | Check `embedder_name` in the logs — R-M09 |
| Qdrant unreachable | Service not ready | The system switches to the NumPy store; check the warning log |
| Cache returns the wrong version | `as_of` missing from the cache key | Check the ADR-015 regression test |
| OCR output has no diacritics | Missing `vie` traineddata | Install the Vietnamese Tesseract language pack |

---

## 10. Deployment  ⬜ *target state*

### 10.1 Minimum resources

| Resource | Minimum |
|----------|---------|
| CPU | 2 vCPU |
| RAM | 4 GB (without reranker) / 8 GB (with) |
| Disk | 10 GB |

### 10.2 Principles

1. **Prepare ≥2 platforms** so no single vendor is a dependency (risk R-P02).
2. **Do not ship `data/crawl/` (4.4 GB) to the deployment** — build the index
   elsewhere and deploy the built index.
3. **Rate-limit** public endpoints (risk R-S05).
4. Set `VIRAG_DEFAULT_AS_OF=today` in production and a fixed date in eval
   environments.

### 10.3 Pre-launch checklist

- [ ] `ANTHROPIC_API_KEY` supplied via environment variable, **not** baked into
      the Docker image
- [ ] Rate limiting enabled
- [ ] The disclaimer appears on every answer
- [ ] `/healthz` returns 200
- [ ] Logs contain no PII
- [ ] The injection suite rerun against the deployment, ASR ≤ 5%

---

## 11. Operating runbook

### 11.1 Daily
- Check `/healthz` and `/api/admin/stats`
- Review crawler error logs

### 11.2 Weekly
- Run the eval on the 50-question dev split → `reports/weekly/`
- Compare with the previous week; any metric down > 5 points → investigate
  **before** new work
- Update the early-warning indicator table
  ([07 §7](07-risk-analysis.md))

### 11.3 When a new document appears
- Crawl → ingest → diff → change event
- Invalidate cache entries touching the affected `document_id`
- Confirm `data-quality.json` shows no new violations

### 11.4 When a wrong answer is discovered
Follow the 8-step process in [07 §9](07-risk-analysis.md). The most important
step is **step 5**: turn the failing case into a regression eval item.

---

**Previous:** [09 — Evaluation plan](09-evaluation-plan.md)
**Next:** [11 — Compliance, ethics and limits](11-compliance-and-ethics.md)
