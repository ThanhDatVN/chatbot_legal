# 11 — Compliance, Ethics and Limits

> A system that answers questions about tax obligations stands between the
> taxpayer and the state. Errors here carry real financial and legal
> consequences. This document defines the boundaries the system must not cross.

---

## 1. Founding principles

### 1.1 This is not legal advice

The system's output is **referenced reference information**, not legal advice,
and it does not substitute for the opinion of a licensed practitioner.

**The accompanying technical constraints:**

- The disclaimer is inserted by the **output guardrail**, not dependent on the
  LLM remembering it.
- There is no way for a user to switch the disclaimer off — including by asking
  directly (that is payload group 6 in the injection suite).
- Output language uses **referential** constructions ("under Article X, cases
  where … fall within …") rather than **imperative** ones ("you must pay…").

### 1.2 The human decides

Consistent with the position stated by the Ministry of Justice when assessing AI
solutions for looking up and reviewing legal normative documents: **AI acts only
in a supporting role; results require human review.**

**Expert review is mandatory** for conclusions materially affecting:

- a taxpayer's obligations or rights;
- the choice of filing treatment;
- dispute strategy;
- procedural or filing/payment deadlines.

### 1.3 The system is designed to be checked, not to be trusted

Every mechanism in this dossier — citation to the Clause, named conflict rules,
the confidence light, the retrieval trace — exists so that **the user can verify
it**. That is a deliberate design choice, not decoration.

---

## 2. User scope

### 2.1 Target users (v1)

Accountants, tax specialists, advisers — **people with the expertise and the
duty to verify**.

### 2.2 Why the general public is excluded in v1

> An assistant that is 5% wrong, used by a **professional** who knows how to
> verify, is a useful tool. An assistant that is 5% wrong, used by the **general
> public** who cannot verify, is a dangerous tool.

This is an ethical decision, not a technical one. Widening the user scope
demands a different accuracy level and different safeguards.

---

## 3. Sources and attribution

### 3.1 Official sources only

| Source tier | Used in v1 |
|-------------|:----------:|
| Official Gazette, government portal | ✅ |
| Ministry portals | ✅ |
| Commercial legal databases | ⛔ |
| News media | ⛔ |
| User-generated content | ⛔ |

### 3.2 Attribution and traceability

Each document is stored with its source URL, SHA-256, fetch timestamp and
attribution string (e.g. *"Source: Government Electronic Information Portal"*).

Every citation shown to a user traces back to a checksummed copy in the Bronze
layer.

### 3.3 Respecting robots and technical limits

The crawler records the `robots.txt` status for every fetch in the manifest.
Collection is limited to publicly published documents for the purpose of legal
research and lookup.

### 3.4 Third-party benchmark licensing

Before using VLegal-Bench or any external benchmark, **licence conditions must
be checked** (risk R-L04). Do not place restrictively licensed data in a public
repository.

---

## 4. Privacy and data isolation

| Principle | Enforcement |
|-----------|-------------|
| No PII in logs | Redact PII before logging and before caching |
| Per-client data isolation | Case facts never enter a shared conversational memory |
| No user data used for training | No training loop receives user data |
| No cross-contamination via cache | Cache keys contain no identifying data |
| Feedback separated from sensitive content | Only PII-redacted questions are stored |

**Design note:** the semantic cache is a potential leakage point — a question
containing specific business information could be served back to another user if
the cache key is too loose. Therefore the cache stores only the
**(normalised question, as_of, answer)** triple, and the question is
PII-redacted before it becomes a key.

---

## 5. Known limits (published in the Model Card)

| # | Limit | Consequence for the user |
|--:|-------|--------------------------|
| 1 | **22.9% of documents lack an effective date** | For these, the system cannot confirm validity at the relevant date — a 🟡 light is shown |
| 2 | Corpus limited to 6 of 131 audited shards | Coverage is not complete over all 13,058 documents |
| 3 | Central instruments only | No provincial-level documents |
| 4 | A 10-year window (2016–2026) | Questions about periods before 2016 cannot be answered |
| 5 | v1 scope: VAT and invoices | Coverage of other taxes is thinner |
| 6 | **Does not compute the tax owed** | It cites formulas and conditions only |
| 7 | Implicit repeal is usually left open | The rule engine returns "expert review needed" rather than guessing |
| 8 | Sector/location incentives not fully modelled | A special rule may be missed |
| 9 | The parser may degrade to Article or Passage level | Less precise citation on difficult PDFs |
| 10 | Not a real-time system | Update latency target P50 ≤ 24 h |

**Principle:** limits must be **displayed**, never **hidden**. A system that
states what it does not know is safer than one that conceals it.

---

## 6. Communicating uncertainty

Do not display a percentage confidence — LLMs are poorly calibrated, and a
figure like `87.5%` communicates a precision that does not exist.

| Light | Meaning to the user |
|-------|---------------------|
| 🟢 | Clear legal basis; the relevant date is established |
| 🟡 | May need more information, or an unverified-date document is involved |
| 🔴 | Multiple readings, or an unresolved conflict — expert review required |

Always accompanied by a **stated reason**, for example:

> "The result depends on the date the transaction arose."
> "The highest basis found is an Official Letter, which carries indicative
> value only."

The derivation of each level is specified in
[ADR-019](05-design-decisions.md).

---

## 7. Accountability

### 7.1 Every answer is reconstructible

Because of the two time axes (valid time + transaction time) and immutable
versioning, an answer issued months ago can be reconstructed: the same question,
the same `as_of` and the same corpus hash yield the same evidence.

This is the precondition for answering *"why did the system say that at the
time?"*.

### 7.2 Every legal decision carries a rule name

The rule engine never returns "the model thought so". It returns the rule's
name: *temporal validity*, *lex superior*, *lex specialis*, … — or it admits it
could not adjudicate.

### 7.3 Audit log

Each answer records: the (PII-redacted) question, `as_of` and its provenance,
the configuration, the retrieved chunks with their component scores, detected
conflicts, guardrails triggered, and the backends used.

---

## 8. Safety boundaries

### 8.1 What the system refuses

| Request | Behaviour |
|---------|-----------|
| Advice on unlawful tax evasion or avoidance | Refuse, explain the boundary |
| Role-play as a lawyer asserting certainty | Refuse |
| Drop citations or the disclaimer | Refuse, keep them |
| Confirm a non-existent provision | Correct it |
| Questions outside tax law | Decline politely, point to an appropriate source |

An important boundary: **lawful tax-optimisation guidance** (stating incentives,
eligibility conditions, with citations) is **in scope**; **instructions for
unlawful conduct** are out of scope. The system states the rules and conditions;
it does not design avoidance schemes.

### 8.2 The system asks rather than guesses

When a missing fact would change the answer — especially the **date the
obligation arose** — the system asks. At most one round, always with a quick
escape option.

---

## 9. Bias and coverage gaps

| Bias source | Manifestation | Mitigation |
|-------------|---------------|------------|
| **Volume bias** | 307 Circulars swamp 9 Laws → similarity favours the implementation tier | The authority component of the composite score |
| **Selection bias** | Title-keyword filtering omits relevant documents | The rule: keywords **only schedule**, never exclude |
| **Recency bias** | Newer documents use language closer to modern questions | Filter and validity score keyed to `as_of` |
| **Data-quality bias** | Documents with good PDFs index better | Measure and publish OCR / parse rates |
| **Tax-domain bias** | v1 concentrates on VAT | Publish the eval distribution by tax domain |

---

## 10. A responsible feedback loop

Four feedback types, of which the two warnings carry the highest diagnostic
value:

| Button | Maps to metric |
|--------|----------------|
| 👍 Helpful | — |
| 👎 Inaccurate | Answer Accuracy |
| ⚠️ **Wrong point in time** | **TVA** |
| ⚠️ **Wrong legal basis** | **Citation Precision** |

Each warning becomes **a candidate eval item with its error label attached**. A
reviewer confirms it before it enters the eval set — automatic inclusion is
unsafe, because users can also be wrong.

---

## 11. Pre-launch checklist

- [ ] The disclaimer appears on **every** answer and cannot be disabled
- [ ] The confidence light and its stated reason are displayed
- [ ] The Model Card publishes all 10 limits from §5
- [ ] A "System limits" page is reachable from the main interface
- [ ] Logs contain no PII
- [ ] The injection suite has been run against the deployment, ASR ≤ 5%
- [ ] Rate limiting is enabled
- [ ] Source attribution is displayed alongside every citation
- [ ] No source still marked "unverified" is cited in published material
- [ ] No numeric table is missing its backend column

---

## 12. The short statement used in the product

> **Disclaimer.** Content generated by this system is reference information
> quoted from legal normative documents obtained from official sources. It is
> not legal advice and does not replace the opinion of a licensed practitioner.
> The applicable provision depends on the date the tax obligation arose and on
> the specific circumstances of each case. Please consult the original documents
> and a qualified professional before making decisions.

---

**Previous:** [10 — Setup & operations guide](10-operations-guide.md)
**Back to the index:** [00 — Index](00-index.md)
