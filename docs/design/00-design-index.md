# Bộ hồ sơ thiết kế sản phẩm

**Sản phẩm:** Tax Legal Workspace - Trợ lý pháp luật thuế Việt Nam  
**Wedge:** B2B, VAT và hóa đơn  
**Trạng thái:** thiết kế để triển khai; mọi ngưỡng chất lượng phải được xác nhận
bằng benchmark và pilot trước production  
**Phiên bản thiết kế:** 0.2, ngày 11/08/2026  
**Mốc kiểm chứng tài liệu nền và ingestion pilot:** 11/08/2026

## 1. Mục đích

Thư mục này chuyển đề án nghiên cứu thành hợp đồng làm việc chung cho product,
tax/legal, UX, data, backend, applied AI, security, QA và vận hành. Mỗi yêu cầu
phải truy được tới use case, màn hình, API, dữ liệu, tác vụ AI và kiểm thử.

Bộ hồ sơ không phải ý kiến pháp lý, migration production hay cam kết chất lượng
đã đạt. Khi thiết kế và mã nguồn khác nhau, thay đổi phải đi qua ADR/change
request; không âm thầm sửa tài liệu sau để hợp thức hóa hành vi hệ thống.

## 2. Thứ tự đọc

1. [Product requirements](01-product-requirements.md)
2. [Use cases](02-use-cases.md)
3. [Thiết kế giao diện](03-interface-design.md)
4. [Thiết kế dữ liệu](04-data-model.md)
5. [Thiết kế backend và API](05-backend-api.md)
6. [Kiến trúc hệ thống](06-system-architecture.md)
7. [Kiến trúc AI theo tác vụ](07-ai-task-architecture.md)
8. [Truy vết và chiến lược kiểm thử](08-traceability-and-test-strategy.md)

Tài liệu nền:

- [Đề án tổng thể](../de-an-tong-the.md)
- [Benchmark và kế hoạch web](../benchmark-va-ke-hoach-web.md)
- [Đặc tả kiến trúc nghiên cứu](../product-architecture-blueprint.md)
- [Kế hoạch nghiên cứu](../research-reading-plan.md)
- [Sổ nguồn](../source-register.md)
- [Pilot thu thập dữ liệu VAT/hóa đơn](../crawl-pilot.md)
- [Corpus pháp luật thuế chọn lọc 10 năm](../crawl-tax-law-10y.md)

## 3. Quyền sở hữu từng tài liệu

| Tài liệu | Quyết định chuẩn | Owner chính | Người duyệt bắt buộc |
|---|---|---|---|
| 01 PRD | mục tiêu, phạm vi, yêu cầu, KPI | Product lead | Tax/legal lead, engineering lead |
| 02 Use cases | hành vi nghiệp vụ và ngoại lệ | Product analyst | Tax SME, UX, QA |
| 03 Interface | IA, tương tác, trạng thái, accessibility | Product designer | Product, frontend, accessibility reviewer |
| 04 Data model | entity, invariant, lifecycle, retention | Data/backend lead | Security, tax knowledge lead |
| 05 Backend/API | module, contract, event và workflow | Backend lead | Frontend, AI, security, QA |
| 06 System architecture | boundary, deployment, SLO và trade-off | Architect | Engineering, security, operations |
| 07 AI tasks | pipeline, tool, gate, eval và fallback | Applied AI lead | Tax SME, security, evaluation lead |
| 08 Traceability/test | coverage và release evidence | QA/evaluation lead | Tất cả owner liên quan |

## 4. Chuẩn định danh

| Tiền tố | Đối tượng | Ví dụ |
|---|---|---|
| `G-` | product goal | `G-001` |
| `FR-` | functional requirement | `FR-012` |
| `NFR-` | non-functional requirement | `NFR-006` |
| `BR-` | business/legal rule | `BR-004` |
| `UC-` | use case | `UC-007` |
| `ACT-` | actor/role trong use case | `ACT-003` |
| `SCR-` | screen/view | `SCR-005` |
| `CMP-` | UI component dùng chung | `CMP-010` |
| `AI-` | AI/deterministic intelligence task | `AI-009` |
| `DATA-INV-` | database invariant | `DATA-INV-005` |
| `ADR-` | architecture decision record | `ADR-005` |
| `T-` | test/evaluation case or suite | `T-020` |

ID không được tái sử dụng sau khi xóa. Tài liệu đánh dấu `deprecated` và liên kết
ID thay thế. API dùng `operationId` camelCase ổn định, ví dụ `matterCreate`.
Domain/integration event dùng tên có version `domain.event.vN`, ví dụ
`research.completed.v1`, thay vì một ID song song không truy được tới schema.

## 5. Thuật ngữ chuẩn

| Thuật ngữ | Nghĩa trong hệ thống |
|---|---|
| Matter/case | hồ sơ tư vấn được cách ly theo tenant và quyền matter |
| Fact | dữ kiện vụ việc; có trạng thái đề xuất, xác nhận, tranh chấp hoặc thay thế |
| Event date | ngày sự kiện dùng để xác định quy phạm áp dụng |
| Known at | thời điểm hệ thống/người tư vấn biết một phiên bản nguồn |
| Instrument | văn bản pháp luật hoặc tài liệu có thẩm quyền |
| Provision version | phiên bản một điều/khoản/điểm trong khoảng hiệu lực |
| Snapshot | bản sao bất biến của nguồn kèm hash và provenance |
| Claim | mệnh đề trong đầu ra cần evidence hoặc nhãn suy luận rõ |
| Citation/source anchor | liên kết tới snapshot, trang, bbox/text offsets và đoạn nguồn |
| Corpus release | tập nguồn/index/graph đã kiểm thử và phát hành atomically |
| Rule version | phiên bản logic tính/điều kiện có khoảng hiệu lực và test |
| Draft | đầu ra chưa được người đủ thẩm quyền phê duyệt |
| Approved deliverable | phiên bản đã ký duyệt; bất kỳ sửa đổi nào tạo phiên bản mới |
| Stale | kết quả cần xem lại vì source, rule, fact hoặc dependency thay đổi |
| Abstain | chủ động không kết luận do thiếu căn cứ/phạm vi, không phải lỗi hệ thống |

## 6. Invariant xuyên hệ thống

1. Mọi truy vấn matter đều bị lọc tenant và matter ACL **trước** SQL, search,
   vector, graph, object access và model context.
2. Văn bản gốc/snapshot không bị ghi đè; sửa metadata hoặc parse tạo version.
3. Luật áp dụng được giải bằng `event_date`; khả năng tái tạo dùng thêm `known_at`.
4. Search/vector/graph/cache là projection; PostgreSQL và object evidence store
   là nguồn chuẩn.
5. Mọi claim trọng yếu phải có source anchor đủ thẩm quyền hoặc bị chặn/abstain.
6. LLM không tự quyết hiệu lực pháp luật, số thuế, deadline hoặc trạng thái duyệt.
7. Fact do AI trích chỉ là `proposed` cho tới khi qua rule hoặc người xác nhận.
8. Tool có side effect mặc định bị cấm; thao tác ngoài hệ thống cần preview và
   phê duyệt tách biệt.
9. Không lưu/phơi chain-of-thought. Audit lưu input/output có cấu trúc, tool call,
   nguồn, gate, version và quyết định người dùng.
10. Đổi fact, source, rule, corpus, prompt hoặc model phải xác định dependency và
    làm stale đúng output liên quan.
11. Chỉ bản approved được gửi khách hàng mà không có nhãn `Bản nháp AI`.
12. Không dùng dữ liệu khách hàng để huấn luyện hoặc evaluation ngoài phạm vi đã
    được phê duyệt và ghi nhận.

## 7. Nguồn sự thật cho từng quyết định

```text
Why / scope / success       -> PRD
Who does what / exceptions -> Use cases
What the user sees         -> Interface design
What is persisted          -> Data model
What crosses boundaries    -> Backend/API
Where it runs / qualities  -> System architecture
How intelligence executes -> AI task architecture
How it is proved           -> Traceability and tests
```

Một tài liệu không được sao chép đầy đủ nội dung thuộc nguồn sự thật khác. Nó
tham chiếu bằng ID và chỉ bổ sung chi tiết thuộc trách nhiệm của mình.

## 8. Quy trình thay đổi thiết kế

1. Tạo change request nêu vấn đề, ID bị ảnh hưởng và bằng chứng.
2. Xác định owner, legal/security/privacy impact và migration need.
3. Viết ADR nếu thay boundary, source of truth, framework hoặc quality trade-off.
4. Cập nhật tài liệu nguồn sự thật trước hoặc cùng pull request mã nguồn.
5. Cập nhật traceability, test và rollout/rollback.
6. Lấy phê duyệt của owner và reviewer bắt buộc.
7. Ghi version/release note; không sửa deliverable đã approved tại chỗ.

## 9. Definition of ready

Một feature sẵn sàng vào sprint khi có:

- FR/UC và persona/value rõ;
- screen/state hoặc API contract phù hợp;
- data owner, classification, retention và permission;
- AI task/gate/eval nếu có model;
- acceptance criteria và test ID;
- dependency, migration, telemetry, rollout/rollback;
- tax/legal reviewer cho logic quy phạm.

## 10. Definition of done

Một feature chỉ hoàn thành khi:

- happy path, failure, empty/loading, permission và accessibility đều hoạt động;
- contract/schema/migration backward-compatible hoặc có kế hoạch chuyển đổi;
- unit/integration/E2E/security/eval tương ứng vượt gate;
- audit/provenance tái tạo được hành vi;
- dashboard/runbook/alert và rollback được kiểm tra;
- tài liệu, traceability và release manifest cập nhật;
- không còn lỗi P0/P1; residual risk được owner chấp nhận bằng văn bản.
