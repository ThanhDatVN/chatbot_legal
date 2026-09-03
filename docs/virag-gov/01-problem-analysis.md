# 01 — Problem Analysis

> This document defines the problem, demonstrates why the "RAG + chatbot"
> approach fails in the tax-law domain, and fixes the success criteria.

---

## 1. The surface problem and the real problem

### 1.1 The wrong framing

```text
User → "Does my company have to pay VAT?" → LLM + RAG → Answer
```

This treats legal Q&A as **Question Answering over documents**. It is
technically valid and operationally wrong, because it assumes three things that
are not true:

1. There is **one** correct answer to the question.
2. The answer is **independent of time**.
3. Every document found carries **equal weight**.

All three assumptions are false under Vietnamese law.

### 1.2 The correct framing

```text
User question
      ↓
Understand intent
      ↓
Identify the subject (company / household business / individual / foreign contractor)
      ↓
Identify the tax (VAT / CIT / PIT / SCT / import-export / …)
      ↓
Identify the DATE THE OBLIGATION AROSE          ← break point 1
      ↓
Identify scope (sector, location, incentives)
      ↓
Retrieve candidate documents
      ↓
Filter to the version in force AT THAT DATE     ← break point 2
      ↓
Analyse amendment / supplement / replacement    ← break point 3
      ↓
Detect and resolve conflicts                    ← break point 4
      ↓
Apply legal precedence rules
      ↓
Generate the answer
      ↓
Cite Article – Clause – Point                   ← break point 5
      ↓
Report confidence and conditions of application
```

**Conclusion:** this is not one problem but **five coupled problems**:

| # | Sub-problem | Nature | Risk if skipped |
|---|-------------|--------|-----------------|
| 1 | Tax Question Answering | Text generation | Wrong content |
| 2 | Legal Information Retrieval | Domain IR | Wrong document |
| 3 | **Temporal Legal Reasoning** | Time reasoning | **Citing a document that does not apply** |
| 4 | **Legal Conflict Resolution** | Rule reasoning | Wrong provision chosen on conflict |
| 5 | **Legal Change Detection** | Version comparison | Not knowing a rule changed |

Problems 1–2 are what everyone does. Problems 3–5 are where research
contribution and enterprise value live.

---

## 2. Users, jobs to be done, and the cost of error

### 2.1 Three user groups

| Group | Characteristics | Typical question | Ability to verify |
|-------|-----------------|------------------|:-----------------:|
| **A. Corporate accountants** | Work in periods, under deadline pressure | "What VAT rate applies to this service invoice?" | Medium |
| **B. Tax specialists / advisers** | Know how to research, need speed and evidence | "Does Article 9 of Law 48/2024 amend any article of 13/2008?" | **High** |
| **C. Household business owners / individuals** | No professional background | "I sell online — do I owe tax?" | **Low** |

**Scope decision for v1: serve groups A and B only.** Reasoning in §9.3.

### 2.2 The jobs actually being done

Users do not "want to ask a chatbot". They have four jobs:

| # | Job | The hidden question | Serving module |
|--:|-----|---------------------|----------------|
| J1 | **Determine the obligation** for a specific transaction | "Which provision does *my* case fall under?" | Ask |
| J2 | **Verify** an existing conclusion | "Exactly which legal basis do I cite in the file?" | Ask + citation |
| J3 | **Finalise / review the past** | "For the 2022 period, was what I applied correct *at that time*?" | **Time Machine** |
| J4 | **Track changes** | "How does the new instrument affect my current process?" | **Change Monitor** |

**The observation that drives the design:** J2, J3 and J4 **cannot be satisfied**
by an ordinary QA chatbot.

- J2 needs citation to the **Clause**, not the document name — a file justified
  to the tax authority must cite Article/Clause/Point.
- J3 needs a **multi-version** corpus — precisely what "always the latest law"
  destroys.
- J4 needs **version comparison**, not retrieval.

Three of the four core jobs require capabilities plain RAG does not have.

### 2.3 The cost of a wrong answer

Not all errors cost the same. Ordered by real cost to the user:

| Error type | User can detect it? | Typical cost |
|------------|:-------------------:|--------------|
| Says "insufficient basis" when a basis exists | ✅ immediately | Lost time, manual lookup |
| **Fabricated** citation (Article does not exist) | ✅ on opening the document | Lost trust, lost time |
| Misstates the content | ⚠️ if the source is read carefully | Medium |
| Omits an exception condition | ❌ usually not | Wrong treatment, back-tax assessment |
| **Wrong version for the date** | ❌ **almost never** | **Wrong tax period filing → back-tax + late-payment penalty + interest** |

**The central proposition of the whole project:**

> The **cheapest** error is the one the system admits to. The **most expensive**
> error is the one that looks like a correct answer.

This is why principle P1 — *"a silent wrong answer is worse than no answer"* —
heads the design principles ([05 §0](05-design-decisions.md)), and why
**Abstention Accuracy** is a first-class metric rather than an afterthought.

### 2.4 Why this problem is solvable only now

| Condition | Status |
|-----------|--------|
| Digitised legal corpus, publicly accessible | ✅ Official Gazette and government portal publish in full |
| Language model good enough in Vietnamese | ✅ Current generation |
| Strong multilingual embeddings for Vietnamese | ✅ BGE-M3 and equivalents |
| Inference cheap enough to run many verification layers | ✅ |
| Legal awareness of AI's supporting role | ✅ The Ministry of Justice has a clear position |

Three years ago every row in this table read "not yet".

---

## 3. Why "Answer Correctness" is not enough

The canonical example:

> **Q:** "What is the VAT rate for service X?"
> **A:** "10%"

The answer may be **numerically right** while the system has:

- retrieved the wrong document;
- retrieved the right document but the wrong version;
- retrieved a document no longer in force;
- cited the wrong Article;
- ignored an exception that removes this case from that rate.

Therefore:

```text
Answer Correctness  ≠  Legal Reliability
```

A legal assistant must be measured on **six independent axes**:

```text
1. Retrieval correct?  → was the necessary evidence found?
2. Version correct?    → is it the version in force at the date?
3. Article correct?    → does it point at the right Article/Clause/Point?
4. Reasoning correct?  → were the precedence rules applied correctly?
5. Answer correct?     → is the content right?
6. Citation correct?   → does the cited text actually support the assertion?
```

This is the basis for the composite **LAA** metric in §8.

---

## 4. Risk number one: Temporal Misgrounding

### 4.1 The failure mechanism

```text
Transaction arose:  15/06/2021
User asks:          03/09/2026
Ordinary RAG:       query → vector search → top document → LLM
Result:             cites the 2026 rule
```

This is the **most dangerous** error because:

- It **does not look like hallucination**. The cited document is **real**, the
  Article/Clause is **real**, the figures are **real**.
- Every "does this citation exist?" check **passes**.
- A non-specialist user has **no way to detect it**.
- The financial consequence is real: wrong tax-period filing, back-tax
  assessment, late-payment penalties.

### 4.2 Why vector search cannot save you

Embeddings encode **meaning**, not **legal force**. Two versions of the same
Article differing by a few digits produce nearly identical vectors. Similarity
cannot distinguish "10%" from 2021 and "8%" from 2022 — indeed the newer version
is often **closer** to the question because its language is more modern.

**Design consequence:** time must be a **hard filter at the retrieval layer**,
evaluated **during index traversal**, not a post-filter. Post-filtering shrinks
top-k: ask for 30 neighbours, get 30 current-law hits, filter down to 2.

### 4.3 Evidence from this project's own corpus

Measured on `data/crawl/tax-document-all-fulltext-run-v4-2026-08-11`:

| Metric | Value |
|--------|-------|
| `source_page` records | 698 |
| With `effective_date` | 538 (77.1%) |
| **Missing `effective_date`** | **160 (22.9%)** |

Nearly **a quarter** of crawled documents have **no effective date in the portal
metadata**. If the system defaults to "no date = in force", it injects 160
unverified documents into every answer. If it defaults to "no date = discard",
it loses 23% of the corpus.

**This is why the system needs an `UNKNOWN` status and a graded validity score
rather than a binary flag.** Details in
[document 06 §9](06-data-pipeline.md).

---

## 5. Seven kinds of conflict to handle

A conflict is not merely "A says 10%, B says 8%".

### 5.1 Temporal Conflict

```text
2019: rate A     2022: rate B     2025: rate C
Q: "What about 2020?"   →  RAG returns C  →  WRONG
```
**Resolution:** only provisions in force at `as_of` may compete at all.

### 5.2 Hierarchical Conflict

```text
similarity: Official Letter = 0.92   |   Law = 0.89
```
The Official Letter must not win on score.
**Resolution:** *lex superior* — higher legal force prevails.

### 5.3 Amendment Conflict

Article 5 exists in 2020, 2022 and 2024 versions in the vector DB. The chatbot
takes its first sentence from 2020 and its second from 2024, producing a
conclusion that **never existed in any version of the law**.

This is **Version Mixing Hallucination** — a distinct class of hallucination
needing its own metric (VMR, [document 03 §5.5](03-benchmark-viettaxbench.md)).

### 5.4 Partial Amendment

```text
Circular B: "Amends Khoản 2 Điều 3 of Circular A"

→ Điều 1 of A:          still in force
→ Điều 2 of A:          still in force
→ Điều 3 Khoản 1 of A:  still in force
→ Điều 3 Khoản 2 of A:  CHANGED
→ Điều 4 of A:          still in force
```

Document-level metadata `{"status": "amended"}` is **not sufficient**. Status
must descend to **Article → Clause → Point**.

### 5.5 Implicit Repeal

A new instrument does not say "Article X is repealed", but the new rule
contradicts or wholly supersedes the old content. The system must distinguish:

```text
Explicit change  |  Implicit conflict  |  Potential overlap  |  No conflict
```

**Do not delegate this decision to the LLM.** The correct flow:

```text
LLM nominates conflict candidates → Rule engine → Legal graph → Decision / open
```

### 5.6 General vs Special

General rule: rate X. Sector-specific rule for sector Y: rate Z. The user is in
sector Y. RAG returns the general rule because similarity is higher.
**Resolution:** *lex specialis* — the special rule prevails, **conditional on**
confirming the taxpayer falls within that special scope.

### 5.7 Formal Law vs Administrative Guidance

| Tier 1 (binding) | Tier 2 (guidance) |
|------------------|-------------------|
| Law, Decree, Circular | Official Letter, guidance, FAQ, replies to businesses |

An Official Letter answering *Business A, situation B* does **not automatically**
apply to *Business C, situation D*. The system is required to say:

> "This is guidance for a specific case and carries indicative value only."

### 5.8 Summary: which conflict needs which mechanism

| Conflict type | Needs what data | Needs what mechanism |
|---------------|-----------------|----------------------|
| 5.1 Temporal | Validity interval | Filter + validity score |
| 5.2 Hierarchical | Legal force tier | Authority component in ranking |
| 5.3 Amendment | `version_id` | Version-mixing detection (VMR) |
| 5.4 Partial | Clause-level status | `legal_status` per chunk |
| 5.5 Implicit repeal | Relation graph | Rule engine + controlled abstention |
| 5.6 General/Special | Scope of application | Detection of special-rule markers |
| 5.7 Formal/Guidance | Document type | Separate tier 9 + mandatory warning |

None of these is solved by "a better prompt". All seven require **metadata that
plain RAG never collects**.

---

## 6. "The latest law" is not "the applicable law"

Many products advertise *"always up to date with the latest law"*. In law:

```text
Latest Law   ≠   Applicable Law
```

When the event date is unknown, the correct behaviour is **not** to guess but
to **ask** — the **Temporal Clarification** mechanism:

> "To determine the applicable provision precisely, I need the date your
> transaction / tax obligation arose."

And to lower the confidence level. A system that answers confidently while
missing a decisive fact is **less safe** than one that knows how to stay
silent.

---

## 7. A taxonomy of failure in existing systems

Eight failure modes, ordered by how hard they are to detect. Every mechanism in
documents 04 and 05 exists to counter this list.

| # | Failure mode | Symptom | Who can detect it | Countermeasure |
|--:|--------------|---------|-------------------|----------------|
| F1 | **Fabrication** | Cites a non-existent Article/Clause | User, on opening the source | Mechanical `[Sn]` check (ADR-014 step 1) |
| F2 | **Retrieval miss** | No evidence found, vague answer | Specialist | Hybrid + Recall@K measurement |
| F3 | **Attribution error** | Real citation that does not support the assertion | Specialist reading carefully | Semantic check (ADR-014 step 2) |
| F4 | **Granularity failure** | Cites only the document name, not the Clause | Specialist | Parent–child chunking (ADR-002) |
| F5 | **Authority inversion** | Official Letter beats Law | Specialist | Authority component (ADR-008) |
| F6 | **Scope error** | Applies the general rule where a special rule exists | Experienced specialist | Lex specialis + specificity |
| F7 | **Version mixing** | Mixes two versions of the same Article | **Almost nobody** | VMR + guardrail block |
| F8 | **Temporal misgrounding** | Right document, wrong point in time | **Almost nobody** | 7 defence layers ([07 §3](07-risk-analysis.md)) |

**Observation:** F1–F3 are what the RAG community already measures (RAGAS
catches them). F4–F8 are **legal-domain specific** and **no standard RAG metric
catches any of them**. That is exactly the gap VietTaxBench fills.

Worth noting: the two **hardest-to-detect** failure modes are also the two
**least-measured** in the existing literature.

---

## 8. Success criteria

### 8.1 The composite metric: LAA — Legal Applicability Accuracy

An answer counts as **fully correct** only if **all** hold:

```text
LAA = 1  ⟺  Answer Correct
           ∧ Correct Legal Source
           ∧ Correct Article (Điều/Khoản/Điểm)
           ∧ Correct Version
           ∧ Applicable at Relevant Time
```

Example:

```text
Answer Correct   = 1
Citation Correct = 1
Version Wrong    = 0
──────────────────────
LAA              = 0
```

Stricter than ordinary accuracy, deliberately so: in law, "close enough" has no
value.

### 8.2 Ten priority metrics

| # | Metric | v1 target | Why it matters |
|---|--------|-----------|----------------|
| 1 | Answer Accuracy | ≥ 0.80 | Content is right |
| 2 | Retrieval Recall@10 | ≥ 0.85 | Evidence available to answer from |
| 3 | Citation Precision | ≥ 0.90 | Citations genuinely support assertions |
| 4 | Citation Completeness | ≥ 0.75 | No omitted legal basis |
| 5 | **TVA** (Temporal Version Accuracy) | ≥ 0.85 | Right version for the date |
| 6 | Legal Authority Accuracy | ≥ 0.90 | Right tier prioritised |
| 7 | Conflict Resolution Accuracy | ≥ 0.75 | Correct resolution on conflict |
| 8 | Hallucination Rate | ≤ 0.05 | No invented rules |
| 9 | **Abstention Accuracy** | ≥ 0.85 | Knows when not to answer |
| 10 | **LAA** | ≥ 0.65 | The unified score |

These are **design targets**, not measurements. Measurement methods in
[document 03](03-benchmark-viettaxbench.md).

**A note on the LAA = 0.65 target.** It sits deliberately below Answer Accuracy
= 0.80: LAA is a conjunction of five conditions, so it is **always** lower than
any component. LAA = 0.65 means *two-thirds of answers are right on every
axis* — for a v1 system on a corpus where 23% of documents lack a date, that is
an ambitious target, not a modest one.

### 8.3 Operational metrics

| Metric | Target |
|--------|--------|
| P50 time to first token (streaming) | ≤ 1.2 s |
| P95 full answer latency | ≤ 8 s |
| Semantic cache hit rate | ≥ 30% after 1,000 queries |
| Attack Success Rate (prompt injection) | ≤ 5% over ≥ 20 payloads |
| Update latency (P50), publication → indexed | ≤ 24 h |
| Clarification Rate | 15–25% |
| Over-clarification Rate (asked, answer unchanged) | ≤ 5% |

---

## 9. Version 1 scope

### 9.1 In scope

- **Taxes:** VAT and invoices/vouchers (per the repository's foundation design).
- **Users:** groups A and B from §2.1 — **professionals**.
- **Sources:** only legal normative documents from official sources verified for
  number, date and checksum.
- **Time window:** 10 years (2016-08-11 – 2026-08-11).
- **Language:** Vietnamese.

### 9.2 Out of scope (v1)

| Out of scope | Reason |
|--------------|--------|
| Advice to the general public across all taxes | §9.3 |
| **Computing the tax amount owed** | Needs a deterministic tool (decision table), not an LLM |
| Tax-dispute strategy advice | High liability, requires a licensed practitioner |
| Client case data / files | Requires a different isolation and security posture |
| Provincial-level instruments | Not in the corpus |
| Pre-2016 periods | Outside the crawl window |

### 9.3 Why the user scope is narrowed

> An assistant that is 5% wrong on one tax, used by a **professional** who knows
> how to verify, is a useful tool.
>
> An assistant that is 5% wrong across all taxes, used by the **general public**
> who cannot verify, is a dangerous tool.

The table in §2.1 shows group C has the **lowest ability to verify** and bears
the financial consequence most directly. Serving group C demands a different
accuracy level and different safeguards — a v2 decision, after real numbers
exist.

---

## 10. Comparison against VNPT SmartBot and the market

### 10.1 Versus a typical FAQ chatbot / SmartBot

| Criterion | FAQ chatbot / SmartBot | ViRAG-Gov |
|-----------|------------------------|-----------|
| Knowledge source | Scripts + hand-edited FAQ | Raw legal corpus with checksums |
| Citation | None, or a document name | Article – Clause – Point + source URL + validity interval |
| Time | Always "current" | `as_of` = date of the event |
| Conflicts | Not handled | 7 types, resolved by a rule engine |
| Versions | A single version | Immutable, multi-version, bitemporal |
| Missing facts | Vague answer | Asks back + lowers confidence |
| Measurement | CSAT / containment rate | 6 metric layers + LAA + RAGAS + ablation |
| Safety | Keyword filters | Two-way guardrails + injection test suite |
| Updates | Manual editing | Crawl → diff → change event |

### 10.2 Versus existing Vietnamese legal-AI systems

Per the summary in [document A §10](A-research-direction.md), the market
already covers **Lookup + Q&A + RAG + Citation**.

**Strategic consequence:** entering that same square means head-on competition
with no advantage. The empty square is **Legal Change Intelligence**:

> "What did the new regulation change?"
> "Which businesses are affected?"
> "Which provisions of the old policy no longer apply?"
> "Is the answer the system gave last month still correct?"

The last question is especially notable: **no current system can answer it**,
because it requires transaction time — the system must remember *what it knew
and when*.

### 10.3 The regulator's constraint

The position stated by the Ministry of Justice when assessing AI solutions for
reviewing legal normative documents — **AI is only a support tool; results
require human review** — is not a recommendation but a **design constraint**. It
means the system must be built so that **a human can check it**, not so that it
replaces the human. Every explainability mechanism in documents 04–05 derives
from this constraint.

---

## 11. Four product modules

```text
┌─────────────────────────────────────────────────────────┐
│                      USER LAYER                          │
│                                                          │
│  💬 Ask            — Q&A with citations        (J1, J2)  │
│  📅 Time Machine   — "which law applied on X?" (J3)      │
│  🔄 Change Monitor — what did the new text change? (J4)  │
│  ⚖️  Conflict Explorer — which rule wins, and why?       │
└─────────────────────────────────────────────────────────┘
```

Module 1 is the centre; modules 2–4 turn the product from **passive search**
into **proactive legal intelligence**. Mapping to jobs-to-be-done in §2.2.
Detailed design in [document 04](04-system-architecture.md).

---

## 12. Assumptions and preconditions

| Assumption | Risk if false | Verification | Risk ID |
|------------|---------------|--------------|---------|
| Portal date metadata is trustworthy | The entire time axis is wrong | Cross-check the Official Gazette (done: 19/22 laws match) | R-D05 |
| Article/Clause/Point structure is parseable from PDF | Loss of pin-point citation | Measure parse success rate, [document 06 §5.5](06-data-pipeline.md) | R-D04 |
| **The corpus holds enough multi-version documents** | **The central research contribution cannot be validated** | Count before anything else — gate G0 | **R-D02** |
| Amendment relations are declared explicitly in the text | Implicit repeals missed | Accepted; marked low confidence | — |
| Users are professionals who verify | Consequences of error worsen | Constrained by the scope in §9 | R-L01 |
| Vietnamese OCR is good enough for scans | Part of the corpus lost | Measure per page, [document 06 §4](06-data-pipeline.md) | R-D03 |
| The LLM judge is reliable enough to score the eval | Every measurement becomes meaningless | Calibrate against 30 hand-scored items | R-M07 |

The bolded assumption is the **only one that can invalidate the scientific
standing of the whole project**, and is therefore tested **first**
([08 §3](08-implementation-plan.md)).

---

## 13. Conclusion

The problem to solve is not:

> *"Build a chatbot that answers tax questions."*

but:

> **"How can an AI system determine the correct tax provision applicable to a
> specific situation, at a specific point in time, amid documents that amend,
> replace and overlap one another and carry different legal force — and know
> how to say 'I do not have sufficient basis' when that is the truth?"**

Three compressed propositions:

1. **The most expensive error is the one that looks like a correct answer**
   (§2.3) → so the system is designed to surface errors rather than hide them.
2. **Five of the eight legal-domain failure modes are caught by no standard RAG
   metric** (§7) → so a purpose-built benchmark is required.
3. **All seven conflict types need metadata plain RAG never collects** (§5.8) →
   so the hard part is the data pipeline, not the model.

Every architectural, data and measurement choice in the following documents
serves those three propositions.

---

**Next:** [02 — Related work & research gap](02-related-work.md)
