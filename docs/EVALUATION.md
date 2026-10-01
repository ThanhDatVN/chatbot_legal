# CiteAgent VN — đánh giá và phân tích lỗi

Tài liệu này giải thích **cách đo**; con số được sinh tự động ở [`../reports/benchmark_v2.md`](../reports/benchmark_v2.md)
(JSON gốc trong [`../reports/`](../reports)). Không có số nào trong README hay dashboard được nhập tay. Báo cáo
v1 ([`benchmark_v1.md`](../reports/benchmark_v1.md), snapshot `corpus-2026-09-30`) được giữ để đối chiếu.

## 1. Bộ dữ liệu `questions_v2`

[`evaluation/dataset_v2.py`](../evaluation/dataset_v2.py) sinh [`data/eval/questions_v2.jsonl`](../data/eval/questions_v2.jsonl)
từ v1 ([`dataset_v1.py`](../evaluation/dataset_v1.py)) và liệt kê từng thay đổi:

| Loại | Số câu | Nhãn |
| --- | ---: | --- |
| Trả lời trực tiếp | 44 | 1 Điều gold (có thể kèm Điều thay thế tương đương), dữ kiện bắt buộc |
| Cần nhiều nguồn | 20 | ≥ 2 Điều gold (mọi Điều đều bắt buộc), dữ kiện bắt buộc của từng phần |
| Không đủ căn cứ | 15 | phải từ chối; 6 câu chỉ có căn cứ ở điều khoản đã hết hiệu lực/bị thay thế bởi văn bản ngoài kho (`superseded_by_amendment`), 9 câu không có trong corpus |
| Ngoài phạm vi | 10 | phải từ chối (`out_of_scope`) |
| Mơ hồ | 5 | chấp nhận trả lời, trả lời một phần hoặc từ chối |
| Đối kháng | 10 | bất biến máy kiểm tra được: chuỗi cấm, bắt buộc có trích dẫn nếu trả lời |

- Bằng chứng gold neo theo `(document_id, Điều)` để không đổi khi chia chunk lại; dữ kiện bắt buộc của câu mới và
  của mọi Điều gold thay thế được kiểm tra xuất hiện nguyên văn trong Điều đó khi sinh bộ dữ liệu.
- Split cố định: số lẻ → `dev` (53 câu), số chẵn → `test` (51 câu). Mọi ngưỡng và tham số chỉ được chọn trên dev.
- **Giới hạn:** câu hỏi và nhãn do AI soạn từ chính nguyên văn Điều luật (`annotator: "AI draft (Claude)"`,
  `reviewed: false`). Câu hỏi vì vậy dùng từ gần với văn bản, làm số truy xuất lạc quan hơn câu hỏi thật của
  người dùng; cần một lượt người duyệt và một bộ câu hỏi diễn đạt lại.

### Thay đổi so với v1 và lý do

Snapshot `corpus-2026-10-01` áp dụng sổ theo dõi hiệu lực cấp điều khoản
([`DATA_QUALITY_ASSESSMENT.md` §7](DATA_QUALITY_ASSESSMENT.md#7-sổ-theo-dõi-hiệu-lực-cấp-điều-khoản-2026-10-01)), nên đáp án đúng của một số câu thay đổi:

1. 4 câu v1 phải từ chối vì văn bản "chưa xác minh hiệu lực" nay có căn cứ còn hiệu lực theo sổ (hồ sơ cấp giấy
   phép lao động — Điều 18 Nghị định 219/2025; danh mục công việc cho thuê lại — Phụ lục II, sổ quản lý lao động —
   Điều 3, báo trước của thành viên tổ lái tàu bay — Điều 7 Nghị định 145/2020) → chuyển thành `dir_41`–`dir_44`.
2. Chỗ trống của chúng trong nhóm "không đủ căn cứ" (`una_01`, `una_02`, `una_10`, `una_11`) nhận 4 câu mới mà căn
   cứ duy nhất là điều khoản đã hết hiệu lực hoặc đang thực hiện theo văn bản ngoài kho; `una_14` đổi lý do sang
   `superseded_by_amendment`.
3. `una_12` (tháng bắt đầu hưởng lương hưu) bị thay: quy tắc tại khoản 2 Điều 3 Nghị định 135/2020 đã hết hiệu lực
   nhưng Phụ lục I còn cột "thời điểm hưởng lương hưu", nên đáp án đúng là câu hỏi pháp lý chưa giải quyết.
4. 7 câu trả lời từ Bộ luật Lao động nhận thêm Điều của nghị định hướng dẫn làm gold thay thế. 3 được thêm khi đưa
   văn bản mới vào kho; 4 được thêm **sau khi xem kết quả truy xuất** theo quy tắc cố định: ứng viên là các Điều
   nghị định nằm trong top 5 và chứa nguyên văn mọi dữ kiện bắt buộc, sau đó đọc từng ứng viên và chỉ giữ Điều
   nêu đúng quy tắc được hỏi (giữ 5/17, loại các trùng chuỗi như "24 giờ" trong Điều về người giúp việc gia
   đình). Điều chỉnh nhãn sau khi xem kết quả có thể làm số truy xuất lạc quan hơn; các câu bị ảnh hưởng là
   `dir_07`, `dir_11`, `dir_17`, `dir_19`, `dir_25`.

Các câu khác giữ nguyên id, nội dung, nhãn và split.

## 2. Hệ thống được so sánh

Cùng snapshot `corpus-2026-10-01`, cùng bộ câu hỏi, cùng máy (RTX 3050 Laptop, CUDA fp16):

| Hệ thống | Truy xuất | Trả lời | Từ chối | Kiểm tra citation |
| --- | --- | --- | --- | --- |
| A | dense bge-m3 top 5 | 3 dòng đầu của 2 đoạn đứng đầu | không | không |
| B | dense 20 + BM25 20 → RRF (k=60) | như A | không | không |
| C | B → rerank bge-reranker-v2-m3 | như A | không | không |
| D | C, tách câu hỏi nhiều vế, tìm riêng từng vế | khoản/điểm nguyên văn chọn bằng cross-encoder | chính sách bằng chứng + phạm vi + hiệu lực | đủ 6 kiểm tra |

A–C tìm trên mọi chunk thuộc phạm vi (kể cả văn bản cũ, hết hiệu lực hoặc chưa xác minh) như một RAG đơn giản
sẽ làm; D chỉ dùng chunk đủ điều kiện cho câu hỏi hiện hành và tìm riêng các chunk chưa đủ điều kiện để giải
thích lý do từ chối. Từ v2, D từ chối với lý do `superseded_by_amendment` khi một điều đã hết hiệu lực/bị thay thế
mà văn bản thay thế không có trong kho xếp hạng cao hơn mọi bằng chứng hợp lệ (`superseded_margin = 0.0`, chọn trên
dev: số trả lời sai trên dev 3 → 1, số từ chối nhầm không đổi). Đánh giá truy xuất (Hit@5, MRR) chạy cả ba phương
pháp trên **cùng** tập ứng viên đủ điều kiện để so sánh công bằng.

## 3. Định nghĩa chỉ số

- **Hit@5**: tỷ lệ câu (trực tiếp + nhiều nguồn) có ít nhất một Điều gold trong top 5. **MRR**: trung bình `1/rank`
  của Điều gold đầu tiên. **Đủ mọi bằng chứng@5**: với câu nhiều nguồn, tỷ lệ có đủ mọi Điều gold bắt buộc trong top 5.
- **Quyết định đúng**: quyết định (ANSWER/PARTIAL/REFUSE) thuộc tập chấp nhận của câu.
- **Refusal accuracy / precision / recall / F1**: trên các câu có nhãn `should_refuse` (bỏ câu mơ hồ và đối kháng
  không xác định), lớp dương là REFUSE. **Trả lời sai** = trả lời khi phải từ chối; **từ chối nhầm** = từ chối
  khi có căn cứ.
- **Correctness (proxy)**: với câu trả lời được, 2 nếu câu trả lời chứa mọi dữ kiện bắt buộc, 1 nếu chứa một phần,
  0 nếu không chứa hoặc từ chối; báo cáo trung bình/2 và phân bố. Đây là phép so khớp chuỗi, không phải người chấm.
- **Citation precision (proxy)**: tỷ lệ trích dẫn trỏ tới một Điều gold hoặc có chứa dữ kiện bắt buộc. Trích dẫn tới
  Điều liên quan nhưng không nằm trong nhãn gold bị tính là sai, nên chỉ số này **chặt hơn** đánh giá của người.
- **Groundedness**: tỷ lệ nhận định có text xuất hiện nguyên văn trong nguồn được trích. Ở chế độ extractive chỉ
  số này bằng 1 theo cấu trúc; nó có ý nghĩa khi chạy chế độ Claude.
- **Độ trễ**: p50/p95 toàn request sau khi model đã nạp, kèm thời gian truy xuất và rerank. **Chi phí**: chi phí API
  LLM trên 100 câu theo giá niêm yết (Claude Opus 5.5: $4/$20 mỗi triệu token vào/ra); chế độ extractive = $0
  API nhưng GPU và điện không miễn phí.

## 4. Kết quả (commit `33f11cc`, 2026-10-01)

| Hệ thống | Hit@5 | MRR | Citation precision | Correctness | Refusal accuracy | Trả lời sai | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 0.984 | 0.922 | 0.529 | 0.578 | 0.681 | 15 | 0.09 s |
| B | 0.984 | 0.947 | 0.549 | 0.547 | 0.681 | 15 | 0.09 s |
| C | 1.000 | 0.982 | 0.578 | 0.562 | 0.681 | 15 | 1.0 s |
| **D** | **1.000** | **0.982** | **0.634** | **0.891** | **0.957** | **1** | 4.2 s |

D: quyết định đúng 49/51, refusal F1 0.933 (precision 0.933, recall 0.933), groundedness 1.000, 0 vi phạm đối
kháng, 30/30 ca bảo mật. Theo loại: trực tiếp 21/22, nhiều nguồn 10/10, không đủ căn cứ 6/7, ngoài phạm vi 5/5,
mơ hồ 2/2, đối kháng 5/5. Trên dev (đã dùng để hiệu chỉnh nên không phải số báo cáo chính): quyết định đúng 0.962.

**So với v1** (snapshot `corpus-2026-09-30`, test 49 câu): D có quyết định đúng 0.980, 0 trả lời sai, MRR 1.000,
citation precision 0.708, correctness 0.917. Hai lần đo **không cùng điều kiện**: corpus dùng được tăng từ 242 lên
504 chunk (thêm các Điều còn hiệu lực của bốn nghị định hướng dẫn và Nghị định 219/2025), nên có nhiều ứng viên cạnh
tranh hơn, và câu hỏi về điều khoản bị thay thế là loại câu khó mới. Mức giảm citation precision và MRR là có thật
và được phân tích ở mục 5 (lỗi 3 và 6).

## 5. Phân tích lỗi

Các ca dưới đây lấy từ `reports/answers_test_extractive_traces.jsonl` (test) và lần hiệu chỉnh trên dev.

| # | Kiểu lỗi | Ca | Điều xảy ra | Hướng xử lý |
| --- | --- | --- | --- | --- |
| 1 | Diễn đạt khác văn bản → từ chối nhầm | `dir_34` (test) | Hỏi "giữ bản chính căn cước hay văn bằng"; Điều 17 viết "giấy tờ tùy thân, văn bằng, chứng chỉ". Điểm reranker dưới ngưỡng 0.8 nên D từ chối; dense (A) và hybrid (B) cũng trượt Hit@5. | Mở rộng truy vấn bằng từ đồng nghĩa pháp lý; ngưỡng theo loại câu; chế độ Claude tự tìm lại với truy vấn khác. |
| 2 | Reranker bão hòa → trả lời từ điều lân cận | `una_10` (test) | "Hồ sơ gia hạn giấy phép lao động" — Điều 27 Nghị định 219/2025 đang thực hiện theo Nghị quyết 24/2026 (ngoài kho). Reranker cho cả Điều 27 lẫn Điều 18, 20 (hồ sơ *cấp*, *cấp cho trường hợp đã có giấy phép*) ~0,999, nên quy tắc `superseded_margin` không tách được; D trích Điều 20 và 18. | Reranker đo "liên quan", không đo "đúng thủ tục được hỏi": cần bước kiểm tra khả năng trả lời (LLM) hoặc so khớp tiêu đề Điều với thủ tục trong câu hỏi; bổ sung Nghị quyết 24/2026 vào kho. |
| 3 | Trích thêm Điều nghị định về chế độ riêng | `dir_10`, `dir_18`, `dir_22`, `mul_06` (test) | Từ khi các Điều còn hiệu lực của 145/2020 được dùng, Điều 89 (quy định riêng cho người giúp việc gia đình) được trích kèm cho câu hỏi chung về nghỉ hằng tuần, thanh toán khi chấm dứt hợp đồng và hình thức kỷ luật. 21/23 trích dẫn 145/2020 trên test không thuộc gold; một phần là hợp lý (Điều 8 về trợ cấp thôi việc) nhưng Điều 89 là nhiễu thật. Citation precision 0.708 → 0.634. | Nhận diện Điều áp dụng cho đối tượng riêng (tiêu đề "đối với lao động là…") và chỉ dùng khi câu hỏi nhắc đối tượng đó; người chấm mẫu để tách phần do proxy. |
| 4 | Liên quan chủ đề ≠ đủ căn cứ → trả lời sai | `una_07` (dev) | "Danh mục nghề nặng nhọc gồm những nghề nào?" — các Điều nhắc "nặng nhọc, độc hại" vượt ngưỡng nên D trả lời, trong khi danh mục thật do Bộ trưởng ban hành và không có trong corpus. | Như lỗi 2: bước phân loại "đủ căn cứ" hoặc nhận diện yêu cầu "danh mục/mức cụ thể". |
| 5 | Phụ lục dạng danh sách: chọn nhầm dòng tiêu đề | `dir_42` (test) | Hỏi danh mục công việc cho thuê lại; D trích đúng Phụ lục II nhưng bộ chọn đoạn lấy dòng tiêu đề "CHO THUÊ LẠI LAO ĐỘNG" thay vì các dòng công việc. Quyết định đúng, nội dung thiếu. Phát hiện trên test nên **chưa sửa** để không chỉnh hệ thống theo split test. | Loại dòng tiêu đề phụ lục (chữ in hoa, "Kèm theo…") khỏi đơn vị trích; với phụ lục danh sách trả về các dòng bảng. Kiểm chứng trên dev/bộ câu mới. |
| 6 | Nhiều ứng viên còn hiệu lực hơn → MRR giảm | `dir_41`, `mul_03` | Corpus dùng được tăng gấp đôi: Điều 20 Nghị định 219/2025 xếp trên Điều 18 cho câu hỏi hồ sơ cấp giấy phép; Điều 55 Nghị định 145/2020 (tiền lương làm thêm giờ) xếp trên Điều 98 và 107 Bộ luật cho câu hỏi hai vế về làm thêm giờ. Hit@5 vẫn 1.000, MRR 1.000 → 0.982. | Đây là cái giá của corpus thật hơn; đo lại khi có câu hỏi do người viết. |
| 7 | Cần kết hợp và tính toán | `mul_02` (test) | "Làm 10 năm được nghỉ hằng năm bao nhiêu ngày?" cần Điều 113 (12 ngày) + Điều 114 (+1 ngày mỗi 5 năm) = 14. D trích Điều 113, thiếu Điều 114. | Chế độ extractive không suy luận; chế độ Claude được phép nêu phép tính nếu trích dẫn đủ quy tắc. |
| 8 | Vế sau mất ngữ cảnh khi tách câu | `mul_04`, `mul_14` (test) | D trả lời PARTIAL và nêu rõ vế thiếu căn cứ (đúng chính sách, thiếu dữ kiện). | Ghép lại cụm ngữ cảnh đầu câu vào từng vế. |
| 9 | Không có cổng bằng chứng (A–C) | `una_02`, `una_12`, `una_14`, `out_04`, `adv_06`… | A–C luôn trả về đoạn gần nhất: trả lời câu về ký quỹ cho thuê lại bằng Điều 15 Nghị định 145/2020 đã bị thay thế, câu về danh mục khai thác than bằng Phụ lục III 135/2020 đã hết hiệu lực, câu thời tiết bằng phụ lục lương tối thiểu. 15 trả lời sai/51. | Đây là giá trị chính của D: phạm vi, ngưỡng và trạng thái hiệu lực theo điều khoản. |
| 10 | Độ trễ | D | Rerank chiếm 3.8/4.2 s ở p95; câu nhiều vế chạy 3 lượt tìm và chọn đoạn. Docker CPU: ~15–20 s/câu đơn. | Giảm ứng viên, chưng cất reranker, cache theo câu hỏi. |

**Kết luận:** chính sách bằng chứng vẫn loại bỏ 14/15 câu trả lời sai của RAG đơn giản trên test, kể cả các câu
mà RAG đơn giản trả lời bằng điều khoản đã bị thay thế; lỗi còn lại tập trung ở chỗ reranker không phân biệt
"liên quan" với "đúng thủ tục được hỏi", nhiễu từ các Điều về đối tượng riêng, và diễn đạt khác văn bản. Số liệu
truy xuất gần tuyệt đối phản ánh bộ câu hỏi soạn từ nguyên văn và corpus nhỏ (504 chunk dùng được), không nên
ngoại suy cho câu hỏi thật.

## 6. Chưa đo

- Chế độ Claude (`LLM_PROVIDER=anthropic`): đã có mã và test với client giả lập, chưa benchmark vì môi trường phát
  triển không có API key. Lệnh: `python -m evaluation.answer_eval --split test --provider anthropic --systems D`
  (tốn phí API — cần duyệt ngân sách trước khi chạy).
- Correctness/citation precision do người chấm; khoảng tin cậy (mẫu 51 câu quá nhỏ để có khoảng hẹp).
- Câu hỏi diễn đạt lại / câu hỏi thật của người dùng (dữ liệu phản hồi trong `sessions.sqlite3` có thể dùng sau).
- Độ chính xác của sổ theo dõi hiệu lực so với ý kiến chuyên gia (sổ chưa có người duyệt).
