# Đánh giá chất lượng dữ liệu pilot 10 văn bản

Ngày đánh giá: 2026-09-25 · Snapshot thu thập: 2026-09-24 · Quyết định ban đầu: **chưa đủ điều kiện đưa vào current QA index**; cập nhật 2026-09-30: luồng xử lý v3 qua mọi cổng tự động (mục 6), hiệu lực vẫn chưa được chuyên gia xác minh. Số liệu ở các mục 1–4 mô tả snapshot OCR ban đầu; kết quả ứng viên Công báo mới nằm ở mục 5. Phương án xử lý: [nghiên cứu khắc phục](REMEDIATION_RESEARCH.md).

Đầu vào và cách chạy lại: [`manifest.jsonl`](../data/pilot/2026-09-24/manifest.jsonl), [`data_quality_metrics.json`](../data/pilot/2026-09-24/data_quality_metrics.json), [`data_quality_summary.json`](../data/pilot/2026-09-24/data_quality_summary.json), [`quality_audit.jsonl`](../data/pilot/2026-09-24/quality_audit.jsonl), [`pilot/README.md`](../pilot/README.md). Các số đếm trong báo cáo do `pilot.assess_quality` tạo từ snapshot; các nhận định về OCR cụ thể đã đối chiếu ảnh PDF. Đây là đánh giá **khả năng dùng dữ liệu**, chưa phải chứng nhận nội dung pháp luật hiện hành.

## 1. Bảng kết quả theo cổng chất lượng

| Cổng | Bằng chứng trong snapshot | Kết luận |
| --- | --- | --- |
| Nguồn và truy vết | 10/10 bản ghi đủ 13 trường provenance bắt buộc, gồm URL metadata/PDF, ngày tải và SHA-256; 10/10 giấy phép phân phối lại chưa xác nhận | Đạt để kiểm toán nội bộ; chưa quyết định phân phối bản PDF/OCR |
| Độ phủ text | 496/496 trang là ảnh toàn trang; native extraction chỉ 210 từ và 0 chunk; OCR tạo 200.867 từ trên 496 trang | OCR là đường xử lý cần thiết cho bộ mẫu này |
| Độ đúng OCR | 5 đoạn chép tay, 235 từ tham chiếu: CER gộp 2,78%, WER gộp 16,17%; 10/10 tài liệu `ocr_review_status=unreviewed` | Chưa đạt cổng nội dung/citation |
| Số ký hiệu | Chuỗi số ký hiệu trong metadata xuất hiện nguyên văn ở OCR của 6/10 tài liệu; 3 lỗi đọc sai đã xác nhận trên ảnh trang đầu | Cần cổng đối chiếu số/ngày với ảnh và metadata nguồn |
| Cấu trúc | 826 chunk thử nghiệm; 189 chunk dưới 100 từ; 108 cảnh báo QA còn mở: 14 nhóm tiêu đề Điều trùng, 20 section dài, 58 gợi ý phụ lục/biểu mẫu, 16 trang ít text | Chưa đạt cổng chia đoạn có ngữ cảnh |
| Hiệu lực | 10/10 `legal_status=unverified`, 10/10 `review_status=pilot_only`; 0 bản ghi đã xác minh hiện hành | Chưa đạt cổng pháp lý |

**Kết quả vận hành:** 0/10 tài liệu đủ điều kiện vào current QA index. Đây là kết quả theo hai cổng bắt buộc `text_quality_status=verified` và `currency_status=verified_current`; không phải đánh giá rằng cả 10 văn bản đều sai hoặc hết hiệu lực.

## 2. Đo OCR: phạm vi và lỗi có tác động cao

Năm đoạn ngắn được chép tay từ ảnh PDF, trải trên 5 tài liệu. So sánh sau NFC, chữ thường, bỏ dấu câu và gộp khoảng trắng. Tổng tham chiếu 1.044 ký tự/235 từ; CER gộp 2,78%, WER gộp 16,17%. Các đoạn **được chọn để chẩn đoán**, không lấy mẫu ngẫu nhiên; không suy ra tỷ lệ lỗi của 200.867 từ OCR, của mọi điều khoản, hay chất lượng tìm kiếm.

| Đoạn | CER | WER |
| --- | ---: | ---: |
| 45/2019/QH14, Điều 113, trang 42 | 2,51% | 17,31% |
| 145/2020/NĐ-CP, Điều 1, trang 1 | 5,75% | 26,42% |
| 293/2025/NĐ-CP, Điều 1, trang 1 | 2,44% | 16,67% |
| 18/VBHN-VPQH, Điều 2, trang 2 | 1,58% | 13,95% |
| 152/2020/NĐ-CP, Điều 2, trang 2 | 1,33% | 5,88% |

Kiểm tra chuỗi số ký hiệu nguyên văn là một **tín hiệu rà soát**, không phải phép đo OCR chính xác: kiểu trình bày PDF có thể chèn khoảng trắng hoặc ngắt dòng. Trong 4 tài liệu không khớp, ảnh trang đầu xác nhận 3 lỗi đọc sai thực sự:

| Văn bản | Metadata và ảnh PDF | OCR trang đầu |
| --- | --- | --- |
| 145/2020/NĐ-CP | `145/2020/NĐ-CP` | `4452020/NĐ-CP` |
| 135/2020/NĐ-CP | `135/2020/NĐ-CP` | `425/2020/NĐ-CP` |
| 152/2020/NĐ-CP | `152/2020/NĐ-CP` | `452/2020/NĐ-CP` |

Với 18/VBHN-VPQH, chuỗi chính xác không xuất hiện trong OCR; chưa kết luận đây là lỗi đọc. Một lỗi khác đã xác nhận trong phụ lục 293/2025/NĐ-CP, trang 5: ảnh ghi `293/2025/NĐ-CP`, OCR ghi `293/2023/NĐ-CP`. Sai số ký hiệu/năm có thể dẫn đến trích dẫn nhầm văn bản ngay cả khi phần câu chung quanh đọc được.

## 3. Cấu trúc và hiệu lực

Các 108 cảnh báo là hàng đợi review, **không phải 108 lỗi đã xác nhận**; chúng có thể chồng lấp. Tuy vậy, kiểm tra ảnh và OCR đã xác nhận các kiểu hỏng sau:

- 145/2020/NĐ-CP: mẫu hợp đồng/quyết định ở phụ lục tạo thêm tiêu đề `Điều` trùng với thân văn bản.
- 152/2020/NĐ-CP: biểu mẫu tạo các tiêu đề `Điều` trùng tương tự.
- 45/2019/QH14: Điều 219 trích một `Điều 55` của luật khác, bị nhận thành Điều 55 mới của chính Bộ luật.
- 293/2025/NĐ-CP: phụ lục bị gộp vào section trước, tạo section 5.084 từ.

Vì vậy, `Điều <số>` và page span đúng chưa đủ để xác định **văn bản nào, vùng nào, điều nào** làm căn cứ. Cần `section_kind` (`main_text`, `annex`, `quoted_amendment`), `section_path` và review ảnh nguồn cho phần dùng làm citation. 189 chunk dưới 100 từ không tự động là lỗi; đây là tín hiệu kiểm tra về đoạn quá vụn.

Manifest chưa ghi quan hệ sửa đổi/thay thế và trạng thái theo từng điều khoản. Nguồn VBPL đã tra cứu cho thấy mức độ rủi ro: [45/2019/QH14](https://vbpl.vn/bolaodong/Pages/vbpq-thuoctinh.aspx?ItemID=139264) và [145/2020/NĐ-CP](https://vbpl.vn/bocongthuong/Pages/vbpq-thuoctinh.aspx?ItemID=152668) được ghi “hết hiệu lực một phần”; [74/2024/NĐ-CP](https://vbpl.vn/bolaodong/Pages/vbpq-thuoctinh.aspx?ItemID=168670) được ghi hết hiệu lực toàn bộ từ 01/01/2026; [152/2020/NĐ-CP](https://vbpl.vn/TW/Pages/vbpq-thuoctinh.aspx?ItemID=152669&Keyword=&dvid=13) được ghi hết hiệu lực một phần và dẫn chiếu 219/2025/NĐ-CP. Truy cập trực tiếp VBPL từ môi trường pilot gặp HTTP 403/redirect, còn kết quả tìm kiếm có thể là bản lưu cũ; các thông tin này chỉ là **đầu mối review**, không được chuyển thành nhãn `verified_current` nếu chưa đối chiếu nguồn chính thức và ngày áp dụng tại thời điểm phát hành corpus.

## 4. Quyết định cải tiến và điều kiện mở cổng

1. **Giữ metadata nguồn độc lập với OCR.** Không ghi đè số ký hiệu/ngày lấy từ trang metadata bằng OCR. Tự động so khớp số ký hiệu và các giá trị nhạy cảm; khi lệch, đưa ảnh trang và hai chuỗi vào hàng đợi review.
2. **Thử nguồn toàn văn HTML chính thức cho từng tài liệu.** Chỉ chọn bản HTML có provenance và đúng phiên bản. Nếu phải OCR, lưu model hash, ảnh gốc, text theo trang và biên bản reviewer.
3. **Rà soát theo tác động pháp lý.** Ưu tiên số văn bản, năm, ngày, tiền, ngưỡng, phủ định/ngoại lệ, điều khoản dùng trong bộ câu hỏi chuẩn; đo lại OCR bằng tập ngẫu nhiên và mẫu rủi ro riêng trước khi đặt ngưỡng chất lượng.
4. **Chia đoạn có loại vùng và đường dẫn cấu trúc.** Phụ lục/biểu mẫu, văn bản trích dẫn sửa đổi và thân văn bản phải phân biệt; kiểm tra tiêu đề trùng và section dài bằng ảnh.
5. **Lập hồ sơ hiệu lực theo thời điểm.** Đối chiếu trạng thái, quan hệ sửa đổi/thay thế và hiệu lực ở cấp điều khoản từ nguồn chính thức; lưu URL, ngày kiểm tra và người duyệt. Văn bản hợp nhất cần vai trò riêng, không tự coi là văn bản gốc còn hiệu lực.
6. **Chỉ phát hành khi hai cổng đều đạt.** Mỗi chunk dùng để trả lời phải có text đã đối chiếu và trạng thái hiệu lực áp dụng đã xác minh; citation phải truy ngược được đến PDF/HTML, trang/điều và snapshot. Tới khi đó giữ toàn bộ 826 chunk ở phạm vi thử nghiệm.

Đánh giá này chưa đo retrieval, chất lượng câu trả lời hay độ đầy đủ corpus chủ đề lao động; những phép đo đó chỉ có ý nghĩa sau khi có tập nguồn đã qua các cổng trên.

## 5. Thí nghiệm cải tiến ngày 2026-09-25: nguồn Công báo có lớp chữ

Đã tìm và tải PDF của cả 10 văn bản từ trang chi tiết trên **Công báo điện tử**. Bản 145/2020/NĐ-CP có hai phần PDF. Mỗi phần được lưu riêng kèm URL và SHA-256 trong [`congbao_candidate_inventory.json`](../data/pilot/2026-09-24/congbao_candidate_inventory.json). Công báo cung cấp lớp chữ trích xuất trực tiếp: ứng viên riêng gồm **552 trang có nội dung, 218.989 từ và 895 chunk**; ba trang trắng cuối tệp được loại và vẫn giữ ánh xạ đến số trang PDF nguồn. Đây là cách sửa có tác động lớn hơn việc đổi cấu hình OCR cho 496 trang scan ban đầu. Bản ứng viên và PDF được giữ riêng; snapshot gốc không bị ghi đè.

| Kiểm tra | Kết quả | Giới hạn |
| --- | --- | --- |
| Năm đoạn chép tay từ ảnh nguồn | 5/5 đoạn xuất hiện nguyên văn trong text Công báo sau cùng phép chuẩn hóa; lỗi trên năm đoạn này bằng 0 | Đây là các đoạn chẩn đoán đã chọn, chưa phải mẫu đại diện toàn corpus |
| Số ký hiệu | 9/10 chuỗi có nguyên dạng trong lớp chữ PDF; 18/VBHN-VPQH có thêm khoảng trắng trước dấu `/` trong thân PDF, còn metadata ghi nguyên dạng | So khớp cho phép khác khoảng trắng đạt 10/10; vẫn cần đối chiếu metadata |
| Cấu trúc Điều | 10/10 văn bản có chuỗi Điều chính liên tục trong parser ứng viên; 45 và 18 đều có Điều 1–220 | Chuỗi liên tục không chứng minh từng khoản, bảng và phụ lục chính xác |
| Giữ text khi phân đoạn | Tổng số từ của các section bằng tổng số từ trích từ trang ở 10/10 văn bản | Trích text PDF vẫn cần kiểm tra thứ tự đọc và bảng |
| Bản 18/VBHN-VPQH | PDF Công báo có 88 trang, số trang in liên tục, đủ Điều 76–79; DOCX cùng trang nguồn cũng có bốn Điều này | Bản scan 86 trang ban đầu vẫn là nguồn lỗi, không dùng để trả lời |

Chi tiết kiểm tra ở [`congbao_candidate_audit.json`](../data/pilot/2026-09-24/congbao_candidate_audit.json), [`alternate_source_audit.json`](../data/pilot/2026-09-24/alternate_source_audit.json) và [`candidate_congbao_all/summary.json`](../data/pilot/2026-09-24/candidate_congbao_all/summary.json). Trang Công báo [18/VBHN-VPQH](https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm) chứa PDF/DOCX thay thế; [145/2020/NĐ-CP](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-145-2020-nd-cp-32732.htm) có hai phần. Trang [45/2019/QH14](https://congbao.chinhphu.vn/van-ban/nghi-quyet-so-45-2019-qh14-30232.htm) ghi nhầm loại “Nghị quyết”; chính PDF Công báo ghi “Bộ luật số: 45/2019/QH14” và [VBPL ghi loại Bộ luật](https://vbpl.vn/bolaodong/Pages/ivbpq-thuoctinh.aspx?ItemID=139264). Manifest ứng viên dùng “Bộ luật”, giữ URL trang Công báo để truy vết dị biệt metadata.

Thử Tesseract trên cùng năm đoạn: `fast_200` WER 16,17%; `best_200` 14,89%; `best_300` 16,60%. Trong bốn vị trí số ký hiệu khó, `best_200` và `best_300` chỉ đúng 1/4, còn crop riêng tại 300/400 DPI không sửa được ba số đầu trang. [`ocr_benchmark.json`](../data/pilot/2026-09-24/ocr_benchmark.json), [`id_crop_benchmark.json`](../data/pilot/2026-09-24/id_crop_benchmark.json). PP-OCRv5 chưa đo được vì Windows Application Control chặn nạp DLL của `pandas` trong môi trường Paddle; không có kết luận về chất lượng PaddleOCR.

**Trạng thái phát hành vẫn là 0/10.** Tất cả chunk ứng viên mang `text_quality_status=unreviewed`, `currency_status=unverified`. Cần kiểm tra các vùng bảng/phụ lục, tạo mẫu đánh giá đại diện, rà soát hiệu lực tại thời điểm sử dụng đến cấp Điều/khoản, và kiểm tra citation ngược về đúng phần PDF. Công báo chứa văn bản đã đăng, không tự chứng minh nội dung đó còn hiệu lực ngày 2026-09-25. Đã tải lại cả 11 phần PDF bằng TLS xác minh qua kho chứng chỉ Windows; SHA-256 khớp với bản đã lưu.

Tra cứu phân luồng hiệu lực sơ bộ được lưu tại [`legal_status_leads.json`](../data/pilot/2026-09-24/legal_status_leads.json): VBPL ghi [38/2022/NĐ-CP](https://vbpl.vn/bolaodong/Pages/ivbpq-thuoctinh.aspx?ItemID=154245) hết hiệu lực từ 01/07/2024 và [74/2024/NĐ-CP](https://vbpl.vn/bolaodong/Pages/ivbpq-lichsu.aspx?ItemID=168670&Keyword=) hết hiệu lực từ 01/01/2026; [45/2019/QH14](https://vbpl.vn/bolaodong/Pages/ivbpq-thuoctinh.aspx?ItemID=139264), [145/2020/NĐ-CP](https://vbpl.vn/bocongthuong/Pages/vbpq-thuoctinh.aspx?ItemID=152668), [135/2020/NĐ-CP](https://vbpl.vn/hanoi/Pages/vbpq-thuoctinh.aspx?ItemID=152734), [152/2020/NĐ-CP](https://vbpl.vn/TW/Pages/vbpq-thuoctinh.aspx?ItemID=152669&Keyword=&dvid=13) và [70/2023/NĐ-CP](https://vbpl.vn/phuyen/Pages/vbpq-thuoctinh.aspx?ItemID=162330&Keyword=) có dấu hiệu hết hiệu lực một phần. Các trang VBPL được công cụ tìm kiếm lập chỉ mục trước ngày đánh giá nên đây là **đầu mối review**, chưa phải xác nhận hiệu lực đến từng Điều/khoản tại ngày sử dụng. Hai văn bản hết hiệu lực toàn bộ vẫn có giá trị cho truy vấn lịch sử đúng khoảng thời gian.

## 6. Luồng xử lý v3 và cổng chất lượng tự động (2026-09-30)

Kiểm tra độc lập ngày 2026-09-30 trên bản ứng viên Công báo cho thấy lớp chữ chính xác (8/8 đoạn lấy ngẫu nhiên khớp nguyên văn ảnh trang; 0 ký tự lỗi; tỷ lệ âm tiết không hợp lệ ≤ 0,07% ở các văn bản chính) nhưng **khâu xử lý** có lỗi: 437/895 chunk (49%) dính header `CÔNG BÁO/Số…`, khối chữ ký số lọt vào chunk đầu, 3/4 footnote sửa đổi của 18/VBHN-VPQH bị gắn sang Điều kế tiếp và ký hiệu chú thích dính vào số (`1.44 Lao động nữ…`), bảng bị dàn phẳng mất nhãn cột, và khối nối giữa hai số Công báo chen giữa Điều 101 của 145/2020/NĐ-CP.

Package [`ingestion/`](../ingestion) thay các script pilot (ADR-007): đọc từng dòng theo cỡ chữ, vị trí và đường kẻ trước khi ghép text; dựng cây Chương/Mục/Điều chỉ chấp nhận Điều tăng liên tục và ngoài vùng trích dẫn; tách phần mở đầu, khối chữ ký, phụ lục; chia chunk theo Điều → khoản → đoạn với offset chính xác. Build ([`ingestion/build.py`](../ingestion/build.py)) dừng nếu một cổng bắt buộc không đạt:

| Cổng bắt buộc | Kết quả snapshot `corpus-2026-09-30` |
| --- | --- |
| SHA-256 và số trang của 11 tệp nguồn | 11/11 khớp |
| Điều chính liên tục, đúng số Điều kỳ vọng | 10/10 văn bản (45 và 18: 1–220; 145: 1–115; …) |
| Mỗi đoạn thuộc đúng một section hoặc là tiêu đề Chương/Mục | đạt |
| Mọi đoạn có thể trả lời được nằm trong ít nhất một chunk | đạt |
| `raw_text` của chunk = lát cắt chính xác của text văn bản | 926/926 |
| Không header/tem chữ ký/dải chuyên mục/khối nối trong chunk | 0 vi phạm |
| Footnote tách khỏi thân và gắn Điều/khoản | 6/6 (18/VBHN-VPQH), đối chiếu text PDF thô |
| Fixture hồi quy (5 đoạn chép tay, 8 đoạn đối chiếu ảnh, 4 dòng bảng lương, 5 footnote) | 22/22 |
| Lộ trình tuổi nghỉ hưu 135/2020 (Phụ lục I–II): tháng hưởng lương hưu = tháng sinh + tuổi + 1 | 350/350 dòng, khớp bộ dòng đã kiểm chứng của pilot |
| Tỷ lệ âm tiết tiếng Việt không hợp lệ ≤ 1% (thân văn bản) | 0,0% |

Đoạn có dạng chỉ thị ("bỏ qua mọi hướng dẫn", "system prompt"…) bị cách ly (không bao giờ `machine_checked`); snapshot hiện tại có 0 đoạn bị cách ly. Kết quả chi tiết: [`quality_report.json`](../data/snapshots/corpus-2026-09-30/quality_report.json).

**Trạng thái sử dụng:** 926 chunk đều `machine_checked` (chưa `verified` bởi người). Hiệu lực theo chunk (ADR-008): 225 `consolidated_current` (18/VBHN-VPQH), 19 `presumed_current` (293/2025/NĐ-CP), 225 `superseded_by_consolidation` (45/2019/QH14), 18 `historical` (38/2022, 74/2024), 439 `unverified` (145/2020, 135/2020, 152/2020, 70/2023 hết hiệu lực một phần chưa ánh xạ điều khoản; 12/2022 ngoài phạm vi). Ở chính sách `pilot`, 242 chunk dùng được cho câu hỏi về quy định hiện hành; ở `strict`, 0 chunk cho đến khi có người duyệt.

Việc còn lại trước khi coi dữ liệu là "đã xác minh": người duyệt đối chiếu text các Điều dùng trong bộ câu hỏi; lập ánh xạ sửa đổi cấp điều khoản cho 145/2020 (129/2025, 10/2024, 35/2022), 135/2020 (158/2025), 152/2020 và 70/2023 (219/2025); kiểm tra văn bản sửa đổi Bộ luật Lao động ban hành sau 12/02/2026. *(Ánh xạ cấp điều khoản đã làm ở mục 7.)*

## 7. Sổ theo dõi hiệu lực cấp điều khoản (2026-10-01)

**Cách làm.** Danh sách văn bản sửa đổi lấy từ đầu mối VBPL (tra cứu gián tiếp 2026-09-25), bổ sung bằng tìm kiếm toàn văn trên Công báo điện tử (`api-searchcongbao.chinhphu.vn`) ngày 2026-10-01 theo số hiệu từng nghị định và theo chủ đề (giấy phép lao động, cho thuê lại lao động, hòa giải viên, tuổi nghỉ hưu…). Mỗi văn bản tìm được tải PDF chính thức, phân tích bằng chính pipeline của dự án và đọc toàn văn mọi Điều có dẫn chiếu tới văn bản trong kho. Tìm kiếm phát hiện hai nghị quyết năm 2026 mà danh sách VBPL không có: **24/2026/NQ-CP** (thay hồ sơ gia hạn tại Điều 15, 27 Nghị định 219/2025) và **66.18/2026/NQ-CP** (từ 01/07/2026 đến hết 28/02/2027 không thực hiện thủ tục cấp/gia hạn/cấp lại/thu hồi giấy phép cho thuê lại lao động, quy định lại ký quỹ và báo cáo tại Điều 12, 15, 17–20, 31, 33, 35 Nghị định 145/2020).

**Kết quả** ([`currency_ledger.json`](../data/corpus/currency_ledger.json), 45 mục từ 9 văn bản có tác động; 11 PDF nguồn khóa SHA-256):

| Văn bản trong kho | Văn bản tác động | Tác động chính |
| --- | --- | --- |
| 135/2020/NĐ-CP | 158/2025/NĐ-CP điểm c khoản 2 Điều 44 | Hết hiệu lực khoản 2 Điều 3, khoản 1 và 3 Điều 7, khoản 2 Điều 8, Phụ lục III (từ 01/07/2025) |
| 152/2020/NĐ-CP | 219/2025/NĐ-CP khoản 2 Điều 35; 70/2023/NĐ-CP | Hết hiệu lực phần lao động nước ngoài (khoản 1 Điều 1, khoản 1–2 Điều 2, Điều 3–21, khoản 3 Điều 29, Phụ lục I) từ 07/08/2025; Điều 30 hỗn hợp → chưa xác minh; Chương III còn hiệu lực, khoản sửa đổi bởi 70/2023 trỏ sang 70/2023 |
| 70/2023/NĐ-CP | 219/2025/NĐ-CP | Hết hiệu lực khoản 1–8, 12 Điều 1, khoản 2 Điều 3, Phụ lục; khoản 9–10 Điều 1 (sửa Chương III của 152) còn hiệu lực |
| 145/2020/NĐ-CP | 35/2022, 10/2024, 129/2025/NĐ-CP; 66.18/2026/NQ-CP | Khoản 2 Điều 4, khoản 2 Điều 31 đã sửa; Điều 91, 93–95, 97, 110–112 thực hiện theo 129/2025 (đến trước 01/03/2027); Điều 12, 15, 17–28, 31, 33, 35 thực hiện theo 66.18/2026; Điều 29, 34, Phụ lục III hỗn hợp → chưa xác minh |
| 219/2025/NĐ-CP (mới thêm) | 24/2026/NQ-CP | Điều 15, 27 thực hiện theo Nghị quyết (đến trước 01/03/2027) |

Văn bản đã kiểm tra nhưng không tác động thêm: 128/2025/NĐ-CP (Điều 8 đã bị 219/2025 bãi bỏ), 66.7/2025/NQ-CP (chỉ các thủ tục cấp phép đã bị 66.18 dừng), 66.17/2026/NQ-CP (không nhắc tới cho thuê lại lao động).

**Kiểm soát chất lượng.** 45/45 câu trích tìm thấy nguyên văn trong PDF nguồn; mọi Điều/khoản đích tồn tại trong văn bản đã phân tích (khoản được xác định bỏ qua số thứ tự trong ngoặc kép trích dẫn); build `corpus-2026-10-01` qua mọi cổng (1017 chunk). Trạng thái chunk: 286 `presumed_current`, 225 `consolidated_current`, 128 `superseded_by_amendment`, 135 `unverified` (106 thuộc 12/2022 ngoài phạm vi, 29 điều khoản hỗn hợp), 225 `superseded_by_consolidation`, 18 `historical`. Ở chính sách `pilot`, **504 chunk** dùng được (trước: 242).

**Giới hạn còn lại.** Sổ do AI hỗ trợ trích xuất và chưa có người duyệt; tìm kiếm Công báo xếp theo độ liên quan nên có thể sót văn bản; Nghị quyết 66.16/2026/NQ-CP không có trên Công báo điện tử (phần về cho thuê lại lao động đã bị 66.18 bãi bỏ); chưa đối chiếu các văn bản sắp xếp bộ máy năm 2025 nên tên cơ quan (Bộ/Sở Lao động – Thương binh và Xã hội, cấp huyện) trong văn bản có thể đã thay đổi; Phụ lục I của 135/2020 còn cột "thời điểm hưởng lương hưu" dựa trên quy tắc tại khoản 2 Điều 3 đã hết hiệu lực — cần ý kiến chuyên gia. Một dự thảo năm 2026 sửa/thay 145/2020 chưa có hiệu lực nên không đưa vào sổ.
