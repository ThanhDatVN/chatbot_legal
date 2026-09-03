# 03 — VietTaxBench: Evaluation Set and Metric Design

> This document defines **how we measure**. Without it, every claim about
> system quality is an opinion.

---

## 1. Design principles

1. **Measure in layers, not one number.** A single number hides what is broken.
2. **Gold must reach the Clause.** Document-level gold rewards wrong behaviour.
3. **Every question must trace to the corpus.** No question is written from
   memory; each binds to a real `chunk_id`.
4. **There must be questions that must not be answered.** A benchmark made only
   of answerable questions rewards recklessness.
5. **The benchmark is versioned.** Changing the corpus changes the benchmark;
   both carry hashes.

---

## 2. Five task families

```text
VietTaxBench
├── TaxQA        Question                    → Answer
├── TaxRAG       Question                    → Document / Article / Clause
├── TaxTime      Question + Time             → Correct Version
├── TaxChange    Old Law + New Law           → Changes
└── TaxConflict  Multiple Regulations        → Applicable Rule
```

### 2.1 TaxQA — content answering

Measures the ability to answer correctly when the evidence is available.

```text
Q:    "What VAT rate applies to exported goods?"
Gold: "0%" + the specific Article/Clause
```

### 2.2 TaxRAG — evidence retrieval

Measures the ability to retrieve the right **passage**, not merely the right
document.

```json
{
  "relevant_documents": ["LUAT-GTGT-48-2024"],
  "relevant_articles": ["LUAT-GTGT-48-2024#Điều 9"],
  "relevant_clauses": ["LUAT-GTGT-48-2024#Điều 9#Khoản 1"]
}
```

### 2.3 TaxTime — version selection  ← **the most important family**

**Case 1 — explicit date**

```text
Transaction date: 15/06/2022
Q: "Which tax rules do I apply?"

Gold:
  Document: A
  Version:  2022-01-01 → 2022-12-31
  Article:  Điều X
```

**Case 2 — date implicit in the phrasing**

```text
User says: "Last year I …"

The system must: Temporal Information Extraction → Normalize Date
                 → Determine Legal Version
```

**Case 3 — no date, time-sensitive question**

```text
Q: "What is the VAT rate for transport services?"

Gold behaviour: ASK for the event date; do not answer immediately.
```

Case 3 is the **humility test**. Answering immediately is scored wrong even if
the number happens to match the current rule.

### 2.4 TaxChange — change detection

```text
Circular A (original)  +  Circular B (amending)

Gold:
Điều 5:
  - Khoản 1: modified
  - Khoản 2: unchanged
  - Khoản 3: removed
  - Khoản 4: added
```

### 2.5 TaxConflict — conflict adjudication

```text
Q:        "Which provision applies?"
Evidence: Document A, Document B
Gold:     applicable = A
          reason     = "higher legal force"
          rule       = "lex superior"
```

---

## 3. Schema of one item

```jsonc
{
  "question_id": "vtb-taxtime-0042",
  "task": "taxtime",                    // taxqa|taxrag|taxtime|taxchange|taxconflict
  "category": "version_selection",
  "difficulty": "hard",                 // easy|medium|hard

  "question": "On 15/06/2022 my company exported software — which VAT rate applies?",
  "ground_truth": "0% under the rules for exported goods and services.",

  "as_of_date": "2022-06-15",

  // Gold at three granularities - lets Document / Article / Clause Recall be measured separately
  "gold_document_ids":   ["LUAT-GTGT-13-2008"],
  "gold_article_keys":   ["LUAT-GTGT-13-2008#Điều 8"],
  "gold_chunk_ids":      ["a3f9c1d2e4b58607"],
  "gold_citation_labels":["Điều 8 khoản 1 - Luật 13/2008/QH12"],

  // Gold for the time axis
  "gold_version_id": "13/2008/QH12#7c1e4a9b22f0",

  // Expected behaviour
  "should_refuse": false,
  "expects_clarification": false,

  // Traceability
  "provenance": "generated_from_corpus",  // or curated | adversarial
  "source_shard": "shard-0003",
  "created_at": "2026-09-03",
  "reviewed_by": null
}
```

---

## 4. Building ≥200 questions

### 4.1 Three sources, three roles

| Source | Count | Role | Construction |
|--------|------:|------|--------------|
| **A. Generated from corpus** | ~120 | The base; guarantees gold exists | Pick Articles/Clauses with quantitative content → generate templated questions → gold = that chunk |
| **B. Hand-written** | ~50 | Realistic, in an accountant's natural language | Write from operational scenarios → search the corpus for gold |
| **C. Adversarial** | ~40 | Traps; measures humility | Deliberately missing facts / out of scope / temporal traps |

**Total: ≥ 210 questions.**

### 4.2 Source A — generation from corpus (detail)

Only **eligible** chunks are selected:

- has a determined `dieu` and `khoan` (citable to the Clause);
- has an `effective_from` (the time axis is measurable);
- length 40–400 tokens (not so short as to be meaningless, not so long as to be
  ambiguous);
- contains at least one **quantitative entity**: `%`, an amount, a number of
  days, a revenue threshold.

Question templates by entity type:

| Entity | Template |
|--------|----------|
| `%` | "Under {document}, what rate applies to {subject}?" |
| days | "What is the deadline for {action} under {document}?" |
| amount | "What is the {item} level prescribed in {document}?" |
| definition | "How is {term} defined in {document}?" |
| condition | "What are the conditions for {action} under {document}?" |

**Important:** generated questions **must not repeat verbatim** a sentence from
the chunk, or the task degenerates into string matching. Rule: strip the
instrument number from 50% of questions to force genuine retrieval.

### 4.3 Source C — 40 adversarial questions

| Trap type | Count | Correct behaviour |
|-----------|------:|-------------------|
| No date, time-sensitive question | 10 | Ask for the event date |
| Asks about a past date (2018–2022) | 8 | Answer with the old version |
| Asks about a repealed document | 5 | State that it is no longer in force |
| Out of scope (criminal, labour law) | 5 | Decline, point to another source |
| Not present in the corpus | 5 | Say "insufficient basis"; do not invent |
| False presupposition ("under Article 99 of Law X…") | 4 | Correct it; do not confirm |
| Official Letter vs Law conflict | 3 | Choose the Law and explain |

### 4.4 Quality assurance

- **Cross-review:** every question in sources B and C is read independently by
  **two people**; record **inter-annotator agreement (Cohen's κ)** on the
  `gold_chunk_ids` field. Acceptance threshold: **κ ≥ 0.70**. Below that,
  rewrite the question.
- **Existence check:** a script confirms **100%** of `gold_chunk_ids` exist in
  `chunks.jsonl`. Gold pointing at nothing corrupts all Recall figures.
- **Leakage control:** never use an LLM to both generate the question **and**
  score it on the same item without human-confirmed gold.
- **Balance:** no more than 3 questions from the same `document_id`, so the
  benchmark is not dominated by one long document.

### 4.5 Target distribution

| Task family | Count | % |
|-------------|------:|--:|
| TaxQA | 70 | 33% |
| TaxRAG | 45 | 21% |
| **TaxTime** | **50** | **24%** |
| TaxChange | 20 | 10% |
| TaxConflict | 25 | 12% |
| **Total** | **210** | 100% |

| Difficulty | Count |
|------------|------:|
| easy | 60 |
| medium | 100 |
| hard | 50 |

| Tax domain | Count |
|------------|------:|
| VAT | 80 |
| Invoices / vouchers | 45 |
| Tax administration | 40 |
| Corporate income tax | 25 |
| Other | 20 |

---

## 5. The six-layer metric system

```text
Layer 1  Retrieval     →  Recall@K, MRR, nDCG@K, Hit Rate
Layer 2  Evidence      →  Article Recall@K, Clause Recall@K, Evidence F1
Layer 3  Answer        →  Answer Accuracy, F1, RAGAS Answer Correctness
Layer 4  Citation      →  Citation Precision, Citation Recall, Citation F1
Layer 5  Temporal      →  TVA, Version Mixing Rate
Layer 6  Legal Safety  →  Hallucination Rate, Abstention Accuracy,
                          Authority Accuracy, Conflict Resolution Accuracy
```

### 5.1 Layer 1 — Retrieval

```text
Recall@K = |retrieved@K ∩ gold| / |gold|

MRR      = (1/N) Σ 1 / rank_of_first_gold

nDCG@K   = DCG@K / IDCG@K,  DCG@K = Σ rel_i / log2(i+1)

HitRate@K = share of questions with at least 1 gold in the top-K
```

Report at **K ∈ {1, 3, 5, 10, 20}**.

### 5.2 Layer 2 — Evidence (Article and Clause level)

This is the layer LegalBench-RAG emphasises, and the layer that separates a
legal assistant from a search engine.

```text
Article Recall@K = |{retrieved Articles} ∩ {gold Articles}| / |{gold Articles}|
Clause Recall@K  = |{retrieved Clauses} ∩ {gold Clauses}| / |{gold Clauses}|

Evidence F1 = 2·P·R / (P+R)   at Clause level
```

### 5.3 Layer 3 — Answer

- **Answer Accuracy**: binary LLM-judge against `ground_truth`, with a rubric.
- **Numeric Exact Match**: for quantitative questions, match the number after
  normalisation (`10%` == `10 %` == `ten percent`). This metric uses **no LLM**,
  so it cannot drift.

### 5.4 Layer 4 — Citation

```text
Citation Precision = |citations that are correct and supporting| / |citations given|
Citation Recall    = |gold bases cited| / |gold bases|
```

**"Supporting"** is checked in two steps, not by an LLM alone:

1. **Mechanical check** — is the cited chunk actually present in the context
   given to the model? (blocks fabricated citations)
2. **Semantic check** — does the sentence carrying the citation follow from that
   chunk? (LLM judge, or NLI)

### 5.5 Layer 5 — Temporal

**TVA — Temporal Version Accuracy**

```text
TVA = (questions where EVERY citation was in force at as_of_date)
      ────────────────────────────────────────────────────────────
                  (questions that have an as_of_date)
```

One out-of-force citation in the answer sets that question's TVA to 0. There is
no partial credit: a user cannot "use 80% of a provision".

**VMR — Version Mixing Rate**

```text
VMR = (answers citing ≥2 different version_ids OF THE SAME article_key)
      ─────────────────────────────────────────────────────────────────
                          (total answers)
```

This is the dedicated metric for the hallucination class in
[document 01 §5.3](01-problem-analysis.md). Target: **VMR = 0**. The key
distinction: citing two different Articles of two different documents is
**normal**; citing two *versions* of **the same Article** is an **error**.

### 5.6 Layer 6 — Legal Safety

**Hallucination Rate**

```text
HR = (answers containing at least one normative assertion
      unsupported by any context) / N
```

**Abstention Accuracy** — measures humility, computed on a confusion matrix:

|  | Should answer | Should decline/ask |
|--|---------------|--------------------|
| **Answered** | ✅ correct | ❌ **over-confident** (most dangerous) |
| **Declined** | ❌ over-cautious | ✅ correct |

```text
Abstention Accuracy = (TP + TN) / N
Over-confidence Rate = over-confident / (questions that should be declined)
```

Report **both** — a system that declines everything scores Hallucination Rate =
0 and is entirely useless.

**Legal Authority Accuracy**

```text
LAuA = (questions where the highest-tier citation is the correct tier)
       / (questions with ≥2 documents of different tiers in context)
```

**Conflict Resolution Accuracy** — on the `taxconflict` subset:

```text
CRA = (cases where the correct applicable provision was chosen) / (conflict cases)
CRA-explained = share of cases whose decision traces to a named rule
```

### 5.7 The composite metric: LAA

```text
LAA(item) = AnswerCorrect
          ∧ CorrectSource
          ∧ CorrectArticle
          ∧ CorrectVersion
          ∧ ApplicableAtTime

LAA = (1/N) Σ LAA(item)
```

**LAA is the project's headline number.** Every other metric explains *why* LAA
sits where it does.

---

## 6. Integrating RAGAS

RAGAS runs in parallel; it does not replace the metric system above.

| RAGAS metric | Answers | Blind spot |
|--------------|---------|------------|
| Faithfulness | Is it grounded in the context? | **Scores 1.0 on a repealed document** |
| Answer Relevancy | Is it on point? | Knows nothing about legal correctness |
| Context Precision | Is the context clean? | Knows nothing about version correctness |
| Context Recall | Is the context sufficient? | — |
| Answer Correctness | How close to the reference? | Depends on gold quality |

**LLM-judge protocol** (mandatory for reproducibility):

1. Judge model: `claude-opus-5`, `effort=high`, default temperature.
2. Score each item **3 times**, take the **majority** (self-consistency).
3. The judge **must not see** which configuration it is scoring (bias control).
4. Record the judge prompts in `reports/judge-prompts/` for reproduction.
5. **Calibration:** 30 items are scored by hand; report the human ↔ judge
   correlation. If Spearman ρ < 0.7, the judge is not usable and the rubric must
   be fixed.

---

## 7. Benchmark versioning

```text
eval/
├── viettaxbench.jsonl              # the question set
├── viettaxbench.meta.json          # corpus hash, creation date, distribution, κ
├── injection_payloads.jsonl        # the attack suite
└── CHANGELOG.md
```

`viettaxbench.meta.json` records `corpus_hash`. Change the corpus → the hash
changes → all previous results are **flagged as measured on a different
corpus** and may not be compared directly.

---

## 8. Outstanding work

- [ ] Fix the eligible-chunk list for source A (script + criteria in §4.2).
- [ ] Write the 50 source-B questions with a tax or accounting practitioner.
- [ ] Write the 40 adversarial questions per the table in §4.3.
- [ ] Cross-review, compute κ, record it in `.meta.json`.
- [ ] Calibrate the judge against 30 hand-scored items.
- [ ] Fix the Answer Accuracy rubric in writing **before** the first measurement
      run.

---

**Previous:** [02 — Related work](02-related-work.md)
**Next:** [04 — System architecture](04-system-architecture.md)
