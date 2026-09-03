# A — Research Direction Analysis

> **Provenance:** edited from `analystic.md` (original preserved at
> [`_source/analystic.original.md`](_source/analystic.original.md), in
> Vietnamese). This version keeps every argument of the original, reorders it
> along the line of reasoning, removes duplication, adds analysis, and converts
> ASCII diagrams to tables where a table is clearer.
>
> **Source warning:** the external links in this document have **not been
> independently verified**. See §12 for the checklist to complete before citing
> any of them formally.

---

## 1. The central thesis

A project framed as:

> ❌ *"A tax-law Q&A chatbot using RAG"*

is very hard to differentiate — the technique is commoditised and the market
already has products.

The correct framing:

> ✅ **Vietnamese Tax Legal Intelligence System**
>
> A system that does not merely answer tax questions, but determines **which
> provision applies, at which point in time, in which version of the document,
> which provisions have changed, and how confident the conclusion is.**

This framing rests on three properties of Vietnamese law:

| Property | Technical consequence |
|----------|----------------------|
| **Hierarchical** (Law → Decree → Circular → Official Letter) | Documents cannot be weighted equally |
| **Time-dependent** | Indexing only the current version is not enough |
| **Frequently amended** | A document is not a single immutable entity |

The Law on Promulgation of Legal Normative Documents sets out the principles of
application by effective date, precedence of higher legal force, the
later-instrument rule in certain cases, and the states of amendment,
replacement and expiry. These three properties are **matters of law**, not
technical conjecture.

---

## 2. What is the problem, really?

### 2.1 The naive framing

```text
User → "Does my company have to pay VAT?" → LLM → Answer
```

This is just **Question Answering**.

### 2.2 The complete framing

A real tax question must pass through a processing chain:

| Step | What must happen | Typical failure point |
|-----:|------------------|----------------------|
| 1 | Understand intent | Confusing lookup with advice |
| 2 | Identify the subject | Ignoring entity type → wrong applicable provision |
| 3 | Identify the tax | Mixing VAT with CIT |
| 4 | **Identify the date the obligation arose** | **Defaulting to "now"** |
| 5 | Identify location / scope | Ignoring location-based incentives |
| 6 | Retrieve documents | Similarity beats authority |
| 7 | **Identify the version in force at that date** | **Taking the newest** |
| 8 | Analyse amendment / replacement relations | Not knowing a clause was amended |
| 9 | Check for conflicts | Not detected |
| 10 | Apply precedence rules | Letting the LLM decide |
| 11 | Generate the answer | — |
| 12 | Cite Article – Clause – Point | Citing only the document name |
| 13 | Report confidence | Always confident |

### 2.3 Five coupled problems

1. **Tax Question Answering**
2. **Legal Information Retrieval**
3. **Temporal Legal Reasoning**
4. **Legal Conflict Resolution**
5. **Legal Change Detection**

> Problems 3, 4 and 5 are where a genuine research contribution is possible.

Problems 1–2 are what everyone can do, and they do not distinguish a good
system from a mediocre one.

---

## 3. Existing benchmarks and their limits

### 3.1 VLegal-Bench

A Vietnamese legal benchmark designed for the Vietnamese legal context, >10,000
questions, multiple cognitive levels: recognition, comprehension, reasoning,
interpretation, plus ethics/fairness aspects.

**Limitation:**

> VLegal-Bench evaluates **general legal capability**, not a benchmark
> specialised for tax law.

**Conclusion:** not recommended as the sole measure.

**Correct use:**

```text
VLegal-Bench
      +  A purpose-built Vietnam Tax Benchmark
      +  A Temporal / Version Benchmark
      +  A RAG Retrieval Benchmark
```

### 3.2 LegalBench-RAG

Most useful for its **way of thinking about evaluating legal RAG systems**: it
is not enough to answer correctly, the system must retrieve **the specific
legal passage required**.

Illustration:

> **Q:** "What is the VAT rate for service X?"
> **A:** "10%"

The answer may be right. But the system may have:

- retrieved the wrong document;
- retrieved an outdated document;
- retrieved a document no longer applicable;
- cited the wrong Article;
- ignored an exception condition.

Therefore:

```text
Answer Correctness  ≠  Legal Reliability
```

A good legal chatbot must evaluate six axes **separately**:

```text
1. Retrieval correct?   2. Version correct?   3. Article correct?
4. Reasoning correct?   5. Answer correct?    6. Citation correct?
```

### 3.3 Temporal Misgrounding in Legal RAG (French tax law)

The work closest to the central problem here. It identifies an extremely
dangerous failure:

> The system retrieves the **current version** of the law even though the
> question actually requires the version **in force in the past**.

Illustration:

```text
User asks: "In 2021, what rate did my business have to apply?"

Ordinary RAG:  Query → Vector Search → top current document → LLM
Result:        cites the 2026 law
```

The work shows that RAG over a corpus containing **only current versions** can
confidently cite a **real** document that **does not apply at the relevant
time**; the authors propose a **multi-version corpus** and a **separate
evaluation of temporal version selection**.

**This is a highly suitable direction for a Vietnamese tax chatbot.**

---

## 4. A purpose-built benchmark: VietTaxBench

Instead of only evaluating `Question → Answer`, design the full chain:

```text
Question → Intent → Tax Domain → Temporal Context
        → Applicable Legal Documents → Applicable Document Version
        → Relevant Articles → Legal Reasoning → Answer → Citation
```

### 4.1 Five task families

| Family | Input → Output |
|--------|----------------|
| **TaxQA** | Question → Answer |
| **TaxRAG** | Question → Document / Article |
| **TaxTime** | Question + Time → Correct Version |
| **TaxChange** | Old Law + New Law → Changes |
| **TaxConflict** | Multiple Regulations → Applicable Rule |

### 4.2 Task 1 — Tax Legal Retrieval

```text
Input:  "Does a household business with revenue below X owe tax?"

Output: {
  "relevant_documents": ["Document A", "Document B"],
  "relevant_articles":  ["Điều X Khoản Y"]
}
```

**Metrics:** Recall@K, Precision@K, MRR, nDCG, Hit Rate.

### 4.3 Task 2 — Article-level Retrieval

Do not evaluate only *finding the right document*, but *finding the right
**Article – Clause – Point***.

```text
VAT Law
   ├── Điều 1
   ├── Điều 2
   └── Điều 3
          ├── Khoản 1
          ├── Khoản 2
          └── Khoản 3
```

If RAG returns the entire 100-page VAT Law, it technically "retrieved the right
document". But:

```text
Correct Document  ≠  Correct Evidence
```

**Metrics:** Article Recall@K, Clause Recall@K, Citation Precision, Evidence F1.

### 4.4 Task 3 — Temporal Legal Retrieval ← rated highest

**Case 1 — explicit date**

```text
Transaction date: 15/06/2022
Q: "Which tax rules do I apply?"

Gold: Document A, Version 2022-01-01 → 2022-12-31, Article X
```

**Case 2 — implicit date**

```text
User says: "Last year I …"

System must: Temporal Information Extraction → Normalize Date
             → Determine Legal Version
```

**Metrics:** Temporal Retrieval Accuracy, Applicable Version Accuracy, Temporal
Citation Accuracy — collectively **TVA (Temporal Version Accuracy)**.

### 4.5 Task 4 — Legal Change Detection

```text
Circular A → Circular B amends Điều 5 → Decree C partially replaces
```

User asks: *"What did the new regulation change?"*

The system must detect: **Added / Modified / Removed / Replaced / Unaffected**

```text
Điều 5:
  - Khoản 1: modified
  - Khoản 2: unchanged
  - Khoản 3: repealed
  - Khoản 4: added
```

**Metrics:** Change Detection Precision / Recall / F1.

### 4.6 Task 5 — Impact Analysis

The question: *"Which provisions does a new law affect?"*

```text
New Tax Regulation
   ├─ Directly modifies  → Article A, Article B
   └─ Indirectly impacts → Circular C, Decree D, Guidance E
```

Modelled as a **Legal Dependency Graph**:

```text
              [Law]
        ┌───────┴───────┐
    [Decree]        [Decree]
        │               │
   [Circular]      [Circular]
        │
[Official Letter]
```

**Relation types:** `AMENDS`, `REPLACES`, `REPEALS`, `DETAILS`, `GUIDES`,
`REFERS_TO`, `OVERRIDES`, `CONFLICTS_WITH`, `INTERPRETS`.

**Metrics:** Impact Detection Precision / Recall, Impact Graph F1, Relation
Classification Accuracy.

### 4.7 Task 6 — Legal Conflict Resolution

```text
Is this actually a conflict?  →  YES / NO
        → Why?
        → Which rule prevails?
```

**Benchmark sample:**

```text
Question: Which provision applies?
Evidence: Document A, Document B
Expected: applicable = A; reason = "Higher legal authority"
```

**Metrics:** Conflict Detection Accuracy, Conflict Classification F1,
Resolution Accuracy, Legal Justification Score.

---

## 5. Seven kinds of conflict

A conflict is not merely *"A says 10%, B says 8%"*.

### 5.1 Temporal Conflict — risk number one

```text
2019: rate A   |   2022: rate B   |   2025: rate C
Q: "What about 2020?"   →   RAG returns C   →   WRONG
```

### 5.2 Hierarchical Conflict

```text
Law  >  Decree  >  Circular  >  Official Letter
```

The system must not weight documents equally:

```text
Vector similarity:  Document A = 0.92  |  Document B = 0.89
But:                A = Official Letter |  B = Law
```

A cannot be chosen merely for higher similarity. What is needed:

```text
Legal Relevance Score  +  Legal Authority Score  +  Temporal Validity Score
```

### 5.3 Amendment Conflict → Version Mixing Hallucination

```text
Điều 5:  2020 version  |  2022 version  |  2024 version
```

The vector DB holds all three. The chatbot may take its first sentence from
2020 and its second from 2024, producing a conclusion that **never existed in
any version of the law**.

> This is **Version Mixing Hallucination** and deserves its own metric.

### 5.4 Partial Amendment

```text
Circular A: Điều 1, 2, 3, 4
Circular B: "Amends Khoản 2 Điều 3"

→ Điều 1 stands · Điều 2 stands · Điều 3 Khoản 1 stands
→ Điều 3 Khoản 2 CHANGED · Điều 4 stands
```

Metadata of `{"document_status": "amended"}` is **not sufficient**. Status must
descend to **Article → Clause → Point**.

### 5.5 Implicit Repeal

A new instrument does not say *"Điều X is repealed"*, but the new rule
contradicts or wholly supersedes the old content. The system must distinguish:

```text
Explicit change | Implicit conflict | Potential overlap | No conflict
```

**The LLM must not decide this alone.** The recommended flow:

```text
LLM detects candidate conflict → Rule Engine → Legal Knowledge Graph
                               → Final decision / uncertainty
```

### 5.6 General Rule vs Special Rule

The user belongs to a sector with its own rule, but RAG returns the general
rule because similarity is higher. Legally: **Specific rule > General rule**.

Required: classify the subject · determine scope of application · detect
exceptions · reason across multiple documents.

### 5.7 Formal Law vs Administrative Guidance

| Tier 1 | Tier 2 |
|--------|--------|
| Law, Decree, Circular | Official Letter, guidance, FAQ, replies to businesses |

An Official Letter answering *Business A, situation B* does not automatically
apply to *Business C, situation D*. The chatbot must say so:

> "This is guidance for a specific case and may be indicative only."

---

## 6. "Current law" is not always right

Many chatbots advertise *"Always up to date with the latest law."* But:

```text
Latest Law  ≠  Applicable Law
```

```text
2020 transaction → user asks in 2026 → applicable regulation = 2020 version
```

The chatbot must ask or infer: **When did your event occur?**

If unknown → **Confidence ↓**, and the chatbot should say:

> "To determine the applicable provision precisely, I need the date the
> transaction arose."

This mechanism is called **Temporal Clarification**.

---

## 7. Recommended data architecture

**Do not do:**

```text
PDF → Chunking → Embedding → Vector DB
```

**Do:**

```text
Official Sources
      ↓ Document Acquisition
      ↓ Document Parsing
      ↓ Legal Structure Extraction
        ┌─────────────────────────┐
        │ Document                │
        │ └── Chapter             │
        │     └── Article         │
        │         └── Clause      │
        │             └── Point   │
        └─────────────────────────┘
      ↓ Metadata Extraction
      ↓ Temporal Versioning
      ↓ Legal Relation Extraction
      ↓ Legal Knowledge Graph
        ├── Vector DB
        ├── Graph DB
        └── Version Database
```

### 7.1 Mandatory metadata per chunk

```json
{
  "document_id": "", "document_type": "", "document_number": "",
  "issuer": "", "issue_date": "", "effective_date": "", "expiration_date": "",
  "legal_status": "", "version_id": "",
  "article": "", "clause": "", "point": "",
  "tax_domain": "", "taxpayer_type": "",
  "supersedes": [], "amends": [], "repeals": [], "references": []
}
```

### 7.2 `legal_status` must not be merely active/inactive

```text
ACTIVE · PARTIALLY_AMENDED · PARTIALLY_REPEALED · REPLACED
EXPIRED · SUSPENDED · NOT_YET_EFFECTIVE · SUPERSEDED · UNKNOWN
```

---

## 8. System architecture: Hybrid RAG

Vector search alone is not recommended.

```text
User Question
      ↓ Intent Detection
      ↓ Temporal Detection
      ↓ Legal Entity Extraction
      ↓ Query Expansion
┌─────────────┬──────────────┬──────────────┐
│ BM25        │ Vector Search│ Graph Search │
└─────────────┴──────────────┴──────────────┘
      ↓ Candidate Docs
      ↓ Temporal Filter
      ↓ Authority Filter
      ↓ Legal Reranker
      ↓ Evidence Set
      ↓ LLM
      ↓ Citation Validation
      ↓ Final Answer
```

### 8.1 The ranking formula

Instead of `score = semantic_similarity`, use:

```text
Final Score = α·Semantic Relevance + β·Legal Authority + γ·Temporal Validity
            + δ·Specificity + ε·Citation Quality
```

| Component | Answers |
|-----------|---------|
| Semantic Relevance | Is the passage relevant to the question? |
| Legal Authority | Law > Decree > Circular > Official Letter |
| Temporal Validity | Was it in force at the date of the event? |
| Specificity | Does it match the subject / tax / sector / special conditions? |
| Citation Quality | How precisely can it be cited? |

---

## 9. A six-layer metric system

| Layer | Metrics |
|-------|---------|
| Retrieval | Recall@K, MRR, nDCG |
| Evidence | Article / Clause Recall |
| Answer | Accuracy, F1 |
| Citation | Citation Precision / Recall |
| Temporal | Temporal Version Accuracy |
| Legal Safety | Hallucination & Conflict Rate |

### 9.1 The ten most important metrics

| # | Metric | Answers |
|--:|--------|---------|
| 1 | Answer Accuracy | Is the answer correct? |
| 2 | Retrieval Recall@K | Was the right evidence found? |
| 3 | Citation Precision | Does the citation actually support the answer? |
| 4 | Citation Completeness | Was an important legal basis omitted? |
| 5 | Temporal Version Accuracy | Was the right version selected? |
| 6 | Legal Authority Accuracy | Was the right tier prioritised? |
| 7 | Conflict Resolution Accuracy | On conflict, was it resolved correctly? |
| 8 | Hallucination Rate | How many answers state non-existent rules? |
| 9 | Abstention Accuracy | Does it know when not to answer confidently? |
| 10 | Update Latency | P50 / P95 from publication to system availability |

### 9.2 The composite metric: LAA

**Legal Applicability Accuracy** — an answer is fully correct only if:

```text
Correct Answer ∧ Correct Legal Source ∧ Correct Article
∧ Correct Version ∧ Applicable at Relevant Time
```

Example:

```text
Answer Correct = 1 · Citation Correct = 1 · Version Wrong = 0  →  LAA = 0
```

Stricter than ordinary accuracy, and appropriate for a legal chatbot.

---

## 10. The Vietnamese market context

| Product | Description (per the cited sources) |
|---------|-------------------------------------|
| **AI Luật / LuatVietnam** | Multi-domain legal Q&A including tax, with legal-basis citations, emphasising frequent updates |
| **CLEX** | Chatbot, document lookup, cross-checking provisions showing signs of overlap or contradiction |
| **Ministry of Justice** | Has assessed AI solutions for looking up and reviewing legal normative documents; emphasises that **AI is only a support tool and results require human review** |
| **Tax authority / Ministry of Finance** | Developing an AI chatbot on eTax Mobile; customs has piloted a chatbot over a standardised professional document base |

### 10.1 The market gap

Current products concentrate on: **Lookup + Q&A + RAG + Citation**.

The large remaining gap: **Legal Change Intelligence** — a system that
proactively answers:

- "What did the new regulation change?"
- "Which businesses are affected?"
- "Which provisions of the old policy no longer apply?"
- "I am following a process based on the old law — how far does the new rule
  reach?"
- "Is the answer the chatbot gave last month still correct?"

This is the highest-value direction for enterprise customers.

---

## 11. Positioning the research topic

For a thesis / hackathon / research project: **do not centre it on the
chatbot**. Proposed title:

> **Version-Aware and Conflict-Aware RAG for Vietnamese Tax Law**

Six components: version-aware retrieval · temporal reasoning · legal knowledge
graph · legal change detection · conflict-aware ranking · citation validation.

**Research questions:**

1. Can ordinary RAG answer Vietnamese tax-law questions accurately while citing
   a version of the law that does not apply at the relevant time?
2. Does integrating temporal versioning and a legal dependency graph improve
   the accuracy of determining the applicable provision?

### 11.1 Conclusion

> **How can an AI system determine the correct tax provision applicable to a
> specific situation, at a specific point in time, amid documents that amend,
> replace and overlap one another and carry different legal force?**

The escalation of the problem:

```text
Question Answering → Legal Retrieval → Versioned Legal Retrieval
→ Temporal Legal Reasoning → Conflict Resolution → Legal Change Intelligence
```

Businesses do not only need to know *"what the law says"*. They need to know:

> **Which provision actually applies to me? From when? What did it just change?
> And does my current process need to change?**

---

## 12. Sources requiring verification

| # | Source cited in the original | Status |
|--:|------------------------------|--------|
| 1 | Law on Promulgation of Legal Normative Documents (Law 64/2025/QH15) — xaydungchinhsach.chinhphu.vn | ⬜ unverified |
| 2 | VLegal-Bench — vlegalbench.cmcai.vn | ⬜ unverified |
| 3 | LegalBench-RAG — arXiv:2408.10343 | ⬜ unverified |
| 4 | Temporal Misgrounding in Legal RAG (French Tax Law) — arXiv:2608.09393 | ⬜ unverified |
| 5 | AI Luật – LuatVietnam.vn — phapluat.gov.vn | ⬜ unverified |
| 6 | CLEX — clex.aicongvu.gov.vn | ⬜ unverified |
| 7 | AI-assisted review — phapluat.gov.vn | ⬜ unverified |
| 8 | eTax Mobile chatbot — mof.gov.vn | ⬜ unverified |

**Action required:** open each link, record the exact title, authors, year,
DOI/arXiv ID and access date into [`docs/source-register.md`](../source-register.md).
Do not cite any source still marked ⬜ in a formal report.

---

**Next:** [B — Product Direction Analysis](B-product-direction.md)
