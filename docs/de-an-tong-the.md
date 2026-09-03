# Đề án tổng thể: Trợ lý pháp luật thuế Việt Nam

**Mốc kiểm chứng nguồn:** 09/08/2026  
**Phạm vi pháp luật:** Việt Nam  
**Trạng thái:** đề án nghiên cứu, sản phẩm và kiến trúc; không phải ý kiến pháp lý

## 1. Tóm tắt điều hành

Sản phẩm không nên được xây như một chatbot hỏi đáp chung có thêm kho PDF.
Thuế là bài toán xác định luật áp dụng theo thời điểm, quan hệ giữa nhiều văn
bản, dữ kiện của từng giao dịch và chứng cứ hồ sơ. Một câu trả lời nghe hợp lý
nhưng dùng sai phiên bản điều luật hoặc bỏ qua ngoại lệ có thể làm phát sinh
tiền thuế, phạt, chậm nộp và mất quyền khiếu nại.

Định hướng đề xuất:

1. Khởi đầu bằng **copilot cho chuyên gia thuế, kế toán và luật sư**, giới hạn ở
   VAT và hóa đơn. Chỉ mở rộng CIT, PIT, quản lý thuế và tư vấn trực tiếp cho
   khách hàng sau khi đạt các ngưỡng đánh giá tương ứng.
2. Xây một **hệ tri thức pháp luật theo hai trục thời gian** và đồ thị quy phạm
   trước khi tối ưu mô hình sinh. Đây là lớp ngăn xung đột luật cũ - mới.
3. Dùng **hybrid RAG** làm đường cơ sở; dùng đồ thị pháp lý để mở rộng quan hệ;
   chỉ dùng agent/ReAct cho luồng nghiên cứu có giới hạn, có ngân sách và có
   điểm dừng. Không áp dụng mọi kỹ thuật chỉ vì chúng mới.
4. Tách LLM khỏi các quyết định có thể xác định: phép tính, thời hạn, bảng thuế,
   điều kiện và kiểm chứng trích dẫn phải do code hoặc decision table thực hiện.
5. Trả lời theo một hợp đồng bắt buộc: kết luận, giả định, luật áp dụng, phân
   tích, phép tính, hồ sơ cần bổ sung, rủi ro, mức tin cậy và bước duyệt chuyên gia.
6. Xem hệ thống là **AI rủi ro cao theo thiết kế nội bộ** cho tới khi có ý kiến
   pháp lý chính thức về phân loại theo Luật Trí tuệ nhân tạo 2025.

Lợi thế cạnh tranh bền vững không nằm ở một mô hình ngôn ngữ riêng lẻ. Nó nằm
ở corpus có bản quyền và lịch sử phiên bản, ontology thuế Việt Nam, bộ tình
huống do chuyên gia chấm, các rule đã kiểm thử và vòng phản hồi nghiệp vụ.

## 2. Vấn đề phải giải quyết

### 2.1 Năm lớp của một câu hỏi thuế

Mỗi yêu cầu cần được tách thành năm lớp:

| Lớp | Câu hỏi hệ thống phải trả lời |
|---|---|
| Dữ kiện | Ai, giao dịch gì, ở đâu, khi nào, số tiền nào, chứng từ nào? |
| Phân loại pháp lý | Chủ thể, thu nhập, hàng hóa/dịch vụ, nơi tiêu dùng và kỳ tính thuế thuộc loại nào? |
| Thời gian | Ngày phát sinh nghĩa vụ, ngày lập hóa đơn, kỳ khai và ngày tư vấn là ngày nào? |
| Quy phạm | Văn bản nào có thẩm quyền, hiệu lực và phạm vi điều chỉnh phù hợp? |
| Hậu quả | Cách tính, kê khai, chứng từ, thời hạn, rủi ro và phương án xử lý là gì? |

Nếu thiếu dữ kiện trọng yếu, hệ thống phải hỏi lại hoặc trả lời có điều kiện;
không được tự điền một giả định âm thầm.

### 2.2 Các lỗi nguy hiểm nhất

- Trích đúng câu chữ nhưng sai văn bản, sai điều/khoản hoặc sai khoảng hiệu lực.
- Áp dụng văn bản mới cho giao dịch cũ hoặc bỏ qua điều khoản chuyển tiếp.
- Dùng văn bản hợp nhất như một văn bản làm thay đổi hiệu lực pháp lý.
- Chỉ tìm đoạn tương đồng, không theo liên kết sửa đổi, dẫn chiếu, ngoại lệ.
- Dùng công văn cho một trường hợp cụ thể như quy tắc phổ quát.
- Trộn nguồn chính thức với bài báo, blog hoặc câu trả lời của AI mà không phân cấp.
- Mô hình tự tính sai tiền thuế hoặc thời hạn dù phần diễn giải đúng.
- Dữ liệu một khách hàng xuất hiện trong phiên hoặc kết quả của khách hàng khác.
- Agent lặp tìm kiếm, vượt chi phí hoặc kết luận khi chứng cứ còn mâu thuẫn.
- Luật mới được nhập nhưng cache, embedding, rule và câu trả lời cũ chưa bị vô hiệu.

## 3. Phạm vi sản phẩm

### 3.1 Người dùng và công việc ưu tiên

**Nhóm chính:** chuyên gia thuế nội bộ, kế toán trưởng, tư vấn viên và luật sư.

**Nhóm thứ hai:** nhân viên vận hành cần tra cứu có kiểm soát; khách hàng doanh
nghiệp nhận bản tư vấn đã được duyệt.

Các công việc của bản đầu:

- hỏi đáp luật theo một ngày xác định;
- so sánh quy định cũ và mới;
- mở một case, thu thập dữ kiện và tài liệu còn thiếu;
- tạo bản phân tích có trích dẫn để chuyên gia duyệt;
- tính một số tình huống VAT bằng rule đã kiểm thử;
- nhận cảnh báo văn bản mới và danh sách case/rule/nội dung bị ảnh hưởng.

Chưa làm ở bản đầu: tự động nộp hồ sơ, tự đại diện tranh chấp, kết luận dứt khoát
khi thiếu dữ kiện, bao phủ mọi sắc thuế và tư vấn trực tiếp không có giám sát.

### 3.2 Ba năng lực sản phẩm

1. **Authority Q&A:** tra cứu, so sánh theo thời điểm và trích dẫn chính xác.
2. **Case workspace:** hồ sơ vụ việc, timeline, chứng cứ, issue tree, phép tính,
   phê duyệt và audit log.
3. **Change intelligence:** theo dõi văn bản, tạo semantic diff, lan truyền tác
   động đến rule, câu trả lời mẫu, case đang mở và tài liệu khách hàng.

### 3.3 Hợp đồng đầu ra

Mọi câu trả lời nghiệp vụ phải có cấu trúc tối thiểu:

1. **Phạm vi và ngày áp dụng.**
2. **Kết luận ngắn**, có điều kiện nếu cần.
3. **Dữ kiện đã dùng và giả định.**
4. **Vấn đề pháp lý cần giải quyết.**
5. **Căn cứ:** tên/số văn bản, điều/khoản/điểm, khoảng hiệu lực, liên kết nguồn.
6. **Phân tích:** quy tắc, áp dụng vào dữ kiện, ngoại lệ và phản biện.
7. **Phép tính hoặc bảng quyết định** kèm phiên bản rule.
8. **Tài liệu còn thiếu và phương án thay thế.**
9. **Rủi ro, mức tin cậy và lý do chuyển chuyên gia.**
10. **Dấu vết:** snapshot nguồn, phiên bản corpus, model/prompt/tool và thời gian.

Không đủ bằng chứng, có xung đột chưa giải quyết, hoặc gần hạn thủ tục là điều
kiện chuyển người, không phải tín hiệu để mô hình viết thuyết phục hơn.

## 4. Cơ sở pháp lý hiện hành phải đưa vào thiết kế

Các nguồn đầy đủ nằm trong [danh mục nguồn](source-register.md). Những điểm ảnh
hưởng trực tiếp đến kiến trúc gồm:

- Luật Ban hành văn bản quy phạm pháp luật 2025 và luật sửa đổi quy định cách
  xác định hiệu lực, nguyên tắc áp dụng và xử lý văn bản khác nhau; nên dùng bản
  hợp nhất [54/VBHN-VPQH](https://vbpl.vn/TW/Pages/vbpq-thuoctinh-hopnhat.aspx?ItemID=182331&View=0)
  để đọc thuận tiện nhưng vẫn truy về văn bản gốc.
- Luật Quản lý thuế [108/2025/QH15](https://vanban.chinhphu.vn/?docid=216541&pageid=27160)
  có hiệu lực từ 01/07/2026; corpus phải giữ cả lịch sử của Luật 38/2019/QH14
  cho sự kiện xảy ra trước mốc thích hợp.
- Các trục thuế chính đã thay đổi gần nhau: Luật VAT 48/2024/QH15, Luật CIT
  67/2025/QH15 và Luật PIT 109/2025/QH15. Không thể gắn một nhãn `current` duy
  nhất cho toàn bộ kho luật.
- Luật Trí tuệ nhân tạo [134/2025/QH15](https://vanban.chinhphu.vn/?classid=1&docid=216334&orggroupid=1&pageid=27160)
  có hiệu lực từ 01/03/2026 và Nghị định
  [142/2026/NĐ-CP](https://vanban.chinhphu.vn/?docid=218029&orggroupid=2&pageid=27160)
  từ 01/05/2026 đặt ra quản trị theo rủi ro, minh bạch và kiểm soát con người.
- Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 và Nghị định
  [356/2025/NĐ-CP](https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=187276)
  cùng có hiệu lực từ 01/01/2026. Hồ sơ thuế chứa dữ liệu định danh, tài chính
  và có thể có dữ liệu nhạy cảm, nên privacy-by-design là yêu cầu nền tảng.
- Luật Luật sư xác định tư vấn pháp luật là dịch vụ pháp lý. Mô hình vận hành,
  vai trò người phê duyệt, hợp đồng và tuyên bố trách nhiệm cần được luật sư
  Việt Nam rà soát trước khi thương mại hóa.

Đây là danh mục nền, không phải kết luận đầy đủ về nghĩa vụ tuân thủ. Trước mỗi
lần phát hành cần lập legal register, xác nhận phân loại AI, vai trò kiểm soát/xử
lý dữ liệu, điều kiện cung cấp dịch vụ và yêu cầu lưu trữ/chuyển dữ liệu.

## 5. Mô hình tri thức chống xung đột luật cũ - mới

### 5.1 Nguồn chứng cứ bất biến

Mỗi lần thu thập phải lưu:

- tệp gốc/PDF/HTML và URL chính thức;
- hash nội dung, thời điểm tải, tác nhân tải và kết quả chữ ký nếu có;
- metadata phát hành, công bố, hiệu lực, hết hiệu lực và phạm vi;
- bản OCR cùng điểm tin cậy nhưng không ghi đè tệp gốc;
- quan hệ với văn bản sửa đổi, bãi bỏ, hướng dẫn và hợp nhất.

Nguồn được xếp hạng: nguồn công báo/cơ sở dữ liệu cơ quan nhà nước; nguồn cơ
quan ban hành; nguồn thương mại được cấp phép; học thuật; bình luận thứ cấp.
Chỉ hai hạng đầu được mặc định làm căn cứ quy phạm. Nguồn khác dùng để phát hiện
vấn đề hoặc giải thích, và phải được xác minh lại.

### 5.2 Hai trục thời gian

Mọi `ProvisionVersion` cần ít nhất:

```text
valid_from, valid_to       # quy định có hiệu lực cho sự kiện nào
recorded_from, recorded_to # hệ thống biết/ghi nhận phiên bản từ khi nào
publication_date
effective_status          # chưa hiệu lực, có hiệu lực, đình chỉ, hết hiệu lực
transitional_rule
source_snapshot_id
```

Truy vấn phải nhận `event_date` và `as_of_knowledge_time`. Trục thứ nhất trả lời
"luật nào điều chỉnh giao dịch"; trục thứ hai tái tạo "tại thời điểm tư vấn, hệ
thống đã biết gì". Không có hai trục này thì audit và sửa sai hồi tố không đáng tin.

### 5.3 Đồ thị pháp lý chuẩn tắc

Các nút cốt lõi:

```text
Instrument -> Provision -> ProvisionVersion
TaxConcept, TaxpayerType, TransactionType, Jurisdiction
AdministrativeProcedure, Form, Deadline, Rate, Exemption
OfficialGuidance, CaseMatter, Fact, Issue, Evidence, RuleVersion
```

Các cạnh có kiểu, nguồn và khoảng hiệu lực:

```text
AMENDS, REPEALS, REPLACES, SUSPENDS, CONSOLIDATES
IMPLEMENTS, GUIDES, REFERS_TO, EXCEPTION_TO, SUBJECT_TO
DEFINES, APPLIES_TO, HAS_RATE, HAS_DEADLINE, REQUIRES_DOCUMENT
SUPPORTS, CONTRADICTS, DERIVED_FROM, AFFECTS
```

Đây là **normative graph** do parser và chuyên gia kiểm soát. Nó khác GraphRAG
dạng cộng đồng chủ đề được LLM trích tự động. Graph cộng đồng hữu ích cho câu
hỏi tổng hợp rộng, nhưng không đủ thẩm quyền để xác định luật áp dụng.

### 5.4 Chunking có cấu trúc

Đơn vị chính là điều/khoản/điểm, không phải cửa sổ token tùy ý. Mỗi chunk mang
đường dẫn văn bản, tiêu đề cha, định nghĩa liên quan, dẫn chiếu, trạng thái và
khoảng hiệu lực. Bảng, phụ lục, biểu mẫu được parse thành cấu trúc riêng. Khi
truy xuất một khoản, hệ thống có thể lấy thêm định nghĩa, khoản dẫn chiếu, ngoại
lệ và điều chuyển tiếp theo cạnh đồ thị.

## 6. Kiến trúc truy xuất và suy luận

### 6.1 Luồng yêu cầu chuẩn

```text
Xác thực và phân quyền
  -> phân loại ý định/rủi ro
  -> trích xuất dữ kiện và timeline
  -> phát hiện dữ kiện còn thiếu
  -> xác định miền luật + ngày sự kiện
  -> lọc phiên bản có hiệu lực
  -> hybrid retrieval
  -> mở rộng đồ thị pháp lý có giới hạn
  -> rerank theo thẩm quyền/thời gian/quan hệ
  -> chạy rule hoặc calculator
  -> soạn câu trả lời có dẫn chứng
  -> kiểm chứng trích dẫn, mâu thuẫn, phép tính
  -> duyệt người nếu vượt ngưỡng
  -> lưu audit bundle
```

### 6.2 Hybrid RAG làm đường cơ sở

Kết hợp bốn tín hiệu:

- lexical/BM25 cho số văn bản, thuật ngữ, cụm từ chính xác;
- dense retrieval cho diễn đạt tương đương;
- metadata filter cho thẩm quyền, sắc thuế, ngày và trạng thái;
- reranker cho mức liên quan sau khi đã lọc hợp lệ.

Trọng số cuối còn tính `authority`, `temporal_fit`, `citation_completeness` và
`graph_distance`. Vector similarity không được phép lấn át hiệu lực pháp lý.
ColBERT/late interaction chỉ nên thử sau khi đường cơ sở đã đo được. Self-RAG,
CRAG và RAPTOR là các thí nghiệm có giả thuyết, không phải phụ thuộc bắt buộc.

### 6.3 Agentic RAG và ReAct

Agent chỉ được gọi cho câu hỏi nhiều bước như đối chiếu nhiều văn bản, điều tra
thay đổi hoặc lập memo. Bộ công cụ được cấp phép hẹp:

```text
search_authority(query, date, filters)
get_provision_version(id, event_date)
follow_legal_edge(id, edge_type, depth_limit)
compare_versions(old_id, new_id)
extract_case_facts(document_id)
run_tax_rule(rule_id, inputs)
verify_citation(claim, source_id)
request_human_review(reason)
```

Mỗi run có tối đa số bước, số tài liệu, token, chi phí và thời gian. State machine
được kiểm soát phù hợp hơn agent tự do. ReAct hữu ích để xen kẽ hành động và
quan sát, nhưng scratchpad không phải chứng cứ và không cần phơi ra cho người dùng.

### 6.4 Quy trình deep research

1. Chuyển yêu cầu thành issue tree và danh sách dữ kiện thiếu.
2. Lập kế hoạch nguồn theo thứ bậc thẩm quyền.
3. Tìm từng vấn đề độc lập; ghim mọi nguồn vào snapshot.
4. Lập claim-evidence matrix: mỗi mệnh đề phải có căn cứ hoặc được đánh dấu suy luận.
5. Tìm chủ động căn cứ phản đối, ngoại lệ và điều khoản chuyển tiếp.
6. Chạy bộ giải quyết thời gian và phát hiện mâu thuẫn.
7. Thực hiện phép tính bằng rule có phiên bản.
8. Soạn memo; kiểm chứng trích dẫn từng mệnh đề.
9. Chuyên gia duyệt trước khi phát hành tư vấn có hệ quả đáng kể.

Các nền tảng kỹ thuật quan trọng được dẫn trong [kế hoạch đọc](research-reading-plan.md):
[RAG](https://papers.nips.cc/paper_files/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html),
[ReAct](https://arxiv.org/abs/2210.03629),
[GraphRAG](https://arxiv.org/abs/2404.16130),
[Self-RAG](https://openreview.net/forum?id=hSyW5go0v8),
[CRAG](https://arxiv.org/abs/2401.15884),
[RAPTOR](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8a2acd174940dbca361a6398a4f9df91-Abstract-Conference.html)
và nghiên cứu [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/).

## 7. Cập nhật luật và phân tích tác động

### 7.1 Pipeline cập nhật

```text
Theo dõi nguồn chính thức
  -> tải và đóng dấu chứng cứ
  -> nhận dạng/OCR + kiểm tra cấu trúc
  -> trích metadata và đơn vị điều/khoản/điểm
  -> phát hiện văn bản mới hoặc phiên bản mới
  -> semantic diff
  -> đề xuất quan hệ sửa/bãi bỏ/thay thế/hướng dẫn
  -> chuyên gia xác nhận
  -> lập phiên bản index/graph/rule mới
  -> chạy regression benchmark
  -> phát hành atomically
  -> vô hiệu cache và tạo cảnh báo tác động
```

Crawler không được trực tiếp biến nội dung mới thành luật đang dùng. Mỗi lần
phát hành corpus là một manifest bất biến; nếu kiểm thử thất bại thì giữ phiên
bản đang chạy và đưa tài liệu vào hàng chờ chuyên gia.

### 7.2 Semantic diff

Diff phải phân biệt:

- thay đổi hình thức, đánh số hoặc chính tả;
- thay đổi định nghĩa, đối tượng, điều kiện, ngoại lệ;
- thay đổi thuế suất, ngưỡng, công thức hoặc thời hạn;
- thêm/bỏ dẫn chiếu;
- điều khoản chuyển tiếp và hiệu lực;
- thay đổi biểu mẫu/chứng từ.

LLM có thể đề xuất bản tóm tắt tác động, nhưng một parser xác định phải chứng
minh các đoạn thay đổi và chuyên gia chịu trách nhiệm duyệt ý nghĩa pháp lý.

### 7.3 Lan truyền tác động

Từ `ProvisionVersion` thay đổi, đi theo cạnh `AFFECTS` tới:

- `RuleVersion` và test case;
- mẫu câu trả lời, memo, checklist và calculator;
- câu hỏi thường gặp đã xuất bản;
- case đang mở có ngày/sự kiện phù hợp;
- alert subscription theo khách hàng/ngành;
- embedding, index, graph projection và cache key.

Mỗi đối tượng nhận một trạng thái: `unaffected`, `review_required`, `obsolete`,
`recomputed` hoặc `republished`. Cảnh báo phải nói rõ **ai bị ảnh hưởng, từ ngày
nào, thay đổi nghĩa vụ gì, nguồn nào và cần hành động gì**, không chỉ tóm tắt văn bản.

## 8. Rule engine, phép tính và kiểm chứng

Mỗi rule cần ID, phiên bản, khoảng hiệu lực, căn cứ pháp lý, schema đầu vào, công
thức/decision table, ví dụ biên, người duyệt và bộ test. Kết quả rule luôn trả:

```json
{
  "rule_id": "VAT.EXAMPLE.001",
  "rule_version": "2026-07-01",
  "inputs": {},
  "result": {},
  "authority_ids": [],
  "trace": [],
  "warnings": []
}
```

Các kiểm tra bắt buộc trước khi trả lời:

- mọi trích dẫn tồn tại nguyên văn trong snapshot;
- điều/khoản/điểm thuộc đúng văn bản và có hiệu lực tại `event_date`;
- một mệnh đề pháp lý quan trọng có ít nhất một nguồn đủ thẩm quyền;
- nguồn mâu thuẫn được nêu và giải quyết hoặc chuyển chuyên gia;
- số liệu đầu vào khớp hồ sơ; tổng, tỷ lệ, làm tròn và thời hạn vượt test;
- không có dữ liệu khách hàng khác trong context hoặc output.

## 9. Bộ nhớ, context và tối ưu chi phí

Không dùng một "bộ nhớ chatbot" chung. Tách năm tầng:

| Tầng | Nội dung | Thời hạn/kiểm soát |
|---|---|---|
| 1. Turn state | ý định và dữ kiện đang hỏi | ngắn, xóa sau phiên theo policy |
| 2. Matter memory | timeline, issue, evidence của một case | mã hóa, ACL theo hồ sơ |
| 3. User preference | ngôn ngữ, định dạng, quyền | tối thiểu, có consent |
| 4. Legal knowledge | corpus, graph, rule dùng chung | không chứa dữ kiện khách hàng |
| 5. Audit memory | nguồn, prompt, tool, output, duyệt | bất biến theo retention policy |

Tối ưu context:

- tạo `case state` có cấu trúc thay vì gửi toàn bộ lịch sử chat;
- nén riêng facts, issues, authorities và unresolved questions;
- chỉ lấy các đoạn có hiệu lực và các node lân cận cần thiết;
- dùng citation-first context: đưa đoạn chứng cứ cùng ID ổn định;
- đặt giới hạn token cho từng phần và ưu tiên nguồn có thẩm quyền;
- dùng model nhỏ cho routing/extraction, model mạnh cho synthesis khó;
- cache theo `query + event_date + corpus_version + permission_scope`;
- vô hiệu cache theo dependency graph, không chỉ theo TTL;
- batch embedding và chỉ re-embed chunk thay đổi;
- theo dõi chi phí trên mỗi case, câu trả lời được duyệt và lỗi tránh được.

Không fine-tune kiến thức luật dễ thay đổi vào model. Fine-tuning chỉ phù hợp cho
định dạng, phân loại ý định, trích xuất có schema hoặc phong cách, sau khi có bộ
dữ liệu hợp pháp. Kiến thức quy phạm vẫn phải đến từ corpus có phiên bản.

## 10. Kiến trúc triển khai tham chiếu

Kế hoạch triển khai web, ma trận nền tảng, benchmark sản phẩm quốc tế, trust UX,
feature backlog và release gates được cụ thể hóa tại
[benchmark-va-ke-hoach-web.md](benchmark-va-ke-hoach-web.md).

### 10.1 Các dịch vụ

```text
Web/API gateway
  |-- Identity, tenant, RBAC/ABAC
  |-- Case service + document service
  |-- Research orchestrator/state graph
  |-- Legal resolver + citation verifier
  |-- Rule/calculation service
  |-- Ingestion/change-intelligence service
  |-- Review/approval + audit service

Storage
  |-- Object store: bản gốc, snapshot, audit bundle
  |-- PostgreSQL: metadata, bitemporal state, case, workflow
  |-- Search engine: BM25 + filter + vector/hybrid
  |-- Graph projection: ban đầu trong PostgreSQL; graph DB khi benchmark chứng minh
  |-- Queue/event bus: ingestion, indexing, alerts, review jobs
```

### 10.2 Lựa chọn thực dụng

- API: FastAPI hoặc framework hiện có của đội.
- Workflow: state graph có checkpoint; LangGraph phù hợp để thử nghiệm agent,
  hệ bền vững kiểu Temporal phù hợp với job dài và retry có kiểm soát.
- Dữ liệu: PostgreSQL trước, object store tương thích S3, OpenSearch/Elasticsearch
  cho hybrid retrieval; pgvector đủ cho prototype nhỏ.
- Graph: bắt đầu bằng bảng cạnh có version. Chỉ thêm Neo4j hoặc graph DB tương
  đương khi truy vấn nhiều hop, quản trị đồ thị và benchmark chứng minh giá trị.
- Model gateway: provider-neutral, schema output bắt buộc, redaction, budget,
  retry, circuit breaker, telemetry và policy theo loại dữ liệu.
- Quan sát: trace end-to-end nhưng redact PII; log riêng latency, token, retrieval,
  citation validation, rule execution và human override.

Không nên khóa toàn bộ logic vào một framework agent. Hợp đồng tool, schema dữ
liệu, resolver thời gian, rule engine và verifier phải độc lập nhà cung cấp.

## 11. Bảo mật, riêng tư và quản trị AI

Các kiểm soát tối thiểu:

- tách tenant bằng khóa và chính sách truy cập; object/key namespace riêng;
- MFA/SSO, least privilege, phân tách người soạn và người duyệt;
- mã hóa khi truyền/lưu; quản lý khóa và secrets tập trung;
- DLP/redaction trước khi gọi model ngoài; allowlist vùng lưu trữ và nhà cung cấp;
- consent, purpose limitation, retention, deletion và xử lý yêu cầu chủ thể dữ liệu;
- DPIA/AI impact assessment cho từng use case;
- audit log chống sửa, truy được từ kết luận tới nguồn và quyết định người duyệt;
- phòng prompt injection trong tài liệu: nội dung được truy xuất là dữ liệu,
  không phải lệnh; tool có allowlist và quyền tối thiểu;
- kiểm tra exfiltration, cross-tenant retrieval, citation poisoning, source spoofing,
  document parser exploits và indirect prompt injection;
- incident response, rollback corpus/model/rule và thông báo có quy trình;
- model card/system card nội bộ, change log, owner, risk acceptance và kill switch.

Tham chiếu quản trị nên kết hợp quy định Việt Nam với
[NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework),
[NIST GenAI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence),
ISO/IEC 42001 và [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/).

## 12. Đánh giá: thước đo và cổng phát hành

### 12.1 Bộ benchmark trước khi tối ưu model

Tạo tối thiểu 300 tình huống VAT/hóa đơn do hai chuyên gia độc lập gắn nhãn,
có hòa giải bất đồng. Phân tầng:

- câu hỏi lookup một điều khoản;
- câu hỏi cần nhiều văn bản và dẫn chiếu;
- giao dịch nằm sát mốc thay đổi luật;
- điều khoản chuyển tiếp;
- dữ kiện thiếu hoặc mâu thuẫn;
- ngoại lệ/miễn/không chịu thuế;
- tính toán và thời hạn;
- nguồn gây nhiễu, công văn cá biệt, văn bản hết hiệu lực;
- câu hỏi không đủ thẩm quyền trả lời hoặc cần từ chối;
- tấn công prompt injection và rò rỉ tenant.

Mỗi case có facts, event date, issues, authorities, expected conclusion, acceptable
alternatives, calculation, required follow-up và escalation label.

### 12.2 Metrics

**Corpus/temporal:** độ đầy đủ văn bản, metadata exact match, hiệu lực đúng,
quan hệ sửa đổi đúng, độ trễ cập nhật.

**Retrieval:** Recall@k của căn cứ vàng, authority precision, temporal precision,
MRR/nDCG, tỷ lệ lấy đủ định nghĩa + ngoại lệ + dẫn chiếu.

**Answer:** correctness theo chuyên gia, citation entailment/precision/coverage,
faithfulness, completeness, numerical accuracy, calibration và unsupported-claim rate.

**Agent:** task success, tool error, vòng lặp, số bước, chi phí, latency, tỷ lệ
chuyển người đúng và tỷ lệ tự dừng khi thiếu chứng cứ.

**Vận hành:** override của chuyên gia, thời gian duyệt, incident, data leakage,
chi phí trên câu trả lời được duyệt và tỷ lệ cảnh báo tác động hữu ích.

Có thể tham khảo [LegalBench](https://papers.nips.cc/paper_files/paper/2023/hash/89e44582fd28ddfea1ea4dcb0ebbf4b0-Abstract-Datasets_and_Benchmarks.html),
ALCE, RAGTruth, RAGAS và ARES, nhưng benchmark quyết định phải là tiếng Việt,
theo luật Việt Nam và được chuyên gia thuế xây dựng.

### 12.3 Cổng phát hành đề xuất

- 100% citation ID hợp lệ và trỏ đúng snapshot;
- 100% test xác định cho phép tính/thời hạn trọng yếu;
- temporal precision trên tập ranh giới đạt 100% trước production;
- không có cross-tenant retrieval trong security suite;
- mọi câu có nghĩa vụ đáng kể có human review theo policy;
- unsupported-claim rate trọng yếu bằng 0 trên gold set;
- rollback corpus/rule/model được diễn tập thành công.

Các ngưỡng khác phải được đặt sau baseline; không chọn phần trăm đẹp khi chưa có
dữ liệu. Accuracy tổng hợp không được che lỗi hiếm nhưng gây hậu quả lớn.

## 13. Lộ trình 9-12 tháng

| Giai đoạn | Thời gian | Kết quả bắt buộc |
|---|---:|---|
| 0. Pháp lý và dữ liệu | Tuần 1-4 | legal register, source license, ontology v0, threat model, 100 case đầu |
| 1. Temporal retrieval | Tuần 5-10 | corpus VAT có version, resolver hai thời gian, hybrid baseline, citation verifier |
| 2. Professional Q&A MVP | Tuần 11-16 | giao diện hỏi đáp, nguồn cạnh câu, hỏi lại, review queue, audit export, 300 case |
| 3. Case workspace | Tuần 17-26 | timeline, evidence, issue tree, rule/calculator, draft memo, RBAC tenant |
| 4. Graph + change intelligence | Tuần 27-36 | normative graph, semantic diff, impact propagation, alerts, regression gate |
| 5. Mở rộng có kiểm soát | Sau tuần 36 | CIT/PIT/quản lý thuế theo từng benchmark và legal sign-off riêng |

Mỗi giai đoạn chỉ qua khi đạt cổng đánh giá. Không gắn GraphRAG hoặc multi-agent
vào critical path trước khi hybrid baseline và temporal resolver hoạt động đúng.

### 13.1 Nhân sự tối thiểu

- product lead hiểu workflow thuế;
- legal/tax knowledge lead chịu trách nhiệm ontology và gold set;
- 2-3 chuyên gia VAT/hóa đơn bán thời gian hoặc toàn thời gian;
- data/IR engineer;
- backend/platform engineer;
- applied AI/evaluation engineer;
- security/privacy engineer dùng chung;
- UX researcher/designer cho workflow chuyên gia.

Mỗi artifact có một owner: nguồn luật, provision version, rule, benchmark, model
release, policy, incident và quyết định phát hành.

## 14. Rủi ro và cách khắc phục

| Rủi ro | Biện pháp |
|---|---|
| Quyền sử dụng dữ liệu không rõ | ưu tiên nguồn chính thức; ký license; lưu provenance và điều khoản sử dụng |
| Sai hiệu lực/thời điểm | bitemporal resolver, transition rule, boundary test, expert review |
| Hallucination/trích dẫn giả | constrained citation IDs, claim-evidence matrix, verifier xác định |
| Mâu thuẫn nguồn | xếp hạng thẩm quyền, graph quan hệ, conflict queue, không tự kết luận |
| Luật mới phá logic cũ | semantic diff, dependency graph, regression gate, atomic release, rollback |
| OCR/bảng/biểu mẫu sai | parser theo cấu trúc, confidence threshold, đối chiếu visual, human QA |
| Rò rỉ dữ liệu | tenant isolation, DLP, encryption, provider policy, adversarial tests |
| Prompt injection từ tài liệu | coi retrieval là dữ liệu, sandbox tool, allowlist domain, output validation |
| Agent tốn chi phí/lặp | state graph, step/token/time budget, deterministic stopping, model routing |
| Người dùng quá tin AI | uncertainty rõ, hiển thị căn cứ, review bắt buộc, audit và training |
| Không đủ chuyên gia gắn nhãn | active error mining, ưu tiên case rủi ro cao, đo agreement, adjudication |
| Quá nhiều hạ tầng sớm | PostgreSQL + search baseline trước; thêm graph/model khi ablation chứng minh |
| Vượt ranh giới dịch vụ pháp lý | legal opinion, professional workflow, engagement terms, licensed reviewer |

## 15. Chương trình nghiên cứu và đọc

Kế hoạch chi tiết theo câu hỏi, tài liệu, thí nghiệm, artifact và exit criteria nằm
tại [research-reading-plan.md](research-reading-plan.md). Thứ tự ưu tiên:

1. **Học thuyết nguồn và hiệu lực:** thứ bậc văn bản, áp dụng theo thời gian,
   chuyển tiếp, văn bản hợp nhất, hướng dẫn/công văn và giải quyết xung đột.
2. **Mô hình miền thuế:** chủ thể, giao dịch, nơi đánh thuế, kỳ tính, thuế suất,
   miễn/không chịu, khấu trừ, hóa đơn, hồ sơ, thủ tục, xử phạt.
3. **Workflow tư vấn:** intake, timeline, issue spotting, IRAC/CRAC, chứng cứ,
   alternative analysis, review và privilege/confidentiality.
4. **IR/RAG:** BM25, dense, hybrid, reranking, ColBERT, context construction,
   citation-grounded generation và failure analysis.
5. **Graph + temporal:** ontology, versioned property graph, graph expansion,
   semantic diff, dependency/impact propagation và GraphRAG cộng đồng.
6. **Agent/deep research:** ReAct, tool contracts, state machines, planning,
   stopping, verifier, human-in-the-loop và cost controls.
7. **Evaluation:** legal reasoning benchmark, retrieval, citation, hallucination,
   calibration, adversarial/security, online feedback.
8. **Pháp lý sản phẩm:** AI, dữ liệu cá nhân, dữ liệu, an ninh mạng, người tiêu
   dùng, dịch vụ pháp lý, sở hữu trí tuệ và hợp đồng nhà cung cấp.
9. **Nghiên cứu thị trường:** CoCounsel, Lexis+ with Protégé, Harvey, vLex,
   LuatVietnam AI Luật, Thư Viện Pháp Luật AI Pháp Luật; chỉ dùng trang sản phẩm
   để hiểu workflow/tuyên bố, không coi claim marketing là bằng chứng chất lượng.

Kết quả rà soát mở rộng gồm CoCounsel Tax, CCH AnswerConnect, Blue J, TaxGPT,
Bloomberg Law/Tax, Legora, Spellbook, Avalara, IBFD và Regology nằm trong
[benchmark-va-ke-hoach-web.md](benchmark-va-ke-hoach-web.md).

Các bài cần đọc đầu tiên: RAG, ReAct, GraphRAG, Self-RAG, CRAG, RAPTOR, ColBERT,
Lost in the Middle, LegalBench, LexGLUE, ALCE, RAGTruth, RAGAS và ARES. Mọi kết
luận chọn kỹ thuật phải có baseline và ablation trên benchmark Việt Nam.

## 16. Các thí nghiệm quyết định kiến trúc

1. BM25 so với dense và hybrid có/không reranker.
2. Chunk theo cấu trúc so với cửa sổ token.
3. Filter hiệu lực trước retrieval so với filter sau retrieval.
4. Mở rộng normative graph 0/1/2 hop và ảnh hưởng đến recall, nhiễu, latency.
5. PostgreSQL edge table so với graph DB trên truy vấn thật.
6. Single orchestrator so với planner-researcher-verifier có giới hạn.
7. Context đầy đủ so với context nén theo issue/citation.
8. Model nhỏ/lớn theo từng bước và chi phí trên câu trả lời được duyệt.
9. Verifier xác định so với LLM judge; đo cả false accept nguy hiểm.
10. Semantic diff parser so với LLM-assisted diff có human confirmation.

Mỗi thí nghiệm phải khai báo giả thuyết, dataset, metrics, ngưỡng thắng, chi phí
và quyết định sau thử nghiệm. Một kỹ thuật chỉ đi vào production nếu cải thiện
đáng kể chất lượng/rủi ro trên chi phí và không làm mất khả năng audit.

## 17. Việc cần làm ngay trong 30 ngày

1. Thuê/chỉ định legal-tax lead; lấy ý kiến về mô hình dịch vụ, phân loại AI và
   dữ liệu cá nhân.
2. Chốt wedge VAT/hóa đơn, ba persona và 20 workflow có giá trị cao nhất.
3. Lập source matrix: cơ quan, URL/feed, phạm vi, license, SLA, parser và owner.
4. Thiết kế ontology v0, schema bitemporal và 20 quan hệ đồ thị quan trọng.
5. Thu thập corpus thử nghiệm; kiểm tra thủ công 100 provision version.
6. Xây 100 gold cases đầu, trong đó ít nhất 30 case ranh giới hiệu lực.
7. Dựng BM25 + metadata filter baseline và citation verifier trước LLM synthesis.
8. Prototype một rule VAT có version, trace và test biên.
9. Hoàn thành threat model, data-flow map và tenant-isolation test plan.
10. Demo một luồng hoàn chỉnh: intake -> retrieval -> rule -> draft -> verify -> review.

## 18. Tiêu chí thành công của sản phẩm

Sản phẩm thành công khi chuyên gia có thể xử lý case nhanh hơn mà vẫn tái tạo
được đầy đủ lý do và chứng cứ của từng kết luận; hệ thống biết dừng khi không đủ
thông tin; luật mới tạo ra danh sách tác động có thể hành động; và mọi câu trả
lời quan trọng có thể được kiểm toán theo đúng phiên bản dữ liệu, rule và nguồn.

Khả năng "trả lời giống chuyên gia" không phải tiêu chí đủ. Tiêu chí cuối cùng
là **đúng luật tại đúng thời điểm, đúng dữ kiện, có thể kiểm chứng và có người
chịu trách nhiệm ở những quyết định cần trách nhiệm nghề nghiệp**.
