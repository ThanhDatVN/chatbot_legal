# Yêu cầu sản phẩm: Tax Legal Workspace

**Phiên bản:** 0.1  
**Trạng thái:** baseline để discovery, thiết kế và nghiệm thu MVP  
**Phạm vi:** B2B, pháp luật Việt Nam, VAT và hóa đơn  
**Mốc nguồn nền:** 09/08/2026  
**Tài liệu liên quan:** [Use case](02-use-cases.md), [Thiết kế giao diện](03-interface-design.md), [Đề án tổng thể](../de-an-tong-the.md), [Kế hoạch web](../benchmark-va-ke-hoach-web.md)

## 1. Mục đích tài liệu

Tài liệu này xác định sản phẩm cần giải quyết việc gì, cho ai, giới hạn ở đâu và
điều kiện nào phải đạt trước khi một đầu ra được sử dụng. Đây không phải đặc tả
mô hình AI, schema database hay hợp đồng API; các tài liệu đó phải truy vết về
các mã `FR-*`, `NFR-*` và `BR-*` tại đây.

Trong tài liệu:

- **case/matter**: hồ sơ tư vấn của một khách hàng về một hoặc nhiều vấn đề;
- **fact**: dữ kiện vụ việc, luôn có trạng thái xác nhận và nguồn gốc;
- **event date**: ngày phát sinh sự kiện dùng để xác định quy định áp dụng;
- **knowledge time**: thời điểm hệ thống đã ghi nhận một phiên bản nguồn;
- **authority**: căn cứ pháp lý hoặc nguồn giải thích có phân hạng;
- **claim**: một mệnh đề nguyên tử trong bản phân tích;
- **snapshot**: bản sao nguồn bất biến, có hash và thời điểm thu thập;
- **draft**: đầu ra chưa được người có thẩm quyền phê duyệt;
- **stale**: tài sản cần rà soát lại vì fact, nguồn, rule hoặc dependency đổi.

## 2. Tầm nhìn và định vị

Xây một **workspace tư vấn thuế có AI dành cho chuyên gia**, giúp chuyển từ câu
hỏi và tài liệu của khách hàng thành facts được xác nhận, nghiên cứu theo đúng
thời điểm, phép tính tái lập, bản tư vấn có căn cứ và quy trình phê duyệt có audit.

Sản phẩm không được định vị là chatbot biết mọi luật. Đơn vị giá trị là một kết
quả chuyên môn có thể kiểm tra và tiếp tục xử lý: câu trả lời có nguồn, case có
trạng thái, memo đã duyệt, calculation trace hoặc cảnh báo thay đổi có owner.

### 2.1 Nguyên tắc sản phẩm

1. **Case trước, chat sau:** trao đổi quan trọng phải thuộc case hoặc research run.
2. **Nguồn cạnh kết luận:** mỗi claim pháp lý mở được đúng nguồn và đúng đoạn.
3. **Đúng thời điểm:** luôn tách ngày hỏi, ngày sự kiện, kỳ thuế và knowledge time.
4. **AI đề xuất, con người xác nhận:** fact, issue, impact và tư vấn case không tự
   chuyển thành dữ liệu cuối cùng chỉ vì mô hình tự tin.
5. **Phép tính xác định:** tiền thuế, thời hạn và bảng điều kiện trong phạm vi phải
   dùng rule có phiên bản, không lấy số do LLM tự tính.
6. **Không đủ thì dừng:** thiếu căn cứ hoặc dữ kiện trọng yếu dẫn đến hỏi lại,
   trả lời có điều kiện hoặc chuyển chuyên gia.
7. **Mọi thay đổi truy vết được:** source, corpus, model, prompt, rule, người sửa và
   phê duyệt phải tái tạo được tại phiên bản đầu ra.

## 3. Người dùng, persona và JTBD

### P-01 Chuyên gia tư vấn thuế

- **Bối cảnh:** xử lý nhiều câu hỏi VAT/hóa đơn, nguồn phân tán, thường phải tạo
  memo hoặc email cho khách hàng.
- **JTBD:** Khi nhận một case có tài liệu và thời điểm cụ thể, tôi muốn nhanh chóng
  hình thành facts, issues, căn cứ và phép tính có thể kiểm tra để dành thời gian
  cho phán đoán chuyên môn thay vì thao tác lặp lại.
- **Tiêu chí giá trị:** giảm thời gian tới bản nháp có nguồn mà không tăng sửa lỗi
  trọng yếu sau review.

### P-02 Reviewer/partner

- **Bối cảnh:** chịu trách nhiệm cuối, khó thấy người soạn hoặc AI đã dựa vào gì.
- **JTBD:** Khi duyệt một tư vấn, tôi muốn xem diff, claim-source, giả định, xung
  đột và calculation trace tại một nơi để quyết định approve/return có căn cứ.
- **Tiêu chí giá trị:** giảm thời gian review, phát hiện lỗi trước khi phát hành,
  không làm mất trách nhiệm hoặc quyền kiểm soát.

### P-03 Bộ phận thuế/kế toán doanh nghiệp

- **Bối cảnh:** câu hỏi, tài liệu, deadline và ý kiến tư vấn nằm ở nhiều công cụ.
- **JTBD:** Khi phát sinh giao dịch hoặc thay đổi luật, tôi muốn tập trung hồ sơ,
  theo dõi trách nhiệm và biết việc nào cần chuyển chuyên gia.
- **Tiêu chí giá trị:** giảm cycle time, ít bỏ lỡ deadline, alert có hành động.

### P-04 Knowledge admin

- **Bối cảnh:** theo dõi nguồn mới, kiểm tra parser, liên kết sửa đổi, rule và mẫu.
- **JTBD:** Khi nguồn luật thay đổi, tôi muốn xác nhận diff và dependency, chạy
  regression rồi phát hành/rollback một corpus release có kiểm soát.
- **Tiêu chí giá trị:** rút ngắn thời gian từ phát hiện đến phát hành đã duyệt và
  bao phủ đầy đủ các tài sản bị ảnh hưởng.

### P-05 Compliance/audit admin

- **Bối cảnh:** cần kiểm tra truy cập, dữ liệu, model/rule release và quyết định.
- **JTBD:** Khi có sự cố hoặc yêu cầu kiểm toán, tôi muốn tái tạo ai đã làm gì,
  trên dữ liệu và phiên bản nào, mà không phải mở quyền nội dung quá mức cần thiết.
- **Tiêu chí giá trị:** audit đầy đủ, truy xuất có kiểm soát, bằng chứng không sửa.

### P-06 Khách hàng doanh nghiệp

- **Bối cảnh:** không trực tiếp dùng công cụ nghiên cứu; nhận đầu ra do chuyên gia
  chia sẻ.
- **JTBD:** Khi nhận tư vấn, tôi muốn hiểu kết luận, điều kiện, việc cần làm và có
  thể mở căn cứ được phép xem.
- **Giới hạn:** chỉ thấy bản đã duyệt và dữ liệu được chủ case chia sẻ.

## 4. Mục tiêu và không phải mục tiêu

### 4.1 Mục tiêu MVP

- `G-001` Cho phép tra cứu VAT/hóa đơn theo `event_date` và mở chính xác căn cứ chính thức.
- `G-002` Xử lý một case từ intake, tài liệu, fact, issue, nghiên cứu, calculator đến memo.
- `G-003` Buộc duyệt người đối với tư vấn case và mọi deliverable ra ngoài tổ chức.
- `G-004` Hỗ trợ so sánh phiên bản quy định và đánh dấu tài sản stale khi nguồn đổi.
- `G-005` Chứng minh độ tin cậy bằng benchmark, audit và workflow, không bằng nhãn phần
  trăm tự tin do mô hình tạo.
- `G-006` Đạt trải nghiệm desktop cho công việc sâu; mobile dùng được cho tra cứu, trạng
  thái, cảnh báo và phê duyệt ngắn.

### 4.2 Không phải mục tiêu MVP

- Bao phủ CIT, PIT, hải quan hoặc mọi ngành trước khi VAT/hóa đơn đạt release gate.
- Tự nộp tờ khai, thanh toán, gửi cơ quan nhà nước hoặc đại diện tranh chấp.
- Phát hành tư vấn case trực tiếp cho công chúng mà không có chuyên gia kiểm soát.
- Xây foundation model, fine-tune để ghi nhớ luật hoặc dùng model memory làm căn cứ.
- Dùng multi-agent tự do, community GraphRAG hoặc graph database chỉ để quảng bá.
- Thay thế DMS, ERP, phần mềm kế toán hoặc hệ thống quản lý văn phòng toàn diện.
- Tự suy luận cấu trúc tránh/trốn thuế, che giấu giao dịch hoặc sửa chứng cứ.

## 5. Phạm vi phát hành

| Năng lực | MVP professional | Sau MVP | Ngoài phạm vi hiện tại |
|---|---|---|---|
| Authority Q&A | VAT/hóa đơn, theo ngày, nguồn chính thức | CIT/PIT sau benchmark riêng | hỏi mọi luật không giới hạn |
| Case workspace | facts, issues, timeline, documents, analysis | case template theo ngành | case litigation đầy đủ |
| Document intelligence | PDF/HTML, fact extraction có span | bảng lớn, email/DMS | tự coi extraction là fact xác nhận |
| Retrieval | lexical + dense + filter + rerank | late interaction khi có lợi | web mở làm nguồn kết luận |
| Legal graph | cạnh chuẩn tắc đã duyệt, 1-2 hop | graph projection chuyên dụng | graph do LLM tạo làm thẩm quyền |
| Research | state machine có budget và review | durable workflow quy mô lớn | agent tự do không điểm dừng |
| Calculator | 5-10 rule VAT/hóa đơn có test | decision table/policy simulation | LLM tính số cuối |
| Deliverable | memo/email, version, review, export | Word add-in/client portal mở rộng | tự gửi ra ngoài |
| Change intelligence | nguồn, diff, stale, task nội bộ | subscription theo profile | tự công bố impact chưa duyệt |
| Admin | tenant, role, matter access, audit | SAML/SCIM nâng cao | cross-tenant knowledge mặc định |

## 6. Yêu cầu chức năng

`P0` là bắt buộc cho professional MVP; `P1` có thể vào sau khi vertical slice ổn
định; `P2` là giả thuyết cần nghiên cứu. Acceptance chi tiết nằm trong use case.

| ID | Mức | Yêu cầu | Điều kiện chính |
|---|---|---|---|
| FR-001 | P0 | Xác thực người dùng và chọn đúng tenant | MFA/SSO theo policy; không mang cache giữa tenant |
| FR-002 | P0 | Phân quyền theo role và membership của case | default deny; filter trước mọi search/vector/object access |
| FR-003 | P0 | Tạo, cập nhật, lưu trữ và phân công case | có client, tax domain, event/period, owner, sensitivity, status |
| FR-004 | P0 | Thu thập intake có cấu trúc và save draft | câu hỏi có lý do; required/optional; consent/purpose |
| FR-005 | P0 | Tải và quản lý tài liệu case | scan file; version; hash; trạng thái parse; provenance |
| FR-006 | P0 | Trích fact và timeline kèm source span | output là `proposed`; không tự thành `confirmed` |
| FR-007 | P0 | Cho phép xác nhận, sửa, bác bỏ fact/assumption | ghi người, thời gian, lý do; invalidation có phạm vi |
| FR-008 | P0 | Đề xuất và quản lý issue tree | issue có trạng thái, owner, materiality và dependency |
| FR-009 | P0 | Hỏi pháp luật theo ngày và miền thuế | không im lặng mặc định event date khi có thể đổi kết quả |
| FR-010 | P0 | Trả lời theo answer contract có cấu trúc | kết luận, phạm vi, facts, assumptions, claims, nguồn, rủi ro |
| FR-011 | P0 | Mở citation tới đúng snapshot và exact span | hiện authority, hiệu lực, hash và quan hệ pháp lý |
| FR-012 | P0 | Tìm kiếm lai có lọc thẩm quyền/thời gian/tenant | corpus release và query parameters được lưu audit |
| FR-013 | P0 | Mở rộng cạnh pháp lý có giới hạn | chỉ edge được chấp nhận; giới hạn type/depth |
| FR-014 | P0 | So sánh hai phiên bản điều khoản | structural diff, semantic label, transition, exact spans |
| FR-015 | P0 | Chạy research nhiều bước có progress | queued/running/needs_input/needs_review/failure/completed |
| FR-016 | P0 | Pause, resume, cancel và retry research có kiểm soát | checkpoint; idempotency; không nhân đôi artefact |
| FR-017 | P0 | Hiển thị claim-evidence matrix và nguồn bất lợi | claim không nguồn hoặc hỗ trợ một phần phải có cờ |
| FR-018 | P0 | Chạy calculator theo rule có phiên bản | typed input, units, steps, warnings, reproducible result |
| FR-019 | P0 | So sánh scenario calculation | cùng rule release hoặc nêu rõ khác phiên bản |
| FR-020 | P0 | Tạo draft memo/email từ dữ liệu đã kiểm chứng | không ghép raw model output vào deliverable |
| FR-021 | P0 | Version và diff draft | mọi edit sau approve tạo version cần duyệt lại |
| FR-022 | P0 | Submit, assign, return và approve review | reviewer đủ quyền; comment/flag; chữ ký phiên bản |
| FR-023 | P0 | Chặn phát hành khi gate không đạt | xung đột, citation hỏng, thiếu fact, rule lỗi hoặc review thiếu |
| FR-024 | P0 | Xuất bản đã duyệt và audit bundle | watermark bản nháp; export có source/corpus/rule metadata |
| FR-025 | P1 | Chia sẻ có hạn qua client portal | chỉ approved version; expiry; revoke; download policy |
| FR-026 | P0 | Tiếp nhận nguồn luật vào quarantine | snapshot bất biến; hash; parser/OCR QA; không tự publish |
| FR-027 | P0 | Curator xác nhận metadata, cấu trúc và legal edge | dual control cho thay đổi trọng yếu |
| FR-028 | P0 | Tạo, kiểm thử, publish và rollback corpus release | atomic release; regression gate; invalidation event |
| FR-029 | P1 | Phân loại diff và đề xuất dependency bị tác động | proposal có exact changed span, không tự là kết luận |
| FR-030 | P1 | Đánh dấu stale và tạo impact/review task | owner, severity, SLA, reason, dependency path |
| FR-031 | P1 | Subscription/cảnh báo thay đổi theo case/profile | dedupe; materiality; kênh/chu kỳ do user chọn |
| FR-032 | P0 | Quản lý user, role, matter membership và ethical wall | thay quyền có hiệu lực với session/cache/stream/download grant |
| FR-033 | P0 | Lưu và tra cứu audit event bất biến | actor, action, object, version, outcome, correlation ID |
| FR-034 | P0 | Cấu hình retention, legal hold và xóa theo workflow | không xóa artefact đang hold; mọi thao tác có audit |
| FR-035 | P0 | Abstain, hỏi lại hoặc chuyển chuyên gia theo policy | lý do cụ thể; không hoàn thiện bằng model memory |
| FR-036 | P0 | Thu feedback ở cấp claim/citation/workflow | không dùng thumbs-up làm bằng chứng đúng duy nhất |
| FR-037 | P0 | Dashboard công việc theo quyền | near-deadline, review, stale/impact, job health |
| FR-038 | P1 | Evidence grid rà nhiều tài liệu | provenance từng ô; review/lock/comment; virtualized table |
| FR-039 | P1 | Hỏi trong một tài liệu với scope khóa | không dùng nguồn ngoài trừ khi user bật rõ ràng |
| FR-040 | P1 | Tìm case tương tự trong phạm vi được phép | filter quyền trước retrieval; không lộ client/fact khác |

## 7. Yêu cầu phi chức năng

Các mã này là contract sản phẩm; kiến trúc và test plan phải chi tiết hóa cách đo.

| ID | Nhóm | Mục tiêu nghiệm thu MVP |
|---|---|---|
| NFR-001 | Độ tin cậy | 0 citation bịa/không mở được trên benchmark khóa; output bị chặn nếu anchor lỗi |
| NFR-002 | Đúng thời điểm | 100% đúng provision version trên tập historical/transition đã khóa |
| NFR-003 | Calculation | 100% exact match cho rules/deadlines deterministic trong phạm vi |
| NFR-004 | Retrieval | R1 alpha: controlling-provision Recall@20 >=95% và citation-support precision >=98%; R2 professional beta: tương ứng >=97% và >=99%, xác nhận lại sau baseline nhưng mọi thay đổi phải qua risk acceptance |
| NFR-005 | Tenant isolation | 100% kiểm thử isolation pass ở DB/search/vector/object/cache; default deny |
| NFR-006 | Bảo mật | không còn finding critical/high; upload và prompt-injection controls vượt gate |
| NFR-007 | Hiệu năng | page/source p95 <2s khi sẵn dữ liệu; quick research p95 <10s; trạng thái bền vững/progress đầu tiên <1s; độ trễ event tiếp theo đo riêng |
| NFR-008 | Workflow dài | background sau 10s; resume/retry; không mất confirmed edit hoặc duplicate side effect |
| NFR-009 | Khả dụng | pilot target 99,5%; health, backup và restore drill trước mở pilot |
| NFR-010 | Audit | tái tạo được 100% high-impact output từ snapshot/release/rule/model/prompt/tool metadata |
| NFR-011 | Accessibility | WCAG 2.2 AA cho workflow chính; keyboard, zoom 400%, screen reader và axe test |
| NFR-012 | Privacy | dữ liệu tối thiểu, retention/hold/delete; không prompt/file thô trong analytics/log chung |
| NFR-013 | Tính nhất quán | command idempotent; publish corpus atomic; stale/invalidation có eventual SLA đo được |
| NFR-014 | Khả năng quan sát | correlation xuyên request/job/model/tool; redaction trước telemetry; alert theo SLO |
| NFR-015 | Khả năng bảo trì | modular monolith, contract typed, migration/rebuild projection và rollback được kiểm thử |
| NFR-016 | Khả năng dùng | median task completion và error rate của workflow chính đạt baseline pilot đã chốt |
| NFR-017 | Địa phương hóa | tiếng Việt là locale gốc; ngày tuyệt đối; tìm kiếm không làm hỏng dấu/tên văn bản |
| NFR-018 | Chi phí | budget theo tenant/run/model; cảnh báo và hard cap; báo cost per approved matter |

## 8. Workflow sản phẩm cốt lõi

### WF-001 Tra cứu nhanh có căn cứ

`Câu hỏi -> intent/risk -> event date -> temporal filter -> hybrid retrieval ->
claim draft -> citation/time/conflict checks -> answer hoặc abstain -> feedback/audit`.

### WF-002 Giải quyết case

`Tạo case -> intake/upload -> proposed facts -> user confirm -> issue tree ->
research/calculation -> draft -> verifier/policy gate -> review -> export/share`.

### WF-003 Cập nhật luật

`Discover -> quarantine snapshot -> parse/OCR -> metadata/structure/edge review ->
diff -> regression -> atomic publish -> invalidate -> stale/impact tasks`.

### WF-004 Duyệt và phát hành

`Submit version -> reviewer checks facts/time/sources/calculation/risk -> return
hoặc approve -> immutable approval -> export -> revoke/stale nếu dependency đổi`.

Chi tiết happy path và lỗi nằm trong [02-use-cases.md](02-use-cases.md).

## 9. Quy tắc nghiệp vụ

| ID | Quy tắc |
|---|---|
| BR-001 | Mỗi nghiệp vụ thuộc đúng một tenant; quyền tenant không thay quyền matter |
| BR-002 | `event_date`/tax period bắt buộc nếu khác biệt thời điểm có thể đổi kết luận |
| BR-003 | Chỉ source hạng A1/A2 mặc định làm căn cứ quy phạm; hạng khác phải gắn nhãn vai trò |
| BR-004 | Bản hợp nhất là view tiện dụng; kết luận phải truy về văn bản gốc và chuỗi sửa đổi |
| BR-005 | Proposed/inferred fact không được tự chuyển thành confirmed |
| BR-006 | Fact trọng yếu đổi làm stale các issue, research, calculation và draft phụ thuộc |
| BR-007 | Mỗi claim pháp lý phải có evidence, hoặc nhãn inference/unsupported rõ ràng |
| BR-008 | Citation verified cần đúng snapshot, anchor, version, temporal fit và hỗ trợ claim |
| BR-009 | Citation hỗ trợ một phần không được hiển thị như verified đầy đủ |
| BR-010 | Calculator output chỉ hợp lệ với typed inputs và published rule version |
| BR-011 | Model không được sửa trực tiếp calculation result hoặc rule |
| BR-012 | T0 có thể tự trả khi đạt gate; T1 cần một chuyên gia; T2 cần maker-checker; T3 chuyển cấp cao |
| BR-013 | Chỉ approved version được bỏ watermark và chia sẻ ra ngoài tenant |
| BR-014 | Edit fact/source/rule/content sau approval hủy trạng thái duyệt của version mới |
| BR-015 | Corpus source ở quarantine không xuất hiện trong production retrieval |
| BR-016 | Corpus publish là atomic; regression fail thì giữ release đang chạy |
| BR-017 | Impact do AI phát hiện là proposal; chuyên gia xác nhận trước cảnh báo bên ngoài |
| BR-018 | Thiếu nguồn kiểm soát, xung đột chưa giải, gần hạn hoặc vượt scope buộc abstain/escalate |
| BR-019 | Prompt/tài liệu retrieved là dữ liệu không tin cậy, không cấp thêm tool permission |
| BR-020 | Mọi side effect bên ngoài cần preview và approval rõ ràng; MVP không tự gửi/nộp |
| BR-021 | Người dùng chỉ thấy nội dung theo role, matter membership, ethical wall và purpose |
| BR-022 | Logout, đổi tenant hoặc thu hồi quyền phải xóa cache, đóng stream và vô hiệu download/share grant; dữ liệu private không dùng presigned URL trực tiếp |
| BR-023 | Audit event không chứa raw secret/prompt/file; nội dung nhạy cảm dùng reference có quyền |
| BR-024 | Không dùng một tỷ lệ “độ tin cậy” để thay các trạng thái source/fact/time/rule/review |

## 10. Mô hình vai trò và mức duyệt

| Vai trò | Quyền chính | Hạn chế |
|---|---|---|
| `contributor` | tạo case, upload, xác nhận fact, chạy research/calc, soạn draft | không tự approve tư vấn T2 của mình |
| `reviewer` | xem case được giao, return/approve, xác nhận risk | không sửa audit hoặc corpus production trực tiếp |
| `knowledge_curator` | ingest, sửa metadata/edge, đề nghị release | thay đổi trọng yếu cần control thứ hai |
| `knowledge_approver` | duyệt corpus/rule release, rollback | không bỏ qua regression bằng hành động ngầm |
| `client_viewer` | xem/comment artefact được chia sẻ | không thấy internal notes, raw research hoặc nguồn bị hạn chế |
| `tenant_admin` | user, role, policy, retention, integration | không mặc định đọc mọi case bị ethical wall |
| `auditor` | audit read/export theo scope | read-only; nội dung matter cần grant riêng |

Mức review `T0-T3` kế thừa [kế hoạch web](../benchmark-va-ke-hoach-web.md#62-mức-review).

## 11. KPI và đo lợi ích

Không công bố ROI trước khi đo baseline cùng loại case, cùng mức review.

### 11.1 Chất lượng và độ tin cậy

- tỷ lệ đúng kết luận theo rubric chuyên gia và theo severity;
- citation existence, temporal fit, support, completeness và open-to-span rate;
- controlling provision/exception/transition recall;
- exact calculation rate; false-accept và selective accuracy;
- lỗi trọng yếu lọt qua review, correction/recall sau phê duyệt;
- tỷ lệ draft bị stale sau corpus/rule/fact update.

### 11.2 Trải nghiệm

- median/p90 time-to-first-sourced-draft theo case type;
- median thời gian review một claim và một memo;
- số vòng hỏi lại do thiếu fact; task completion và abandonment;
- tỷ lệ click citation, xác nhận/correct fact, return-with-reason;
- accessibility task success; error recovery và resume success.

### 11.3 Vận hành và giá trị

- giờ thực tiết kiệm **sau review**; số case hoàn thành trên mỗi chuyên gia;
- detection-to-reviewed-publication và impacted-asset coverage;
- alert action rate, duplicate/noise rate và missed material change;
- cost per quick answer, research run và approved matter;
- SLA review, update latency, rollback success và support incidents.

### 11.4 Tiêu chí thành công pilot

Pilot thành công khi release gates tại mục 7 đạt, tổng thời gian từ intake đến
approved deliverable giảm có ý nghĩa so với baseline, lỗi trọng yếu không tăng,
reviewer chấp nhận workflow và audit có thể tái tạo mọi output mẫu.

## 12. Rollout và cổng phát hành

### R0: Vertical slice nội bộ

- Một tenant giả lập, 20-30 tình huống VAT/hóa đơn, 1-2 rules.
- Hoàn thành UC-002, UC-004..UC-010 và UC-018 trên đường đi chuẩn.
- Không dùng dữ liệu khách hàng thật; security/isolation test bắt đầu từ đây.

### R1: Internal alpha

- Corpus được curator quản lý, 100+ test cases, maker-checker review.
- 5-10 rules, ingestion/quarantine/release và stale flow hoạt động.
- Đạt gate NFR-004 alpha: Recall@20 >=95% và citation-support precision >=98%.
- Chỉ chuyên gia nội bộ; tất cả đầu ra là draft.

### R2: Professional pilot

- 2-3 tổ chức/nhóm được chọn; tenant isolation, privacy và incident runbook đạt gate.
- Benchmark 300+ case đã adjudicate; canary model/corpus không tự phát hành ngoài.
- Đạt tối thiểu Recall@20 >=97% và citation-support precision >=99% trên benchmark
  khóa; ngưỡng được hiệu chuẩn theo severity/baseline, không hạ âm thầm theo average.
- Theo dõi KPI theo cohort và case type ít nhất 6-8 tuần.

### R3: General professional availability

- Chỉ sau legal review về dịch vụ, AI risk, dữ liệu, nguồn và điều khoản sử dụng.
- SLO/on-call/support/recall vận hành; onboarding và content owner rõ ràng.
- Client portal chỉ mở khi sharing, revoke, export và access audit vượt test.

Rollback ngay nếu có cross-tenant leak, source/corpus corruption, sai calculation
trọng yếu có hệ thống hoặc citation resolver không mở được snapshot production.

## 13. Giả định và quyết định còn mở

### 13.1 Giả định đang dùng

- Người dùng chính là chuyên gia B2B; khách hàng không nhận raw AI answer.
- Có quyền hợp pháp để thu thập/lưu/hiển thị lại nguồn trong corpus pilot.
- Chuyên gia VAT/hóa đơn có thể tạo và adjudicate benchmark liên tục.
- MVP chạy modular monolith; search/graph là projection tái tạo được.
- Mô hình được gọi qua adapter và hợp đồng dữ liệu không train/retention phù hợp.

### 13.2 Quyết định phải đóng trước pilot

| ID | Quyết định | Bằng chứng cần có |
|---|---|---|
| OD-001 | Ranh giới dịch vụ pháp lý và ai chịu trách nhiệm duyệt | legal opinion và operating model |
| OD-002 | Phân loại/ràng buộc hệ thống AI | classification/impact assessment trên hành vi thật |
| OD-003 | Nguồn nào được crawl, lưu và cung cấp lại | terms/license/API agreement |
| OD-004 | Data residency, model/OCR/IAM provider | customer tier, DPA, threat/cost benchmark |
| OD-005 | Giá: seat, approved matter hay enterprise | pilot usage/value/cost; không tính token cho user |
| OD-006 | Ngưỡng materiality và deadline escalation | policy do chuyên gia phê duyệt |
| OD-007 | Khi nào thêm Neo4j, Temporal, DMN/self-host model | benchmark/SLO/operating evidence |
| OD-008 | Retention, legal hold và recall communication | privacy/legal/business impact analysis |

## 14. Nghiệm thu sản phẩm

Một MVP không được coi là hoàn thành chỉ vì UI chạy. Nghiệm thu yêu cầu:

1. UC-001..UC-018 có test happy path, permission và lỗi trọng yếu; các UC P0 đạt.
2. FR-001..FR-040 có ma trận truy vết tới use case, screen, API, data và test.
3. NFR-001..NFR-018 có phương pháp đo, owner và evidence từ môi trường release.
4. Demo dọc chứng minh event-date retrieval, exact citation, confirmed fact,
   deterministic calculation, reviewer approval, export và stale-after-change.
5. Tenant B không đọc/tìm/download được artefact, vector hoặc audit của tenant A.
6. Hệ thống dừng với lý do cụ thể khi thiếu fact/source hoặc có conflict.
7. Chuyên gia có thể tái tạo output từ corpus/model/rule/prompt/tool snapshot.
8. Accessibility, keyboard, reflow, loading/error/empty và recovery flows được test.
9. Không còn finding critical/high; rollback corpus và incident drill hoàn thành.
10. Legal/compliance approvals cho đúng rollout stage đã được ghi nhận.

Ma trận nghiệm thu chi tiết tiếp tục tại [02-use-cases.md](02-use-cases.md) và
[03-interface-design.md](03-interface-design.md).
