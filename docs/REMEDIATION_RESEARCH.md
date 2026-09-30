# Nghiên cứu phương pháp khắc phục chất lượng dữ liệu

Ngày: 2026-09-25 · Đầu vào: [đánh giá pilot 10 văn bản](DATA_QUALITY_ASSESSMENT.md) · Trạng thái: **đã triển khai thí nghiệm nguồn thay thế, OCR và parser; chưa phát hành data**.

## 1. Kết luận và thứ tự thực hiện

Pilot đã thu đúng 10 PDF và lưu provenance, nhưng 496/496 trang là ảnh scan, OCR chưa được duyệt, parser nhầm Điều trong phụ lục/trích dẫn, và manifest chưa xác minh hiệu lực. Giải pháp nên đi theo thứ tự: **(1) lập bộ chuẩn đo chất lượng; (2) cải thiện OCR trên cùng bộ chuẩn; (3) nhận diện vùng tài liệu trước khi chia Điều; (4) lập hồ sơ hiệu lực theo thời điểm; (5) mở cổng index từng chunk sau review**. Không nên dùng một mô hình OCR hoặc LLM mới để tự chứng nhận text pháp lý.

| Vấn đề | Phương pháp ưu tiên | Phương án chỉ thử khi cần | Điều kiện chọn |
| --- | --- | --- | --- |
| OCR sai chữ/số | So nguồn toàn văn chính thức; nếu phải OCR, so `fast`/`best`, 200/300 DPI, chỉnh nghiêng có điều kiện, crop riêng vùng số/ngày | PP-OCRv5 tiếng Việt trên các trang khó | Giảm CER/WER trên holdout **và** không tăng lỗi số/ngày quan trọng |
| Nhầm Điều/phụ lục | Phân loại vùng trang rồi parse cấu trúc có trạng thái (`main_text`, `annex`, `quoted_amendment`) | Layout model trên trang bảng/biểu mẫu khó | Tăng recall nhận diện phụ lục và độ đúng gán Điều về đúng văn bản |
| Hiệu lực chưa rõ | Hồ sơ quan hệ sửa đổi/thay thế có URL, mốc áp dụng và reviewer ở cấp điều khoản | Adapter tự động hóa VBPL khi endpoint thực sự truy cập được | Không còn chunk current nào mang trạng thái `unknown` hoặc thiếu nguồn xác minh |
| Citation chưa an toàn | Hai cổng text và hiệu lực độc lập, đối chiếu ảnh cho chunk được dùng, kiểm tra citation ngược về nguồn | Hỗ trợ reviewer bằng OCR confidence/diff | 100% chunk phát hành qua cả hai cổng, không có lỗi số/ngày còn mở |

## 2. OCR: sửa đầu vào và so mô hình bằng dữ liệu của chính dự án

### 2.1. Nguồn text và tiền xử lý

Trước tiên tìm **toàn văn HTML chính thức cùng số ký hiệu và phiên bản**; lưu URL, ngày truy cập và hash. HTML có thể tránh một lớp lỗi OCR, nhưng vẫn cần đối chiếu với PDF/metadata vì có thể khác bản hoặc thiếu phụ lục. Khi chỉ có scan, giữ PDF gốc bất biến và tạo ảnh dẫn xuất có cấu hình riêng.

Tesseract khuyến nghị thử ảnh đủ độ phân giải (thường từ 300 DPI), chỉnh nghiêng nếu trang bị lệch, xử lý nền/nhiễu khi cần, và chọn page segmentation mode phù hợp cho vùng nhỏ. OCRmyPDF phân biệt `--rotate-pages` cho hướng 90°/180° với `--deskew` cho lệch nhẹ; tránh áp dụng mù vì thao tác ảnh cũng có thể làm mất nét chữ/số. [Tesseract — Improving Quality](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html), [OCRmyPDF — Cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html).

**Ma trận thử trên cùng ảnh trang và ground truth:**

1. A0: pipeline hiện tại, `tessdata_fast/vie`, 200 DPI.
2. A1: `tessdata_best/vie`, 200 DPI; phép thử cũ trên **một** đoạn Điều 113 giảm WER 17,31% → 13,46%, chưa đủ chứng minh cho cả corpus.
3. A2: `best/vie`, 300 DPI; bật deskew chỉ trên trang có góc lệch đo được, so với ảnh không xử lý.
4. A3: nhận dạng riêng vùng số ký hiệu/ngày với crop và PSM phù hợp; kết quả là **ứng viên đối chiếu**, không ghi đè metadata hoặc text đã duyệt.
5. A4: thử một OCR thứ hai trên nhóm trang khó. Tài liệu PP-OCRv5 liệt kê tiếng Việt trong model Latin đa ngữ; chưa có bằng chứng nó tốt hơn Tesseract trên scan pháp luật của dự án. [Tesseract — data files](https://github.com/tesseract-ocr/tessdoc/blob/main/Data-Files.md), [Tesseract — PSM](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [PaddleOCR — multilingual models](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md).

PyMuPDF hỗ trợ OCR và tái dùng `TextPage`, nên có thể giữ cơ chế cache hiện tại cho A0–A2. Nếu thử OCRmyPDF trên máy Windows, tài liệu của dự án hướng dẫn chạy qua WSL; đây là nhánh thí nghiệm riêng, không thay đổi nguồn PDF gốc. [PyMuPDF OCR](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html), [OCRmyPDF installation](https://ocrmypdf.readthedocs.io/en/stable/installation.html).

**Đo:** CER, WER trên text thường; tỷ lệ khớp chính xác của số ký hiệu, ngày, giá trị tiền/ngưỡng và phủ định; thời gian/trang, dung lượng model. Báo cả chỉ số tổng và theo nhóm trang. Một cấu hình được chọn khi cải thiện trên holdout và không đánh đổi lỗi nghiêm trọng lấy WER trung bình thấp hơn. Không tự sửa `145` thành `445` hay năm `2023` thành `2025` chỉ bằng regex: regex dùng để **báo lệch**, reviewer xác nhận trên ảnh.

## 3. Cấu trúc: nhận diện vùng trước, chia Điều sau

Regex `Điều <số>` chỉ nhìn thấy chuỗi chữ, không biết nó thuộc thân văn bản, biểu mẫu trong phụ lục hay đoạn trích luật khác. Cần một cây cấu trúc gắn trang/toạ độ: `document → chapter/section → article → clause/point`, kèm `section_kind`, `parent_document_id`, `source_page`, bounding box và phiên bản parser. Lưu text theo dòng/vùng trước khi nối trang; khi gặp marker `PHỤ LỤC`, `MẪU`, `VĂN BẢN ĐƯỢC SỬA ĐỔI`, trích dẫn mở/đóng, chuyển trạng thái parser và yêu cầu review ở vùng mơ hồ.

Ưu tiên parser có quy tắc kiểm chứng được: thứ tự Điều trong thân văn bản, marker phụ lục, vị trí/kiểu chữ nếu có, khoảng cách đến đầu trang, và liên tục trang. Một số Điều trùng **không đủ** để tự loại vì văn bản sửa đổi có thể trích lại Điều hợp pháp. Với bảng lương/địa bàn, ghi vùng bảng và tọa độ ô; nếu bảng không đọc đủ hàng/cột thì giữ `unverified`, không biến nó thành văn xuôi để citation. Tesseract ghi nhận bảng cần xử lý layout riêng. [Tesseract — tables](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html).

Nếu quy tắc vẫn thất bại trên phụ lục nhiều cột hoặc biểu mẫu, chạy thử PP-StructureV3 **chỉ trên trang khó** để lấy vùng, bảng và thứ tự đọc. Tài liệu dự án mô tả khả năng đó, nhưng số đo công bố không phải benchmark văn bản pháp luật tiếng Việt; quyết định dùng phải dựa trên nhãn nội bộ. [PP-StructureV3](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PP-StructureV3.en.md).

**Đo:** precision/recall/F1 của tiêu đề Điều trong thân văn bản, phát hiện phụ lục, gán vùng `quoted_amendment`, đọc đúng thứ tự, và tỷ lệ chunk có đúng `section_path` + trang. Dùng các ca đã thấy ở 45, 145, 152, 293 làm bộ regression; giữ thêm trang mới chưa dùng để viết quy tắc làm holdout.

## 4. Hiệu lực: hồ sơ có bằng chứng và ngày áp dụng

Thiết kế một bảng sự kiện pháp lý thay vì một cờ `current` toàn văn:

```text
document_id | target_section_path | relation_type | source_document_id
effective_from | effective_to | evidence_url | evidence_location
observed_at | reviewer | decision | confidence_status
```

Reviewer đọc tab thuộc tính/lịch sử/văn bản liên quan trên nguồn chính thức, xác định văn bản nào sửa đổi, bãi bỏ hoặc thay thế **phần nào**, và mốc bắt đầu áp dụng. [VBPL — ví dụ 145/2020/NĐ-CP hết hiệu lực một phần](https://vbpl.vn/bocongthuong/Pages/vbpq-thuoctinh.aspx?ItemID=152668), [VBPL — ví dụ 74/2024/NĐ-CP hết hiệu lực toàn bộ từ 01/01/2026](https://vbpl.vn/bolaodong/Pages/vbpq-thuoctinh.aspx?ItemID=168670). Đây là ví dụ cho thiết kế, không thay thế việc xác minh lại tại ngày phát hành corpus.

Truy vấn theo `as_of_date` chỉ lấy điều khoản có khoảng hiệu lực đã duyệt bao phủ ngày đó. Khi trạng thái một phần chưa mapping xong, điều khoản liên quan vẫn `unverified`; câu hỏi hiện hành phải từ chối kết luận thay vì trả bản cũ. Văn bản hợp nhất giữ loại nguồn và quan hệ với văn bản gốc/sửa đổi; cách viện dẫn phải đối chiếu quy định đang áp dụng tại thời điểm triển khai, nhất là khi Bộ Tư pháp đã thông tin về sửa đổi quy định liên quan đến giá trị viện dẫn của văn bản hợp nhất trong năm 2026. [Bộ Tư pháp — văn bản hợp nhất](https://moj.gov.vn/portal/tin-tuc/chi-tiet/van-ban-hop-nhat-uoc-cong-nhan-gia-tri-phap-ly-trong-qua-trinh-vien-dan-th2hn6f9f9.html).

VBPL hiện trả 403/redirect với client pilot; vì vậy tiến trình tự động phải có `access_probe` và ghi `manual_fallback` nếu reviewer xem được nguồn bằng cách khác. Không suy trạng thái hiệu lực từ search snippet, ngày ban hành, hoặc từ một bản hợp nhất đơn lẻ.

## 5. Bộ chuẩn và thí nghiệm đủ để ra quyết định

Tài liệu OCR-D khuyến nghị ground truth **đại diện** gồm ảnh và bản chép tay, đo riêng chất lượng text và layout; chỉ số CER/WER của vài đoạn thuận tiện không thể hiện hết lỗi cấu trúc. [OCR-D — Quality Assurance](https://ocr-d.de/en/spec/ocrd_eval), [OCR-D — workflow evaluation](https://ocr-d.de/en/workflows).

**Protocol đề xuất cho 10 tài liệu:** chọn 4 trang/tài liệu (trang đầu, thân văn bản, trang giữa/cuối, trang phụ lục hoặc trang khó; nếu không có phụ lục thì chọn ngẫu nhiên có seed). Trên mỗi trang chép tay 2 vùng khoảng 100 từ và gắn nhãn tất cả tiêu đề/vùng pháp lý quan trọng; tổng mục tiêu 40 trang/80 vùng. Khoá 1 trang/tài liệu (10 trang) làm holdout trước khi chỉnh pipeline. Review chéo ít nhất 20% bản chép và mọi trường số/ngày bất đồng. Các ca lỗi đã biết làm regression riêng, **không** tính là holdout. Đây là quy mô thử nghiệm đề xuất, chưa phải số liệu đã thu.

| Đầu ra đo | Cách báo cáo và quyết định |
| --- | --- |
| OCR | CER/WER theo trang/tài liệu/loại vùng; exact match số/ngày/tiền; thời gian/trang; so A0–A4 trên cùng vùng |
| Layout | F1 Điều thân văn bản, recall phụ lục/bảng, nhầm `quoted_amendment`, page/section path đúng |
| Hiệu lực | Tỷ lệ điều khoản có bằng chứng ngày áp dụng; số trường hợp `unknown`, xung đột, cần reviewer |
| Citation | Tỷ lệ citation mở đúng file/trang/điều và đúng phiên bản; kiểm tra thủ công toàn bộ chunk đưa vào demo |

**Cổng phát hành:** mọi chunk trong current QA index phải có provenance, text/ảnh được reviewer đối chiếu, hiệu lực áp dụng tại snapshot được reviewer xác minh và citation kiểm tra ngược thành công. Bất kỳ lệch số/ngày quan trọng nào còn mở thì chunk đó không vào index. Chưa đặt ngưỡng WER chung để “tự động đạt” trước khi có mẫu đại diện; OCR score chỉ chọn cấu hình và xếp hàng review. Thử retrieval/RAG trên một tập đã duyệt, không lấy việc model trả đúng vài câu để suy ngược rằng nguồn OCR đã sạch.

## 6. Công việc tiếp theo có thể triển khai

1. Tạo biểu mẫu ground truth với `document_id`, trang, tọa độ vùng, ảnh/hash, text chép tay, loại vùng, số/ngày nhạy cảm, hai reviewer và trạng thái bất đồng.
2. Chạy A0–A2 trên 40 trang đã chọn, A3 trên vùng số/ngày; chỉ thử A4/PP-StructureV3 nếu sai sót còn tập trung ở layout hoặc văn bản khó.
3. Tạo parser vùng và regression fixture cho 45/145/152/293, rồi đo trên holdout trang.
4. Lập relation/effect ledger cho 10 văn bản từ nguồn chính thức, bắt đầu với nhóm đã thấy trạng thái một phần hoặc hết hiệu lực.
5. Chỉ sau khi có phần dữ liệu được duyệt mới tạo một snapshot current QA nhỏ để thử retrieval, citation và từ chối khi thiếu chứng cứ.

Quyết định về model, DPI và rule cuối cùng phải ghi kèm dataset version, thông số, hash model, số đo holdout và các lỗi còn mở; không mặc định một phương pháp thắng chỉ vì tài liệu sản phẩm nói có hỗ trợ tiếng Việt.

## 7. Kết quả thực nghiệm và quyết định kỹ thuật hiện tại

Phương án nguồn toàn văn chính thức đã tìm được cho **cả 10 văn bản** qua Công báo điện tử, gồm PDF có lớp chữ; 145/2020/NĐ-CP gồm hai tệp. Bản ứng viên có 552 trang có nội dung/218.989 từ/895 chunk (ba trang trắng cuối tệp được loại) và qua kiểm tra giữ số từ, hash, thứ tự trang trong các tệp. Năm đoạn chép tay hiện có đều khớp nguyên văn. Với 18/VBHN-VPQH, bản Công báo 88 trang có đủ Điều 1–220 và trang in liên tục, khắc phục hai trang thiếu trong PDF scan cũ. Vì vậy ưu tiên tiếp theo là **thẩm định native text và hiệu lực**, không chạy OCR toàn bộ 496 trang một lần nữa. Xem [đánh giá mục 5](DATA_QUALITY_ASSESSMENT.md#5-thí-nghiệm-cải-tiến-ngày-2026-09-25-nguồn-công-báo-có-lớp-chữ).

Đã chạy Tesseract `fast_200`, `best_200`, `best_300` trên năm đoạn và bốn số ký hiệu khó. WER lần lượt 16,17%, 14,89%, 16,60%; crop số ở 300/400 DPI không đọc đúng ba số đầu trang. PP-OCRv5 chưa chạy được trên máy này do Windows Application Control chặn DLL của `pandas`. Không đổi model OCR mặc định theo điểm của tập chẩn đoán nhỏ.

Parser v2 đã tách phụ lục theo trang và chỉ tạo Điều chính khi số Điều tăng liên tục; Điều 68 được trích bên trong 70/2023/NĐ-CP không còn bị nhận thành Điều chính. Các ngoại lệ ở PDF scan được ghi riêng theo ảnh đã kiểm tra; bản Công báo được kiểm tra lại độc lập. Mọi chunk đầu ra vẫn có `unreviewed`/`unverified`.

Việc còn cần làm trước khi mở cổng: (1) tạo mẫu chép tay đại diện cho cả 10 văn bản, gồm bảng/phụ lục và số tiền/ngày/ngoại lệ; (2) kiểm tra thứ tự đọc, citation và đường dẫn nguồn từng chunk; (3) lập ledger hiệu lực theo Điều/khoản tại ngày truy vấn, kể cả các văn bản đã bị thay thế hoặc hết hiệu lực. Đã tải lại cả 11 phần PDF qua TLS xác minh với kho chứng chỉ Windows và so khớp SHA-256. Dị biệt nhãn “Nghị quyết” cho 45/2019/QH14 trên trang Công báo đã đối chiếu với chính PDF và VBPL: đây là **Bộ luật**. Kết quả 5/5 đoạn khớp giúp chọn nguồn ứng viên, **không tự chuyển các cổng còn lại sang đạt**.
