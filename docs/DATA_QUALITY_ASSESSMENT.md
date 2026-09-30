# Đánh giá chất lượng dữ liệu pilot 10 văn bản

Ngày đánh giá: 2026-09-25 · Snapshot thu thập: 2026-09-24 · Quyết định: **chưa đủ điều kiện đưa vào current QA index**. Số liệu ở các mục 1–4 mô tả snapshot OCR ban đầu; kết quả ứng viên Công báo mới nằm ở mục 5. Phương án xử lý: [nghiên cứu khắc phục](REMEDIATION_RESEARCH.md).

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
