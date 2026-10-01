# CiteAgent VN — đánh giá và phân tích lỗi

Tài liệu này giải thích **cách đo**; con số được sinh tự động ở [`../reports/benchmark_v3.md`](../reports/benchmark_v3.md)
(JSON gốc trong [`../reports/`](../reports); chạy lại toàn bộ bằng `python scripts/run_benchmark.py`). Không có số nào
trong README hay dashboard được nhập tay. Báo cáo cũ được giữ để đối chiếu: [`benchmark_v1.md`](../reports/benchmark_v1.md)
(snapshot `corpus-2026-09-30`), [`benchmark_v2.md`](../reports/benchmark_v2.md) (snapshot `corpus-2026-10-01`).

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

Cùng snapshot `corpus-2026-10-01-r2`, cùng bộ câu hỏi, cùng máy (RTX 3050 Laptop, CUDA fp16):

| Hệ thống | Truy xuất | Trả lời | Từ chối | Kiểm tra citation |
| --- | --- | --- | --- | --- |
| A | dense bge-m3 top 5 | 3 dòng đầu của 2 đoạn đứng đầu | không | không |
| B | dense 20 + BM25 20 → RRF (k=60) | như A | không | không |
| C | B → rerank bge-reranker-v2-m3 | như A | không | không |
| D | C với truy vấn được bổ sung thuật ngữ pháp lý; tách câu hỏi nhiều vế, tìm riêng từng vế | khoản/điểm nguyên văn chọn bằng cross-encoder; nguồn bổ sung phải có khoản đạt `unit_threshold` | chính sách bằng chứng + phạm vi + hiệu lực | đủ 6 kiểm tra |

A–C tìm trên mọi chunk thuộc phạm vi (kể cả văn bản cũ, hết hiệu lực hoặc chưa xác minh) như một RAG đơn giản
sẽ làm; D chỉ dùng chunk đủ điều kiện cho câu hỏi hiện hành và tìm riêng các chunk chưa đủ điều kiện để giải
thích lý do từ chối. D từ chối với lý do `superseded_by_amendment` khi một điều đã hết hiệu lực/bị thay thế mà văn
bản thay thế không có trong kho xếp hạng cao hơn mọi bằng chứng hợp lệ (`superseded_margin = 0.0`). Mọi ngưỡng được
chọn trên dev v2 và bộ paraphrase dev ([`reports/policy_tuning.json`](../reports/policy_tuning.json)). Đánh giá truy
xuất (Hit@5, MRR) chạy mọi phương pháp trên **cùng** tập ứng viên đủ điều kiện.

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

## 4. Kết quả trên bộ v2 (commit `edd90b9`, 2026-10-01)

| Hệ thống | Hit@5 | MRR | Citation precision | Correctness | Refusal accuracy | Trả lời sai | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 0.984 | 0.922 | 0.529 | 0.578 | 0.681 | 15 | 0.13 s |
| B | 0.984 | 0.947 | 0.549 | 0.547 | 0.681 | 15 | 0.15 s |
| C | 1.000 | 0.982 | 0.578 | 0.562 | 0.681 | 15 | 1.0 s |
| **D** | **1.000** | **0.982** | **0.651** | **0.922** | **0.979** | **1** | 4.4 s |

D: quyết định đúng 50/51, refusal F1 0.966 (precision 1.000, recall 0.933), 0 từ chối nhầm, groundedness 1.000,
0 vi phạm đối kháng, 30/30 ca bảo mật. Theo loại: trực tiếp 22/22, nhiều nguồn 10/10, không đủ căn cứ 6/7, ngoài
phạm vi 5/5, mơ hồ 2/2, đối kháng 5/5.

**Đọc số này thận trọng.** Hai lỗi của lần đo v2 (`dir_34` từ chối nhầm, `dir_42` trích tiêu đề phụ lục) được phát
hiện **trên split test**; các sửa đổi sau đó (từ điển thuật ngữ, bỏ tiêu đề phụ lục) được viết theo nguyên tắc
chung và chỉnh trên dữ liệu phát triển, nhưng việc đã nhìn thấy hai ca này khiến mức tăng trên test (0.961 → 0.980)
không còn hoàn toàn khách quan. Thước đo khách quan cho các sửa đổi là bộ held-out ở mục 4b.

Lịch sử: v1 (snapshot `corpus-2026-09-30`, 49 câu test) D đúng 0.980; v2 (snapshot `corpus-2026-10-01`, 51 câu)
D đúng 0.961, citation precision 0.634. Các lần đo khác snapshot và nhãn nên không so trực tiếp.

## 4b. Câu hỏi diễn đạt theo lối thông thường

Bộ dev v2 và test v2 dùng từ gần với văn bản luật. Để đo khả năng hiểu câu hỏi thật, có hai bộ mới cùng phong
cách ("công ty", "nhân viên", "nghỉ phép", "Chủ nhật", "đặt cọc"…), đều do AI soạn từ nguyên văn và chưa người duyệt:

- [`questions_heldout_v1.jsonl`](../data/eval/questions_heldout_v1.jsonl) — 40 câu (28 trả lời được, 12 phải từ
  chối), **viết và commit (`95e38fa`) trước mọi sửa đổi**, không dùng để chẩn đoán hay chỉnh; đo một lần trước
  và một lần sau khi sửa.
- [`questions_paraphrase_dev_v1.jsonl`](../data/eval/questions_paraphrase_dev_v1.jsonl) — 27 câu khác, dùng để
  chẩn đoán lỗi và chọn ngưỡng.

| Bộ / hệ thống | Commit | Quyết định đúng | Trả lời sai | Từ chối nhầm | Correctness | Citation precision |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Held-out — D trước khi sửa | `95e38fa` | 0.775 | 0 | 9 | 0.643 | 0.857 |
| Held-out — A (RAG đơn giản) | `edd90b9` | 0.700 | 12 | 0 | 0.536 | 0.475 |
| **Held-out — D sau khi sửa** | `edd90b9` | **0.825** | 1 | 6 | 0.714 | 0.688 |
| Paraphrase dev — D trước / sau | — / `edd90b9` | 0.556 / 0.815 | 2 / 2 | 10 / 3 | 0.455 / 0.773 | 0.500 / 0.548 |

Truy xuất trên held-out (Hit@5 / MRR): 0.893 / 0.822 trước → 0.964 / 0.819 sau khi bổ sung thuật ngữ.

**Diễn giải.** Chẩn đoán trên paraphrase dev cho thấy Điều đúng thường đứng hạng 1 nhưng điểm cross-encoder tuyệt
đối với cách nói đời thường thấp hơn ngưỡng 0.8 được hiệu chỉnh trên câu hỏi sát văn luật; hạ ngưỡng làm tăng trả
lời sai (câu "chồng được nghỉ mấy ngày khi vợ sinh" đạt 0.81 trên Điều về thai sản của lao động nữ). Bổ sung thuật
ngữ pháp lý vào truy vấn tăng paraphrase dev từ 0.556 lên 0.815, nhưng held-out chỉ tăng 0.775 → 0.825: phần lớn mức
tăng trên paraphrase dev là do được chỉnh trên chính bộ đó. Trên held-out, 4 câu từ chối nhầm được khắc phục, 1 câu
trước đây trả lời được nay bị từ chối (`hp_25`), 1 câu phải từ chối nay bị trả lời (`hp_30`), và citation
precision giảm vì có thêm câu được trả lời với nhiều nguồn hơn. Hệ thống vẫn từ chối nhầm 6/28 câu hỏi đời thường.
Từ nay held-out v1 đã được dùng để đo; sửa đổi tiếp theo cần một bộ held-out mới.

## 5. Phân tích lỗi

Các ca dưới đây lấy từ `reports/answers_test_extractive_traces.jsonl` (test), `answers_heldout_extractive_traces.jsonl`
(held-out, chỉ đọc sau lần đo cuối) và lần chẩn đoán trên dữ liệu phát triển.

| # | Kiểu lỗi | Ca | Điều xảy ra | Trạng thái / hướng xử lý |
| --- | --- | --- | --- | --- |
| 1 | Cách nói đời thường → điểm reranker thấp → từ chối nhầm | `dir_34` (test v2), `hp_01`, `hp_02`, `hp_10`, `hp_20`, `hp_26` (held-out) | Điều đúng thường đứng hạng 1 nhưng điểm cross-encoder dưới 0.8 với câu "công ty có được… không", "đòi giữ bằng gốc", "thấp nhất là bao nhiêu"; `hp_01` còn cần suy luận "kỹ sư tốt nghiệp đại học" ⇒ "trình độ từ cao đẳng trở lên". | Đã thêm từ điển thuật ngữ (ADR-013): sửa `dir_34` và 4/9 ca held-out; còn 6/28 câu held-out bị từ chối nhầm. Cần bước kiểm tra khả năng trả lời không dựa trên điểm tuyệt đối (LLM hoặc mô hình QA) và câu hỏi thật để hiệu chỉnh. |
| 2 | Reranker bão hòa → trả lời từ điều lân cận | `una_10` (test), `hp_30` (held-out) | "Hồ sơ gia hạn giấy phép lao động" — Điều 27 Nghị định 219/2025 đang thực hiện theo Nghị quyết 24/2026 (ngoài kho); reranker cho Điều 27 lẫn Điều 18, 20, 28 (hồ sơ *cấp*, *trình tự gia hạn*) ~0,999 nên `superseded_margin` không tách được. | Chưa sửa. Đưa phần liên quan của Nghị quyết 24/2026 vào kho; hoặc so khớp thủ tục được hỏi với tiêu đề Điều; hoặc bước kiểm tra khả năng trả lời. |
| 3 | Trích thêm Điều không chứa câu trả lời | `dir_10`, `dir_18`, `dir_22`, `mul_06` (test) | Điều 89 Nghị định 145/2020 (người giúp việc gia đình) được trích kèm cho câu hỏi chung. | Một phần: nguồn bổ sung nay phải có khoản đạt `unit_threshold` 0.2 (chọn trên dữ liệu phát triển) — citation precision test 0.634 → 0.651, mức cải thiện nhỏ. Hướng tiếp: nhận diện Điều cho đối tượng riêng. |
| 4 | Liên quan chủ đề ≠ đủ căn cứ → trả lời sai | `una_07` (dev), `pd_23` (paraphrase dev) | "Danh mục nghề nặng nhọc" (danh mục thật do Bộ trưởng ban hành, không có trong kho); "chồng được nghỉ mấy ngày khi vợ sinh" (chế độ của Luật Bảo hiểm xã hội) trả lời bằng Điều thai sản của lao động nữ. | Như lỗi 2: cần bước phân loại "đủ căn cứ". |
| 5 | Phụ lục dạng danh sách: trích dòng tiêu đề | `dir_42` (test v2) | Bộ chọn đoạn lấy "CHO THUÊ LẠI LAO ĐỘNG" thay vì các dòng công việc. | Đã sửa (khối tiêu đề phụ lục không còn được trích). Phát hiện trên test — xem lưu ý ở mục 4. |
| 6 | Thoái lui khi bổ sung thuật ngữ | `hp_25` (held-out) | Câu về thời gian nghỉ của người giúp việc gia đình trước đây trả lời được, nay bị từ chối sau khi truy vấn được bổ sung thuật ngữ. | Chưa sửa; ghi nhận như chi phí của từ điển thủ công. |
| 7 | Nhiều ứng viên còn hiệu lực hơn → MRR giảm | `dir_41`, `mul_03` | Điều 20 Nghị định 219/2025 xếp trên Điều 18; Điều 55 Nghị định 145/2020 xếp trên Điều 98 và 107 Bộ luật. Hit@5 vẫn 1.000. | Cái giá của corpus thật hơn. |
| 8 | Cần kết hợp và tính toán | `mul_02` (test) | "Làm 10 năm được nghỉ hằng năm bao nhiêu ngày?" cần Điều 113 + Điều 114; D trích Điều 113. | Chế độ extractive không suy luận; chế độ Claude được phép nêu phép tính nếu trích dẫn đủ quy tắc. |
| 9 | Vế sau mất ngữ cảnh khi tách câu | `mul_04`, `mul_14` (test) | D trả lời PARTIAL và nêu rõ vế thiếu căn cứ. | Ghép cụm ngữ cảnh đầu câu vào từng vế. |
| 10 | Không có cổng bằng chứng (A–C) | `una_02`, `una_12`, `una_14`, `out_04`, `adv_06`… | A–C trả lời câu về ký quỹ bằng Điều 15 Nghị định 145/2020 đã bị thay thế, câu về khai thác than bằng Phụ lục III 135/2020 đã hết hiệu lực, câu thời tiết bằng phụ lục lương tối thiểu: 15/51 trả lời sai trên test, 12/40 trên held-out. | Giá trị chính của D: phạm vi, ngưỡng và hiệu lực theo điều khoản. |
| 11 | Độ trễ | D | Rerank chiếm 3.8/4.4 s ở p95; câu nhiều vế chạy 3 lượt. Docker CPU ~15–20 s/câu đơn. | Giảm ứng viên, chưng cất reranker, cache. |

**Kết luận:** chính sách bằng chứng loại bỏ 14/15 câu trả lời sai của RAG đơn giản trên test và 11/12 trên held-out,
kể cả câu trả lời bằng điều khoản đã bị thay thế. Điểm yếu lớn nhất còn lại là **từ chối nhầm câu hỏi đời thường**
(6/28 trên held-out) và việc reranker không phân biệt "liên quan" với "trả lời được câu hỏi" (lỗi 1, 2, 4): đây là
giới hạn của chế độ extractive dựa trên điểm cross-encoder, không phải của dữ liệu. Số liệu trên bộ v2 phản ánh câu
hỏi sát văn luật và corpus nhỏ (516 chunk dùng được), không nên ngoại suy cho người dùng thật.

## 6. Chưa đo

- Chế độ Claude (`LLM_PROVIDER=anthropic`): đã có mã và test với client giả lập, chưa benchmark vì môi trường phát
  triển không có API key. Lệnh: `python -m evaluation.answer_eval --split test --provider anthropic --systems D`
  (tốn phí API — cần duyệt ngân sách trước khi chạy).
- Correctness/citation precision do người chấm; khoảng tin cậy (mẫu 51 câu quá nhỏ để có khoảng hẹp).
- Câu hỏi thật của người dùng (bộ held-out vẫn do AI soạn; dữ liệu phản hồi trong `sessions.sqlite3` có thể dùng sau). Sau mỗi vòng sửa cần một bộ held-out mới, vì held-out v1 đã được dùng để đo.
- Độ chính xác của sổ theo dõi hiệu lực so với ý kiến chuyên gia (sổ chưa có người duyệt).
