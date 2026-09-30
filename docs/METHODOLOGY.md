# CiteAgent VN — phương pháp xây corpus và đánh giá

Trạng thái: cập nhật sau [pilot 10 văn bản](PILOT_10_DOCUMENTS.md) và [nghiên cứu khắc phục chất lượng](REMEDIATION_RESEARCH.md) · 2026-09-25. Mục đích của tài liệu là để người khác có thể lặp lại cách chọn nguồn, tạo nhãn và đo kết quả. Các con số trong ví dụ là **ngưỡng thử nghiệm**, không phải kết quả benchmark.

## 1. Câu hỏi nghiên cứu

1. Corpus được chọn có đúng phạm vi quan hệ lao động, có provenance và được cập nhật theo một mốc thời gian công bố không?
2. Hybrid retrieval và reranking có cải thiện việc tìm đúng chứng cứ so với dense baseline trên cùng snapshot không?
3. Hệ thống có giảm câu trả lời thiếu căn cứ và citation sai mà không từ chối quá nhiều câu hỏi có thể trả lời không?
4. Chi phí, độ trễ và các trường hợp thất bại có được báo cáo đủ để đánh giá trade-off không?

Mọi báo cáo ghi `as_of_date`, `corpus_snapshot_id`, git commit, dataset version, model revisions và cấu hình. Không mô tả hệ thống là cập nhật thời gian thực.

## 2. Protocol xây corpus

### 2.1. Phạm vi

MVP chỉ hỗ trợ quy định **hiện hành tại ngày snapshot** về quan hệ giữa người lao động và người sử dụng lao động theo Bộ luật Lao động và văn bản trực tiếp hướng dẫn/sửa đổi: hợp đồng, thử việc, tiền lương, thời giờ làm việc/nghỉ, làm thêm, kỷ luật, chấm dứt, trợ cấp, đối thoại, thỏa ước, tuổi nghỉ hưu và lao động nước ngoài khi văn bản trực tiếp liên quan. Không mặc nhiên bao gồm BHXH, thuế, công chức/viên chức, an toàn vệ sinh lao động, công đoàn và quy định địa phương. Nếu câu hỏi chạm vùng giao nhau, ghi `out_of_scope` hoặc `PARTIAL` theo evidence thực có.

### 2.2. Nguồn và seed

- Nguồn khám phá ưu tiên: `vbpl.vn`; nguồn đối chiếu/bổ sung bản văn chính thức: `vanban.chinhphu.vn`. Pilot trong môi trường này không truy cập được trang chi tiết VBPL, nên mỗi adapter phải có access probe và đường fallback chính thức. Không dùng redirect về trang chủ như một kết quả metadata hợp lệ. Các domain khác cần quyết định ghi vào manifest trước khi thu thập.
- Seed đề xuất: Bộ luật Lao động 45/2019/QH14, Nghị định 145/2020/NĐ-CP, Nghị định 135/2020/NĐ-CP và văn bản hợp nhất liên quan nếu xác minh được tại thời điểm thu thập. **Đây là danh sách ứng viên**, không phải tuyên bố về tình trạng hiệu lực hoặc nội dung hiện hành.
- Mỗi seed được reviewer xác nhận số ký hiệu, issuer, URL, loại văn bản, status, các quan hệ và ngày kiểm tra trên trang chính thức. Ghi cả URL metadata và URL file thực tế.

Trang chính thức dùng làm điểm bắt đầu tham chiếu: [Bộ luật Lao động 45/2019/QH14 trên Cổng văn bản Chính phủ](https://vanban.chinhphu.vn/?classid=1&docid=198540&pageid=27160&typegroupid=3), [lịch sử Nghị định 145/2020/NĐ-CP trên VBPL](https://vbpl.vn/bolaodong/Pages/ivbpq-lichsu.aspx?ItemID=152668&Keyword=), [lược đồ Nghị định 145/2020/NĐ-CP trên VBPL](https://vbpl.vn/bolaodong/pages/ivbpq-luocdo.aspx?ItemID=152668). Tính đúng đắn của thông tin ghi trong corpus phải được kiểm tra lại khi tạo snapshot.

### 2.3. Khám phá ứng viên

Thu metadata từ seed và, khi nguồn quan hệ truy cập được, duyệt BFS tối đa depth 2 qua quan hệ `amends`, `replaces`, `implements`, `guides`, `consolidates`. Nếu endpoint relation không truy cập được, lập relation table từ trang/văn bản chính thức được reviewer kiểm tra; ghi `discovery_mode=manual_fallback` và coverage chưa biết. Chỉ lưu edge khi có URL nguồn và loại quan hệ đọc được; quan hệ mơ hồ gắn `unverified` để review. Deduplicate bằng số ký hiệu + issuer + ngày ban hành, có fallback canonical URL. Lưu toàn bộ candidate pool, kể cả loại, để audit mức coverage.

Crawler giới hạn tốc độ, có timeout/retry có giới hạn, nhận diện lỗi nguồn, không vượt allowlist qua redirect. Thu **metadata trước nội dung**; chỉ download PDF/HTML sau khi candidate được duyệt. Nếu nguồn thiếu file hoặc parser lỗi, ghi trạng thái rõ; không tự tìm bản sao không chính thức.

### 2.4. Filter và review

Hard filters: domain chính thức, loại văn bản chấp nhận (`Bộ luật`, `Luật`, `Nghị định`, `Thông tư`, `Thông tư liên tịch`, `Văn bản hợp nhất`), phạm vi toàn quốc và không phải dự thảo/tin tức. Văn bản `expired` không vào current corpus; có thể lưu metadata cho quan hệ lịch sử. `partially_expired` được review ở cấp điều khoản. Không dùng status `unknown` để khẳng định hiện hành.

Điểm liên quan là công cụ **xếp hàng review**, không tự chứng minh văn bản thuộc phạm vi. Feature: quan hệ trực tiếp với seed/corpus, lĩnh vực, taxonomy chủ đề, negative terms về tổ chức/nhân sự/kế hoạch, và similarity title+trích yếu với mô tả phạm vi. Trọng số `+10` quan hệ trực tiếp, `+4` metadata, `-6` negative term; các mốc include/review/exclude trong `data.md` chỉ là khởi tạo. Khóa trọng số trước khi chấm toàn bộ candidate pool; ghi version và phân bố điểm. Không auto include chỉ nhờ semantic similarity.

`data/review/candidates.csv` tối thiểu có candidate ID, URL, document number, title, relation paths, status, score + feature breakdown, proposed decision, reviewer decision, reason, reviewer, timestamp. Queue ưu tiên vùng điểm mơ hồ. Người review phải mở trang nguồn và kiểm tra scope, loại, status, quan hệ. Nếu điểm cao nhưng reviewer loại, giữ cả hai quyết định và lý do. Thay đổi quyết định sau snapshot tạo snapshot mới.

### 2.5. Kiểm tra hiệu lực và văn bản hợp nhất

Ghi `legal_status` của tài liệu như website công bố tại `verified_at`. Với `partially_expired`, reviewer đối chiếu văn bản sửa đổi và bản hợp nhất, lập mapping điều/khoản bị sửa; đánh dấu chunk `verified_current`, `historical`, hoặc `unverified`. Chỉ `verified_current` được truy xuất cho câu hỏi hiện hành. Nếu bản hợp nhất được dùng, lưu quan hệ đến văn bản gốc và các văn bản sửa đổi; citation hiển thị đúng tên/loại nguồn được trích, không gọi nó là luật mới.

Khi thiếu mapping, corpus coverage giảm có chủ đích. Hệ thống báo chưa đủ căn cứ, không chọn bản cũ chỉ vì điểm retrieval cao. Tạo regression case cho từng tình huống sửa đổi phức tạp.

### 2.6. Snapshot và audit

Snapshot chứa: manifest JSONL, raw source bytes hoặc đường dẫn có hash, review CSV, relation graph, parser/chunker/tokenizer/model revisions, BM25 artifact, Qdrant collection ID, `as_of_date`, checksums. Manifest ghi `license` hoặc `publicly_accessible_unknown_license`; chỉ liên kết công khai tới source nếu quyền phân phối lại bytes chưa rõ. Corpus mục tiêu khoảng 30–50 văn bản đã review; số thực tế dựa trên coverage, không lấy số lượng làm mục tiêu độc lập.

Kiểm tra phát hành: 100% tài liệu có provenance và hash; chunk truy ngược được tới nguồn; không có ID trùng/empty chunk; active index cùng snapshot; truy vấn mẫu trả chunk đúng; fixture nguồn có sửa đổi không được trả lời như quy định hiện hành khi status chưa xác minh.

### 2.7. PDF scan, OCR và QA text nguồn

Thử trích text native trước. Phát hiện scan bằng tỷ lệ trang có text thực và ảnh phủ trang; không lấy vài từ footer/ký số làm dấu hiệu toàn văn có thể trích. Nếu là scan, ưu tiên bản toàn văn HTML chính thức có thể truy cập; nếu không, OCR offline với language data tiếng Việt đã khóa hash. Lưu riêng PDF gốc, text native, text OCR, page number, engine/model/DPI và trạng thái review. Không sửa OCR text âm thầm bằng paraphrase hoặc LLM.

OCR chunk chỉ được gắn `text_quality_status=verified` sau khi reviewer đối chiếu ảnh nguồn, đặc biệt số ký hiệu, ngày, ngưỡng số, ngoại lệ và điều khoản được dùng trong gold/demo. Giữ số ký hiệu/ngày từ metadata nguồn độc lập; so khớp OCR để tạo cảnh báo, không ghi đè metadata bằng OCR. Phụ lục/biểu mẫu và trích dẫn sửa luật cần `section_kind`/`section_path` riêng. Nếu không đủ nguồn lực review, loại khỏi current QA index và công bố khoảng trống coverage. Pilot 10 PDF đều là scan, OCR được 496 trang nhưng còn lỗi; số đo ở [`PILOT_10_DOCUMENTS.md`](PILOT_10_DOCUMENTS.md) và [`DATA_QUALITY_ASSESSMENT.md`](DATA_QUALITY_ASSESSMENT.md) chỉ định hướng kỹ thuật, không chứng minh OCR đủ chính xác cho kết luận pháp lý.

## 3. Protocol lập dataset

### 3.1. Tập 100 câu hỏi tối thiểu

| Nhóm | Số câu mục tiêu | Nhãn chính |
| --- | ---: | --- |
| Có thể trả lời trực tiếp | 40 | gold source/section, answer |
| Cần nhiều nguồn | 20 | ít nhất hai gold evidence |
| Không đủ bằng chứng | 15 | `should_refuse=true` |
| Ngoài phạm vi | 10 | `should_refuse=true` |
| Mơ hồ | 5 | nhãn theo diễn giải và policy |
| Đối kháng / bảo mật | 10 | expected behavior |

Security suite độc lập có **ít nhất 30 ca**; 10 câu đối kháng trong eval có thể trùng chủ đề nhưng ID/test run riêng. Có ít nhất 5 ca indirect prompt injection từ nội dung tài liệu. Dataset chứa câu hỏi tự viết hoặc lấy từ tình huống thực có quyền sử dụng; tránh copy nguyên văn câu điều luật làm query duy nhất vì dễ tạo lexical leakage.

### 3.2. Nhãn gold

Mỗi record có `id`, `question`, `type`, `scope`, `as_of_date`, `should_refuse`, `gold_document_ids`, `gold_section_paths`, `gold_chunk_ids` của snapshot hiện hành, `reference_answer`, `required_claims`, `notes`, `annotator`, `reviewed_at`. Gold section/document là neo bền qua lần chunk lại; gold chunk IDs chỉ hợp lệ với snapshot được ghi. Với OCR, annotator kiểm tra gold trực tiếp trên ảnh/PDF nguồn, không lấy OCR text làm chuẩn duy nhất. Câu hỏi ngoài phạm vi không có gold chunk ép buộc. Với câu nhiều nguồn, ghi tập chứng cứ tối thiểu cần thiết.

Hai lượt nhãn: người tạo nhãn xác định nguồn và câu trả lời; lượt review mở trực tiếp source để xác nhận đủ căn cứ, tình trạng hiệu lực và chỗ mơ hồ. Bất đồng lưu `adjudication_note`. Tách tập development/validation/holdout trước khi tune threshold, tokenizer hoặc prompt; giữ holdout cố định để tránh chỉnh theo test. Không để biến thể câu hỏi gần trùng xuất hiện ở nhiều split.

## 4. Thước đo và cách tính

### 4.1. Retrieval

- `Hit@5`: tỷ lệ câu answerable có ít nhất một gold evidence trong top 5. Với câu multi-source, báo thêm `all_evidence@5` = tỷ lệ có đủ tập chứng cứ tối thiểu trong top 5.
- `MRR`: trung bình `1/rank` của gold evidence đầu tiên; câu answerable không tìm thấy đóng góp 0. Ghi rõ mẫu số chỉ gồm answerable in-scope.
- Báo thêm Recall@5/10 khi hữu ích. So sánh A/B/C trên cùng snapshot, split và filter; lưu danh sách result per query.

### 4.2. Câu trả lời và citation

- Correctness: 0 sai, 1 đúng một phần, 2 đúng, đối chiếu gold và nguồn; báo phân bố từng mức và mean/2.
- Groundedness: số factual claims được cited evidence hỗ trợ / tổng factual claims. Claim thiếu nguồn tính không grounded.
- Citation precision: số citation thực sự hỗ trợ claim được gắn / tổng citation cho factual claims; citation tồn tại nhưng chỉ liên quan chủ đề vẫn tính sai.
- Với `PARTIAL`, đánh giá riêng phần trả lời đúng và mức trung thực của phần nói chưa đủ căn cứ.
- Judge model có thể sàng lọc quy mô lớn, nhưng lưu model/prompt/version; lấy mẫu thủ công để ước lượng lỗi judge. Không dùng kết quả LLM judge như sự thật không kiểm tra.

### 4.3. Refusal

Từ `should_refuse`, tính precision, recall, F1 và accuracy cho việc từ chối. Báo riêng `false answer` (trả lời khi phải từ chối) và `false refusal` (từ chối khi có nguồn đủ). `PARTIAL` được quy định nhãn trước theo required claims; không tùy tiện tính là thành công hoàn toàn. Phân nhóm lý do `out_of_scope`, `insufficient_evidence`, `conflicting_sources`, `currency_unverified` để nhận diện lỗi corpus và policy.

### 4.4. Độ trễ, chi phí, bảo mật

Đo p50/p95 của retrieval, rerank, generation và end-to-end trên cùng cấu hình máy; công bố số lần chạy, điều kiện cache nóng/lạnh, batch size và hardware. Tính chi phí/100 câu từ token input/output và giá provider tại ngày benchmark; nếu model local, ghi API cost = 0 và thông số máy/tài nguyên, không gọi tổng chi phí là 0.

Security suite kiểm tra instruction override, fabricated citation, tool misuse, request vượt phạm vi, data exfiltration, indirect injection và URL/source manipulation. Mỗi test có input, fixture, expected invariants và kết quả máy kiểm tra được; ca semantic cần review thủ công. Ghi tỷ lệ pass theo nhóm và tất cả failure, không chỉ tổng pass.

## 5. Quy trình thí nghiệm

1. Đóng băng corpus snapshot, dataset version, model revisions, prompt và điều kiện máy.
2. Chạy baseline A; lưu per-query retrieval/answer/citation traces và report. Không tune khi chưa có baseline.
3. Chạy B, C, D cùng đầu vào. Thay một thành phần ở mỗi bước; lưu config diff.
4. Tune trên validation split; chạy holdout một lần cho phiên bản đã chốt. Nếu đổi corpus hoặc gold labels, tạo experiment version mới.
5. Phân tích 10–20 failure cases: lexical mismatch, sai Điều, status mơ hồ, thiếu context, reranker lỗi, citation không support, false answer/refusal.
6. Báo con số thật, mẫu số, confidence interval khi dữ liệu đủ và giới hạn của dataset; không điền bảng trước khi chạy.

## 6. Checklist xuất bản kết quả

- Có manifest và review trail cho tất cả tài liệu được index.
- Có version của dataset, snapshot, models, prompts, thresholds, code commit.
- Báo đủ A/B/C/D, các metric bắt buộc và phân tích lỗi.
- Demo bốn ca: trả lời rõ, nhiều nguồn, từ chối, prompt injection.
- README nêu phạm vi pháp lý, ngày snapshot và giới hạn, không trình bày ứng dụng như nguồn tư vấn pháp lý cập nhật liên tục.

Các tài liệu nguồn kỹ thuật liên quan: [Qdrant payload/filtering](https://qdrant.tech/documentation/concepts/payload/), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/). Quy trình corpus là thiết kế của project dựa trên [`../data.md`](../data.md), không phải tính năng được các nguồn kỹ thuật này bảo đảm.
