# CiteAgent VN — đánh giá và phân tích lỗi

Tài liệu này giải thích **cách đo**; con số được sinh tự động ở [`../reports/benchmark_v1.md`](../reports/benchmark_v1.md)
(JSON gốc trong [`../reports/`](../reports)). Không có số nào trong README hay dashboard được nhập tay.

## 1. Bộ dữ liệu `questions_v1`

[`evaluation/dataset_v1.py`](../evaluation/dataset_v1.py) sinh [`data/eval/questions_v1.jsonl`](../data/eval/questions_v1.jsonl):

| Loại | Số câu | Nhãn |
| --- | ---: | --- |
| Trả lời trực tiếp | 40 | 1 Điều gold, dữ kiện bắt buộc |
| Cần nhiều nguồn | 20 | ≥ 2 Điều gold (mọi Điều đều bắt buộc), dữ kiện bắt buộc của từng phần |
| Không đủ căn cứ | 15 | phải từ chối; 6 câu chỉ có căn cứ trong văn bản chưa xác minh hiệu lực (`currency_unverified`), 9 câu không có trong corpus |
| Ngoài phạm vi | 10 | phải từ chối (`out_of_scope`) |
| Mơ hồ | 5 | chấp nhận trả lời, trả lời một phần hoặc từ chối |
| Đối kháng | 10 | bất biến máy kiểm tra được: chuỗi cấm, bắt buộc có trích dẫn nếu trả lời |

- Bằng chứng gold neo theo `(document_id, Điều)` để không đổi khi chia chunk lại; 100% dữ kiện bắt buộc xuất hiện
  nguyên văn trong Điều gold (script kiểm tra khi sinh).
- Split cố định: số lẻ → `dev` (51 câu), số chẵn → `test` (49 câu). Mọi ngưỡng và tham số chỉ được chọn trên dev.
- **Giới hạn:** câu hỏi và nhãn do AI soạn từ chính nguyên văn Điều luật (`annotator: "AI draft (Claude)"`,
  `reviewed: false`). Câu hỏi vì vậy dùng từ gần với văn bản, làm số truy xuất lạc quan hơn câu hỏi thật của
  người dùng; cần một lượt người duyệt và một bộ câu hỏi diễn đạt lại.

## 2. Hệ thống được so sánh

Cùng snapshot `corpus-2026-09-30`, cùng bộ câu hỏi, cùng máy (RTX 3050 Laptop, CUDA fp16):

| Hệ thống | Truy xuất | Trả lời | Từ chối | Kiểm tra citation |
| --- | --- | --- | --- | --- |
| A | dense bge-m3 top 5 | 3 dòng đầu của 2 đoạn đứng đầu | không | không |
| B | dense 20 + BM25 20 → RRF (k=60) | như A | không | không |
| C | B → rerank bge-reranker-v2-m3 | như A | không | không |
| D | C, tách câu hỏi nhiều vế, tìm riêng từng vế | khoản/điểm nguyên văn chọn bằng cross-encoder | chính sách bằng chứng + phạm vi | đủ 6 kiểm tra |

A–C tìm trên mọi chunk thuộc phạm vi (kể cả văn bản cũ hoặc chưa xác minh hiệu lực) như một RAG đơn giản sẽ làm;
D chỉ dùng chunk đủ điều kiện cho câu hỏi hiện hành và tìm riêng các chunk chưa đủ điều kiện để giải thích lý do
từ chối. Đánh giá truy xuất (Hit@5, MRR) chạy cả ba phương pháp trên **cùng** tập ứng viên đủ điều kiện để so
sánh công bằng.

## 3. Định nghĩa chỉ số

- **Hit@5**: tỷ lệ câu (trực tiếp + nhiều nguồn) có ít nhất một Điều gold trong top 5. **MRR**: trung bình `1/rank`
  của Điều gold đầu tiên. **Đủ mọi bằng chứng@5**: với câu nhiều nguồn, tỷ lệ có đủ mọi Điều gold trong top 5.
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

## 4. Kết quả (commit `ecfeb14`, 2026-10-01)

Báo cáo ghi `ecfeb14-dirty` vì trong lúc chạy chỉ có tệp tài liệu `docs/*.md` thay đổi; mã nguồn đúng commit `ecfeb14`.
Snapshot có cùng `chunks_sha256` (`aefb3ac6…`) với các lần build trước — build tất định.

| Hệ thống | Hit@5 | MRR | Citation precision | Correctness | Refusal accuracy | Trả lời sai | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 0.983 | 0.968 | 0.541 | 0.617 | 0.667 | 15 | 0.15 s |
| B | 1.000 | 0.983 | 0.561 | 0.583 | 0.667 | 15 | 0.16 s |
| C | 1.000 | 1.000 | 0.582 | 0.600 | 0.667 | 15 | 1.0 s |
| **D** | **1.000** | **1.000** | **0.708** | **0.917** | **0.978** | **0** | 4.3 s |

D: quyết định đúng 48/49, refusal F1 0.968 (precision 0.938, recall 1.000), groundedness 1.000, 0 vi phạm đối
kháng, 30/30 ca bảo mật. Theo loại: trực tiếp 19/20, nhiều nguồn 10/10, không đủ căn cứ 7/7, ngoài phạm vi 5/5,
mơ hồ 2/2, đối kháng 5/5. Trên dev (đã dùng để hiệu chỉnh nên không phải số báo cáo chính): quyết định đúng 0.98.

## 5. Phân tích lỗi

Các ca dưới đây lấy từ `reports/answers_test_extractive_traces.jsonl` (test) và lần hiệu chỉnh trên dev.

| # | Kiểu lỗi | Ca | Điều xảy ra | Hướng xử lý |
| --- | --- | --- | --- | --- |
| 1 | Diễn đạt khác văn bản → từ chối nhầm | `dir_34` (test) | Hỏi "giữ bản chính căn cước hay văn bằng"; Điều 17 viết "giấy tờ tùy thân, văn bằng, chứng chỉ". Điểm reranker dưới ngưỡng 0.8 nên D từ chối; dense (A) cũng trượt Hit@5 câu này, BM25 cứu được ở tầng truy xuất. | Mở rộng truy vấn bằng từ đồng nghĩa pháp lý; ngưỡng theo loại câu; chế độ Claude tự tìm lại với truy vấn khác. |
| 2 | Liên quan chủ đề ≠ đủ căn cứ → trả lời sai | `una_07` (dev) | "Danh mục nghề nặng nhọc gồm những nghề nào?" — các Điều nhắc "nặng nhọc, độc hại" đạt 0.86 nên D trả lời, trong khi danh mục thật do Bộ trưởng ban hành và không có trong corpus. | Reranker đo mức liên quan, không đo khả năng trả lời: cần bước phân loại "đủ căn cứ" (LLM) hoặc nhận diện yêu cầu "danh mục/mức cụ thể". |
| 3 | Cần kết hợp và tính toán | `mul_02` (test) | "Làm 10 năm được nghỉ hằng năm bao nhiêu ngày?" cần Điều 113 (12 ngày) + Điều 114 (+1 ngày mỗi 5 năm) = 14. D trích Điều 113, thiếu Điều 114. | Chế độ extractive không suy luận; chế độ Claude được phép nêu phép tính nếu trích dẫn đủ quy tắc. |
| 4 | Vế sau mất ngữ cảnh khi tách câu | `mul_04`, `mul_14` (test) | Vế "công ty phải thanh toán trong bao lâu?" không còn chủ ngữ "khi nghỉ việc" nên điểm thấp; D trả lời PARTIAL và nêu rõ vế thiếu căn cứ (đúng chính sách, thiếu dữ kiện). | Ghép lại cụm ngữ cảnh đầu câu vào từng vế. |
| 5 | Trích thêm Điều liền kề | `dir_22`, `dir_32`, `mul_08`… | Nguồn thứ hai/ba đạt ngưỡng và trong 85% điểm cao nhất (ví dụ hỏi hình thức kỷ luật, trích thêm Điều 122, 125). Citation precision 0.708; một phần là do proxy coi Điều liên quan nhưng không gold là sai. | Chỉ giữ nguồn bổ sung khi nó chứa đoạn được chọn có điểm cao; người chấm mẫu để đo đúng precision. |
| 6 | Không có cổng bằng chứng (A–C) | `una_02`, `una_12`, `out_04`, `adv_06`… | A–C luôn trả về đoạn gần nhất: trả lời từ 145/2020 chưa xác minh hiệu lực, từ phụ lục 135/2020, trả lời câu thời tiết bằng phụ lục lương tối thiểu, trả lời "cho tôi API key" bằng phụ lục biểu mẫu. 15 trả lời sai/49. | Đây là giá trị chính của D: phạm vi, ngưỡng và trạng thái hiệu lực. |
| 7 | Truy xuất tốt hơn không tự nâng chất lượng trả lời | A→C | Hit@5 0.983 → 1.000, MRR 0.968 → 1.000 nhưng correctness của A–C dao động 0.58–0.62 vì cách ghép câu ngây thơ lấy 3 dòng đầu của đoạn. D tăng lên 0.917 nhờ chọn khoản/điểm theo câu hỏi và tìm riêng từng vế. | — |
| 8 | Độ trễ | D | Rerank chiếm 3.8/4.3 s ở p95; câu nhiều vế chạy 3 lượt tìm và chọn đoạn. Docker CPU: ~15–20 s/câu đơn. | Giảm ứng viên, chưng cất reranker, cache theo câu hỏi. |

**Kết luận:** chính sách bằng chứng loại bỏ toàn bộ 15 câu trả lời sai của RAG đơn giản trên test với một ca
từ chối nhầm; lỗi còn lại tập trung ở diễn đạt khác văn bản, câu cần kết hợp/tính toán và sự khác biệt giữa
"liên quan" và "đủ để trả lời". Số liệu truy xuất gần tuyệt đối phản ánh bộ câu hỏi soạn từ nguyên văn và
corpus nhỏ (242 chunk dùng được), không nên ngoại suy cho câu hỏi thật.

## 6. Chưa đo

- Chế độ Claude (`LLM_PROVIDER=anthropic`): đã có mã và test với client giả lập, chưa benchmark vì môi trường phát
  triển không có API key. Lệnh: `python -m evaluation.answer_eval --split test --provider anthropic --systems D`
  (tốn phí API — cần duyệt ngân sách trước khi chạy).
- Correctness/citation precision do người chấm; khoảng tin cậy (mẫu 49 câu quá nhỏ để có khoảng hẹp).
- Câu hỏi diễn đạt lại / câu hỏi thật của người dùng (dữ liệu phản hồi trong `sessions.sqlite3` có thể dùng sau).
