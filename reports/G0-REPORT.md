# G0 Gate Report — Phase 0 Measurement

**Revision 2 — 2026-09-03**, after the tax-priority crawl.
Revision 1 is summarised in §7 rather than deleted, because the two runs
together are the evidence that the corpus, not the code, was the constraint.

**Executed by:** `tools/measure_corpus_versions.py`, `tools/trial_parse_pdfs.py`
**Artifacts:** `reports/g0-corpus-versions.json`, `reports/g0-parser-trial.json`

---

## 1. Verdict

**One blocker remains. The other is resolved, and every parser gate now passes.**

| Criterion | Threshold | Rev 1 | **Rev 2** | Verdict |
|-----------|----------:|------:|----------:|:-------:|
| Instruments with ≥2 legal states | ≥ 60 | 32 | **108** | ✅ PASS |
| — tax-related subset | ≥ 60 | 25 | **101** | ✅ PASS |
| — TaxTime probes (the real requirement) | ≥ 50 | 50 | **149** | ✅ PASS, 3.0× margin |
| Documents yielding ≥1 Article *(main, text-bearing)* | ≥ 85% | 92.3% | **88.9%** | ✅ PASS |
| Articles yielding ≥1 Clause | ≥ 70% | 77.3% | **83.7%** | ✅ PASS |
| Chunks citable at Clause level | ≥ 60% | 88.8% | **91.2%** | ✅ PASS |
| Extraction crashes | 0 | 0/50 | **0/120** | ✅ PASS |
| **Pages with no text layer** | — | 21.3% | **34.5%** | ❌ **B-1 open** |

- **B-2 — version-chain margin: RESOLVED.** The corpus now yields 149 TaxTime
  probes against a requirement of 50.
- **B-1 — OCR: still open, and larger than first measured.** 54.2% of sampled
  documents and 34.5% of pages have no extractable text.

---

## 2. What changed between revisions

Revision 1 found the corpus held **exactly** the 50 TaxTime probes the
benchmark requires — no margin. The cause was coverage: only 819 of 13,058
queued documents had been fetched (6.3%).

Rather than crawl all 12,239 remaining records, the queue's own priority class
`direct_tax_title` was used to select the slice whose titles already carry a
direct tax or invoice term — **757 documents**. This is scheduling, not
exclusion: the other classes remain in the queue for later passes, per the
corpus rule that a title keyword may only order the work.

| | Rev 1 | Rev 2 | Change |
|--|------:|------:|-------:|
| Distinct documents | 819 | **1,580** | +93% |
| `effective_date` usable | 78.8% | **82.6%** | +3.8 pt |
| Base instruments with ≥2 states | 32 | **108** | 3.4× |
| — tax-related | 25 | **101** | 4.0× |
| Links resolved by number | 59 | 184 | 3.1× |
| Links resolved by name | 134 | 239 | 1.8× |
| **TaxTime probes** | **50** | **149** | **3.0×** |

---

## 3. The tax-priority crawl

| Metric | Value |
|--------|------:|
| Documents planned | 757 |
| Documents fetched | **756** |
| Source pages fetched | 756 |
| Attachments fetched / attempted | **864 / 897** (96.3%) |
| PDFs on disk | 866 (1.92 GB) |
| Stray `.partial` files | **0** |

Failures were isolated per attachment and recorded: 23 `URLError`,
9 `ValueError` (content rejected by the PDF check), 1 `TimeoutError`.

### 3.1 D-12 validated under a real interruption

The run was killed mid-download during shard 0008. The result is the strongest
available evidence that the streaming rewrite works:

- The in-flight file remained `gov-decree-186261-3.pdf.**partial**` and was
  **never promoted to `.pdf`**. No truncated file masquerades as complete.
- Its size was exactly **2,097,152 bytes = 2 × 1 MiB**, confirming block-wise
  streaming stopped cleanly at a block boundary.
- The affected document appeared correctly in the missing list and was
  recovered by the resume pass.

Shard 0008 was resumed into `shard-0008-resume` — **the partial directory was
not overwritten**, per the corpus discipline — recovering 12/12 pages and 21/22
attachments.

---

## 4. Corpus measurement

| Metric | Value |
|--------|------:|
| Distinct documents | **1,580** |
| Roles: base / amending / consolidating | 1,122 / 307 / 151 |
| `effective_date` usable | **1,305 (82.6%)** |
| `effective_date` missing or unusable | 275 (17.4%) |

### 4.1 Version chains — R-D02 answered

| Metric | Value |
|--------|------:|
| Base instruments with ≥2 legal states | **108** |
| — tax-related | **101** |
| Total legal states in tax chains | 265 |
| — carrying a usable date | 249 |
| **Distinct temporal probes** | **149** |

Chain depth (states per chain): 2 × 80, 3 × 6, 4 × 6, 5 × 2, 6 × 3, 7 × 1,
9 × 2, 10 × 1.

**R-D02 is closed.** The central research contribution is testable: 149 probes
support the 50-question `TaxTime` family three times over, leaving room for
chains that later prove unusable.

### 4.2 Name-based matching remains decisive

| Resolution path | Rev 1 | Rev 2 |
|-----------------|------:|------:|
| By instrument number | 59 | 184 |
| **By subject name** | **134** | **239** |
| Share resolved by name | 69% | **56%** |

Even after the corpus doubled, the majority of amendment links carry no
instrument number. A number-only extractor (the state before D-14) would still
miss more than half the graph.

---

## 5. Parser trial

120 PDFs sampled at random (seed 42) from 2,225, run through
extract → clean → structure → chunk.

### 5.1 Gated population — main instruments with a text layer

| Metric | Measured | Gate | Verdict |
|--------|---------:|-----:|:-------:|
| Population | 45 documents | — | — |
| % docs with ≥1 Article | **88.9%** | ≥85 | ✅ |
| % Articles with ≥1 Clause | **83.7%** | ≥70 | ✅ |
| % chunks at Clause level | **91.2%** | ≥60 | ✅ |
| Extraction crashes | 0 / 120 | 0 | ✅ |

The sample tripled (13 → 45 main instruments) and all three gates hold. The
Clause figure improved from 77.3% to 83.7%.

### 5.2 Contrast populations (not gated)

| Population | n | Docs with ≥1 Article |
|------------|--:|---------------------:|
| All sampled PDFs | 120 | 35.0% |
| Text-bearing, incl. annexes | 55 | 76.4% |
| Annexes only | 10 | 20.0% |

Annexes score 20% because an annex of forms and tables legitimately contains no
`Điều`. Scoring them as parse failures is what produced the alarming "34%"
headline in Revision 1 (defect D-16, now fixed).

### 5.3 B-1 — OCR, now measured correctly and larger

| Metric | Rev 1 | **Rev 2** |
|--------|------:|----------:|
| Documents without a text layer | 52.0% | **54.2%** |
| **Pages needing OCR** | 21.3% | **34.5%** (1,771 / 5,134) |
| Pages OCR actually applied | 0 | **0** |
| OCR coverage of the burden | 0% | **0%** |

Revision 1 reported "% pages needing OCR: 0.0%" — it counted pages *actually
OCR'd* rather than pages *below the text threshold* (defect D-15, now fixed).
The corrected metric shows the burden grew: the tax-priority documents from the
government portal are more scan-heavy than the earlier sample.

Two software escape routes were tested and **both rejected** in Revision 1:

- **Source substitution** — Official Gazette PDFs always carry a text layer,
  but the two corpora overlap on 1 instrument out of 508 (0.2%).
- **A better extractor** — PyMuPDF recovered 148–243 characters from documents
  where `pypdf` found 2–96, i.e. a digital-signature annotation layer only.
  **0 of 26 documents rescued.**

**OCR is unavoidable.** `winget install UB-Mannheim.TesseractOCR --scope user`
returns *"No applicable installer found"*; a machine-scope install or a direct
binary install is required, plus the `vie` traineddata.

---

## 6. Remaining actions

| # | Action | Addresses | Blocking |
|--:|--------|-----------|:--------:|
| 1 | Install Tesseract + `vie`; re-run the trial with OCR | **B-1** | ✅ |
| 2 | Backfill `effective_date` for the 275 unusable records | R-D01 | ⚠️ |
| 3 | Promote reviewed records into Silver/Gold (D-01) | evidence gate | ✅ for G1 |
| 4 | Fix parent-window truncation (D-03) | citation integrity | ✅ for G1 |

Actions 3 and 4 belong to G1, not G0.

---

## 7. Revision 1 summary (superseded)

Revision 1, on the 819-document corpus, reported: 32 instruments with ≥2 states
(25 tax-related), exactly 50 TaxTime probes, and a 34% headline parse rate that
proved to be a sampling artefact. It raised four defects — D-13 (the literal
string `"Công báo"` in date fields), D-14 (69% of amendment links missed),
D-15 (misleading OCR metric) and D-16 (annexes scored as parse failures) — all
of which are now closed.

Its central finding stands: **the parser was never the problem; the corpus
was.** Revision 2 confirms it by fixing the corpus and watching every version
metric multiply while the parser numbers held.
