# Thiết kế giao diện: Tax Legal Workspace

**Phiên bản:** 0.1  
**Phạm vi:** professional web MVP, B2B VAT/hóa đơn  
**Yêu cầu:** [01-product-requirements.md](01-product-requirements.md)  
**Use case:** [02-use-cases.md](02-use-cases.md)

## 1. Mục tiêu trải nghiệm

Giao diện phải giúp chuyên gia đi từ dữ kiện đến đầu ra đã duyệt mà luôn thấy:

- đang làm trong tenant/case nào và dữ liệu có mức nhạy cảm nào;
- ngày nào quyết định luật áp dụng;
- đâu là fact đã xác nhận, fact đề xuất, giả định hoặc xung đột;
- claim nào được nguồn nào hỗ trợ, ở phiên bản và đoạn nào;
- phép tính nào đến từ rule có phiên bản;
- còn blocker gì, ai cần xử lý và đầu ra đã được duyệt hay chưa.

UI không hiển thị chain-of-thought, scratchpad hoặc token stream nội bộ. Chỉ hiển
thị kế hoạch công việc, tool/status, dữ kiện, nguồn, các bước rule, kiểm tra và lý
do nghiệp vụ có thể audit.

### 1.1 Nguyên tắc

1. **Desktop-first cho công việc sâu:** case, evidence grid, compare và review cần
   chiều ngang; mobile tập trung lookup, trạng thái, alert và quyết định ngắn.
2. **Source-first:** citation mở cạnh claim; không đưa user ra tab khác để tự tìm.
3. **Dense nhưng có thứ bậc:** dùng bảng, split pane và toolbar; không biến từng
   section thành card nổi hoặc đặt card trong card.
4. **Stable layout:** panel, grid, toolbar, icon button có kích thước ổn định;
   loading/dynamic content không làm nhảy bố cục.
5. **Progressive disclosure:** kết luận/action trước; evidence, metadata, checks và
   audit mở theo nhu cầu.
6. **Trust là trạng thái kiểm tra:** không hiển thị một phần trăm confidence chung.
7. **Sửa được và hồi phục được:** autosave, undo cho edit local phù hợp, version/diff,
   retry/resume; destructive command có preview/confirmation.
8. **Quyền nhìn thấy được:** tenant, classification, sharing và approved/stale luôn
   ở vùng header; nhưng server vẫn là nơi enforce quyền.

## 2. Kiến trúc thông tin

```text
Tax Legal Workspace
|-- Dashboard
|-- Tra cứu
|   |-- Tra cứu mới
|   |-- Research run
|   `-- Nguồn / So sánh phiên bản
|-- Cases
|   |-- Tổng quan
|   |-- Intake & facts
|   |-- Tài liệu & evidence
|   |-- Issues
|   |-- Phân tích
|   |-- Calculations
|   |-- Deliverables
|   `-- Activity
|-- Reviews
|-- Thay đổi pháp luật
|-- Quản trị tri thức        [knowledge roles]
`-- Quản trị tổ chức
    |-- Người dùng & quyền   [tenant admin]
    `-- Audit               [auditor/admin]
```

### 2.1 Điều hướng toàn cục

- **Desktop >=1280 px:** rail trái rộng 240 px; có thể thu về 64 px bằng icon;
  top bar cao 56 px; work area dùng toàn bộ phần còn lại.
- **Tablet 768-1279 px:** rail mặc định thu gọn; secondary navigation thành tab
  ngang cuộn được; source drawer overlay hoặc split 42% khi đủ rộng.
- **Mobile <768 px:** bottom navigation chỉ gồm Dashboard, Tra cứu, Cases, Công
  việc; menu Tài khoản chứa phần còn lại theo quyền. Editor/grid sâu chuyển sang
  chế độ read/review từng mục, không cố mô phỏng desktop ba cột.
- Tenant switcher luôn có tên tenant và icon; classification dùng icon + text,
  không chỉ màu. Chuyển tenant yêu cầu loading boundary và clear cache.

## 3. Route map và screen registry

| ID | Route | Tên màn hình | Actor/use case chính |
|---|---|---|---|
| SCR-001 | `/auth/sign-in` | Đăng nhập/chọn tenant | UC-001 |
| SCR-002 | `/dashboard` | Dashboard công việc | UC-001, UC-012 |
| SCR-003 | `/research/new` | Tra cứu mới | UC-002, UC-018 |
| SCR-004 | `/research/:runId` | Research run/answer viewer | UC-002, UC-007, UC-017, UC-018 |
| SCR-005 | `/matters` | Danh sách case | UC-004 |
| SCR-006 | `/matters/:matterId/overview` | Tổng quan case | UC-004 |
| SCR-007 | `/matters/:matterId/facts` | Smart intake, facts và timeline | UC-005, UC-006 |
| SCR-008 | `/matters/:matterId/documents` | Tài liệu và evidence grid | UC-005 |
| SCR-009 | `/matters/:matterId/issues` | Issue tree | UC-006, UC-007 |
| SCR-010 | `/matters/:matterId/analysis` | Phân tích case | UC-007, UC-009, UC-017, UC-018 |
| SCR-011 | `/matters/:matterId/calculations` | Calculator/scenarios | UC-008 |
| SCR-012 | `/matters/:matterId/deliverables` | Memo, version và export | UC-009, UC-011 |
| SCR-013 | `/sources/:snapshotId?anchor=:anchorId` | Source viewer | UC-002, UC-003, UC-005, UC-010 |
| SCR-014 | `/provisions/:provisionId/compare?from=&to=` | So sánh phiên bản | UC-003 |
| SCR-015 | `/reviews` | Review queue | UC-010, UC-018 |
| SCR-016 | `/reviews/:reviewId` | Review detail | UC-010 |
| SCR-017 | `/changes` | Change center | UC-012, UC-014 |
| SCR-018 | `/changes/:changeId` | Change/impact detail | UC-012..UC-014 |
| SCR-019 | `/admin/knowledge` | Knowledge admin | UC-013 |
| SCR-020 | `/admin/security` | User, quyền và policy | UC-015 |
| SCR-021 | `/admin/audit` | Audit explorer | UC-016 |
| SCR-022 | `/portal/deliverables/:shareId` | Bản tư vấn chia sẻ | UC-011 |

Route là định danh UI, không phải security boundary. Mọi loader/action phải nhận
authorization decision từ API; route không được preload dữ liệu khi user chưa có
matter membership.

## 4. App shell và component nền

### 4.1 App shell desktop

```text
+------------------------+-----------------------------------------------------+
| Logo  [Tenant v]       | Breadcrumb                 [Search] [?] [User v]    |
|------------------------+-----------------------------------------------------|
| Dashboard              | Context header: title | status | date | owner       |
| Tra cứu                |-----------------------------------------------------|
| Cases                  |                                                     |
| Reviews          (3)   |                 Route content                       |
| Thay đổi         (7)   |                                                     |
|                        |                                                     |
| ---------------------- |                                                     |
| Quản trị (theo quyền)  |                                                     |
+------------------------+-----------------------------------------------------+
```

### 4.2 Thành phần dùng chung

| Component ID | Thành phần | Quy tắc |
|---|---|---|
| CMP-001 | `ContextHeader` | title 1 dòng ưu tiên, wrap tối đa 2; status/date/owner không che action |
| CMP-002 | `CommandBar` | command chính bên trái; icon quen thuộc dùng Lucide + tooltip; không dùng text pill giả button |
| CMP-003 | `StatusBadge` | icon + text + semantic color; fixed min-height; không chỉ dùng màu |
| CMP-004 | `DateScopeControl` | event date/tax period/knowledge snapshot; absolute format; warning nếu unknown |
| CMP-005 | `CitationMarker` | số ổn định theo answer version; focus/click liên kết claim và source anchor |
| CMP-006 | `SourceDrawer` | resizable 360-640 px; focus trap khi overlay; nhớ kích thước theo user preference không chứa matter data |
| CMP-007 | `FactRow` | value, status, date, evidence, materiality, actions; edit không làm lệch grid |
| CMP-008 | `IssueTree` | tree keyboard pattern; status/owner/materiality; drag chỉ là tiện ích, có menu thay thế |
| CMP-009 | `JobProgress` | step labels, counts, budget, timestamps, pause/cancel/retry; không spinner vô hạn |
| CMP-010 | `ClaimBlock` | proposition, conclusion type, citations, flags, edit history; không lộ hidden reasoning |
| CMP-011 | `CalculationTrace` | inputs, units, rule, steps, rounding, result; result read-only |
| CMP-012 | `ReviewChecklist` | required checks, blocker links, signer; cannot collapse unresolved blockers |
| CMP-013 | `EmptyState` | mô tả trạng thái + một command hợp lệ; không dùng hình trang trí |
| CMP-014 | `InlineError` | mã lỗi hữu ích, recovery action, correlation ID copy icon |
| CMP-015 | `DataTable` | sticky header, resize/virtualize, column visibility; mobile row view |
| CMP-016 | `DiffViewer` | before/after, structural path, semantic label, linked exact spans |
| CMP-017 | `PermissionLabel` | tenant/matter/share/sensitivity state ở header hoặc share dialog |
| CMP-018 | `ActivityTimeline` | actor/action/version/time; filter; content references theo quyền |

## 5. Đặc tả từng màn hình

### SCR-001 Đăng nhập/chọn tenant

- Dùng giao diện IdP theo branding tối thiểu; không có marketing hero.
- Sau xác thực, nếu một tenant thì chuyển thẳng; nếu nhiều tenant hiển thị list có
  tên tổ chức, vai trò và last-used time, không hiển thị dữ liệu case.
- Loading: skeleton 3 hàng cố định. Error: session/policy/MFA rõ hành động.
- Mobile/desktop cùng một cột, max-width 440 px; focus vào tiêu đề hoặc lỗi đầu.
- Acceptance: hoàn tất UC-001 bằng keyboard; back sau switch không lộ tenant cũ.

### SCR-002 Dashboard công việc

- Band đầu: việc cần xử lý hôm nay gồm deadline, review và impact task; không dùng
  KPI vanity hoặc banner chào mừng lớn.
- Hai vùng dưới: `Cases gần hạn/đang chạy` và `Thay đổi cần rà`; knowledge roles có
  thêm ingestion health dạng bảng nhỏ.
- Mỗi item hiển thị owner, due date tuyệt đối, state, blocker và one-click route.
- Empty: “Không có việc đến hạn trong phạm vi đang xem” + mở Cases/Tra cứu.
- Mobile: một feed ưu tiên theo severity/time; filter mở bottom sheet.

### SCR-003 Tra cứu mới

- Input câu hỏi ở vùng chính, không phải chat bubble; dưới là `DateScopeControl`,
  tax domain cố định VAT/hóa đơn, source scope và mức đầu ra.
- Gợi ý lịch sử chỉ trong tenant/user scope; không hiện câu hỏi người khác.
- Submit disabled kèm inline reason khi thiếu input bắt buộc; event date có lựa chọn
  `Chưa biết` nhưng hệ thống sẽ hỏi trước khi kết luận.
- Không dùng placeholder dài thay label. Cho phép paste text nhưng không đưa PII
  vào URL hoặc analytics.

### SCR-004 Research run/answer viewer

- Desktop dùng ba vùng: issue/mục lục 240-320 px; answer co giãn; source drawer
  360-640 px. Khi drawer đóng, marker vẫn keyboard reachable.
- Header hiện scope, event date, corpus snapshot, trạng thái run và review tier.
- Answer sections theo contract: Kết luận; facts/assumptions; issues; analysis;
  calculations; alternatives/risks; missing info; next actions; review.
- `JobProgress` thay answer khi queued/running nhưng giữ skeleton theo section để
  không nhảy layout. Partial output có nhãn rõ và không giống completed.
- `cannot_conclude` dùng panel trạng thái, danh sách thiếu và command Bổ sung/Chuyển
  chuyên gia; không dùng lỗi màu đỏ nếu đây là kết quả đúng của policy.

### SCR-005 Danh sách case

- Data table: case, client, domain, event/tax period, owner, status, due date, stale,
  updated. Default sort theo việc cần xử lý, filter state nằm trong URL không PII.
- Bulk action MVP chỉ assign/tag; export cần quyền riêng và confirmation.
- Search server-side theo quyền. Empty phân biệt “chưa có case” với “filter không có
  kết quả”. Mobile hiển thị row view, không cắt tên dài.

### SCR-006 Tổng quan case

- Context header cố định: client/case, sensitivity, status, owner, event date,
  `Bắt đầu/tiếp tục phân tích` và overflow menu.
- Progress band theo workflow: Intake -> Facts -> Research -> Draft -> Review ->
  Approved; đây là trạng thái, không phải wizard khóa điều hướng.
- Main: summary, blockers, near deadline, latest analysis/deliverable; side 320 px:
  members, activity, related changes.
- Mobile: header actions vào menu, workflow cuộn ngang có text accessible, side
  sections xuống dưới.

### SCR-007 Smart intake, facts và timeline

- Tabs trong route: `Intake`, `Facts`, `Timeline`, `Assumptions`; trạng thái lưu luôn
  thấy ở toolbar.
- Facts table không dùng confidence phần trăm; state là proposed/confirmed/rejected/
  conflict/missing, kèm evidence và materiality.
- Edit dùng side sheet có typed input, date/period, source, reason và impacts preview.
- Câu hỏi intake nêu lý do nghiệp vụ ngắn dưới label; required/optional rõ ràng.
- Mobile: từng fact là row expandable; confirm/reject dùng icon + text command,
  confirmation khi fact material.

### SCR-008 Tài liệu và evidence grid

- Khu upload là command rõ, không chiếm toàn viewport. Bảng document: filename,
  version, source type, date, parse/OCR status, facts count, access, actions.
- Evidence grid: document ở hàng, schema fact/issue ở cột, mỗi cell có provenance,
  review/lock/comment. Sticky first column; virtualization khi >100 rows.
- Parsing progress hiển thị stage; file lỗi vẫn có original/quarantine status.
- Mobile chỉ hỗ trợ document list, status, open source và review một extraction;
  evidence grid đầy đủ yêu cầu desktop và UI nói rõ bằng action “Mở trên desktop”,
  không bằng đoạn quảng bá.

### SCR-009 Issue tree

- Tree bên trái; detail bên phải gồm question, materiality, owner, status, facts,
  research runs, claims và blockers. Nút Thêm issue là command, AI proposals nằm
  trong inbox riêng để accept/edit/reject.
- Keyboard tree navigation đúng ARIA. Reorder có menu Up/Down làm phương án thay thế
  drag. Issue accepted không đồng nghĩa legal conclusion.
- Empty: tạo issue thủ công hoặc phân tích facts đã confirmed.

### SCR-010 Phân tích case

- Bố cục gần SCR-004 nhưng issue tree thuộc case và toolbar có Tạo draft.
- Claim blocks hiển thị conclusion type, source state, counter-authority, linked facts,
  calculation và reviewer comments. Edit proposition tạo version/audit.
- Source drawer ghim đồng thời tối đa hai nguồn để so; quá số đó dùng tab trong drawer.
- Long run hiển thị `JobProgress`; user có thể tiếp tục xem version trước trong khi
  version mới chạy, với nhãn rõ.
- Không hiển thị “AI đang suy nghĩ”; chỉ tên bước như Tìm nguồn, Kiểm tra thời điểm,
  Kiểm tra trích dẫn.

### SCR-011 Calculator và scenarios

- Trái 360 px: typed input form, fact links và validation; giữa: result/trace;
  phải: scenario list. Result dùng typography nhấn vừa phải, không kiểu hero.
- Rule version, effective interval và nguồn luôn thấy cạnh result. Input material
  cần checkbox/confirmation trước run.
- Compare table giữ cùng unit/rounding; khác rule version tạo warning không cho so
  như cùng cơ sở. Result read-only; sửa bằng input rồi tạo run mới.
- Mobile: input -> result -> trace theo step; scenario comparison chuyển row list.

### SCR-012 Deliverables

- List versions bên trái; editor/read view giữa; validation/review panel phải.
- Toolbar dùng icon quen thuộc cho undo/redo, bold/italic, link và comment với
  tooltip; commands Tạo bản, Gửi duyệt, Export dùng text rõ.
- Hiển thị các nhãn vòng đời `draft`, `ready_for_review`, `in_review`, `returned`,
  `approved`; `stale` là cờ chặn trực giao. Đây là presentation state được ánh xạ
  từ state backend tại mục 7.3, không phải enum để frontend tự ghi.
- Citation removal/update chạy validation và hiện blocker cạnh đoạn, không chỉ toast.
- Mobile là read/comment/approve-short; không cung cấp full rich editor nếu không
  đảm bảo fit và accessibility.

### SCR-013 Source viewer

- Hiển thị PDF/HTML/text snapshot; toolbar có page, find, zoom, download theo quyền,
  copy citation và compare version. Dùng Lucide icons + tooltip/accessible name.
- Metadata panel: instrument, authority class, issued/effective/expired dates,
  provision path, source URL, snapshot time/hash và legal relationships.
- Anchor có page + bbox + text offsets; khi mở từ citation, focus/highlight exact
  span và announce cho screen reader. OCR text layer không thay original.
- Nếu anchor chỉ hỗ trợ một phần claim, banner ghi `Hỗ trợ một phần`; source hạng
  thấp có label vai trò, không dùng màu trung tính dễ nhầm với primary authority.
- Snapshot unavailable là blocker; không tự redirect sang bản web có thể đã đổi.

### SCR-014 So sánh phiên bản

- Header chứa provision path và hai date/version selectors. Main split 50/50 có
  scroll đồng bộ tùy chọn; gutter hiển thị add/remove/change markers.
- Summary panel liệt kê semantic labels và transition, mỗi mục click tới diff hunk.
- Toggle chỉ gồm `Song song`/`Hợp nhất`; dùng segmented control. Whitespace-only
  changes có filter riêng nhưng không bị xóa khỏi audit.
- Mobile: từng hunk theo before rồi after, không dùng hai cột quá hẹp.

### SCR-015 Review queue

- Bảng theo priority/due/tier: deliverable/case, submitter, reviewer, blockers,
  age, stale. Saved views là option menu, không nhiều pill controls.
- Reviewer chỉ thấy queue được phép; manager assignment là command riêng.
- Empty phân biệt “không có việc” và “filter không khớp”. Near-deadline không nhấp
  nháy; dùng icon + text + màu có contrast.

### SCR-016 Review detail

- Desktop ba vùng: checklist/flags; exact draft diff; source/calculation panel.
- Sticky command bar: Return, Approve; Approve disabled nếu blocker, hover/focus
  giải thích và link tới blocker. Return yêu cầu reason và assignee.
- Checklist không tự tick vì AI score; verifier chỉ mở cờ/evidence cho người duyệt.
- Concurrent change dùng blocking dialog với version mới và command Reload/Compare.
- Mobile chỉ quick review cho thay đổi nhỏ; T2/T3 full memo có thể đọc nhưng approve
  yêu cầu checklist phù hợp, không ẩn nội dung quan trọng.

### SCR-017 Change center

- Tabs: `Cần xử lý`, `Đang theo dõi`, `Đã giải quyết`; filter theo effective date,
  domain, severity, owner và asset type.
- Mỗi row có instrument/change, effective date, changed provisions, impact count,
  owner/due/status. Alert phải trả lời “vì sao liên quan” và “việc gì tiếp theo”.
- Bulk assign/acknowledge không cho bulk-confirm legal impact.
- Mobile là prioritized task feed; semantic diff mở SCR-018 dạng hunk rows.

### SCR-018 Change/impact detail

- Header: source/release/effective date/status; main: structural/semantic diff;
  side: dependency tree và impact proposals.
- Dependency path hiện `change -> provision -> rule/template/draft/matter`; với
  restricted matter chỉ hiện opaque identifier/owner cho curator thiếu grant.
- Confirm/dismiss yêu cầu reason; confirm material impact tạo stale/task preview.
- Publish/rollback chỉ hiện cho knowledge approver và có regression evidence dialog.

### SCR-019 Knowledge admin

- Đây là platform control plane với session/audience/JIT role riêng; không xuất
  hiện chỉ vì user là tenant admin. Tenant knowledge overlay dùng màn hình và
  namespace riêng, không có lệnh publish corpus công cộng.
- Work queues: source discovery, quarantine, parser/OCR QA, duplicate/conflict,
  proposed edges, releases và regression. Đây là các bảng/console, không phải dashboard
  trang trí.
- Source detail đặt original cạnh parsed structure; curator sửa metadata/anchor bằng
  form typed và preview impact. Không có command “Đưa thẳng vào production”.
- Release page hiển thị manifest diff, test slices, failures, approvals, build state,
  publish/rollback. Command trọng yếu yêu cầu step-up và confirmation nhập release ID.
- Mobile chỉ theo dõi/assign; parse editing và publish yêu cầu desktop.

### SCR-020 User, quyền và policy

- Tabs: Users, Roles, Matter access, Ethical walls, Sessions, Retention, Data/model
  policy. Bảng hiển thị effective access và nguồn grant.
- Edit access dùng impact preview: session/cache/URL nào bị revoke, case nào mất owner.
- Không hiển thị secret; integration credential chỉ có rotate/revoke và last-used.
- Dangerous action ở menu riêng, confirmation nêu object cụ thể; không dùng màu đỏ
  cho mọi secondary action.

### SCR-021 Audit explorer

- Query builder có time range bắt buộc, actor/action/object/correlation/release;
  saved query chứa IDs/filters không chứa raw case text.
- Results là immutable timeline/table. Detail hiển thị event envelope và reference;
  nội dung matter chỉ resolve nếu user có grant.
- Export dialog preview scope, redaction, format, expiry; tiến độ job chạy nền.
- Không có edit/delete command. Search và export cũng xuất hiện trong audit.

### SCR-022 Client deliverable

- Brand tối thiểu theo tenant; tiêu đề, approved-by/time, scope/date, conclusion,
  conditions, actions và citations được phép. Không hiển thị internal flags/comments.
- Client có thể mở source nếu license/share policy cho phép, download theo grant và
  comment theo section. Link expired/revoked dùng trang chung không lộ case tồn tại.
- Mobile-first read view; heading/landmark rõ; table có row view/reflow.

## 6. Wireframes

Wireframe thể hiện cấu trúc, không quy định thẩm mỹ cuối cùng.

### 6.1 Dashboard desktop

```text
+------------+---------------------------------------------------------------+
| Navigation | Dashboard                              10/08/2026  [Filter v] |
|            |---------------------------------------------------------------|
| Dashboard  | VIỆC CẦN XỬ LÝ                                              |
| Tra cứu    | [2 review gần hạn] [3 impact task] [1 research cần input]     |
| Cases      |---------------------------------------------------------------|
| Reviews 3  | Cases gần hạn                 | Thay đổi cần rà                |
| Changes 7  | Case | Owner | Due | Blocker   | Văn bản | Hiệu lực | Owner     |
|            | ...                         | ...                             |
|            |---------------------------------------------------------------|
| Admin      | Job/ingestion health [chỉ vai trò phù hợp]                    |
+------------+---------------------------------------------------------------+
```

### 6.2 Tra cứu và source-first answer

```text
+------------------+------------------------------------+----------------------+
| Issues / mục lục | VAT đầu vào giao dịch X            | NGUỒN                |
|                  | Event: 01/07/2025  Corpus: CR-42   | Luật ...             |
| Kết luận         |------------------------------------| Điều 12, khoản 2      |
| Facts            | KẾT LUẬN CÓ ĐIỀU KIỆN             | Hiệu lực: ...         |
| Vấn đề 1         | Claim A [1] [Đã kiểm chứng nguồn]  |----------------------|
| Vấn đề 2         | Claim B [2] [Hỗ trợ một phần]      | exact highlighted     |
| Rủi ro           |                                    | source span           |
|                  | Facts / assumptions                |                      |
| Versions         | Analysis theo claim                | [Mở toàn trang]       |
+------------------+------------------------------------+----------------------+
```

### 6.3 Case workspace

```text
+------------+---------------------------------------------------------------+
| Navigation | Case VAT-024 | Nội bộ mật | Event 30/06/2025 | Owner [v]      |
|            | Intake > Facts > Research > Draft > Review > Approved         |
|------------+---------------------------------------------------------------|
| Overview Facts Documents Issues Analysis Calculations Deliverables Activity |
|----------------------------------------------------------------------------|
| BLOCKERS (2)                     | THÔNG TIN CASE                            |
| - Xác nhận ngày nghiệm thu       | Client / tax period / members            |
| - Nguồn [3] có xung đột          | Scope / sensitivity / purpose            |
|----------------------------------+------------------------------------------|
| Phân tích gần nhất               | Activity / related changes               |
| Claims: 8 | verified: 6 | flags:2| ...                                      |
+----------------------------------------------------------------------------+
```

### 6.4 Facts và evidence

```text
+----------------------+------------------------------------------------------+
| Facts | Timeline     | FACTS                          [Lọc] [+ Thêm fact]    |
|----------------------+------------------------------------------------------|
| Status   Fact        | Value       Date       Evidence         Materiality  |
| [Confirm] Loại HHDV  | Dịch vụ ... 30/06/...  Invoice p.2      Cao          |
| [Propose] Thanh toán | ...         15/07/...  Bank stmt p.1    Cao   [✓][x] |
| [Conflict] Ngày NT   | 2 giá trị              2 sources        Cao   [Mở]   |
|----------------------+------------------------------------------------------|
| Cần bổ sung: Địa điểm tiêu dùng   Lý do: quyết định phạm vi VAT             |
+----------------------------------------------------------------------------+
```

### 6.5 Calculator

```text
+------------------------+--------------------------------+--------------------+
| INPUT                  | KẾT QUẢ                        | SCENARIOS          |
| Giá trị [________] VND | 100.000.000 VND                | Base        active |
| Thuế suất [10% v]      | Rule VAT-R-07 v3              | Alternative        |
| Event date [__/__/__]  | Hiệu lực ... [Mở nguồn]       | [+ Nhân scenario]  |
| Nguồn fact [Case v]    |--------------------------------|                    |
|                        | Steps / rounding / warnings    | Compare            |
| [Chạy tính]            | 1. ...                         |                    |
+------------------------+--------------------------------+--------------------+
```

### 6.6 Review detail

```text
+-------------------+-------------------------------------+---------------------+
| CHECKLIST / FLAGS | DRAFT v7  [Diff với v6]             | EVIDENCE            |
| [x] Scope/date    | Claim A [1]                         | Source [1] span     |
| [ ] Conflict #2   | - old text                          | Metadata/effective  |
| [x] Calculations  | + reviewer edit                     |---------------------|
|                   |                                     | Calculation trace   |
| Comment thread    | Memo content...                     | Rule v3 / inputs    |
|-------------------+-------------------------------------+---------------------|
| [Return]                     Blocker còn 1     [Approve disabled]            |
+----------------------------------------------------------------------------+
```

### 6.7 Change/impact detail

```text
+------------------------------+---------------------------------------------+
| Nghị định ... | Hiệu lực ... | IMPACT PROPOSALS                            |
|------------------------------| change -> provision -> asset                |
| BEFORE       | AFTER         | [Direct] Rule VAT-R-07     [Confirm][Dismiss]|
| ...          | ...           | [Direct] Memo v4           [Confirm][Dismiss]|
|              |               | [Possible] Matter ...      [Review]          |
| changed span highlighted     |---------------------------------------------|
| Transition / source metadata | Task preview: owner / due / stale reason     |
+------------------------------+---------------------------------------------+
```

### 6.8 Mobile research/review

```text
+----------------------------+
| < Case VAT-024      [menu]  |
| Event 30/06/2025  [Stale]   |
|----------------------------|
| Kết luận có điều kiện       |
| Claim A [1]                 |
| [Mở nguồn] [Gắn cờ]         |
|----------------------------|
| Facts / Assumptions   [>]   |
| Analysis              [>]   |
| Missing information  (2)   |
|----------------------------|
| [Return]       [Approve*]   |
| * chỉ khi checklist đạt     |
+----------------------------+
```

## 7. Trạng thái và phản hồi hệ thống

### 7.1 Trạng thái tin cậy

| UI state | Điều kiện máy kiểm tra | Hiển thị/hành động |
|---|---|---|
| `source_verified` | snapshot/anchor/version/temporal/support checks pass | `Đã kiểm chứng nguồn`, mở exact span |
| `source_partial` | evidence chỉ hỗ trợ một phần claim | `Hỗ trợ một phần`, chỉ rõ phần chưa có căn cứ |
| `conditional` | phụ thuộc assumption/unconfirmed fact | điều kiện cạnh conclusion; command bổ sung fact |
| `conflict` | counter-authority hoặc resolver conflict | hiện hai phía; blocker review/publish |
| `insufficient` | coverage/authority dưới threshold | `Chưa đủ căn cứ`; abstain và next action |
| `rule_verified` | deterministic run có published rule/test | `Đã tính bằng rule`; mở trace |
| `needs_review` | policy/risk tier yêu cầu người | owner/SLA/review command |
| `approved` | signer ký exact version | tên/thời gian/version; edit tạo unapproved version |
| `stale` | dependency đổi sau output/approval | reason/path; khóa phát hành mới tới khi rà |

### 7.2 Trạng thái job dài

UI dùng một tập presentation state cô đọng. Backend vẫn trả domain state canonical
và metadata lỗi; frontend chỉ ánh xạ theo bảng sau, không ghi ngược nhãn UI vào DB.

| Research run/domain state | UI state | Quy tắc hiển thị |
|---|---|---|
| `queued` | `queued` | chỉ hiện vị trí/ước tính nếu backend có dữ liệu thật |
| `planning`, `retrieving`, `analyzing`, `verifying` | `running` | hiện đúng stage name, elapsed, count và budget; không bịa phần trăm |
| `awaiting_input` | `needs_input` | giữ checkpoint, nêu input thiếu và tác động |
| `awaiting_review` | `needs_review` | hiện owner, SLA, blocker và command review |
| `paused` | `paused` | hiện checkpoint/release pin và command resume nếu còn quyền |
| `failed` + `error.retryable=true` | `failed_retriable` | lỗi ngắn gọn, Retry và correlation ID |
| `failed` + `error.retryable=false` | `failed_final` | nêu phần đã lưu và đường escalation; không tự lặp |
| `completed` | `completed` | workflow kết thúc, không đồng nghĩa verified/approved |
| `abstained` | `cannot_conclude` | nêu thiếu nguồn/fact, phạm vi đã tìm và next action; không trình bày như lỗi kỹ thuật |
| `cancellation_requested=true` trên run chưa terminal | `cancelling` | presentation overlay cho tới safe point, không phải state DB riêng |
| `cancelled` | `cancelled` | hiện checkpoint/artifact được giữ và khả năng tạo run mới |

`ResultEnvelope.status` của một tác vụ AI là enum khác với research run. API/orchestrator
phải ánh xạ task status trước khi UI nhận: `needs_input -> awaiting_input`,
`needs_review -> awaiting_review`, `abstained -> abstained`, `failed_final -> failed`
và `cancelled -> cancelled`. `failed_retriable` giữ stage/checkpoint trong lúc retry;
khi hết retry budget mới chuyển run thành `failed`. UI không suy diễn transition này.

### 7.3 Trạng thái draft/review

| Backend lifecycle/condition | Nhãn UI | Ghi chú |
|---|---|---|
| `draft`, `generating`, `editable` | `draft` | `generating` có progress riêng; editor chỉ sửa khi backend cho phép |
| `editable` và mọi validation gate đạt | `ready_for_review` | derived state; submit vẫn là command có ETag/idempotency |
| `submitted`, `in_review` | `in_review` | queue/assignment quyết định sublabel |
| `changes_requested` | `returned` | hiện reason, assignee và blocker cần sửa |
| `approved` | `approved` | gắn exact version/digest và người duyệt |
| `exported`, `archived` | `exported`, `archived` | không làm thay đổi approval của immutable version |
| dependency/fact/source/rule đổi | `stale` overlay | cờ trực giao với lifecycle; chặn phát hành/approve cho tới khi rà lại |

### 7.4 Loading, empty và lỗi

| Context | Loading | Empty | Error/recovery |
|---|---|---|---|
| Table/list | skeleton cùng column width, không giả dữ liệu | phân biệt no-data/no-match/no-permission | inline row/page error, retry giữ filter |
| Source | page shell + metadata skeleton | không áp dụng nếu ID hợp lệ | anchor lỗi chặn verified; reload snapshot, report |
| Answer | section skeleton + JobProgress | câu hỏi mới ở SCR-003 | partial/timeout giữ evidence; resume/retry |
| Facts | row skeleton | CTA intake/upload/add fact | autosave state, retry; không mất edit |
| Review | checklist/diff shell | queue empty/filter empty | version conflict -> Reload/Compare |
| Change | diff/dependency shell | no change/no impact tách biệt | rollback/retry có release state rõ |

Toast chỉ dùng xác nhận ngắn, không chứa lỗi cần hành động hoặc thông tin pháp lý.
Lỗi phải nằm cạnh nơi sửa được và vẫn tồn tại tới khi user xử lý.

## 8. Responsive behavior

| Pattern | Desktop | Tablet | Mobile |
|---|---|---|---|
| Navigation | rail 240/64 px | rail 64 px/drawer | bottom nav + account menu |
| Source-first | ba vùng resizable | answer + overlay/split source | route/overlay toàn màn hình, Back giữ anchor |
| Data table | sticky/resize/virtualize | bớt cột theo priority | row view, label-value, filter sheet |
| Evidence grid | full | read/review hạn chế | không edit grid; từng extraction |
| Editor | editor + validation pane | editor + drawer | read/comment; edit nhẹ theo section |
| Version diff | hai cột | hai cột nếu đủ rộng | before/after theo hunk |
| Calculator | input/result/scenario | input + result, scenario drawer | tuần tự input/result/trace |
| Review | checklist/draft/source | draft + drawers | claim-by-claim; không ẩn blocker |
| Admin | full console | view/assign | status/approval hạn chế; edit sâu desktop |

Breakpoint không được làm mất action đang dở. Sheet/drawer đóng mở phải giữ focus,
unsaved state và scroll anchor. Text không scale theo viewport; container dùng
min/max/grid tracks để từ dài có thể wrap.

## 9. Accessibility

Mục tiêu phát hành: WCAG 2.2 AA cho toàn bộ workflow P0.

- Có skip links tới navigation, nội dung và source panel; landmark/heading đúng cấp.
- Tất cả command dùng bàn phím; focus rõ; focus trả về trigger sau dialog/drawer.
- Icon-only button chỉ dùng icon quen thuộc và phải có accessible name + tooltip.
- Tree/grid/diff/editor dùng pattern ARIA phù hợp; luôn có phương án không drag.
- Badge/status dùng icon + chữ; biểu đồ/trạng thái không phụ thuộc riêng màu.
- Streaming/status thông báo qua `aria-live=polite`, gom cập nhật để không spam.
- Citation marker liên kết ngữ nghĩa với claim và source; source highlight được focus.
- PDF có text layer/OCR; original vẫn truy cập; zoom/reflow 400% không che action.
- Date hiển thị tuyệt đối theo locale `vi-VN`; timezone/period rõ khi có thể gây nhầm.
- Bảng lớn có caption, column headers, row view mobile; virtualized grid được test
  screen reader thực tế, không chỉ automated test.
- Test bắt buộc: axe/Playwright, keyboard-only, NVDA/VoiceOver, contrast, zoom 400%,
  reduced motion và export PDF/DOCX reading order.

## 10. Design tokens

Token là semantic; không hard-code màu theo từng màn hình. Palette chủ đạo trung
tính sáng, dùng xanh lá cho success, xanh dương cho action/source, hổ phách cho
condition, đỏ cho blocker và tím hạn chế cho AI proposal. Không dùng gradient,
orb, palette một màu hoặc corner quá tròn.

```css
:root {
  --color-bg: #f7f8fa;
  --color-surface: #ffffff;
  --color-surface-subtle: #f1f3f5;
  --color-text: #17202a;
  --color-text-muted: #59636e;
  --color-border: #cbd2d9;
  --color-action: #1769aa;
  --color-action-hover: #125487;
  --color-success: #18794e;
  --color-warning: #9a6700;
  --color-danger: #c23030;
  --color-ai-proposal: #6f42a5;
  --color-focus: #005fcc;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;

  --radius-control: 4px;
  --radius-panel: 6px;
  --radius-card: 8px;
  --control-sm: 32px;
  --control-md: 40px;
  --header-height: 56px;
  --nav-expanded: 240px;
  --nav-collapsed: 64px;
  --source-min: 360px;
  --source-max: 640px;

  --font-sans: Inter, "Noto Sans", "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", Consolas, monospace;
  --text-xs: 12px;
  --text-sm: 14px;
  --text-md: 16px;
  --text-lg: 20px;
  --text-xl: 28px;
  --line-tight: 1.3;
  --line-normal: 1.5;
  --letter-spacing: 0;
}
```

- Card chỉ dùng cho item lặp độc lập hoặc modal/tool thật; section trang là band
  hoặc layout không khung, không card lồng card.
- Shadow chỉ cho overlay/drawer/menu, không dùng để biến section thành floating card.
- Motion 120-200 ms cho state transition; tôn trọng `prefers-reduced-motion`.
- Tối thiểu touch target 44x44 px trên mobile; icon visual có thể 18-20 px.

## 11. Nội dung và microcopy

### 11.1 Quy tắc

- Dùng tiếng Việt ngắn, trực tiếp, ngày tuyệt đối. Không dùng “AI chắc chắn rằng”.
- Tách `Đã kiểm chứng nguồn`, `Fact đã xác nhận`, `Đã tính bằng rule`, `Đã phê duyệt`.
- Command dùng động từ + đối tượng: `Xác nhận fact`, `Gửi duyệt`, `Mở nguồn`,
  `Chạy lại phép tính`; không dùng `OK` khi hành động có nghĩa cụ thể.
- Warning nói điều kiện và action, không chỉ “Có lỗi xảy ra”.
- Không viết text trong app để quảng bá tính năng, liệt kê shortcut hoặc giải thích
  phong cách giao diện. Hướng dẫn ngữ cảnh đặt trong label/help/tooltip cần thiết.

### 11.2 Từ vựng chuẩn

| Không dùng | Dùng |
|---|---|
| `Độ tin cậy 92%` | trạng thái theo fact/source/time/rule/review |
| `AI đã xác minh` | `Kiểm tra tự động đã đạt`; ghi loại kiểm tra |
| `Luật hiện hành` không ngày | `Áp dụng cho sự kiện ngày dd/mm/yyyy` |
| `Nguồn uy tín` | authority class và tên nguồn cụ thể |
| `AI nghĩ/suy luận` | `Kết luận`, `Căn cứ`, `Giả định`, `Kiểm tra` |
| `Processing...` | tên bước `Đang kiểm tra phiên bản...` |
| `Success` | `Đã lưu`, `Đã gửi duyệt`, `Đã phê duyệt` |

### 11.3 Mẫu trạng thái

- Thiếu date: `Chưa thể chọn quy định áp dụng. Bổ sung ngày phát sinh giao dịch.`
- Source partial: `Nguồn này hỗ trợ điều kiện A nhưng chưa hỗ trợ kết luận B.`
- Conflict: `Có hai căn cứ dẫn đến cách hiểu khác nhau. Cần reviewer xử lý trước khi phát hành.`
- Stale: `Bản này cần rà soát lại vì Điều ... thay đổi từ ngày ...`.
- Calculation blocked: `Chưa có rule đã phát hành cho ngày giao dịch đã chọn.`
- Permission: `Bạn không có quyền xem nội dung này trong phạm vi case hiện tại.`

## 12. Analytics và telemetry sản phẩm

Không gửi raw question, prompt, source text, filename, client/matter name, fact value,
memo text hoặc PII vào analytics. ID phải pseudonymous/opaque; legal audit store và
product analytics là hai hệ khác nhau.

| Event | Khi phát | Thuộc tính cho phép |
|---|---|---|
| `tenant_switched` | context đổi thành công | role_class, latency_bucket, success |
| `matter_created` | case commit | domain, sensitivity_class, source_channel |
| `document_uploaded` | scan accept/reject | mime_class, size_bucket, scan_result, parse_route |
| `fact_status_changed` | propose/confirm/reject/conflict | old_state, new_state, materiality, source_type |
| `research_started` | run created | mode, domain, risk_tier, has_event_date, budget_bucket |
| `research_state_changed` | state transition | from/to, step_type, elapsed_bucket, retry_count |
| `citation_opened` | source anchor mở | authority_class, support_state, viewer_mode, open_success |
| `answer_abstained` | policy gate dừng | blocker_code, risk_tier, next_action_type |
| `calculation_completed` | deterministic run xong | rule_family/version_id, scenario_count, success |
| `draft_generated` | version created | template_type, claim_count_bucket, blocker_count |
| `review_submitted` | freeze/queue | review_tier, blocker_count, draft_age_bucket |
| `review_decided` | return/approve | decision, review_tier, elapsed_bucket, edit_distance_bucket |
| `deliverable_exported` | export ready | format, share_mode, policy_result |
| `change_opened` | user mở change | severity, asset_type, directness |
| `impact_dispositioned` | confirm/dismiss | disposition, directness, reason_code |
| `corpus_release_attempted` | publish/rollback | action, regression_result, success |
| `permission_changed` | role/grant commit | change_type, scope_type, session_invalidated |
| `ui_error_recovered` | retry/resume thành công | screen_id, error_class, recovery_action |

Mỗi event có `event_name`, `schema_version`, `timestamp`, `tenant_pseudonym`,
`user_pseudonym`, `session_id`, `screen_id`, `correlation_id`; sampling không được
làm mất security/audit events trong kho audit riêng.

## 13. Quy tắc instrumentation và thí nghiệm UX

- Đo `time-to-first-sourced-draft` từ intake đủ điều kiện tới draft có citation,
  tách thời gian chờ user, hệ thống và reviewer.
- Review time đo active time và elapsed time riêng; không diễn giải tab mở là lao động.
- Citation success cần cả click mở được exact anchor, không chỉ click-through.
- Thumbs-up/down chỉ là feedback workflow; sample chuyên gia độc lập vẫn bắt buộc.
- A/B test không được thay review gate, source authority hoặc risk policy. Thử nghiệm
  model/retrieval dùng shadow/canary và không tự gửi output.
- Ghi accessibility failures và mobile abandon theo screen/task, không fingerprint user.

## 14. Acceptance theo màn hình

### 14.1 Acceptance chung

1. Mọi SCR có loading, empty, error, no-permission, stale và recovery phù hợp.
2. Navigation/command/focus hoạt động bằng keyboard; axe không có violation nghiêm trọng;
   workflow chính vượt test screen reader và zoom 400%.
3. Tenant/sensitivity/status/date không bị che hoặc truncate mất nghĩa ở viewport hỗ trợ.
4. Không raw sensitive content trong URL, analytics, error message hoặc client persistence.
5. Server-side authorization được test; hide button không được coi là access control.
6. Dynamic state không làm toolbar/grid/panel đổi kích thước gây thao tác nhầm.
7. API error hiển thị domain action và correlation ID; retry command idempotent.
8. Mọi citation từ answer/review/diff mở exact immutable snapshot hoặc claim bị chặn.

### 14.2 Acceptance workflow P0

| Journey | Màn hình | Tiêu chí UX |
|---|---|---|
| Tra cứu point-in-time | SCR-003, 004, 013 | date bắt buộc có lý do; source mở cạnh claim; abstain rõ action |
| Case intake/facts | SCR-005..009 | autosave; provenance; proposed != confirmed; conflict không bị che |
| Research dài | SCR-004, 010 | progress <1s, reconnect/resume/cancel, không spinner vô hạn |
| Calculator | SCR-011 | typed/unit validation, rule/date/source/steps, result read-only |
| Draft/review | SCR-012, 015, 016 | version/diff, blockers, maker-checker, edit hủy approval mới |
| Corpus release | SCR-018, 019 | quarantine, regression evidence, dual control, atomic publish/rollback |
| Quyền/audit | SCR-020, 021 | effective access preview, revoke, immutable/redacted export |

### 14.3 Viewport test matrix

- Desktop: 1440x900 và 1280x800.
- Tablet: 1024x768 và 768x1024.
- Mobile: 390x844 và 360x800.
- Zoom/reflow: 200% và 400%; Windows display scaling 125/150%.
- Nội dung thử gồm tên văn bản/case dài, dấu tiếng Việt, 1000-row table, 50-page
  source, 30 claims, 20 citations, 10 scenarios và mọi trạng thái lỗi.

## 15. Bàn giao frontend

Trước build, đội sản phẩm/frontend cần tạo:

- Figma hoặc code prototype cho SCR-004, 007, 011, 016, 018 và mobile states;
- Storybook cho CMP-001..CMP-018 với accessibility interaction tests;
- typed route/API contracts và fixtures không chứa dữ liệu thật;
- visual regression cho split panes, long Vietnamese text và all status badges;
- Playwright journeys tương ứng UC-001..UC-018;
- content catalogue/error codes/version, analytics schema và privacy review;
- usability test với ít nhất chuyên gia soạn, reviewer và knowledge curator, dùng
  case VAT/hóa đơn thực tế đã ẩn danh.

Mọi thay đổi làm mờ ngày áp dụng, nguồn, trạng thái fact/rule/review hoặc quyền truy
cập phải được coi là thay đổi rủi ro cao và cần product/legal review, không chỉ
được duyệt như chỉnh sửa thẩm mỹ.
