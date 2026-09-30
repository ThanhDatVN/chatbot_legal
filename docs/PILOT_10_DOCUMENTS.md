# Pilot thu thập và xử lý 10 văn bản chính thức

Ngày chạy: 2026-09-24 · Trạng thái: **thí nghiệm ingestion, chưa phát hành corpus cho hỏi đáp pháp lý**. Mã và cách chạy lại: [`../pilot/README.md`](../pilot/README.md). Đánh giá chất lượng sau pilot: [`DATA_QUALITY_ASSESSMENT.md`](DATA_QUALITY_ASSESSMENT.md). Dữ liệu đo: [`../data/pilot/2026-09-24/manifest.jsonl`](../data/pilot/2026-09-24/manifest.jsonl), [`summary.json`](../data/pilot/2026-09-24/summary.json), [`ocr_quality_probe.json`](../data/pilot/2026-09-24/ocr_quality_probe.json), [hàng đợi QA](../data/pilot/2026-09-24/quality_audit.jsonl).

## 1. Mục tiêu và mẫu

Pilot kiểm tra một đường thu thập thực: trang metadata chính thức → PDF đính kèm → hash/provenance → trích text theo trang → phát hiện scan → OCR tiếng Việt → chia theo Điều → đo lỗi và điều chỉnh kế hoạch. Đây là **mẫu chẩn đoán**, gồm văn bản gốc, văn bản hợp nhất, văn bản hướng dẫn/sửa đổi, các phiên bản theo thời gian và một văn bản sát ranh giới phạm vi. Việc có mặt trong pilot **không có nghĩa** văn bản còn hiệu lực hoặc được duyệt vào current corpus.

Trang chi tiết của VBPL trả HTTP 403 với client mặc định và redirect 308 về trang chủ với User-Agent thử nghiệm trong môi trường này. Vì vậy pilot dùng 10 trang metadata và PDF đính kèm trên Cổng văn bản Chính phủ; nguồn PDF thực tế ở `datafiles.chinhphu.vn`. Kết quả này nói về đường truy cập của môi trường hiện tại, không kết luận VBPL luôn không truy cập được.

| Văn bản và trang nguồn chính thức | Vai trò trong mẫu | Trang PDF | Từ OCR | Chunk OCR thử nghiệm |
| --- | --- | ---: | ---: | ---: |
| [45/2019/QH14](https://vanban.chinhphu.vn/?classid=1&docid=198540&pageid=27160&typegroupid=3) | Bộ luật gốc | 83 | 38.792 | 223 |
| [18/VBHN-VPQH](https://vanban.chinhphu.vn/?classid=2629&docid=217002&pageid=27160) | bản hợp nhất, loại riêng | 86 | 38.207 | 219 |
| [145/2020/NĐ-CP](https://vanban.chinhphu.vn/default.aspx?docid=201967&pageid=27160) | nghị định hướng dẫn lớn, có biểu mẫu | 122 | 47.397 | 165 |
| [135/2020/NĐ-CP](https://vanban.chinhphu.vn/default.aspx?docid=201650&pageid=27160) | tuổi nghỉ hưu | 15 | 3.278 | 12 |
| [152/2020/NĐ-CP](https://vanban.chinhphu.vn/?classid=1&docid=202215&orggroupid=2&pageid=27160) | lao động nước ngoài, có biểu mẫu | 55 | 18.512 | 57 |
| [70/2023/NĐ-CP](https://vanban.chinhphu.vn/?classid=1&docid=208673&orggroupid=2&pageid=27160) | văn bản sửa đổi | 21 | 7.084 | 16 |
| [293/2025/NĐ-CP](https://vanban.chinhphu.vn/?classid=1&docid=215832&orggroupid=2&pageid=27160) | lương tối thiểu và phụ lục địa bàn | 14 | 6.013 | 15 |
| [74/2024/NĐ-CP](https://vanban.chinhphu.vn/?classid=1&docid=210536&orggroupid=2&pageid=27160) | phiên bản lương tối thiểu cũ hơn | 9 | 2.945 | 9 |
| [38/2022/NĐ-CP](https://vanban.chinhphu.vn/?classid=1&docid=205950&pageid=27160&typegroupid=5) | phiên bản lương tối thiểu cũ hơn | 8 | 2.680 | 9 |
| [12/2022/NĐ-CP](https://vanban.chinhphu.vn/?classid=1&docid=205182&orggroupid=2&pageid=27160) | ranh giới phạm vi: xử phạt lao động và lĩnh vực khác | 83 | 35.959 | 101 |

Tất cả 10 bản ghi có số ký hiệu, tiêu đề, loại, cơ quan ban hành, URL trang, URL PDF, ngày tải, SHA-256 HTML/PDF và `license=publicly_accessible_unknown_license`. `legal_status=unverified`, `review_status=pilot_only`; không có xác nhận hiệu lực cấp điều khoản. Tổng PDF 61.157.329 bytes (~58,3 MiB); metadata HTML 822.766 bytes. Không có tệp đính kèm PDF thứ hai trên các trang mẫu này.

## 2. Cách xử lý và số đo

- Native extraction: PyMuPDF `get_text("text", sort=True)` theo trang, NFC và chuẩn hóa whitespace bảo thủ. Phát hiện scan khi dưới 20% trang có ≥50 từ **và** ít nhất 80% trang có ảnh chiếm ≥80% diện tích trang. Ngưỡng là heuristic pilot, cần kiểm thử trên PDF born-digital và mixed PDF trước khi dùng rộng.
- OCR: PyMuPDF/Tesseract tích hợp, `vie` từ `tessdata_fast`, 200 DPI, toàn trang. OCR lưu theo trang; dùng `sort=False` vì `sort=True` làm đảo vị trí từ trong các trang thử. Model được kiểm tra SHA-256, trang gốc vẫn giữ nguyên.
- Chunk thử nghiệm: nhận diện tiêu đề `Điều <số>.` hoặc `Điều <số>:`; đoạn dài tách tối đa 600 **từ theo khoảng trắng**, overlap 80 từ. Đây chưa phải token count của embedding model. Mỗi từ giữ page gốc khi tạo chunk để trang trích dẫn chính xác hơn.

| Chỉ số | Kết quả |
| --- | ---: |
| Trang metadata và PDF tải thành công | 10/10 |
| Tổng trang PDF | 496 |
| Trang là ảnh toàn trang | 496/496 |
| Từ native extraction | 210, chủ yếu text phụ |
| PDF được chặn khỏi native index vì scan | 10/10 |
| Trang OCR hoàn tất | 496/496 |
| Từ OCR thử nghiệm | 200.867 |
| Chunk OCR thử nghiệm | 826 |
| Chunk có page span rộng do mất mapping | 0 sau sửa; trước sửa: 190 |
| Kiểm thử pilot | 5/5 đạt |

Phát hiện scan đã sửa một lỗi thực: lần chạy đầu đánh dấu cả 10 file là “processed” chỉ vì mỗi PDF có vài từ phụ. Sau sửa, native index có **0 chunk** từ 10 file này; OCR output có `ocr_review_status=unreviewed` và chưa được đưa vào hệ hỏi đáp. Việc siết regex tiêu đề từ `Điều <số>` tùy ý sang yêu cầu dấu chấm/hai chấm làm số chunk thử nghiệm giảm từ 869 xuống 826; đây là giảm 43 chunk, **không chứng minh tất cả 43 đều sai**. Một trường hợp sai đã xác nhận là dòng dẫn chiếu “Điều 112 của Bộ luật...” bị coi như tiêu đề.

## 3. Kiểm tra chất lượng OCR và cấu trúc

Một đoạn ngắn ở trang 42 của 45/2019/QH14 (tiêu đề Điều 113, câu mở đầu và điểm a) được chép tay từ ảnh PDF để đo. Sau NFC, lowercase, bỏ dấu câu và gộp whitespace:

| Model tiếng Việt | Character error rate | Word error rate |
| --- | ---: | ---: |
| `tessdata_fast/vie`, 200 DPI | 2,51% | 17,31% |
| `tessdata_best/vie`, 200 DPI | 2,09% | 13,46% |

Đây chỉ là **một đoạn 239 ký tự sau chuẩn hóa**, không thể ngoại suy cho cả corpus. Từ bị dính, dấu bị đọc sai và số/ký hiệu pháp lý có thể sai. Kiểm tra ảnh trang 5 của 293/2025/NĐ-CP cho thấy OCR đọc ký hiệu trong phụ lục thành `293/2023/NĐ-CP` trong khi ảnh nguồn ghi `293/2025/NĐ-CP`. Vì thế không dùng OCR text chưa review làm căn cứ kết luận, dù một số câu có thể vẫn đọc hiểu được.

Chunking theo mỗi `Điều` cũng chưa đủ. 145/2020/NĐ-CP có các mẫu hợp đồng/quyết định trong phụ lục từ khoảng trang 90; OCR nhận thêm 16 tiêu đề Điều trùng số với phần thân. 152/2020/NĐ-CP có biểu mẫu từ khoảng trang 27 và thêm 4 tiêu đề Điều trùng. Trong 45/2019/QH14, Điều 219 trích dẫn điều của luật khác; một dòng `Điều 55` bị nhận như Điều 55 mới của chính Bộ luật. Phần phụ lục của 293/2025/NĐ-CP bị gộp vào section trước đó, tạo section dài 5.084 từ. Những đoạn này cần `section_path`, loại vùng `main_text/annex/quoted_amendment` và review bằng ảnh nguồn trước khi index.

Script audit đã tạo **108 cảnh báo mở** cho reviewer: 14 nhóm tiêu đề Điều trùng, 20 section dài hơn 1.200 từ, 58 trang có dấu hiệu phụ lục/biểu mẫu và 16 trang OCR dưới 100 từ. Đây là **tín hiệu ưu tiên review**, không phải 108 lỗi đã được xác nhận; một trang có thể xuất hiện trong nhiều nhóm.

## 4. Quyết định cải tiến luồng

| Ưu tiên | Thay đổi | Trạng thái |
| --- | --- | --- |
| 1 | Thu metadata và tải PDF từ portal chính thức, lưu hash/URL/file gốc, tránh tự gán hiệu lực | Đã làm trong pilot |
| 2 | Phát hiện scan theo tỷ lệ trang/ảnh; không coi footer text là toàn văn | Đã làm + test |
| 3 | OCR offline có cache theo trang, model hash, ngôn ngữ/DPI; `sort=False` cho nhánh OCR | Đã thử trên 496 trang |
| 4 | Giữ vị trí trang theo từng từ/chunk thay vì gắn cả page span của Điều dài | Đã làm + test |
| 5 | Tìm nguồn toàn văn HTML chính thức có thể truy cập và kiểm tra VBPL trong môi trường khác; không phụ thuộc một portal | Chưa làm |
| 6 | Cổng QA OCR: review điều khoản, số/ngày, bảng/phụ lục; chỉ `verified` mới được citation | Đã tạo hàng đợi cảnh báo, chưa duyệt/approve |
| 7 | Nhận diện phụ lục, biểu mẫu và nội dung sửa luật được trích dẫn; section path có context | Chưa làm |
| 8 | Kiểm tra quan hệ sửa đổi/hiệu lực ở cấp điều khoản trước current corpus | Chưa làm |

Pilot **không** đánh giá retrieval/LLM hay tính đúng đắn pháp lý. Chưa có corpus current-law nào được công bố từ 10 file này. Các trang cũ hơn, bản hợp nhất và văn bản sát ranh giới phạm vi được giữ để thử kỹ thuật và lọc, không tự động trở thành nguồn trả lời.

## 5. Tái lập và giới hạn

Phiên bản môi trường đã chạy: Python 3.11.9, `requests 2.34.2`, `beautifulsoup4 4.15.0`, `PyMuPDF 1.28.2`. SHA-256 của model `tessdata_fast/vie` và `tessdata_best/vie` được khóa trong `pilot/download_models.py`. Raw PDF/HTML, OCR text, ảnh QA và model nằm tại `data/pilot/2026-09-24/` trong workspace, nhưng `.gitignore` không đưa chúng vào commit khi chưa xác nhận quyền phân phối. Manifest, summary và quality metrics là các artefact nhỏ có thể review.

Nguồn kỹ thuật chính thức: [PyMuPDF OCR](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html), [PyMuPDF cài language data](https://pymupdf.readthedocs.io/en/latest/installation.html), [Tesseract Vietnamese language data](https://github.com/tesseract-ocr/tessdata/blob/main/script/Vietnamese.traineddata).
