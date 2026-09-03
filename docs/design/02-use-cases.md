# Use case: Tax Legal Workspace

**Phiên bản:** 0.1  
**Phạm vi:** B2B VAT/hóa đơn, professional MVP  
**Nguồn yêu cầu:** [01-product-requirements.md](01-product-requirements.md)  
**Màn hình:** [03-interface-design.md](03-interface-design.md)

## 1. Quy ước

- `P0/P1`: mức ưu tiên trong MVP theo PRD.
- `FR-*`, `NFR-*`, `BR-*`: yêu cầu và quy tắc nghiệp vụ.
- `SCR-*`: màn hình; `operationId`: hợp đồng backend dự kiến.
- `AI-*`: tác vụ trong kiến trúc xử lý AI, không đồng nghĩa mọi tác vụ dùng LLM.
- Mọi command API cần `Idempotency-Key`; mọi response lỗi dùng mã lỗi domain,
  `correlation_id` và thông điệp không lộ dữ liệu nhạy cảm.
- Không use case nào cho phép hiển thị chain-of-thought. UI chỉ hiển thị dữ kiện,
  nguồn, rule, bước công việc, kiểm tra và lý do nghiệp vụ có thể kiểm chứng.

## 2. Mô hình actor

| Actor | Mã | Trách nhiệm/quyền |
|---|---|---|
| Chuyên gia tư vấn | ACT-001 | tạo và xử lý case, xác nhận fact, nghiên cứu, tính, soạn draft |
| Reviewer | ACT-002 | kiểm tra độc lập, return/approve đúng scope và mức rủi ro |
| Platform knowledge curator | ACT-003 | control plane: thu thập, QA, liên kết, diff và đề xuất corpus công cộng; không kế thừa từ tenant role |
| Platform knowledge approver | ACT-004 | control plane: duyệt/rollback corpus/rule công cộng, JIT/step-up và chịu content gate |
| Tenant admin | ACT-005 | user, role, matter access, policy, retention và integration |
| Auditor/compliance | ACT-006 | tra cứu/xuất audit read-only theo grant |
| Client viewer | ACT-007 | xem/comment bản đã duyệt được chia sẻ, không thấy nội bộ |
| Scheduler/worker | ACT-008 | chạy job nền theo state machine và service identity tối thiểu |
| Identity provider | ACT-009 | xác thực, MFA, SSO và session claims |
| Nguồn luật chính thức | ACT-010 | upstream bên ngoài; dữ liệu luôn vào quarantine trước production |

### 2.1 Ranh giới quyền

Ở tenant data plane, quyền hiệu lực là giao của `tenant role`, `matter membership`,
`ethical wall`, `data purpose`, `sensitivity` và trạng thái artefact. `tenant_admin`
không mặc định được đọc matter bị ethical wall. Platform control plane dùng principal,
role, session và audit riêng; tenant role không cấp quyền curate/publish corpus công
cộng. Service identity không kế thừa quyền người dùng rộng hơn job đã cấp.

## 3. Danh mục use case

| ID | Tên | Ưu tiên | Actor chính | FR chính |
|---|---|---|---|---|
| UC-001 | Đăng nhập và chuyển tenant | P0 | ACT-001..006 | FR-001, FR-002 |
| UC-002 | Hỏi luật theo thời điểm | P0 | ACT-001 | FR-009, FR-010, FR-011, FR-012, FR-013, FR-035, FR-036 |
| UC-003 | So sánh phiên bản quy định | P0 | ACT-001, ACT-003 | FR-011, FR-014 |
| UC-004 | Tạo và phân công case | P0 | ACT-001 | FR-003 |
| UC-005 | Tải tài liệu và trích facts | P0 | ACT-001 | FR-005, FR-006 |
| UC-006 | Smart intake và xác nhận facts | P0 | ACT-001 | FR-004, FR-007, FR-008 |
| UC-007 | Nghiên cứu một case | P0 | ACT-001 | FR-012, FR-013, FR-015, FR-017, FR-039, FR-040 |
| UC-008 | Tính và so sánh VAT | P0 | ACT-001 | FR-018, FR-019 |
| UC-009 | Tạo và chỉnh sửa memo | P0 | ACT-001 | FR-020, FR-021 |
| UC-010 | Gửi duyệt, return và approve | P0 | ACT-001, ACT-002 | FR-022, FR-023 |
| UC-011 | Xuất/chia sẻ bản đã duyệt | P0/P1 | ACT-001, ACT-007 | FR-024, FR-025 |
| UC-012 | Theo dõi thay đổi có liên quan | P1 | ACT-001, ACT-008 | FR-030, FR-031 |
| UC-013 | Tiếp nhận và phát hành corpus | P0 | ACT-003, ACT-004 | FR-026, FR-027, FR-028 |
| UC-014 | Xác nhận tác động của thay đổi | P1 | ACT-003, ACT-004 | FR-029, FR-030 |
| UC-015 | Quản trị người dùng và quyền | P0 | ACT-005 | FR-002, FR-032, FR-034 |
| UC-016 | Tra cứu và xuất audit | P0 | ACT-006 | FR-033 |
| UC-017 | Điều khiển research run dài | P0 | ACT-001, ACT-008 | FR-015, FR-016 |
| UC-018 | Abstain và chuyển chuyên gia | P0 | ACT-001, ACT-002 | FR-023, FR-035 |

## 4. Use case chi tiết

### UC-001 Đăng nhập và chuyển tenant

**Mục tiêu:** vào đúng không gian tổ chức mà không mang dữ liệu/cache từ tenant khác.  
**Actor:** ACT-001..ACT-006; hỗ trợ ACT-009.  
**Ánh xạ:** `FR-001`, `FR-002`, `FR-032`; `SCR-001`, `SCR-002`;
`sessionContextGet`, `tenantContextSelect`; không có AI.

**Tiền điều kiện:** user active; tenant membership active; IdP và policy MFA sẵn.  
**Kích hoạt:** user truy cập app hoặc chọn tenant khác.

**Luồng chính:** 1. Redirect tới IdP. 2. IdP xác thực/MFA. 3. Backend kiểm tra
membership, policy, device/session. 4. Nếu nhiều tenant, user chọn một tenant.
5. Hệ thống tạo session có tenant context và quyền tối thiểu. 6. Xóa client cache
không thuộc context mới. 7. Mở `SCR-002` với dữ liệu đã filter.

**Thay thế/lỗi:** membership hết hiệu lực thì từ chối; MFA thiếu thì yêu cầu hoàn
tất; switch thất bại giữ context cũ nhưng không hiển thị dữ liệu tenant đích;
session hết hạn đưa về đăng nhập và giữ URL không chứa dữ liệu nhạy cảm.

**Quyền:** không thể tự chọn tenant chỉ bằng route/header; server xác nhận claim.  
**Dữ liệu:** user, tenant membership, session, role/policy, device metadata tối thiểu.  
**Audit:** login success/failure reason class, tenant switch, logout/revoke; không log token.  
**Hậu điều kiện:** mọi query sau có `tenant_id` được server gắn và policy context mới.  
**Nghiệm thu:** test đổi A->B chứng minh matter/search/cache/download grant của A không
còn truy cập; back button không khôi phục nội dung A.

### UC-002 Hỏi luật theo thời điểm

**Mục tiêu:** nhận câu trả lời VAT/hóa đơn có phạm vi, phiên bản và căn cứ đúng ngày.  
**Actor:** ACT-001; ACT-002 có thể mở kết quả để review.  
**Ánh xạ:** `FR-009`, `FR-010`, `FR-011`, `FR-012`, `FR-013`, `FR-017`,
`FR-035`, `FR-036`; `SCR-003`, `SCR-004`,
`SCR-013`; `researchRunCreate`, `researchRunGet`, `researchRunEventsStream`,
`legalSearchExecute`, `sourceAnchorContentGet`; `AI-001`, `AI-005`..`AI-007`,
`AI-010`, `AI-013`.

**Tiền điều kiện:** tenant có corpus release active; user được dùng research.  
**Kích hoạt:** user nhập câu hỏi, domain, event date/tax period và bấm Tra cứu.

**Luồng chính:** 1. Validate input/risk. 2. Chuẩn hóa timeline và khóa event date.
3. Temporal resolver tạo filter. 4. Hybrid retrieval và graph expansion lấy nguồn
hợp lệ. 5. Tạo atomic claims theo answer contract. 6. Kiểm tra citation, thời gian,
authority, xung đột. 7. Trả kết luận/điều kiện/nguồn và trạng thái review. 8. Click
citation mở exact span trong `SCR-013`. 9. Lưu run và audit bundle. 10. User có
thể phản hồi ở cấp claim, citation hoặc toàn workflow.

**Thay thế/lỗi:** thiếu ngày trọng yếu chuyển UC-018 để hỏi lại; không đủ nguồn
thì `cannot_conclude`; conflict hiện hai phía và khóa publish; source anchor lỗi
thì claim không được gắn verified; timeout chuyển background theo UC-017.

**Quyền:** source license và matter scope được filter trước retrieval.  
**Dữ liệu:** question, dates, filters, claims, evidence, corpus/model releases, checks.  
**Audit:** query đã redact, filter, source IDs, model/tool versions, verifier outcome.  
**Hậu điều kiện:** research run immutable theo version; feedback tạo event riêng.  
**Nghiệm thu:** với case ranh giới hiệu lực, hệ thống lấy đúng provision version;
100% citation hiển thị mở đúng snapshot/span hoặc output bị chặn.

### UC-003 So sánh phiên bản quy định

**Mục tiêu:** hiểu thay đổi câu chữ, ý nghĩa, khoảng hiệu lực và điều khoản chuyển tiếp.  
**Actor:** ACT-001, ACT-003.  
**Ánh xạ:** `FR-011`, `FR-014`, `FR-029`; `SCR-014`, `SCR-013`;
`legalProvisionVersionsList`, `legalProvisionVersionsCompare`,
`legalProvisionVersionGet`; `AI-005`, `AI-014`.

**Tiền điều kiện:** hai version có snapshot/anchors; user có quyền xem nguồn.  
**Kích hoạt:** user chọn quy định và hai mốc/phiên bản.

**Luồng chính:** 1. Resolve version theo lựa chọn. 2. Hiển thị metadata và hiệu lực.
3. Tạo structural diff ở cấp điều/khoản/điểm. 4. Đề xuất semantic label và tóm
tắt thay đổi, mỗi ý trỏ exact changed spans. 5. Hiện transition và legal edges.
6. User mở hai nguồn song song hoặc đưa thay đổi vào research/case.

**Thay thế/lỗi:** version không cùng lineage thì cảnh báo và yêu cầu xác nhận;
OCR/structure confidence thấp thì chỉ hiển thị raw diff và cần curator; thiếu
snapshot thì không tạo semantic conclusion.

**Quyền:** cùng source/tenant/license policy như legal search.  
**Dữ liệu:** provision/version IDs, intervals, diff hunks, labels, links, reviewer status.  
**Audit:** input versions, algorithm/model release, manual corrections.  
**Hậu điều kiện:** comparison versioned; không tự sửa corpus.  
**Nghiệm thu:** mọi summary sentence mở được cặp before/after spans; test đánh số
lại không bị tự gắn nhãn thay đổi nghĩa nếu chưa đủ bằng chứng.

### UC-004 Tạo và phân công case

**Mục tiêu:** tạo không gian xử lý một yêu cầu khách hàng với scope và quyền rõ.  
**Actor:** ACT-001.  
**Ánh xạ:** `FR-003`, `FR-002`, `FR-037`; `SCR-005`, `SCR-006`;
`matterCreate`, `matterUpdate`; không có AI.

**Tiền điều kiện:** user được tạo case; client/profile thuộc tenant hoặc được tạo mới.  
**Kích hoạt:** user chọn Tạo case.

**Luồng chính:** 1. Nhập tên, client, VAT/hóa đơn, event/tax period, owner,
sensitivity và purpose. 2. Chọn thành viên/ethical wall. 3. Validate ngày và dữ
liệu tối thiểu. 4. Tạo case ở trạng thái `intake`. 5. Ghi audit. 6. Mở `SCR-006`
với checklist bước tiếp theo.

**Thay thế/lỗi:** trùng case chỉ cảnh báo; event date chưa biết được lưu `unknown`
nhưng chặn research kết luận; member không đủ clearance thì không được thêm.

**Quyền:** creator cần `matter:create`; membership/ethical wall áp dụng ngay.  
**Dữ liệu:** matter, client reference, scope, dates, members, sensitivity, purpose.  
**Audit:** create/update/member change với before/after không chứa secret.  
**Hậu điều kiện:** case có stable ID và tenant-scoped object prefix.  
**Nghiệm thu:** user ngoài membership không list/search/open case; required fields
và absolute dates được lưu đúng timezone/period semantics.

### UC-005 Tải tài liệu và trích facts

**Mục tiêu:** biến tài liệu case thành fact/timeline đề xuất có provenance.  
**Actor:** ACT-001; hỗ trợ ACT-008.  
**Ánh xạ:** `FR-005`, `FR-006`, `FR-038`; `SCR-008`, `SCR-007`, `SCR-013`;
`documentUploadInitiate`, `documentUploadComplete`, `documentUploadGet`,
`factExtractionCreate`, `sourceAnchorContentGet`; `AI-002`, `AI-008`.

**Tiền điều kiện:** case active; user có quyền upload; quota còn đủ.  
**Kích hoạt:** kéo/thả hoặc chọn PDF/HTML/image được phép.

**Luồng chính:** 1. Client kiểm tra kích thước/type sơ bộ. 2. Backend kiểm MIME,
signature, malware và quota. 3. Lưu original/hash/version. 4. Parser/OCR chạy trong
sandbox. 5. Extract fact/event có page/bbox/text span và confidence. 6. Hiển thị
proposed items để user review. 7. User mở anchor tại tài liệu.

**Thay thế/lỗi:** file nguy hiểm bị quarantine; encrypted/không đọc được yêu cầu
password hoặc bản khác nhưng không lưu password; OCR thấp đưa manual review;
job lỗi có retry và giữ original; duplicate hash hỏi dùng lại/version mới.

**Quyền:** object path tenant/matter; signed URL chỉ cho upload multipart ngắn hạn;
download private qua authorization gateway; file content không vào log.  
**Dữ liệu:** document/version, original, parse artefact, anchor, proposed fact/event.  
**Audit:** uploader, hash, scanner/parser versions, status, retry và view/download.  
**Hậu điều kiện:** proposed facts tồn tại nhưng chưa ảnh hưởng kết luận cho tới xác nhận.  
**Nghiệm thu:** mỗi extracted fact mở đúng page/bbox; embedded prompt không thay
tool policy; tenant khác không suy ra file qua hash/search.

### UC-006 Smart intake và xác nhận facts

**Mục tiêu:** thu đủ dữ kiện có khả năng đổi hướng pháp lý mà không hỏi lan man.  
**Actor:** ACT-001.  
**Ánh xạ:** `FR-004`, `FR-007`, `FR-008`; `SCR-007`, `SCR-009`;
`factExtractionCreate`, `matterFactsList`, `matterFactCreate`, `matterFactUpdate`,
`matterFactConfirm`, `matterFactDispute`, `matterIssuesList`; `AI-002`..`AI-004`.

**Tiền điều kiện:** case tồn tại; user có edit permission.  
**Kích hoạt:** mở intake/facts hoặc hoàn tất extraction.

**Luồng chính:** 1. Hệ thống hiển thị facts theo confirmed/proposed/missing/conflict.
2. Giải thích ngắn vì sao câu hỏi thiếu có thể ảnh hưởng kết quả. 3. User trả lời,
đính evidence hoặc đánh dấu chưa biết. 4. User confirm/edit/reject từng fact.
5. Hệ thống đề xuất timeline/issues. 6. User xác nhận scope và event date. 7. Chỉ
dependency liên quan được đánh stale/chạy lại.

**Thay thế/lỗi:** hai nguồn mâu thuẫn tạo conflict thay vì chọn tự động; fact không
material có thể bỏ qua; edit confirmed fact yêu cầu reason; autosave lỗi giữ local
draft mã hóa trong memory của tab và retry, không dùng persistent localStorage.

**Quyền:** edit fact khác view/comment; client viewer không xác nhận internal fact.  
**Dữ liệu:** fact values/types/dates/status/materiality/evidence, assumptions, issues.  
**Audit:** origin, status transition, before/after, actor, reason, dependency invalidation.  
**Hậu điều kiện:** scope đủ để research hoặc chuyển UC-018 với missing list.  
**Nghiệm thu:** inferred fact không tự thành confirmed; thay event date làm stale
đúng các run/draft phụ thuộc và không làm mất lịch sử.

### UC-007 Nghiên cứu một case

**Mục tiêu:** tạo phân tích nhiều bước có nguồn cho issue đã xác định.  
**Actor:** ACT-001; hỗ trợ ACT-008; ACT-002 đọc để review.  
**Ánh xạ:** `FR-012`, `FR-013`, `FR-015`, `FR-017`, `FR-035`, `FR-039`,
`FR-040`;
`SCR-009`, `SCR-010`, `SCR-004`, `SCR-013`; `researchRunCreate`,
`researchRunGet`, `researchRunClaimsList`, `researchRunEventsStream`;
`AI-001`..`AI-010`, `AI-013`, `AI-016`.

**Tiền điều kiện:** case/event date/issues có đủ tối thiểu; corpus active.  
**Kích hoạt:** user chọn issues, scope nguồn và Chạy nghiên cứu.

**Luồng chính:** 1. Validate facts/scope/budget; nếu scope khóa trong một tài liệu,
không lấy nguồn ngoài trừ khi user bật rõ. 2. Tạo kế hoạch công việc có thể
kiểm tra, không hiển thị suy nghĩ nội bộ của model. 3. Tìm nguồn theo authority và
thời gian. 4. Theo legal edges có giới hạn. 5. Tìm counter-authority/exception.
6. Tạo claim-evidence matrix. 7. Verifier chạy. 8. Hiển thị kết quả, gaps, conflicts,
cost và next action. 9. Khi user yêu cầu case tương tự, filter tenant/matter/ethical
wall chạy trước retrieval và kết quả được ẩn danh theo policy. 10. User nhận/chỉnh
issue hoặc gửi sang draft.

**Thay thế/lỗi:** cần thêm fact chuyển `needs_input`; budget hết trả partial evidence
và gaps; provider lỗi retry/fallback theo policy; conflict/coverage thấp abstain;
cancel/resume theo UC-017.

**Quyền:** run chỉ truy cập sources/docs trong capability token đã cấp.  
**Dữ liệu:** run/steps/status/checkpoints, inputs, claims/evidence, source snapshots,
budgets, releases và verifier results.  
**Audit:** state transition/tool call metadata/cost, không lưu hidden chain-of-thought.  
**Hậu điều kiện:** analysis version có thể tạo draft hoặc cần bổ sung dữ kiện/review.  
**Nghiệm thu:** run tái tạo được bằng identifiers; mỗi claim có status và evidence;
tool không truy cập nguồn ngoài allowlist dù tài liệu chứa instruction.

### UC-008 Tính và so sánh VAT

**Mục tiêu:** tính kết quả trong phạm vi rule với input, phiên bản và từng bước tái lập.  
**Actor:** ACT-001; ACT-002 kiểm tra trace.  
**Ánh xạ:** `FR-018`, `FR-019`; `SCR-011`; `calculationRunCreate`,
`calculationRunGet`; `AI-011`.

**Tiền điều kiện:** published rule phù hợp event date; user có input bắt buộc.  
**Kích hoạt:** chọn calculator hoặc gọi từ case analysis.

**Luồng chính:** 1. Resolver chọn rule version. 2. Form hiển thị typed inputs/unit
và nguồn fact. 3. User xác nhận input. 4. Engine validate và tính deterministic.
5. Hiển thị steps, rounding, warnings, rule/source version. 6. User nhân scenario
để so sánh. 7. Chèn calculation reference vào analysis/draft.

**Thay thế/lỗi:** thiếu input thì không tính; input ngoài domain trả validation;
không có rule version phù hợp chuyển chuyên gia; rule deprecated chỉ cho xem run
cũ; model chỉ có thể giải thích output đã ký, không thay số.

**Quyền:** create/read theo matter; rule editing thuộc knowledge role khác.  
**Dữ liệu:** input schema/value/unit/source, rule/version/release, steps/result/warnings.  
**Audit:** exact inputs, rule hash, result, caller, linked fact/draft, rerun.  
**Hậu điều kiện:** immutable calculation run; scenario là run mới có lineage.  
**Nghiệm thu:** golden/boundary/property tests exact; rerun cùng input/rule cho cùng
result; UI không cho sửa text kết quả độc lập với engine.

### UC-009 Tạo và chỉnh sửa memo

**Mục tiêu:** tạo deliverable từ facts, claims, nguồn và calculation đã chọn.  
**Actor:** ACT-001.  
**Ánh xạ:** `FR-020`, `FR-021`, `FR-023`; `SCR-010`, `SCR-012`, `SCR-013`;
`draftCreate`, `draftGet`, `draftUpdate`;
`AI-012`, `AI-013`, `AI-017`.

**Tiền điều kiện:** case có analysis; user có draft permission; template phù hợp.  
**Kích hoạt:** chọn Tạo memo/email.

**Luồng chính:** 1. User chọn audience/template/language và các issues. 2. Backend
đóng snapshot facts/claims/calculations. 3. Grounded drafting tạo cấu trúc answer
contract. 4. Validator gắn claim-source và flags. 5. User edit nội dung, citation
hoặc assumptions. 6. Autosave version. 7. Xem diff và validation status. 8. Submit
review qua UC-010.

**Thay thế/lỗi:** claim unsupported được giữ cờ và chặn submit nếu material; citation
bị xóa làm validation chạy lại; generation lỗi không làm mất bản người dùng;
source/fact update đánh stale và yêu cầu regenerate/review có chọn lọc.

**Quyền:** contributor của case; template/license có scope tenant.  
**Dữ liệu:** draft/version, template, frozen dependencies, editor ops, citations, flags.  
**Audit:** create/generate/edit checkpoints, dependency/version, validation outcome.  
**Hậu điều kiện:** draft version `ready_for_review` hoặc còn blockers.  
**Nghiệm thu:** không có raw model response trong document; click citation mở đúng
span; refresh không mất edit; sửa sau approval tạo version chưa duyệt.

### UC-010 Gửi duyệt, return và approve

**Mục tiêu:** maker-checker kiểm tra và ký đúng một draft version.  
**Actor:** ACT-001 gửi; ACT-002 duyệt.  
**Ánh xạ:** `FR-021`..`FR-023`; `SCR-015`, `SCR-016`, `SCR-013`;
`draftReviewSubmit`, `reviewsList`, `reviewGet`, `reviewChangesRequest`,
`reviewApprove`;
`AI-010`, `AI-013` hỗ trợ flags, không quyết định approval.

**Tiền điều kiện:** draft validation pass hoặc có exception workflow được policy
cho phép; reviewer độc lập/đủ cấp cho T2/T3.  
**Kích hoạt:** contributor submit hoặc reviewer mở queue.

**Luồng chính:** 1. Hệ thống freeze draft version/dependencies. 2. Xác định tier và
reviewer. 3. Reviewer xem diff, facts, dates, claims/sources, counter-authority,
calculation trace và flags. 4. Comment/resolve từng mục. 5. Reviewer chọn Return
với lý do hoặc Approve và xác nhận checklist. 6. Ghi signature/timestamp. 7. Cập
nhật status và thông báo owner.

**Thay thế/lỗi:** maker không tự approve T2; dependency đổi trong lúc review làm
stale và chặn approve; concurrent reviewer conflict dùng optimistic lock; citation
không mở/calculation không tái lập là blocker không override im lặng.

**Quyền:** reviewer grant theo matter/tier; client không truy cập review notes.  
**Dữ liệu:** review, assignment, checklist, comments, flags, decision, signature.  
**Audit:** submit/assign/open/comment/resolve/return/approve và exact version.  
**Hậu điều kiện:** approved version có thể xuất; returned version về contributor.  
**Nghiệm thu:** approval chỉ áp dụng frozen version; mọi edit sau đó mất trạng thái
approved; reviewer tái tạo được source và calculation tại thời điểm ký.

### UC-011 Xuất và chia sẻ bản đã duyệt

**Mục tiêu:** tạo deliverable có kiểm soát, đúng trạng thái và audience.  
**Actor:** ACT-001; người nhận ACT-007.  
**Ánh xạ:** `FR-024`, `FR-025`; `SCR-012`, `SCR-022`;
`draftExportCreate`, `exportGet`; không gọi AI trong bước xuất. Nếu cần
plain-language/translation, hệ thống tạo version mới theo UC-009 bằng `AI-017`.

**Tiền điều kiện:** exact draft version `approved`; user có export/share quyền.  
**Kích hoạt:** chọn Export hoặc Chia sẻ.

**Luồng chính:** 1. Chọn định dạng, audience, phần nguồn/audit được phép, expiry và
download policy. 2. Server kiểm tra approval/stale/license/DLP. 3. Render PDF/DOCX
có heading/link/metadata. 4. Với portal, tạo grant ngắn hạn và thông báo. 5. Client
xác thực, xem/comment bản được phép. 6. Owner có thể revoke.

**Thay thế/lỗi:** draft/stale bị chặn; nguồn license hạn chế bị thay bằng citation
metadata phù hợp; render lỗi retry; DLP flag yêu cầu review; link hết hạn/revoke
trả trang an toàn không xác nhận sự tồn tại của case.

**Quyền:** explicit share grant; default no-download; internal notes loại khỏi export.  
**Dữ liệu:** export artefact/hash, share grant, audience, expiry, access/comment events.  
**Audit:** exporter, exact approved version, policy checks, recipient access/revoke.  
**Hậu điều kiện:** artefact bất biến; version mới không ghi đè link cũ.  
**Nghiệm thu:** draft chưa duyệt có watermark và không share; revoke có hiệu lực
với session/URL; export đọc được bằng keyboard/screen reader ở mức đã định.

### UC-012 Theo dõi thay đổi có liên quan

**Mục tiêu:** nhận cảnh báo luật mới thành một công việc cụ thể, không thành dòng tin.  
**Actor:** ACT-001; hỗ trợ ACT-008.  
**Ánh xạ:** `FR-030`, `FR-031`, `FR-037`; `SCR-002`, `SCR-017`, `SCR-018`;
`legalChangesList`, `legalChangeGet`, `changeSubscriptionCreate`,
`changeSubscriptionUpdate`, `alertsList`, `alertMarkRead`;
`AI-014`, `AI-015`, `AI-018`.

**Tiền điều kiện:** subscription theo matter/profile; impact đã được xác nhận cho
kênh external hoặc gắn rõ `proposal` cho nội bộ.  
**Kích hoạt:** corpus release phát event hoặc user mở Change center.

**Luồng chính:** 1. Dependency matcher tìm subscriptions/cases. 2. Materiality và
dedupe tạo alert/task. 3. User thấy nguồn, changed span, lý do liên quan, severity,
owner và due date. 4. User mở impacted asset, acknowledge/assign/resolve/snooze theo
policy. 5. Resolution cập nhật task và audit.

**Thay thế/lỗi:** match yếu chỉ vào curator queue; duplicate gộp lineage; delivery
channel lỗi vẫn giữ inbox; source rollback thu hồi/đổi trạng thái alert có giải thích.

**Quyền:** user chỉ thấy impacted assets có membership; notification không chứa PII.  
**Dữ liệu:** subscription, dependency, impact/task, severity, delivery/ack state.  
**Audit:** rule/model/release tạo match, curator confirmation, delivery và action.  
**Hậu điều kiện:** mỗi material alert có owner/action hoặc disposition có lý do.  
**Nghiệm thu:** không gửi tên/client fact qua notification ngoài; stale link mở đúng
asset; dedupe không che mất thay đổi có effective date khác.

### UC-013 Tiếp nhận và phát hành corpus

**Mục tiêu:** đưa nguồn mới vào production qua quarantine, QA, regression và atomic release.  
**Actor:** ACT-003, ACT-004; hỗ trợ ACT-008, upstream ACT-010.  
**Ánh xạ:** `FR-026`, `FR-027`, `FR-028`; `SCR-019`, `SCR-018`, `SCR-013`;
`corpusIngestionRunCreate`, `corpusIngestionRunGet`,
`corpusCurationDecisionCreate`, `corpusReleaseCreate`, `corpusReleasePublish`;
`AI-008`, `AI-014`.

**Tiền điều kiện:** source allowlist/license/owner; platform curator session JIT/step-up.  
**Kích hoạt:** monitor phát hiện nguồn hoặc curator nhập URL/file.

**Luồng chính:** 1. Download và lưu original/hash/headers/time. 2. Scan, parse/OCR
vào quarantine. 3. Extract metadata/structure/cross-reference ở trạng thái proposed.
4. Curator đối chiếu original và sửa/xác nhận. 5. Tạo diff/edges. 6. Knowledge
approver duyệt thay đổi trọng yếu. 7. Build projection mới và chạy regression.
8. Nếu pass, publish manifest atomic. 9. Phát invalidation/impact event.

**Thay thế/lỗi:** upstream đổi giữa tải thì hash/version tách riêng; parser thấp
giữ manual queue; duplicate gộp evidence không ghi đè; regression fail không đổi
active release; publish lỗi rollback manifest/projection theo runbook.

**Quyền:** chỉ platform curator/approver dùng control plane; tenant admin/curator chỉ
quản overlay riêng. Curator không tự approve thay đổi do mình tạo khi dual control.  
**Dữ liệu:** source/snapshot, parse artefact, provisions/versions/edges, QA, release manifest.  
**Audit:** URL/hash, tool versions, corrections, approvals, benchmark và publish/rollback.  
**Hậu điều kiện:** production chỉ đọc active immutable release; quarantine cách ly.  
**Nghiệm thu:** search trước publish không thấy source; release fail giữ kết quả cũ;
rollback khôi phục manifest và tạo audit/invalidation rõ ràng.

### UC-014 Xác nhận tác động của thay đổi

**Mục tiêu:** biến diff thành danh sách case/rule/template/answer cần rà soát có chứng cứ.  
**Actor:** ACT-003, ACT-004; ACT-001 là owner tài sản bị ảnh hưởng.  
**Ánh xạ:** `FR-029`, `FR-030`; `SCR-018`, `SCR-017`;
`changeImpactRunCreate`, `changeImpactRunGet`;
`AI-014`, `AI-015`.

**Tiền điều kiện:** change/diff đã gắn source spans; dependency graph có stable IDs.  
**Kích hoạt:** corpus release mới hoặc curator chạy lại impact.

**Luồng chính:** 1. Tìm dependency theo edge/version/rule/citation. 2. Xếp proposal
theo directness/materiality. 3. Hiển thị đường dẫn change -> provision -> asset.
4. Curator kiểm tra changed span, effective date và transition. 5. Confirm/dismiss
kèm lý do. 6. Confirm tạo stale flag/task/owner/SLA. 7. Asset owner review và resolve.

**Thay thế/lỗi:** dependency mơ hồ vào manual queue; false positive dismiss được
dùng cho evaluation nhưng không tự train; missing owner chuyển admin queue; source
rollback đóng hoặc supersede impact thay vì xóa lịch sử.

**Quyền:** curator xem metadata toàn corpus; matter content chỉ khi grant, nếu không
chỉ thấy opaque asset ID/owner.  
**Dữ liệu:** diff hunks, dependency paths, proposals, decisions, stale/task records.  
**Audit:** algorithm/model release, scores, confirmation/dismissal và downstream actions.  
**Hậu điều kiện:** impacted assets có trạng thái rõ; cảnh báo external chỉ từ confirmed impact.  
**Nghiệm thu:** mọi confirmed impact có exact changed span và dependency path; test
source update làm stale đúng calculator/draft fixture.

### UC-015 Quản trị người dùng và quyền

**Mục tiêu:** cấp/thu quyền có kiểm soát và áp dụng nhất quán trên mọi lớp dữ liệu.  
**Actor:** ACT-005.  
**Ánh xạ:** `FR-002`, `FR-032`, `FR-034`; `SCR-020`;
`tenantMembersList`, `tenantMemberInvite`, `tenantMemberUpdate`, `tenantRolesList`,
`matterMembersList`, `matterMemberPut`; không có AI.

**Tiền điều kiện:** admin session được step-up auth cho thay đổi nhạy cảm.  
**Kích hoạt:** admin mời, đổi role, ethical wall, retention hoặc revoke.

**Luồng chính:** 1. Chọn user/policy. 2. Hiển thị quyền hiệu lực và impact preview.
3. Admin xác nhận, với step-up/dual approval nếu cần. 4. Backend cập nhật transaction.
5. Vô hiệu session/cache/stream/download-share grants chịu ảnh hưởng. 6. Gửi thông báo tối thiểu.
7. Ghi audit.

**Thay thế/lỗi:** không được xóa admin cuối; conflict ethical wall bị chặn; revoke
partial failure chạy reconciliation; legal hold thắng deletion/retention policy.

**Quyền:** tenant admin quản lý metadata; không tự cấp quyền đọc ethical-wall matter
cho chính mình nếu thiếu approver.  
**Dữ liệu:** user/membership/role/policy/grant/retention/legal hold.  
**Audit:** before/after, approver, reason, sessions/URLs invalidated.  
**Hậu điều kiện:** authorization decision mới có hiệu lực trên DB/search/object/cache.  
**Nghiệm thu:** revoke được kiểm thử tức thời trên API, SSE, download và active tab;
admin không thể vượt RLS chỉ bằng request parameter.

### UC-016 Tra cứu và xuất audit

**Mục tiêu:** tái tạo hành động và output mà không mở rộng quyền nội dung không cần thiết.  
**Actor:** ACT-006.  
**Ánh xạ:** `FR-033`, `NFR-010`, `NFR-012`; `SCR-021`;
`auditEventsSearch`, `auditExportCreate`, `auditExportGet`; không có AI.

**Tiền điều kiện:** audit grant theo tenant/time/object/purpose; step-up cho export.  
**Kích hoạt:** auditor tìm theo correlation, matter, actor, action hoặc release.

**Luồng chính:** 1. Chọn phạm vi và bộ lọc. 2. Server enforce grant và purpose.
3. Hiển thị timeline events/versions/outcomes. 4. User mở references nếu có quyền
nội dung. 5. Chọn export; hệ thống preview redaction/scope. 6. Tạo bundle ký/hash,
expiry và download audit.

**Thay thế/lỗi:** query quá rộng yêu cầu thu hẹp/approval; event reference đã hết
retention hiển thị tombstone hợp lệ; thiếu matter grant chỉ hiện metadata tối thiểu;
export job lỗi retry không nhân đôi artefact.

**Quyền:** read-only; export là quyền riêng; audit store không sửa/xóa qua UI.  
**Dữ liệu:** immutable events, correlation/causation, artefact/release references, export.  
**Audit:** chính việc search/view/export audit cũng được ghi.  
**Hậu điều kiện:** bundle tái tạo được và có chain/hash verification.  
**Nghiệm thu:** sample high-impact answer truy về exact facts/source/corpus/model/
rule/draft/reviewer; export không chứa raw secret hoặc nội dung ngoài grant.

### UC-017 Điều khiển research run dài

**Mục tiêu:** theo dõi, pause/resume/cancel/retry một workflow dài mà không mất state.  
**Actor:** ACT-001; thực thi ACT-008.  
**Ánh xạ:** `FR-015`, `FR-016`; `SCR-004`, `SCR-010`;
`researchRunGet`, `researchRunEventsStream`, `researchRunPause`,
`researchRunResume`, `researchRunCancel`; `AI-009`.

**Tiền điều kiện:** run thuộc matter/tenant và user có control permission.  
**Kích hoạt:** job vượt 10 giây, cần input, lỗi retriable hoặc user chọn control.

**Luồng chính:** 1. UI nhận state/progress qua SSE và có fallback polling. 2. Mỗi
bước hiển thị tên nghiệp vụ, trạng thái, nguồn count, budget, không hiển thị hidden
reasoning. 3. User pause/cancel hoặc cung cấp input. 4. Backend checkpoint và xác
nhận command idempotently. 5. Resume từ checkpoint hợp lệ. 6. Completed output
được verifier/policy gate trước khi dùng.

**Thay thế/lỗi:** mất mạng reconnect bằng last-event ID; worker crash lease/retry;
cancel trễ hiển thị `cancelling`; non-retriable failure nêu action; quyền bị revoke
đóng stream và không tiếp tục trả payload.

**Quyền:** owner/member; cancel shared run có confirmation; worker capability scoped.  
**Dữ liệu:** run state, checkpoint, commands, event sequence, budget/cost, partial artefacts.  
**Audit:** transitions, initiator, retry reason, provider/tool metadata, terminal state.  
**Hậu điều kiện:** một terminal state duy nhất; partial output không tự thành approved.  
**Nghiệm thu:** refresh/đóng tab rồi mở lại thấy state đúng; duplicate resume/cancel
không tạo duplicate tool calls hoặc charge ngoài policy.

### UC-018 Abstain và chuyển chuyên gia

**Mục tiêu:** ngăn hệ thống đoán khi thiếu điều kiện để kết luận và tạo đường xử lý rõ.  
**Actor:** ACT-001; ACT-002 nhận escalation; policy gate là actor hệ thống.  
**Ánh xạ:** `FR-023`, `FR-035`; `SCR-003`, `SCR-004`, `SCR-010`, `SCR-015`;
`researchRunInputProvide`, `researchRunEscalate`, `researchRunGet`;
`AI-001`, `AI-003`, `AI-010`, `AI-013`; policy/risk gate deterministic.

**Tiền điều kiện:** một query/run/draft chạm gate thiếu fact, source, temporal fit,
conflict, calculation, deadline, scope hoặc risk.  
**Kích hoạt:** validator/policy gate hoặc user chọn Cần chuyên gia.

**Luồng chính:** 1. Hệ thống phân loại blocker bằng mã có thể kiểm tra. 2. Không tạo
kết luận dứt khoát cho phần bị chặn. 3. Hiển thị phần biết được, điều kiện còn thiếu,
nguồn đã kiểm tra và hành động cụ thể. 4. Nếu có thể giải bằng fact, hỏi câu ngắn
kèm lý do. 5. Nếu cần chuyên gia, tạo escalation có tier, owner, SLA và context
được phép. 6. Reviewer resolve, yêu cầu thêm hoặc đóng với disposition.

**Thay thế/lỗi:** không có reviewer chuyển team queue; gần deadline nâng priority;
yêu cầu nghi ngờ gian lận/trốn thuế từ chối phần bị cấm và hướng về tuân thủ;
notification lỗi vẫn giữ queue; user không được override blocker bảo mật/isolation.

**Quyền:** chỉ chia sẻ context tối thiểu cho reviewer đủ matter clearance.  
**Dữ liệu:** blocker codes, missing items, evidence coverage, risk tier, escalation/task.  
**Audit:** gate inputs/version, outcome, user response, assignment và disposition.  
**Hậu điều kiện:** presentation output là `needs_input`, `needs_review` hoặc
`cannot_conclude`; trường hợp cuối ánh xạ từ terminal research-run `abstained`,
không giả trạng thái completed/verified.  
**Nghiệm thu:** bộ test false premise/missing date/conflict/coverage thấp luôn dừng
đúng; thông điệp nói rõ cần gì và không dùng model memory để lấp khoảng trống.

## 5. Ma trận truy vết UC -> màn hình/API/AI

| UC | Màn hình | operationId chính | AI task |
|---|---|---|---|
| UC-001 | SCR-001, SCR-002 | `sessionContextGet`, `tenantContextSelect` | - |
| UC-002 | SCR-003, SCR-004, SCR-013 | `researchRunCreate`, `researchRunGet`, `legalSearchExecute`, `sourceAnchorContentGet` | AI-001, AI-005, AI-006, AI-007, AI-010, AI-013 |
| UC-003 | SCR-014, SCR-013 | `legalProvisionVersionsList`, `legalProvisionVersionsCompare`, `legalProvisionVersionGet` | AI-005, AI-014 |
| UC-004 | SCR-005, SCR-006 | `matterCreate`, `mattersList`, `matterGet`, `matterUpdate`, `matterClose`, `matterMembersList`, `matterMemberPut` | - |
| UC-005 | SCR-008, SCR-007, SCR-013 | `documentUploadInitiate`, `documentUploadComplete`, `documentUploadGet`, `matterDocumentGet` | AI-002, AI-008 |
| UC-006 | SCR-007, SCR-009 | `matterIntakeGet`, `matterIntakeUpdate`, `factExtractionCreate`, `matterFactsList`, `matterFactCreate`, `matterFactUpdate`, `matterFactConfirm`, `matterFactDispute`, `matterIssuesList`, `matterIssueCreate`, `matterIssueUpdate` | AI-002, AI-003, AI-004 |
| UC-007 | SCR-009, SCR-010, SCR-004 | `researchRunCreate`, `researchRunGet`, `researchRunClaimsList`, `researchRunEventsStream` | AI-001..AI-010, AI-013, AI-016 |
| UC-008 | SCR-011 | `calculationRunCreate`, `calculationRunGet` | AI-011 |
| UC-009 | SCR-010, SCR-012 | `draftCreate`, `draftGet`, `draftUpdate` | AI-012, AI-013, AI-017 |
| UC-010 | SCR-015, SCR-016 | `draftReviewSubmit`, `reviewsList`, `reviewGet`, `reviewAssigneePut`, `reviewCommentCreate`, `reviewFlagResolve`, `reviewApprove`, `reviewChangesRequest` | AI-010, AI-013 |
| UC-011 | SCR-012, SCR-022 | `draftExportCreate`, `exportGet`, `draftShareCreate`, `sharedArtifactGet`, `draftShareRevoke`, `sharedArtifactCommentsList`, `sharedArtifactCommentCreate` | - |
| UC-012 | SCR-002, SCR-017, SCR-018 | `legalChangesList`, `legalChangeGet`, `changeSubscriptionCreate`, `changeSubscriptionUpdate`, `alertsList`, `alertMarkRead`, `tasksList`, `taskGet`, `taskAssign`, `taskAcknowledge`, `taskResolve` | AI-014, AI-015, AI-018 |
| UC-013 | SCR-019, SCR-018 | `corpusIngestionRunCreate`, `corpusIngestionRunGet`, `corpusCurationDecisionCreate`, `corpusReleaseCreate`, `corpusReleasePublish`, `corpusReleaseRollback` | AI-008, AI-014 |
| UC-014 | SCR-018, SCR-017 | `changeImpactRunCreate`, `changeImpactRunGet`, `changeImpactConfirm`, `changeImpactDismiss` | AI-014, AI-015 |
| UC-015 | SCR-020 | `tenantMembersList`, `tenantMemberInvite`, `tenantMemberUpdate`, `tenantMemberSessionsRevoke`, `tenantRolesList`, `matterMembersList`, `matterMemberPut`, `tenantRetentionPolicyGet`, `tenantRetentionPolicyUpdate`, `legalHoldsList`, `legalHoldCreate`, `legalHoldRelease` | - |
| UC-016 | SCR-021 | `auditEventsSearch`, `auditExportCreate`, `auditExportGet` | - |
| UC-017 | SCR-004, SCR-010 | `researchRunPause`, `researchRunResume`, `researchRunCancel`, `researchRunEventsStream` | AI-009 |
| UC-018 | SCR-003, SCR-004, SCR-010, SCR-015 | `researchRunInputProvide`, `researchRunEscalate`, `researchRunGet` | AI-001, AI-003, AI-010, AI-013 |

## 6. Test nghiệp vụ xuyên use case

| Test journey | Use case | Kết quả bắt buộc |
|---|---|---|
| Case VAT tại ngày chuyển tiếp | UC-004..UC-010 | đúng version, facts xác nhận, calculator trace, maker-checker |
| File có prompt injection | UC-005, UC-007 | nội dung được coi là data; tool policy không đổi; event được ghi |
| Thu hồi quyền khi đang mở SSE | UC-001, UC-015, UC-017 | stream dừng, cache/URL vô hiệu, không rò payload mới |
| Luật mới làm thay đổi rule | UC-003, UC-013, UC-014, UC-012 | release atomic, asset stale, owner/task/source span đầy đủ |
| Thiếu event date và nguồn mâu thuẫn | UC-002, UC-018 | không đoán; hỏi lại/hiện hai phía/escalate |
| Sửa memo sau approve | UC-009..UC-011 | version mới chưa duyệt; bản cũ bất biến; share không tự đổi |
| Tái tạo tư vấn đã gửi | UC-016 | đủ facts, sources, releases, rule, reviewer và artefact hash |
| Cross-tenant từ search đến download | UC-001, UC-005, UC-007, UC-015 | default deny ở mọi projection và signed object access |

## 7. Definition of done cho một use case

Một UC chỉ hoàn thành khi có contract/schema typed, authorization tests, happy
path và lỗi chính, audit events, loading/empty/error/recovery UI, accessibility
checks, telemetry đã redact, idempotency với command, và liên kết test evidence
về đúng `FR-*`/`NFR-*`. Demo thủ công không thay thế các điều kiện này.
