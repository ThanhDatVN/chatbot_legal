# Research and Reading Plan

**Purpose:** develop the legal doctrine, corpus, evaluation set, and engineering
evidence required to build the product described in the blueprint. Reading is
not considered complete until it produces an artifact, test, or decision.

## 1. Research method

For every source, record:

```yaml
source_id: stable identifier
title: ...
source_type: primary_law | official_guidance | paper | standard | product
authority_or_venue: ...
canonical_url: ...
version_or_access_date: ...
claims_supported: []
limitations: []
product_implications: []
open_questions: []
reviewer: ...
```

Rules:

- Read signed primary law before commentary about it.
- Separate what a source states from the team's inference.
- Reproduce technical claims on Vietnamese legal data before adopting them.
- Preserve negative results. A technique that fails a benchmark is a useful
  decision artifact.
- Have different experts author and adjudicate high-risk evaluation cases.

## 2. Track A: Vietnamese legal doctrine and source authority

### Questions

- What instruments are normative and what is their hierarchy?
- How do effective date, retroactivity, partial expiry, suspension, amendment,
  replacement, and transitional provisions operate?
- What is the legal status of consolidated documents, codification, official
  dispatches, tax-authority answers, court judgments, and precedents?
- Which source is official when HTML, metadata, and signed PDF disagree?
- Under what terms may official and licensed legal data be collected, stored,
  quoted, indexed, and redistributed commercially?

### Required reading

1. Current consolidated Law on Promulgation of Legal Normative Documents,
   especially the instrument system, validity, application, review, consolidation,
   codification, and implementation provisions.
2. Decrees 78/2025, 79/2025 and their amendments concerning implementation,
   checking, review, systematization, and processing of legal documents.
3. National Legal Database and Electronic Legal Codification usage guidance.
4. Law on Lawyers and implementing rules; law on legal aid where the product
   could appear to provide regulated services.

### Artifacts and exit criteria

- `legal-authority-policy-v1`: ranked source classes and conflict rules approved
  by Vietnamese counsel.
- `temporal-resolution-spec-v1`: examples for amendment, repeal, suspension,
  retroactivity, and transition, each with expert-approved expected output.
- Data license/reuse opinion and signed acquisition agreements.
- At least 50 temporal hard cases that the resolver passes exactly.

## 3. Track B: tax-domain model

### Questions

- Which facts determine taxpayer, taxable object, tax base, rate, exemption,
  deduction, declaration, payment, refund, audit, penalty, and appeal?
- Which rules can be encoded deterministically and which require professional
  interpretation?
- How are tax period, transaction date, invoice date, payment date, and filing
  date related?
- Which cross-domain rules are needed from accounting, invoices, enterprise,
  investment, customs, treaties, administrative procedure, and penalties?

### Reading order

1. Law 108/2025/QH15 on Tax Administration and its current implementing
   instruments, including transition from Law 38/2019/QH14.
2. Law 48/2024/QH15 on VAT; Decree 181/2025; amendments in Decrees 359/2025 and
   144/2026; Circular 69/2025; invoice-related instruments.
3. Law 67/2025/QH15 on Corporate Income Tax and current implementation.
4. Law 109/2025/QH15 on Personal Income Tax and current implementation.
5. Tax treaties and domain-specific instruments only after the domestic core is
   modeled.

### Artifacts and exit criteria

- VAT/invoice ontology and issue tree.
- A fact-to-rule decision map with material facts and missing-fact questions.
- Versioned decision tables for at least five common calculations/eligibility
  paths, with boundary and transition tests.
- 300 VAT/invoice cases: 100 lookup, 100 multi-issue, 50 temporal/calculation,
  50 adversarial/unanswerable.

## 4. Track C: legal analysis and professional workflow

### Questions

- What output do tax professionals actually deliver for a first consultation,
  research note, advice memo, audit response, and dispute?
- Which reasoning framework best exposes facts, issues, authority, application,
  counterarguments, risk, and next action?
- At what points must a professional approve, edit, or reject model work?
- What confidence language causes appropriate reliance rather than automation
  bias?

### Research activities

- Interview 10-15 tax lawyers, accountants, and in-house users using anonymized
  real workflows.
- Shadow and time at least 30 cases before building automation.
- Compare IRAC/CRAC-style memo structures with existing Vietnamese professional
  practice.
- Redesign five common workflows as editable fact tables, issue trees, evidence
  ledgers, calculations, and reviewer tasks.

### Artifacts and exit criteria

- Service blueprint and task/risk taxonomy.
- Human-review matrix by output, monetary exposure, deadline, dispute status,
  confidence, and customer type.
- Approved answer/memo schemas and plain-language standards.
- Baseline professional time, quality, and error measurements for later A/B tests.

## 5. Track D: information retrieval and RAG

### Foundation reading

1. Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP
   Tasks*.
2. Khattab and Zaharia, *ColBERT*; understand late interaction and efficiency.
3. LegalBench and LexGLUE for legal reasoning/task taxonomy, while recognizing
   that they are not Vietnamese tax benchmarks.
4. VLQA/ViLQA and relevant VLSP Vietnamese legal QA work; audit data source,
   license, date coverage, label quality, and leakage before use.
5. ALCE for citation correctness/completeness; RAGTruth for unsupported claims;
   RAGAS and ARES for component evaluation, with human calibration.

### Experiments

- Compare exact identifier search, BM25, dense retrieval, late interaction,
  hybrid fusion, and reranking.
- Test accent/no-accent, abbreviations, legal identifiers, misspellings, long
  questions, paraphrased facts, exact thresholds, and date filters.
- Compare fixed token, structural, and parent-child chunking.
- Measure exception, definition, transition, and controlling-provision recall,
  not only generic relevance.
- Evaluate ANN against exact vector search on every critical slice.

### Exit criteria

- Reproducible retrieval benchmark and error analysis.
- Selected baseline with statistically supported improvements over BM25 and
  dense-only alternatives.
- No critical slice traded away for a better average score.

## 6. Track E: graphs, change impact, and temporal data

### Foundation reading

- Current Vietnamese document structure and review/systematization rules.
- Edge et al., *From Local to Global: A Graph RAG Approach to Query-Focused
  Summarization* and Microsoft GraphRAG method/query documentation.
- Property graph and bitemporal data modeling literature; graph constraints and
  provenance models.
- RAPTOR for hierarchical retrieval over long documents and matters.

### Experiments

1. Build a rule-based graph for one VAT instrument chain.
2. Compare explicit citation/amendment edges with LLM-extracted relationships.
3. Seed 20 changes and measure direct/indirect impact recall and false alerts.
4. Compare PostgreSQL recursive queries and Neo4j on actual graph patterns.
5. Test point-in-time materialization around every effective boundary.
6. Test community GraphRAG only on global questions; do not conflate its entity
   graph with the normative graph.

### Exit criteria

- Reviewed graph schema, constraint suite, and provenance policy.
- At least 95% affected-artifact recall on seeded impact tests, with every missed
  critical dependency analyzed.
- Database choice supported by measured correctness, complexity, latency, and
  operating cost.

## 7. Track F: agents, ReAct, and deep research

### Foundation reading

- Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models*.
- Self-RAG and Corrective RAG.
- Durable workflow, checkpoint, human-in-the-loop, and idempotency patterns.
- Research on long-context positional weakness, including *Lost in the Middle*.

### Experiments

- Compare a deterministic pipeline with a bounded tool-using planner on 50
  multi-issue cases.
- Vary maximum steps, query breadth, counter-authority pass, and stop criteria.
- Inject failing tools, stale indexes, contradictory sources, hostile documents,
  and timeouts; verify replay and safe recovery.
- Measure issue coverage, source diversity by authority, expert review time,
  latency, and cost.
- Test a separate verifier model/tool but calibrate it against expert labels;
  model self-critique is not accepted as independent proof.

### Exit criteria

- Explicit state machine with schemas, policies, budgets, and replay tests.
- Agentic flow must beat the deterministic baseline on risk-weighted quality
  enough to justify extra cost and failure surface.
- Human interruption works before any high-risk action or final advice.

## 8. Track G: privacy, security, AI governance, and product law

### Required reading

1. Law 91/2025/QH15 and Decree 356/2025/ND-CP on Personal Data Protection.
2. Law 60/2024/QH15 on Data and current implementation.
3. Law 134/2025/QH15 and Decree 142/2026/ND-CP on AI.
4. Law 19/2023/QH15 on Consumer Protection and remote/digital transactions.
5. Current cybersecurity, electronic-transactions, intellectual-property, and
   professional-confidentiality requirements relevant to the deployment model.
6. NIST AI RMF and GenAI Profile, ISO/IEC 42001, and OWASP LLM Top 10 2025.

### Threat exercises

- direct and indirect prompt injection;
- poisoned or forged legal document;
- cross-tenant retrieval and cache collision;
- tool/URL/SQL injection and excessive agency;
- membership inference and provider retention;
- sensitive facts in logs, traces, analytics, feedback, or eval sets;
- malicious reviewer/support access;
- stale snapshot, partial update, rollback failure, or compromised source.

### Exit criteria

- Formal AI classification and impact assessment where applicable.
- Personal-data processing and transfer assessments, retention schedule,
  processor contracts, and subject-right procedures.
- Threat model, red-team suite, incident playbooks, and security acceptance report.
- No high/critical issue open at launch.

## 9. Track H: product and market research

Study product behavior, not marketing vocabulary:

- CoCounsel: trusted legal content, deep/agentic research, workflow integration.
- Lexis+ with Protege: source grounding, citation-status validation, guided
  research, matter documents.
- Harvey: jurisdiction-specific curated knowledge sources and enterprise
  workflows.
- vLex Vincent: research and multi-jurisdiction workflow.
- CoCounsel Tax and CCH AnswerConnect: tax-specific content operations,
  research-to-deliverable workflow, and calculator/integration patterns.
- Blue J and TaxGPT: tax research UX, matter documents, client context, writing,
  and bounded agent workflows.
- Legora and Spellbook: collaborative evidence review and in-workflow drafting.
- Bloomberg Tax and Regology: change monitoring linked to impacts and actions.
- Avalara AvaTax: deterministic tax-calculation/API patterns, not legal Q&A.
- AI Luat/LuatVietnam and AI Phap Luat/Thu Vien Phap Luat: Vietnamese coverage,
  citations, calculations, update claims, warnings, and user expectations.

For each product, run the same permitted, non-confidential test script:

- one exact provision lookup;
- one old-law question;
- one transition question;
- one case with a material missing fact;
- one nested exception;
- one calculation;
- one false-premise citation;
- one source-status and auditability review.

Do not violate terms of service or use proprietary output as training data.

### Exit criteria

- Feature/quality matrix with observed evidence, not vendor claims.
- Clear wedge, pricing hypothesis, professional-review model, and build/buy list.

## 10. Twelve-sprint integrated schedule

| Sprint | Focus | Required output |
|---|---|---|
| 1 | Legal/service/data boundary | Written opinions, source permissions, risk register |
| 2 | Authority and time | Temporal spec, 50 dated cases, bitemporal schema |
| 3 | VAT issue taxonomy | Ontology, fact map, interview script |
| 4 | Corpus engineering | Raw store, parser benchmark, provenance report |
| 5 | Retrieval baselines | BM25/dense/hybrid results and error slices |
| 6 | Reranking and citations | Evidence pack, ALCE-style citation metrics |
| 7 | Normative graph | VAT graph, constraints, point-in-time queries |
| 8 | Rules/calculations | Five versioned rules and boundary tests |
| 9 | Case workflow | Fact table, issue tree, memo, reviewer queue |
| 10 | Agent/deep research | Bounded state machine and baseline comparison |
| 11 | Security/governance | Red team, privacy/AI documentation, rollback drill |
| 12 | Expert beta gate | 300-case report, shadow-use results, go/no-go memo |

One sprint is assumed to be two weeks. Legal/data blockers pause feature work;
they are not deferred as post-launch compliance tasks.

## 11. Decision log template

Every architecture or model decision should contain:

```text
Decision and owner
Date and legal/knowledge snapshot
Problem and alternatives
Benchmark/data used
Quality by critical slice
Latency, cost, privacy, and operating impact
Known failure modes
Rollback and review date
```

This prevents "latest technique" from becoming an untestable requirement. A new
method is adopted only when it improves the product's risk-weighted outcome.
