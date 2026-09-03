# Blueprint: Vietnamese Tax Legal Assistant

**Status:** research baseline  
**Jurisdiction:** Vietnam  
**Verified through:** 2026-08-09  
**Audience:** founders, tax/legal subject-matter experts, product, data, AI, and
security engineering

## 1. Executive decision

Build a **version-aware tax research and case-analysis system**, not an
autonomous general-purpose legal chatbot.

The first sellable product should be a B2B copilot for tax lawyers, accountants,
and in-house tax teams. Its first domain should be VAT and invoices for small and
medium enterprises. This domain has frequent changes, numerical rules,
documentary conditions, and clear professional workflows, so it tests the core
value proposition without pretending the product already covers the entire legal
system.

The product should have three connected capabilities:

1. **Authority-aware Q&A:** find the applicable rule and quote the exact legal
   basis as of a requested date.
2. **Case workspace:** collect facts and documents, identify missing facts,
   calculate alternatives, produce an issue-based research memo, and route it to
   a professional reviewer.
3. **Change intelligence:** detect a new instrument, compute structural and
   semantic changes, identify affected rules, calculators, templates, saved
   matters, and customers, then create a review task before publishing the new
   knowledge snapshot.

The moat is not a particular LLM. It is the maintained corpus, temporal legal
graph, expert-labeled cases, deterministic validation, operational controls, and
feedback loop.

## 2. Problem statement

### 2.1 Problems the system must solve

- Legal text is hierarchical: instrument, chapter, section, article, clause,
  point, annex, form, and cross-reference.
- The applicable rule depends on jurisdiction, taxpayer type, transaction,
  tax period, effective date, transitional provisions, and sometimes the date a
  procedure is performed.
- A provision may be amended, replaced, suspended, annulled, corrected, or
  consolidated. The status can differ for only one point or one class of subject.
- Guidance, official answers, court decisions, precedents, commentary, and
  customer documents have different authority and cannot be blended silently.
- Tax conclusions are conditional. A single missing fact, invoice, payment
  method, registration status, or deadline can reverse the result.
- Numeric answers require reproducible formulas, rounding, thresholds,
  currencies, periods, and input provenance.
- Users need an actionable analysis but must be able to inspect the evidence and
  understand assumptions and unresolved issues.
- The law changes continuously. An update must be reflected without destroying
  the ability to answer historical questions.

### 2.2 Failure modes that matter most

1. A real citation that does not support the stated proposition.
2. A correct rule from the wrong effective period.
3. A current consolidated paragraph applied to a historical event.
4. A lower-authority source overriding primary law.
5. Missing an exception, definition, transitional rule, or referenced annex.
6. A valid legal rule applied to materially incomplete or misclassified facts.
7. A correct analysis with an incorrect calculation or deadline.
8. Cross-tenant leakage, confidential-document leakage, or provider training on
   customer data.
9. Prompt injection inside a customer PDF or retrieved web page causing an agent
   to disclose data or use unauthorized tools.
10. A new-law ingestion error being promoted globally before expert review.

These are release-blocking risks. Conversational polish is secondary.

## 3. Product scope

### 3.1 Primary personas

| Persona | Main job | Product mode |
|---|---|---|
| Tax professional | Research, analyze, review, and advise | Full case workspace |
| In-house tax/accounting team | Triage and prepare a defensible position | Guided workflow + approval |
| Business owner | Understand a basic obligation and prepare documents | Restricted Q&A + escalation |
| Knowledge manager | Curate law, update interpretations, run quality checks | Corpus and change console |
| Compliance/audit | Inspect who used what source/model and why | Immutable audit view |

### 3.2 Initial jobs to be done

- Ask a plain-language VAT or invoice question and receive the applicable rule,
  exact quotation, effective interval, assumptions, and official source link.
- Upload a small set of matter documents; receive an extracted fact table with
  source page references and explicit uncertainty.
- Complete a dynamic interview that asks only facts capable of changing the
  result.
- Compare two legal positions and see the facts, authorities, calculations,
  counterarguments, and risk level for each.
- Generate a research memo for professional review, not an unreviewed filing.
- Subscribe a matter or business profile to relevant legal changes.

### 3.3 Out of scope for the first release

- Automatic filing, payment, representation, or sending a binding submission to
  a government authority.
- Unreviewed dispute strategy, tax avoidance structures, or confident answers
  where the evidence set is incomplete.
- Training a foundation model from scratch.
- Covering every tax and every industry before VAT quality is demonstrated.
- Treating a disclaimer as a substitute for correct product classification,
  professional licensing, privacy compliance, or human oversight.

## 4. Legal operating model

### 4.1 Authority hierarchy

Every source receives an authority class and jurisdiction. Retrieval may find
lower-authority material, but synthesis must preserve the distinction.

| Class | Examples | Permitted use |
|---|---|---|
| A1 | Signed original, official gazette | Controlling primary evidence |
| A2 | National legal database, official consolidated text/codification | Official discovery and derived current view |
| B | Ministry/tax-authority guidance, official answers | Administrative interpretation or practice, labeled as such |
| C | Licensed publisher, treatise, professional commentary | Issue discovery and explanation; never silently controlling |
| D | Customer contracts, invoices, records | Matter facts only |
| E | General web, forums, model memory | Lead generation only; cannot support a legal conclusion |

Where primary law exists, the answer cites primary law. A source such as an
official dispatch must not be presented as a normative instrument merely because
it was issued by an authority.

### 4.2 Temporal application

The resolver implements the principles in Chapter VI of the current consolidated
Law on Promulgation of Legal Normative Documents, including application from the
effective date, application to events occurring while the document is in force,
priority of higher legal effect, later instruments from the same issuing body,
and relevant treaties. See [54/VBHN-VPQH](https://vbpl.vn/TW/Pages/vbpq-thuoctinh-hopnhat.aspx?ItemID=182331&View=0).

Every query carries at least:

```text
jurisdiction
question_time                 # when the user asks
event_time or tax_period      # when the taxable event occurred
procedure_time                # filing/appeal/payment date when relevant
taxpayer_profile
knowledge_snapshot_id
```

The system must not default silently when `event_time` could change the answer.
It asks a clarifying question or returns dated alternatives.

### 4.3 Professional-service boundary

The Law on Lawyers identifies legal consultancy as a legal service. The exact
business model, branding, engagement terms, review responsibility, and role of a
licensed law practice therefore require a written Vietnamese legal opinion before
launch. The product should be designed on the conservative assumption that
case-specific advice needs professional control, while basic legal information
and professional research support remain distinct product modes. Source:
[Law 65/2006/QH11](https://vbpl.vn/bocongthuong/Pages/vbpq-toanvan.aspx?ItemID=15076).

### 4.4 AI-risk classification

Law 134/2025/QH15 and Decree 142/2026/ND-CP require risk classification,
transparency, incident handling, and stronger controls for high-risk systems. A
tax advice system can materially influence financial obligations and legal
rights. Until Vietnamese counsel completes a formal classification against the
final product behavior, **design and operate it as high risk**. This is a risk
decision, not a definitive legal classification.

Required launch evidence includes the classification memo, system card, intended
purpose, prohibited uses, human-control design, conformity/impact assessment if
applicable, incident process, monitoring plan, and user-facing AI identification.

## 5. Target experience and answer contract

### 5.1 Case interview

The interface first determines the task: information lookup, calculation, case
analysis, change impact, or document review. For a case, it builds an editable
fact table:

| Fact | Value | Date/period | Evidence | Confidence | Materiality |
|---|---|---|---|---|---|
| Taxpayer type | ... | ... | customer statement/document page | confirmed/inferred | can change rule path |

Questions are selected by expected legal impact, not by a fixed questionnaire.
An inferred fact is never upgraded to confirmed without user or document
evidence.

### 5.2 Mandatory answer structure

```yaml
scope:
  jurisdiction: VN
  law_as_of: YYYY-MM-DD
  taxable_event_or_period: ...
  knowledge_snapshot: ...
conclusion:
  short_answer: ...
  confidence: high | medium | low | cannot_conclude
assumptions: []
material_facts: []
analysis:
  - proposition: one atomic legal or factual claim
    reasoning: ...
    citations:
      - instrument_id: ...
        provision: article/clause/point
        valid_from: ...
        valid_to: ...
        source_url: ...
        artifact_hash: ...
        quote_span: ...
calculations:
  inputs: []
  rule_version: ...
  steps: []
  result: ...
alternatives_and_risks: []
missing_information: []
next_actions: []
review:
  required: true | false
  reason: ...
```

The user sees a readable version and may expand each proposition to the exact
source passage. The structured form is stored for audit and evaluation.

### 5.3 Refusal and escalation

Return `cannot_conclude` when no controlling source is found, applicable dates
are unresolved, documents conflict, facts are insufficient, calculation inputs
are unreliable, or the request exceeds allowed risk. The response must say what
is missing and how a professional can resolve it. It must not fill the gap from
model memory.

## 6. Knowledge architecture

### 6.1 Immutable evidence and derived views

```text
official source
  -> raw artifact (PDF/HTML/DOCX, checksum, signature/metadata)
  -> parsed structural tree
  -> normalized provisions and cross-references
  -> legal-change events
  -> reviewed legal graph
  -> point-in-time consolidated views
  -> lexical/vector/graph indexes
  -> versioned knowledge snapshot
```

Never overwrite a raw artifact or previously published snapshot. A correction
creates a new system-time version and an audit event.

### 6.2 Bitemporal core

Every instrument, provision, relationship, interpretation, and executable rule
has:

- `valid_from` / `valid_to`: when it has legal effect.
- `recorded_from` / `recorded_to`: when the platform knew or corrected it.
- `published_at`, `promulgated_at`, `effective_at`, and `status` as separate
  fields.
- `source_artifact_id`, `source_span`, `source_hash`, parser version, reviewer,
  and review status.

This supports both "what law applied on date X?" and "what did our system know
when it answered on date Y?".

### 6.3 Legal graph schema

Core nodes:

- `Instrument`, `InstrumentVersion`, `Provision`, `Definition`, `Norm`
- `Tax`, `TaxpayerClass`, `TransactionType`, `IncomeOrSupply`, `Rate`,
  `Exemption`, `Deduction`, `Procedure`, `Deadline`, `Form`, `Penalty`
- `Authority`, `Jurisdiction`, `Treaty`, `OfficialGuidance`, `Decision`
- `ExecutableRule`, `TestCase`, `ProductWorkflow`, `MatterWatch`

Core edges:

- `CONTAINS`, `CITES`, `DEFINES`, `APPLIES_TO`, `EXCLUDES`, `EXCEPTION_TO`
- `GUIDES`, `DETAILS`, `IMPLEMENTS`, `INTERPRETS`
- `AMENDS`, `REPLACES`, `REPEALS`, `SUSPENDS`, `CORRECTS`, `CONSOLIDATES`
- `HAS_TRANSITION`, `CONFLICTS_WITH`, `DEPENDS_ON`
- `EXECUTED_BY`, `TESTED_BY`, `AFFECTS_WORKFLOW`, `WATCHED_BY`

Every edge has provenance, valid/system time, extraction method, confidence, and
review state. LLM-extracted edges remain `proposed` until deterministic checks or
an expert accepts them. An inferred semantic relationship is never displayed as
if the legislature explicitly stated it.

### 6.4 Structural chunking

Do not split legal text into arbitrary token windows. The indexed unit is usually
a point or clause, with its article heading, parent path, definitions in scope,
referenced provisions, effective interval, and source coordinates attached.

Use parent-child retrieval:

- rank smaller clause/point units for precision;
- expand the selected unit to enough parent/sibling context for interpretation;
- attach definitions, exceptions, transitional provisions, and referenced
  annexes through graph traversal;
- cap the final evidence pack by relevance and coverage, not raw token count.

## 7. Acquisition, updates, and conflict prevention

### 7.1 Source policy

Primary acquisition targets are the National Legal Database, Electronic Official
Gazette, Government document portal, Electronic Legal Codification, Ministry of
Finance, and tax authority. Before production ingestion, obtain documented API,
feed, bulk-data, or reuse permission. Public browser access is not automatically
permission for unrestricted commercial scraping or republication.

### 7.2 Ingestion checks

1. Fetch metadata and signed/original artifact; compute a content hash.
2. Compare identifier, issuer, dates, and status across at least two official
   representations when available.
3. Parse layout and structural numbering. Quarantine low-OCR-confidence pages,
   tables, formulas, and annexes.
4. Resolve explicit citations and amendment instructions deterministically.
5. Generate structural and semantic diffs against the prior version.
6. Validate effective dates, partial-effect scopes, transitional provisions, and
   instrument hierarchy.
7. Run graph constraints and regression cases.
8. Require expert approval for a high-impact change.
9. Publish an atomic snapshot; re-index; retain the previous snapshot for
   rollback and historical answers.

### 7.3 Impact propagation

```text
new instrument
 -> directly amended/replaced provisions
 -> changed normalized norms/definitions/rates/deadlines
 -> inbound and outbound graph dependencies
 -> affected calculators and decision tables
 -> affected benchmark cases and saved templates
 -> matters/customers matching the changed fact pattern
 -> expert review tasks and user alerts
```

An impact report separates:

- textual change;
- effective date and transition;
- legal interpretation proposed by AI;
- validated operational impact;
- unresolved ambiguity.

For example, the VAT implementation chain changed from Decree 181/2025 to
amendments in Decrees 359/2025 and 144/2026. The system must represent three
instruments and their dated change edges, rather than embedding only the latest
merged paragraph. Official sources are listed in the source register.

## 8. Retrieval and reasoning architecture

### 8.1 Request pipeline

```text
API / web app
  -> authentication, tenant/purpose policy, data-loss controls
  -> task and risk classifier
  -> fact/date normalizer and clarification gate
  -> research planner (issue tree + coverage ledger)
  -> parallel bounded retrieval tools
       lexical search
       dense/late-interaction search
       graph traversal
       official-source change search
       matter-document search
  -> authority/date filters and reranking
  -> evidence-pack builder
  -> legal analysis + deterministic rule/calculation tools
  -> counter-authority/exception search
  -> citation, temporal, contradiction, and calculation validators
  -> risk-based human review or response
  -> immutable audit event and evaluation sample
```

### 8.2 Hybrid RAG baseline

Use lexical retrieval and semantic retrieval together. Legal identifiers,
article numbers, dates, thresholds, and defined terms favor BM25/exact fields;
paraphrased facts favor dense retrieval. Fuse rankings, apply hard filters for
jurisdiction and valid time, then use a reranker trained or evaluated on
Vietnamese legal relevance.

Recommended sequence:

1. identifier/exact phrase/keyword query;
2. dense query and optional multi-vector late interaction;
3. reciprocal-rank or learned fusion;
4. cross-encoder reranking;
5. graph expansion for definitions, exceptions, amendments, and implementing
   instruments;
6. coverage-aware evidence selection.

Evaluate every stage. Approximate vector search trades recall for speed, which is
dangerous if it silently drops the one controlling clause.

### 8.3 GraphRAG: two different meanings

Microsoft GraphRAG creates LLM-extracted entity graphs and community summaries,
which is useful for corpus-wide themes and global questions. A legal product also
needs a **normative legal graph** whose nodes and edges reflect instrument
structure, authority, amendment, effect, exception, and implementation.

Use the normative graph for controlling-law resolution and change impact. Use
community-style GraphRAG only for exploratory global synthesis, issue discovery,
or large matter collections, and never let its generated community summary be
the cited authority. Microsoft notes that rich graph extraction is costly and
LLM-derived; its documentation estimates extraction is most of indexing cost.

### 8.4 Agentic RAG and ReAct

Use a bounded state machine, not an unconstrained society of agents. Logical
roles can be separate prompts or nodes while sharing one auditable workflow:

- intake/fact extractor;
- issue planner;
- authority retriever;
- graph/date resolver;
- tax rule and calculation executor;
- counterargument researcher;
- citation/entailment verifier;
- professional reviewer.

ReAct is valuable for interleaving planning and tool use, but the production log
should record tool inputs, results, decisions, and evidence IDs rather than
private free-form chain-of-thought. Each tool has a schema, least privilege,
timeout, budget, allowlist, and idempotency rule. Model-generated SQL, URLs, or
code are not executed directly.

### 8.5 Deep research workflow

1. Define jurisdiction, issue, requested output, event dates, and risk.
2. Extract facts; mark confirmed, disputed, inferred, and missing.
3. Build an issue tree and a source plan for each issue.
4. Search primary law broadly; lock the candidate instruments and versions.
5. Expand each candidate through citations, definitions, exceptions,
   implementation, transitions, and amendment history.
6. Search deliberately for contrary authority and disqualifying facts.
7. Use secondary sources only to discover missed issues or explain context.
8. Execute calculations and decision tables with versioned rules.
9. Maintain a coverage ledger: supported, contradicted, unresolved, not found.
10. Draft atomic propositions from the evidence pack.
11. Verify citation existence, quotation, entailment, effective date, authority,
    and completeness independently of the drafting call.
12. Stop when all material issues meet coverage thresholds, the search budget is
    exhausted, or escalation is required. Do not stop merely because a fluent
    answer exists.

### 8.6 Where advanced techniques fit

| Technique | Use now? | Role and caution |
|---|---|---|
| Hybrid RAG + reranking | Yes, baseline | Highest immediate value; benchmark on legal hard negatives |
| Parent-child/structure-aware retrieval | Yes | Preserves article context without oversized chunks |
| Query decomposition/multi-query | Yes | Required for multi-issue cases; deduplicate and cap breadth |
| Graph traversal | Yes | Amendments, definitions, exceptions, implementing rules, impact |
| Corrective RAG | Selectively | Retry or switch source when retrieval fails; only approved official domains |
| Self-RAG/reflection | Experiment | A model critique is not an independent guarantee |
| RAPTOR/hierarchical summaries | Later | Useful for long matters/global questions; summaries are derived evidence |
| Microsoft community GraphRAG | Later | Global corpus/matter synthesis; expensive, noisy if used as legal truth |
| Fine-tuning | After eval data exists | Improve classification/extraction/style, not freshness or authority |
| Long-context-only | No | Costly and vulnerable to attention dilution; retrieval remains necessary |

## 9. Deterministic legal and tax rules

LLMs should identify candidate rules and explain results. They should not be the
calculator or the final arbiter of a formalizable eligibility rule.

Represent executable rules as versioned decision tables or code with:

- legal basis and exact source spans;
- inputs, types, units, currency, period, and validation;
- conditions, exceptions, priority, and effective interval;
- formula, rounding, and output explanation;
- author, reviewer, test suite, and release version.

Every calculation output includes input provenance and a reproducible trace.
Changes to a referenced provision automatically mark the rule `review_required`
and block unreviewed production use where material.

## 10. Memory, context, and cost optimization

Do not call the whole legal corpus "memory". Separate stores by purpose:

1. **Legal knowledge:** immutable, versioned corpus and graph; retrieved on
   demand.
2. **Matter state:** structured facts, issues, documents, decisions, and evidence
   ledger scoped to one tenant/matter.
3. **Conversation state:** recent turns plus a fact-preserving summary; disposable
   and subordinate to confirmed matter facts.
4. **User preferences:** language, format, role, and notification settings; no
   legal conclusions.
5. **Workflow checkpoints:** resumable agent state with retention policy.

Optimization rules:

- Store document once and reference immutable content IDs.
- Embed the smallest useful structural units; deduplicate identical provisions.
- Re-embed only changed units and affected parent summaries.
- Cache retrieval/evidence packs by normalized query, permissions, event time,
  corpus snapshot, and model/index version. A law update invalidates dependent
  cache keys.
- Cache deterministic tool results separately from generated prose.
- Compact conversation into structured facts and unresolved questions; never
  discard provenance or silently mutate a confirmed fact.
- Route simple lookups, extraction, reranking, and classification to smaller
  evaluated models; reserve expensive models for complex synthesis.
- Set per-stage token/tool budgets and stop criteria. Track cost per completed,
  expert-accepted task rather than cost per chat turn.
- Use model and embedding gateways so benchmarks, not vendor lock-in, control
  upgrades.

## 11. Reference implementation direction

This is a starting hypothesis to validate with prototypes, not a mandatory stack.

| Layer | Initial choice | Reason |
|---|---|---|
| API/domain services | Python + FastAPI | Strong document/AI ecosystem; typed APIs |
| Durable workflow | Explicit state graph; LangGraph for prototype, Temporal-class engine for critical long jobs | Checkpoints, retry, audit, human pause |
| System of record | PostgreSQL | Transactions, bitemporal tables, row-level tenant controls |
| Raw artifacts | S3-compatible object storage with versioning/object lock | Immutable evidence and cheap retention |
| Search | OpenSearch/Elasticsearch hybrid BM25 + vector | Exact legal search, filters, fusion, operations |
| Small-scale vector option | pgvector | Fewer moving parts for the first corpus; measure recall before ANN |
| Legal graph | PostgreSQL adjacency tables first; Neo4j when graph queries/scale justify it | Avoid premature dual-write complexity |
| Rules | Versioned decision tables + typed Python functions | Deterministic, testable calculations |
| Events | Transactional outbox; add a broker when update volume requires it | Reliable snapshot and impact propagation |
| Observability | OpenTelemetry traces + prompt/model/index registry | Reproduce each answer and cost |
| Identity/security | OIDC, MFA, RBAC/ABAC, tenant keys | Enterprise access and isolation |

Do not adopt a graph database merely to claim GraphRAG. First prove graph query
patterns and correctness in the relational model; then benchmark Neo4j or another
graph engine against actual traversals.

## 12. Security, privacy, and governance

### 12.1 Current Vietnamese baseline

- Law 91/2025/QH15 on Personal Data Protection and Decree 356/2025/ND-CP
  have applied since 2026-01-01; Decree 13/2023/ND-CP ceased to be effective on
  that date under Decree 356.
- Law 60/2024/QH15 on Data applies from 2025-07-01.
- Law 134/2025/QH15 on AI applies from 2026-03-01 and Decree 142/2026/ND-CP
  from 2026-05-01.
- Consumer, cybersecurity, electronic transaction, intellectual property,
  professional-services, and contractual obligations also need a launch review.

### 12.2 Required controls

- Data inventory, purpose and legal-basis register, minimization, retention,
  deletion, subject-right workflow, processing-impact assessment, and
  cross-border/processor assessment.
- Tenant isolation in application, database, search, vector, object storage,
  caches, logs, analytics, and support tooling.
- Encryption in transit and at rest; managed secrets; key rotation; restricted
  break-glass access; immutable audit log.
- Contractual controls preventing model/service providers from training on or
  retaining customer content beyond the approved purpose.
- PII and secret detection before prompts, logs, analytics, and evaluation sets;
  redacted test fixtures by default.
- Retrieved content is untrusted data. Strip active content, sandbox parsing,
  label source boundaries, ignore embedded instructions, and enforce tool policy
  outside the model.
- Egress allowlists, read-only research tools, parameterized queries, download
  scanning, rate limits, and per-agent capability tokens.
- Incident playbooks for wrong legal advice, privacy breach, source poisoning,
  model/provider failure, and corrupted legal snapshot.
- Model/system cards, change approval, red-team reports, evaluation results,
  and a kill switch/rollback for each snapshot and model version.

Use the Vietnamese legal requirements as mandatory controls and NIST AI RMF,
NIST's GenAI Profile, ISO/IEC 42001, and OWASP LLM Top 10 as complementary
governance and threat-model references.

## 13. Evaluation and release gates

### 13.1 Build the benchmark before model optimization

Create a Vietnamese tax benchmark authored and adjudicated by tax professionals.
The first 300 cases should cover:

- direct lookup, definitions, and exact citations;
- multi-hop rules and nested exceptions;
- old versus new law and transitional dates;
- conflicting or lower-authority guidance;
- missing material facts and necessary clarifying questions;
- calculations, deadlines, and documentary conditions;
- unanswerable/adversarial questions;
- OCR tables, annexes, and uploaded evidence;
- prompt injection and cross-tenant access attempts;
- changes that should affect a calculator, template, or saved matter.

Keep test cases by legal snapshot. Never change the expected answer silently when
the law changes; create a new dated expectation.

### 13.2 Component metrics

**Parsing and corpus**

- metadata/date/status accuracy;
- structural parse and cross-reference accuracy;
- OCR character/table/formula accuracy;
- amendment and point-in-time materialization accuracy.

**Retrieval**

- recall@k, precision@k, MRR, nDCG;
- controlling-provision recall;
- exception/definition/transition recall;
- version and authority filter accuracy;
- hard-negative rejection.

**Generation and validation**

- legal conclusion correctness by expert rubric;
- citation existence, quotation accuracy, entailment, completeness, and correct
  legal period;
- factual grounding and assumption disclosure;
- calculation exactness and reproducibility;
- abstention and clarification quality;
- counterargument/issue coverage.

**System**

- p50/p95 latency, availability, token/tool cost;
- tenant-isolation/security test pass rate;
- update detection-to-reviewed-publication time;
- expert edit distance, review time, override rate, and escaped-error severity.

### 13.3 Initial release gates

- Zero fabricated or non-resolving citations on the release benchmark.
- 100% exact match for deterministic calculations and deadlines in scope.
- At least 98% citation-support correctness and 95% controlling-provision
  recall on the locked benchmark; failures must be risk-weighted and reviewed.
- 100% temporal-version accuracy on the historical/transitional subset.
- No critical or high security finding; tenant-isolation tests pass completely.
- Every high-impact answer is routed to professional review with a full audit
  trace.
- Regression against the prior production system is non-degrading on critical
  slices, not merely better on the average score.

Passing a finite benchmark does not justify a "hallucination-free" claim. A 2024
study of leading legal research tools still found material hallucination rates;
the correct operating posture is measurable residual risk and human control.

## 14. Delivery roadmap

### Phase 0: legal, data, and evaluation foundation (weeks 1-4)

Deliverables:

- written legal opinions on service boundary, AI classification, privacy roles,
  consumer terms, data reuse/licensing, and professional review;
- source agreements and provenance policy;
- VAT/invoice issue taxonomy and authority map;
- first 100 gold cases, error taxonomy, and annotation handbook;
- threat model and data-flow diagram.

Exit gate: no unresolved blocker to collecting and using the proposed corpus.

### Phase 1: point-in-time retrieval prototype (weeks 5-10)

Deliverables:

- immutable artifact store, structural parser, bitemporal schema;
- VAT corpus with amendment/transition links;
- lexical baseline, dense baseline, hybrid fusion, reranker comparison;
- evidence viewer with exact provision and source artifact;
- 300 gold cases and reproducible evaluation harness.

Exit gate: retrieval, temporal, and citation targets are met before generative
case advice is exposed.

### Phase 2: professional Q&A MVP (weeks 11-16)

Deliverables:

- answer contract, clarification flow, evidence-pack synthesis;
- deterministic citation and temporal validators;
- identity, tenant isolation, audit, feedback, model/index registry;
- private beta for tax professionals; all substantive outputs reviewed.

Exit gate: agreed accuracy, review time, security, latency, and cost targets hold
on both benchmark and shadow production cases.

### Phase 3: case workspace and rules (weeks 17-26)

Deliverables:

- document ingestion and source-page fact extraction;
- structured interview, issue tree, coverage ledger, memo workflow;
- first VAT calculators/decision tables with versioned tests;
- reviewer queue, comments, approval, and corrected-answer capture.

Exit gate: expert-approved end-to-end cases show a material time saving without
an increase in risk-weighted escaped errors.

### Phase 4: legal graph and change intelligence (weeks 27-36)

Deliverables:

- reviewed normative graph and impact propagation;
- source monitoring, diffing, quarantine, atomic snapshots, rollback;
- affected-rule/test/template/matter alerts;
- deep-research workflow with counter-authority search.

Exit gate: seeded legal changes are detected, correctly propagated, reviewed,
and published within the agreed service level.

### Phase 5: controlled expansion (after week 36)

Add corporate income tax, personal income tax, and tax administration one domain
at a time. Each domain requires its own authority map, expert owner, benchmark,
rules, privacy/risk review, and release gate. Consumer mode remains a constrained
surface with stronger escalation.

## 15. Team and ownership

Minimum sustained team:

- product lead with legal-tech experience;
- tax-law lead accountable for legal quality;
- two or more tax professionals for authoring and independent adjudication;
- data/provenance engineer;
- information-retrieval/NLP engineer;
- backend/workflow engineer;
- frontend/product engineer;
- MLOps/evaluation engineer;
- security/privacy lead, with legal/compliance support.

Named owners are required for every corpus domain, executable rule, benchmark
slice, incident class, and production snapshot. "The model" owns nothing.

## 16. Product landscape and lessons

- CoCounsel combines agentic workflows with Westlaw/Practical Law content.
- Lexis+ with Protege emphasizes authoritative content, linked citations,
  citation-status services, matter documents, and guided research.
- Harvey exposes jurisdiction-specific curated knowledge sources and restricts
  citations to the selected source set.
- vLex Vincent combines legal research and workflow over a large legal database.
- In Vietnam, LuatVietnam's AI Luat and Thu Vien Phap Luat's AI Phap Luat show
  demand for cited Vietnamese legal Q&A; their public materials also show that
  complex cases and update quality remain hard problems.

These product pages are market evidence, not proof of technical correctness.
The repeatable lesson is that authoritative data, citation verification,
workflow, and human expertise are the product. Independent research found that
RAG-backed commercial legal tools still produced unsupported or incorrect
answers, so marketing claims must not become acceptance criteria.

The expanded 2026 product matrix, web information architecture, platform choices,
feature backlog, trust UX, and release plan are documented in
[benchmark-va-ke-hoach-web.md](benchmark-va-ke-hoach-web.md).

## 17. Decisions still requiring experiments

1. Which Vietnamese/multilingual embedding and reranking combination wins on the
   first 300 cases?
2. Does exact or HNSW vector search meet controlling-provision recall at expected
   corpus size and latency?
3. When do graph traversals justify Neo4j over PostgreSQL?
4. Which agent runtime best meets replay, pause, audit, and operational needs?
5. Can a smaller local model handle PII extraction, classification, and citation
   verification well enough to reduce cross-border data and cost?
6. What level of expert edit rate and time saving creates a defensible paid
   product without encouraging automation bias?

The research plan turns these questions into measured artifacts and gates.
