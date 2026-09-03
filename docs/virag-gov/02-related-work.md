# 02 — Related Work and the Research Gap

> This document positions the project within the research landscape, identifies
> the gap, and states falsifiable research questions.

**Source note:** §2 and §5 summarise sources supplied by the project owner in
[`analystic.md`](_source/analystic.original.md). The external links have **not
been independently verified in this working session** (no network access).
Before use in a formal report or thesis, reopen each link and check title,
authors and year. The works in §3 are standard background in the RAG field.

---

## 1. Four research strands meeting at this problem

```text
       Vietnamese Legal NLP              RAG evaluation
                  \                          /
                   \                        /
                    ──── ViRAG-Gov ────
                   /                        \
                  /                          \
      Temporal / versioned IR          Legal reasoning & conflict
```

No single strand suffices. The contribution lies at the **intersection**.

---

## 2. Existing legal benchmarks

### 2.1 VLegal-Bench (Vietnam)

A Vietnamese legal benchmark built for the Vietnamese legal context, >10,000
questions, multiple cognitive levels: recognition, comprehension, reasoning,
interpretation, plus ethics/fairness dimensions.

**Why not use it alone:**

> VLegal-Bench evaluates **general legal capability**, not a tax-specialised
> benchmark, and does not measure the ability to **select the right version for
> a point in time**.

**Correct use:** as a **baseline capability control** (does the model know
Vietnamese law at all?), not the primary yardstick.

### 2.2 LegalBench-RAG

A benchmark for evaluating RAG in the legal domain. Its most important
conceptual contribution:

> It is not enough to answer correctly — the system must **retrieve the
> specific legal passage required**.

This is the direct origin of the principle:

```text
Correct Document  ≠  Correct Evidence
```

If a system returns the entire 100-page VAT Law, it technically "retrieved the
right document", but for a legal assistant that is a failure. Hence the need for
**Article Recall@K** and **Clause Recall@K**, not just Document Recall@K.

### 2.3 Temporal Misgrounding in Legal RAG (French tax law)

The work closest to this project's central problem. Core finding:

> RAG over a corpus containing **only current versions** can **confidently cite
> a real document that does not apply at the relevant point in time**.

The proposal: a **multi-version corpus** and a **separate evaluation of temporal
version selection**.

This is independent confirmation that the time axis deserves to be the primary
research axis, and is the direct basis for the **TVA** metric.

### 2.4 The gap common to all three

| Benchmark | VN tax domain | Article/Clause/Point | Time axis | Conflict | Change |
|-----------|:-------------:|:--------------------:|:---------:|:--------:|:------:|
| VLegal-Bench | ✗ (general law) | partial | ✗ | ✗ | ✗ |
| LegalBench-RAG | ✗ (English) | ✓ | ✗ | ✗ | ✗ |
| Temporal Misgrounding (FR) | ✗ (French tax) | partial | ✓ | ✗ | ✗ |
| **VietTaxBench (proposed)** | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 3. Technical foundations of RAG

### 3.1 Hybrid retrieval

- **BM25 / Okapi** — probabilistic ranking over term frequency. Strong on exact
  matches: instrument numbers (`48/2024/QH15`), figures (`10%`), pointers
  (`Điều 9`). These are precisely the **highest-precision queries** in the legal
  domain.
- **Dense retrieval** — a bi-encoder maps query and passage into a shared space.
  Strong on paraphrase, synonymy and colloquial questions.
- **Reciprocal Rank Fusion (RRF)** — merges ranked lists via
  `score(d) = Σᵢ wᵢ / (k + rankᵢ(d))`. Chosen over score addition because BM25
  scores and cosine similarities are **not on a comparable scale**; RRF needs
  only ranks, so it requires no per-corpus calibration.

**Why hybrid is mandatory here:** professional users type instrument numbers
(BM25 wins outright); operational users type colloquial questions (dense wins).
A system with only one half breaks on half the traffic.

### 3.2 Cross-encoder reranking

A bi-encoder encodes query and passage **independently**, so it cannot "see"
that *"rate is 10%"* answers *"what is the rate"* while *"rate is 0%"* does not.
A cross-encoder reads the **pair** and scores the match directly.

Trade-off: more accurate, an order of magnitude slower → run only on the post-
fusion top-k. Target model: `BAAI/bge-reranker-v2-m3` (multilingual, supports
Vietnamese).

### 3.3 Parent–child chunking

Token-window chunking destroys legal structure. The correct design:

- **Child = Clause (Khoản)** — the unit that is embedded and retrieved, because
  it is the unit a question matches and the unit a citation must point at.
- **Parent = Article (Điều)** — the unit handed to the LLM, because a Clause is
  frequently meaningless without the Article's opening sentence:

  > "The following cases are exempt from tax: 1. … 2. …"
  >
  > Clause 2 in isolation does not carry the information "exempt from tax".

Score the Clause, read the Article — that is what the `use_parent_expansion`
parameter means in the ablation table.

### 3.4 RAG evaluation: RAGAS

The reference metric suite, computed by LLM judge:

| Metric | Measures | Needs ground truth? |
|--------|----------|---------------------|
| Faithfulness | Is the answer supported by the context? | No |
| Answer Relevancy | Is the answer on point? | No |
| Context Precision | How much of the retrieved context is relevant? | Yes |
| Context Recall | Was all necessary context retrieved? | Yes |
| Answer Correctness | How close to the reference answer? | Yes |

**The limitation that must be stated:** RAGAS measures *groundedness*, **not
legal correctness**. An answer that faithfully cites a **repealed** document
scores Faithfulness = 1.0. That is exactly why RAGAS must be reported alongside
TVA and LAA.

### 3.5 Prompt injection in RAG

The domain-specific risk: **indirect prompt injection** — the malicious
instruction sits inside a *retrieved document*, not in the question. With a
publicly crawled corpus, this is a real attack surface.

Design countermeasure: strict separation of the data channel from the
instruction channel, never treating document content as commands, and testing
with a dedicated payload suite ([document 09 §9](09-evaluation-plan.md)).

---

## 4. The research gap

Synthesising §2–§3, the gap is:

> **No benchmark or RAG system for Vietnamese tax law evaluates simultaneously
> (a) retrieval of the correct Article–Clause–Point, (b) selection of the
> correct version for the date the obligation arose, and (c) correct
> adjudication when provisions conflict in time, hierarchy or scope.**

Three concrete deficits:

1. **No multi-version Vietnamese corpus.** Most systems index the latest
   consolidated version, destroying the ability to answer questions about the
   past.
2. **No unified metric.** Accuracy, Recall@K and Faithfulness all **score highly**
   on an answer that cites the wrong version.
3. **No auditable conflict-resolution mechanism.** Leaving it to the LLM is not
   defensible before a tax authority.

---

## 5. The Vietnamese product context

Per the summary in [document A](A-research-direction.md):

- **AI Luật / LuatVietnam** — multi-domain legal Q&A with legal-basis citations,
  emphasising frequent updates.
- **CLEX** — chatbot, document lookup, cross-checking provisions showing signs
  of overlap or contradiction.
- **Ministry of Justice** — has assessed AI solutions for looking up and
  reviewing legal normative documents, emphasising that **AI only supports;
  results require human review**.
- **Tax authority / Ministry of Finance** — developing an AI chatbot on eTax
  Mobile; customs has piloted a chatbot over a standardised professional
  document base.

**How to read this context:** the market already covers "lookup + Q&A + RAG +
citation". Entering that square means head-on competition without an advantage.
The empty square is **Legal Change Intelligence** — proactively answering about
*change* and *impact*, not merely about *content*.

At the same time, the Ministry of Justice's position ("AI only supports") is a
**mandatory design constraint**, not a suggestion: the system must be built so
a human can verify it, not so it replaces the human.

---

## 6. Research questions

### RQ1 — Measuring the failure

> **How accurately does standard RAG (hybrid + rerank, single-version corpus)
> answer Vietnamese tax-law questions, and in what percentage of cases does it
> cite a version of the document that did not apply at the date the obligation
> arose?**

- **Independent variable:** retrieval configuration (A→E,
  [document 09 §2](09-evaluation-plan.md)).
- **Dependent variables:** Answer Accuracy, TVA, LAA.
- **Hypothesis H1:** high Answer Accuracy (≥ 0.75) coexists with low TVA
  (≤ 0.50) on the `taxtime` subset — that is, the system *sounds right* while
  being *on the wrong version*.
- **Significance:** if H1 holds, it demonstrates that Answer Accuracy is a
  **misleading** metric in this domain. That is a publishable result even if the
  system itself is imperfect.

### RQ2 — Effectiveness of the intervention

> **Does integrating a multi-version corpus + a validity filter by event date +
> a ranking function weighted by legal hierarchy significantly improve TVA and
> LAA without degrading Recall@K?**

- **Hypothesis H2:** configuration `E` improves TVA by ≥ +25 percentage points
  over `D` with a Recall@10 drop of ≤ 3 percentage points.
- **Test:** paired bootstrap over the same question set, 95% confidence
  interval.

### RQ3 — Conflict adjudication

> **Does a rule engine based on legal application principles (temporal validity
> → legal force → amendment relation → general/special → later instrument)
> adjudicate conflicts more accurately than letting the LLM decide, and is it
> explainable?**

- **Hypothesis H3:** the rule engine achieves Conflict Resolution Accuracy
  ≥ +15 percentage points over LLM-only on the `taxconflict` subset, **and**
  100% of its decisions trace to a named rule.
- **Significance:** explainability matters as much as accuracy — a decision that
  cannot be justified cannot be used before a tax authority.

---

## 7. Expected contributions

| # | Contribution | Type | Artifact |
|---|--------------|------|----------|
| C1 | **VietTaxBench** — a 5-task benchmark, ≥200 questions, with gold Article/Clause/Point and gold version | Resource | `eval/viettaxbench.jsonl` |
| C2 | **LAA / TVA / VMR** — a unified metric suite for legal applicability | Method | `virag/eval/metrics.py` |
| C3 | **Version-aware & conflict-aware RAG** — validity filtering during retrieval + a rule engine for adjudication | System | `virag/retrieval/`, `virag/legal/` |
| C4 | **Evidence of temporal misgrounding in Vietnamese** — replicating the French tax-law finding | Experiment | `reports/ablation.json` |
| C5 | **A 20-case hallucination analysis** with root-cause classification | Experiment | `reports/hallucination-analysis.md` |
| C6 | **A ≥20-payload prompt-injection suite** for Vietnamese legal RAG | Resource | `eval/injection_payloads.jsonl` |

---

## 8. Positioning the topic

If this is a thesis or research project, the focus **should not** be the
chatbot. Proposed title:

> **Version-Aware and Conflict-Aware Retrieval-Augmented Generation for
> Vietnamese Tax Law**

Six components:

```text
1. Version-aware retrieval       4. Legal change detection
2. Temporal reasoning            5. Conflict-aware ranking
3. Legal knowledge graph         6. Citation validation
```

The escalation of the problem:

```text
Question Answering
     ↓
Legal Retrieval
     ↓
Versioned Legal Retrieval
     ↓
Temporal Legal Reasoning
     ↓
Conflict Resolution
     ↓
Legal Change Intelligence
```

---

## 9. To finish the research section

- [ ] Open and verify every link in [document A §12](A-research-direction.md);
      record title, authors, year, DOI/arXiv ID into
      [`docs/source-register.md`](../source-register.md).
- [ ] Read LegalBench-RAG closely to align the Evidence F1 definition.
- [ ] Read the temporal-misgrounding work (French tax law) to align the TVA
      definition — avoid reinventing an existing metric under a new name.
- [ ] Check VLegal-Bench access conditions and licensing before use.
- [ ] Review the current Law on Promulgation of Legal Normative Documents to
      cite the exact provisions underpinning the rule engine
      ([document 04 §6](04-system-architecture.md)).

---

**Previous:** [01 — Problem analysis](01-problem-analysis.md)
**Next:** [03 — VietTaxBench](03-benchmark-viettaxbench.md)
