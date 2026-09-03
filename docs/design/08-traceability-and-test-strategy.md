# Truy vết yêu cầu và chiến lược kiểm thử

**Mục tiêu:** chứng minh mỗi năng lực được xây đúng, hoạt động an toàn và tạo giá
trị; không chỉ chứng minh code chạy hoặc mô hình trả lời trôi chảy.

## 1. Mô hình truy vết

```text
Goal -> FR/NFR/BR -> Use case -> Screen/API -> Data invariant
     -> AI task/tool -> Test suite/case -> Release evidence -> KPI
```

Mỗi pull request ảnh hưởng hành vi phải nêu các ID liên quan. CI kiểm liên kết ID
tồn tại; release manifest đóng băng version của corpus, rule, model, prompt,
retrieval config, API/schema và test report.

## 2. Phân loại rủi ro để quyết định độ sâu test

| Mức | Hậu quả điển hình | Ví dụ | Yêu cầu |
|---|---|---|---|
| R0 | không ảnh hưởng kết luận/dữ liệu | đổi icon, copy không nghiệp vụ | review + UI/unit test phù hợp |
| R1 | ảnh hưởng trải nghiệm nội bộ, phục hồi dễ | sort/filter, draft layout | unit + integration + E2E slice |
| R2 | ảnh hưởng research/case nhưng còn human gate | retrieval/rerank, fact extraction | gold eval + expert sample + rollback |
| R3 | ảnh hưởng luật áp dụng, số tiền, deadline, quyền hoặc external output | temporal resolver, calculator, approval, tenant filter | deterministic critical gate, independent review, canary, no known P0/P1 |

Accuracy trung bình không bù được lỗi R3. Một thay đổi R3 phải chỉ ra negative
tests, boundary tests, rollback và reviewer độc lập.

## 3. Danh mục test suite

| ID | Suite | Đối tượng | Gate chính |
|---|---|---|---|
| T-001 | Source acquisition | download, hash, metadata, duplicate, provenance | snapshot tái tạo được; nguồn lỗi bị quarantine |
| T-002 | Document parsing/OCR | text, reading order, bảng, trang/bbox | đạt ngưỡng theo loại tài liệu; exact text critical được đối chiếu |
| T-003 | Temporal applicability | valid/system time, transition, overlap | 100% critical boundary cases |
| T-004 | Retrieval | BM25/dense/filter/rerank/context | controlling authority Recall@20 gate; tenant/date filter tuyệt đối |
| T-005 | Normative graph | edge type, direction, provenance, valid range | critical edge exact; traversal không vượt allowlist/depth |
| T-006 | Fact/timeline extraction | span, normalization, contradiction | material fact recall; không auto-confirm |
| T-007 | Issue/missing-fact | issue taxonomy và câu hỏi bổ sung | material issue recall và question usefulness do SME chấm |
| T-008 | Citation/claim | existence, anchor, quote, entailment, coverage | 100% material citation mở được; unsupported claim bị chặn |
| T-009 | Rules/calculators | input, formula, rounding, deadline, trace | 100% golden/boundary/property tests |
| T-010 | Answer/deep research | plan, evidence, counter-source, abstention | legal rubric, risk-coverage, step/budget/stop gate |
| T-011 | Change impact | diff, dependency, stale, alert/remediation | known changes tác động đúng asset; rollback thành công |
| T-012 | Tenant/security | RLS, ACL, object/search/vector/graph, injection | zero cross-tenant access; critical abuse blocked |
| T-013 | Privacy/data lifecycle | consent, purpose, retention, deletion, export | lifecycle hoàn tất và audit được theo policy |
| T-014 | API/contracts | schema, status, auth, idempotency, pagination | consumer/provider contract và backward compatibility |
| T-015 | Database/migrations | constraints, concurrency, outbox, restore | migration forward/back plan; invariant giữ dưới race |
| T-016 | UI/accessibility | workflows, keyboard, screen reader, responsive | WCAG 2.2 AA cho phạm vi phát hành; không overlap/cắt text |
| T-017 | Performance/cost | p50/p95, load, token/GPU, index | SLO theo workflow và cost budget |
| T-018 | Resilience/DR | retry, resume, cancel, failover, backup/restore | không nhân đôi side effect; đạt RPO/RTO đã duyệt |
| T-019 | Audit/reproducibility | replay ID/version/source/tool/reviewer | tái tạo được quyết định từ evidence bundle |
| T-020 | User-value pilot | task success, cycle/review time, errors, adoption | lợi ích sau review, không tăng lỗi trọng yếu |

## 4. Các tầng kiểm thử

### 4.1 Static và unit

- type checking, lint, dependency/license/secret scan;
- parser, normalizer, resolver và rule thuần;
- property-based test cho khoảng thời gian, tiền tệ và idempotency;
- component/accessibility test cho trạng thái UI;
- prompt/tool schema validation; prompt là artifact có version.

### 4.2 Component và contract

- module với database/search/object/model giả lập có contract thật;
- OpenAPI consumer/provider, JSON Schema, event schema và migration compatibility;
- kiểm mọi error code, retryability và permission combination;
- model adapter test structured output, timeout, redaction và fallback.

### 4.3 Integration

- PostgreSQL RLS với role giống production;
- object upload grant/authorization download gateway + ACL, OpenSearch filter và graph projection;
- outbox -> worker -> projection -> alias swap;
- upload -> scan -> parse -> quarantine/review/release;
- research -> rule -> verifier -> review -> audit.

### 4.4 End-to-end

E2E chạy năm vertical workflows:

1. tra cứu theo ngày và mở nguồn;
2. so sánh phiên bản/chuyển tiếp;
3. intake tài liệu -> facts -> issues -> research;
4. calculator -> memo -> review -> approve/export;
5. luật mới -> stale -> impact task -> republish.

Mỗi workflow có happy path, missing evidence, permission denied, job failure,
abstention, retry/resume, stale state và accessibility path.

### 4.5 AI/domain evaluation

Gold set do ít nhất hai chuyên gia độc lập gắn nhãn, có adjudication và agreement
report. Chấm từng component trước end-to-end để biết lỗi thuộc ingestion,
retrieval, temporal, graph, rule, synthesis hay verifier.

Các nhãn tối thiểu:

- facts/event date/issues/material missing facts;
- controlling provisions, definitions, exceptions, transitions và contrary sources;
- expected conclusion + acceptable alternatives + abstain/escalate;
- citation spans và authority tier;
- calculation inputs/trace/result;
- severity nếu sai.

LLM-as-judge chỉ dùng sau khi hiệu chuẩn với chuyên gia và không là gate duy nhất
cho R3. Mọi benchmark ghi dataset version, split, contamination audit, model,
prompt, retrieval config, random seed nếu có, cost và latency.

### 4.6 Security và adversarial

- direct/indirect prompt injection trong PDF, HTML, table và metadata;
- source/citation poisoning, Unicode/confusable và spoofed document number;
- cross-tenant SQL/search/vector/graph/object/cache;
- SSRF, unsafe URL fetch, archive bomb, malware, parser exploit;
- tool argument injection, excessive agency và approval bypass;
- sensitive disclosure qua output, log, trace, analytics và error message;
- rate-limit/budget exhaustion, loop và oversized context;
- supply-chain/image/dependency/model artifact integrity.

## 5. Dữ liệu kiểm thử

| Tập | Dùng cho | Quy tắc |
|---|---|---|
| Public-law fixture | parser, temporal, retrieval, citation, graph | snapshot/hash cố định; có license/provenance |
| Synthetic matter | dev/CI/E2E/security | không dựa trên người thật; có canary tenant markers |
| Expert-authored gold | AI/domain evaluation | versioned, blind test split, access hạn chế |
| Anonymized pilot | user-value/error mining | legal basis/consent, de-identification review, purpose limit |
| Adversarial corpus | injection/poisoning/conflict | tách khỏi production corpus, label rõ malicious |

Không đưa matter production vào dev, demo hoặc model training. Log test không chứa
secret hoặc PII; fixture có owner và retention.

## 6. Môi trường và promotion

```text
local -> CI ephemeral -> integration -> security/eval -> staging
      -> shadow/replay -> canary tenant -> controlled production
```

- Mỗi môi trường có account/key/bucket/index riêng.
- Staging dùng dữ liệu synthetic hoặc được phê duyệt, không clone production thô.
- Corpus/search/graph/rule/model promotion theo immutable release ID.
- Canary không tự gửi external deliverable.
- Rollback đổi alias/release pointer; snapshot/audit cũ không bị ghi đè.

## 7. Release gates

### 7.1 Gate chung

- test bắt buộc theo risk class đều pass;
- không P0/P1 mở; P2 có owner, thời hạn và risk acceptance;
- migration, backup/restore và rollback evidence có sẵn;
- traceability và documentation được cập nhật;
- telemetry/alert/runbook hoạt động;
- privacy/security/legal sign-off theo phạm vi thay đổi.

### 7.2 Gate AI/pháp lý

- material citation validity 100% hoặc output bị chặn;
- temporal critical boundary 100%; calculator golden/boundary 100%;
- không cross-tenant retrieval/context;
- controlling authority recall và citation precision đạt ngưỡng release đã duyệt;
- risk-coverage chứng minh abstention giảm lỗi nghiêm trọng;
- mọi T2/T3 output external đi qua human gate;
- hai regression liên tiếp không có lỗi P0 về luật áp dụng/số thuế.

## 8. Severity và xử lý lỗi

| Mức | Ví dụ | Hành động |
|---|---|---|
| P0 | rò tenant, sai số thuế phát hành, dùng luật hết hiệu lực trong final | dừng/rollback/incident ngay; đánh giá recall output bị ảnh hưởng |
| P1 | citation giả được approve, bypass review, mất audit | khóa feature/release; sửa trước tiếp tục |
| P2 | retrieval thiếu nguồn nhưng hệ thống abstain, job retry thất bại | có owner/workaround; quyết định theo risk |
| P3 | lỗi trình bày không làm sai nghĩa hoặc cản accessibility | xếp backlog theo UX impact |

Lỗi dữ liệu/model không chỉ sửa output hiện tại. Phải truy dependency để tìm
corpus release, rule, case và deliverable có thể bị ảnh hưởng.

## 9. Báo cáo release evidence

Mỗi release lưu:

```text
release_id, commit_sha, build_artifacts
database_schema_version, api_schema_version
corpus_release_id, graph_projection_id
rule_release_id, model/provider_version, prompt_hash
test_suite_versions, dataset_versions, metric_report
security/privacy review, known_risks
approvers, deployed_at, rollback_target
```

Dashboard vận hành không thay evidence bundle. Evidence bundle có hash, ACL,
retention và có thể xuất cho audit.

## 10. Ma trận truy vết cần duy trì

Ma trận canonical nằm trong cùng repository và được CI sinh/kiểm từ front matter
hoặc bảng ID. Các cột bắt buộc:

| Goal | Requirement | Rule | Use case | Screen | API operation | Entity/invariant | AI task | Test suite | KPI |
|---|---|---|---|---|---|---|---|---|---|
| mục tiêu giá trị | FR/NFR | BR | UC | SCR | operationId | DB | AI | T | metric owner |

Không cho feature vào release nếu một FR không có use case/acceptance/test, một
AI task không có evaluation/fallback, hoặc một trường dữ liệu nhạy cảm không có
purpose/retention/permission.

## 11. Baseline truy vết đầy đủ

### 11.1 Giá trị, yêu cầu và bằng chứng kiểm thử

| Goal | UC | FR chính | NFR/BR trọng yếu | Test/evaluation | KPI/acceptance chính |
|---|---|---|---|---|---|
| `G-005`, `G-006` | `UC-001` | `FR-001`, `FR-002`, `FR-032` | `NFR-005..007`; `BR-001`, `BR-021`, `BR-022` | `T-012`, `T-014`, `T-016` | zero cross-tenant; switch/revoke không lộ cache, stream hoặc download |
| `G-001`, `G-005`, `G-006` | `UC-002` | `FR-009..013`, `FR-017`, `FR-035`, `FR-036` | `NFR-001`, `NFR-002`, `NFR-004`, `NFR-007`, `NFR-010`; `BR-002..004`, `BR-007..009`, `BR-018` | `T-003..005`, `T-008`, `T-010`, `T-019` | temporal exact; source mở đúng span; Recall@20/citation gate theo release profile |
| `G-001`, `G-004` | `UC-003` | `FR-011`, `FR-014` | `NFR-002`, `NFR-007`; `BR-002..004` | `T-003`, `T-005`, `T-008`, `T-016` | diff đúng hunk/transition; hai version mở được và không trộn thời điểm |
| `G-002`, `G-006` | `UC-004` | `FR-003`, `FR-037` | `NFR-005`, `NFR-010`, `NFR-016`; `BR-001`, `BR-021` | `T-012`, `T-014..016` | tạo/assign idempotent; owner, ACL và due state đúng |
| `G-002`, `G-005` | `UC-005` | `FR-005`, `FR-006`, `FR-038` | `NFR-005`, `NFR-008`, `NFR-012`; `BR-005`, `BR-019`, `BR-021` | `T-002`, `T-006`, `T-012..014` | byte/hash/provenance giữ nguyên; critical fact có span và chỉ `proposed` |
| `G-002`, `G-005`, `G-006` | `UC-006` | `FR-004`, `FR-007`, `FR-008` | `NFR-010`, `NFR-012`, `NFR-016`; `BR-002`, `BR-005`, `BR-006` | `T-006`, `T-007`, `T-014`, `T-016` | đủ material facts với ít vòng hỏi; confirm/change invalidation đúng |
| `G-002`, `G-005` | `UC-007` | `FR-012`, `FR-013`, `FR-015`, `FR-017`, `FR-039`, `FR-040` | `NFR-001`, `NFR-002`, `NFR-004`, `NFR-008`, `NFR-018`; `BR-007..009`, `BR-018`, `BR-019` | `T-003..008`, `T-010`, `T-012`, `T-017..019` | issue/adverse-source coverage; bounded completion, cost và expert edit time |
| `G-002`, `G-005` | `UC-008` | `FR-018`, `FR-019` | `NFR-003`, `NFR-010`; `BR-010`, `BR-011` | `T-003`, `T-009`, `T-015`, `T-019` | 100% golden/boundary; typed input, rule version và trace tái lập |
| `G-002`, `G-003` | `UC-009` | `FR-020`, `FR-021` | `NFR-001`, `NFR-010`; `BR-007`, `BR-013`, `BR-014` | `T-008`, `T-010`, `T-014`, `T-016`, `T-019` | draft có claim-evidence; version/diff đúng; unsupported material claim bị chặn |
| `G-003`, `G-005` | `UC-010` | `FR-022`, `FR-023` | `NFR-001`, `NFR-010`, `NFR-016`; `BR-012..014` | `T-008`, `T-010`, `T-012`, `T-014`, `T-019` | blocker không bypass; signer khóa exact digest; review time/error rate |
| `G-003`, `G-006` | `UC-011` | `FR-024`, `FR-025` | `NFR-005`, `NFR-010`, `NFR-012`; `BR-013`, `BR-020..022` | `T-008`, `T-012..014`, `T-016`, `T-019` | chỉ approved version; revoke stream/download trong SLA; export tái tạo được |
| `G-004`, `G-006` | `UC-012` | `FR-030`, `FR-031`, `FR-037` | `NFR-013`, `NFR-014`; `BR-017`, `BR-021` | `T-011`, `T-012`, `T-014`, `T-017`, `T-019`, `T-020` | impacted-asset coverage, noise/dedupe, action rate và time-to-action |
| `G-004`, `G-005` | `UC-013` | `FR-026..028` | `NFR-001`, `NFR-002`, `NFR-013`, `NFR-014`; `BR-015`, `BR-016`, `BR-019` | `T-001..005`, `T-011`, `T-012`, `T-015`, `T-018`, `T-019` | quarantine cách ly; publish/rollback atomic; critical diff miss bằng 0 |
| `G-004`, `G-005` | `UC-014` | `FR-029`, `FR-030` | `NFR-013`, `NFR-014`; `BR-006`, `BR-017` | `T-005`, `T-011`, `T-012`, `T-014`, `T-019` | mỗi impact có changed span/path; confirm/dismiss audit và stale đúng |
| `G-005` | `UC-015` | `FR-002`, `FR-032`, `FR-034` | `NFR-005`, `NFR-006`, `NFR-012`; `BR-001`, `BR-021`, `BR-022` | `T-012..015`, `T-018`, `T-019` | revoke có hiệu lực DB/search/stream/download; legal hold thắng retention |
| `G-005` | `UC-016` | `FR-033` | `NFR-010`, `NFR-012`; `BR-023` | `T-012..015`, `T-019` | audit bundle đủ/replay được, export đã redact và không chỉnh sửa |
| `G-002`, `G-006` | `UC-017` | `FR-015`, `FR-016` | `NFR-008`, `NFR-013`, `NFR-014`; `BR-019`, `BR-020` | `T-010`, `T-014`, `T-017..019` | pause/resume/cancel sống qua crash, không lặp artefact/side effect |
| `G-003`, `G-005` | `UC-018` | `FR-023`, `FR-035` | `NFR-001`, `NFR-002`; `BR-018`, `BR-024` | `T-003`, `T-004`, `T-007`, `T-008`, `T-010`, `T-019` | false premise/missing date/conflict dừng đúng; next action rõ, không kết luận giả |

### 11.2 Truy vết triển khai

| UC | Screens | OperationId critical path | Aggregate/invariant chính | AI |
|---|---|---|---|---|
| `UC-001` | `SCR-001`, `SCR-002` | `sessionContextGet`, `tenantContextSelect` | `iam.*`, session, `DATA-INV-001/002/016` | - |
| `UC-002` | `SCR-003`, `SCR-004`, `SCR-013` | `researchRunCreate`, `legalSearchExecute`, `sourceAnchorContentGet` | `provision_assertion`, `research_run`, claim/evidence; `DATA-INV-004/005/007` | `AI-001`, `AI-005..007`, `AI-010`, `AI-013` |
| `UC-003` | `SCR-013`, `SCR-014` | `legalProvisionVersionsList`, `legalProvisionVersionsCompare` | `provision_version`, assertion, `change_item` | `AI-005`, `AI-014` |
| `UC-004` | `SCR-005`, `SCR-006` | `matterCreate`, `matterMemberPut`, `matterUpdate` | `matter`, `matter_member`, `matter_event`; `DATA-INV-001/011/012` | - |
| `UC-005` | `SCR-007`, `SCR-008`, `SCR-013` | `documentUploadInitiate`, `documentUploadComplete`, `factExtractionCreate` | `document_version`, `source_anchor`, `fact_version`; `DATA-INV-003/006` | `AI-002`, `AI-008` |
| `UC-006` | `SCR-007`, `SCR-009` | `matterIntakeUpdate`, `matterFactConfirm`, `matterIssueCreate` | intake, fact/assumption/issue; `DATA-INV-006` | `AI-002..004` |
| `UC-007` | `SCR-004`, `SCR-009`, `SCR-010` | `researchRunCreate`, `researchRunEventsStream`, `researchRunClaimsList` | research step/query/hit/claim/evidence; `DATA-INV-005/007/009` | `AI-001..010`, `AI-013`, `AI-016` |
| `UC-008` | `SCR-011` | `calculationRunCreate`, `calculationRunGet` | `rule_version`, `calculation_run/step`; `DATA-INV-008` | `AI-011` |
| `UC-009` | `SCR-010`, `SCR-012` | `draftCreate`, `draftUpdate` | `draft`, `draft_version`, claim/evidence; `DATA-INV-009/015` | `AI-012`, `AI-013`, `AI-017` |
| `UC-010` | `SCR-015`, `SCR-016` | `draftReviewSubmit`, `reviewCommentCreate`, `reviewApprove` | `review`, comment/flag, `approval`, task; `DATA-INV-015` | `AI-010`, `AI-013` |
| `UC-011` | `SCR-012`, `SCR-022` | `draftExportCreate`, `draftShareCreate`, `draftShareRevoke` | export/share grant/comment/audit; `DATA-INV-015` | - |
| `UC-012` | `SCR-002`, `SCR-017`, `SCR-018` | `legalChangesList`, `taskAssign`, `taskAcknowledge`, `taskResolve` | change, subscription, impact, alert, task | `AI-014`, `AI-015`, `AI-018` |
| `UC-013` | `SCR-018`, `SCR-019` | `corpusIngestionRunCreate`, `corpusReleasePublish`, `corpusReleaseRollback` | snapshot, candidate, assertion, release/member; `DATA-INV-003/004/010/016` | `AI-008`, `AI-014` |
| `UC-014` | `SCR-017`, `SCR-018` | `changeImpactRunCreate`, `changeImpactConfirm`, `changeImpactDismiss` | `change_item`, dependency, impact, task | `AI-014`, `AI-015` |
| `UC-015` | `SCR-020` | `tenantMemberSessionsRevoke`, `matterMemberPut`, `tenantRetentionPolicyUpdate`, `legalHoldCreate` | membership/role/ACL/policy/hold; `DATA-INV-001/002/016` | - |
| `UC-016` | `SCR-021` | `auditEventsSearch`, `auditExportCreate`, `auditExportGet` | `audit_event`, retention action, export artifact | - |
| `UC-017` | `SCR-004`, `SCR-010` | `researchRunPause`, `researchRunResume`, `researchRunCancel` | `research_run`, checkpoint, job/outbox; `DATA-INV-011/012` | `AI-009` |
| `UC-018` | `SCR-003`, `SCR-004`, `SCR-010`, `SCR-015` | `researchRunInputProvide`, `researchRunEscalate`, `researchRunGet` | answer snapshot, blocker/task/review; `DATA-INV-005/007` | `AI-001`, `AI-003`, `AI-010`, `AI-013` |

Danh mục endpoint đầy đủ nằm tại mục 20 của tài liệu backend; bảng trên giữ critical
path để đọc được. CI phải kiểm mọi ID tham chiếu tồn tại và mọi operationId trong
use case là một operationId canonical, không chỉ so chuỗi gần giống.

## 12. Vertical slices triển khai đầu tiên

| Năng lực | Use case | Screen | Backend canonical | Data | AI | Tests |
|---|---|---|---|---|---|---|
| Tạo matter, upload và intake | `UC-004..006` | `SCR-005..009` | `matterCreate`, `documentUploadInitiate`, `documentUploadComplete`, `matterIntakeUpdate`, `matterFactConfirm` | matter, document, fact, issue | `AI-002..004`, `AI-008` | `T-002`, `T-006`, `T-007`, `T-012`, `T-014` |
| Tra cứu theo thời điểm | `UC-002`, `UC-007`, `UC-018` | `SCR-003`, `SCR-004`, `SCR-013` | `researchRunCreate`, `legalSearchExecute`, `sourceAnchorContentGet` | assertion/version, research, claim/evidence | `AI-001`, `AI-005..010`, `AI-013`, `AI-016` | `T-003..005`, `T-008`, `T-010`, `T-019` |
| Tính VAT | `UC-008` | `SCR-011` | `calculationRunCreate`, `calculationRunGet` | rule version, calculation run/trace | `AI-011` | `T-003`, `T-009`, `T-019` |
| Soạn, duyệt và phát hành memo | `UC-009..011` | `SCR-010`, `SCR-012`, `SCR-015`, `SCR-016`, `SCR-022` | `draftCreate`, `draftReviewSubmit`, `reviewApprove`, `draftExportCreate`, `draftShareCreate` | draft/version, review/approval, export/share | `AI-010`, `AI-012`, `AI-013`, `AI-017` | `T-008`, `T-010`, `T-012`, `T-014`, `T-016`, `T-019` |
| Tiếp nhận luật mới và xử lý tác động | `UC-012..014` | `SCR-017..019` | `corpusIngestionRunCreate`, `corpusReleasePublish`, `changeImpactRunCreate`, `changeImpactConfirm` | snapshot, assertion/release, change/impact/task | `AI-008`, `AI-014`, `AI-015`, `AI-018` | `T-001..005`, `T-011`, `T-012`, `T-015`, `T-018`, `T-019` |
