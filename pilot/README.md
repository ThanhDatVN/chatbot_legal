# Pilot 10 văn bản

Pilot này thu 10 trang metadata và PDF từ `vanban.chinhphu.vn`/`datafiles.chinhphu.vn`, rồi đo khả năng trích text và thử OCR. Đây là thí nghiệm ingestion, **không phải corpus pháp luật hiện hành đã kiểm duyệt**. Kết quả thu thập ở [`../docs/PILOT_10_DOCUMENTS.md`](../docs/PILOT_10_DOCUMENTS.md); đánh giá chất lượng và cổng sử dụng ở [`../docs/DATA_QUALITY_ASSESSMENT.md`](../docs/DATA_QUALITY_ASSESSMENT.md).

## Chạy lại trên Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r pilot\requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m pilot.collect
.\.venv\Scripts\python.exe -X utf8 -m pilot.download_models --best
.\.venv\Scripts\python.exe -X utf8 -m pilot.process_local --ocr
.\.venv\Scripts\python.exe -X utf8 -m pilot.evaluate_ocr
.\.venv\Scripts\python.exe -X utf8 -m pilot.audit
.\.venv\Scripts\python.exe -X utf8 -m pilot.evaluate_data_quality
.\.venv\Scripts\python.exe -X utf8 -m pilot.assess_quality
.\.venv\Scripts\python.exe -X utf8 -m pilot.validate
.\.venv\Scripts\python.exe -m pytest -q pilot\test_pilot.py
.\.venv\Scripts\python.exe -X utf8 -m pilot.benchmark_ocr
.\.venv\Scripts\python.exe -X utf8 -m pilot.benchmark_id_crops
.\.venv\Scripts\python.exe -X utf8 -m pilot.structure_v2
.\.venv\Scripts\python.exe -X utf8 -m pilot.validate_structure_v2
.\.venv\Scripts\python.exe -m pytest -q pilot\test_structure_v2.py
.\.venv\Scripts\python.exe -X utf8 -W ignore -m pilot.collect_congbao_candidates
.\.venv\Scripts\python.exe -X utf8 -m pilot.audit_congbao_alternate
.\.venv\Scripts\python.exe -X utf8 -m pilot.audit_congbao_candidates
.\.venv\Scripts\python.exe -X utf8 -m pilot.build_congbao_candidate
.\.venv\Scripts\python.exe -X utf8 -m pilot.validate_congbao_candidate
.\.venv\Scripts\python.exe -X utf8 -m pilot.assess_quality
```

`pilot.collect` chỉ chạy khi chưa có manifest để tránh ghi đè bản tải. Muốn tạo snapshot mới, đổi `OUT` sang thư mục mới và ghi lại ngày thu thập. `process_local` có thể chạy lại từ PDF đã tải; kết quả OCR theo từng trang được cache. Kiểm tra SHA-256 của model được định nghĩa trong `download_models.py`.

## Artefact

`data/pilot/2026-09-24/manifest.jsonl` chứa metadata, URL chính thức, hash, trạng thái trích text và OCR. `summary.json` là tổng số. `ocr_quality_probe.json` ghi phép so sánh OCR trên một đoạn được chép tay từ ảnh nguồn. `data_quality_metrics.json` ghi 5 đoạn đối chiếu và `data_quality_summary.json` tổng hợp cổng chất lượng. Raw HTML/PDF, text từng trang, OCR và chunk ở cùng thư mục nhưng được `.gitignore` loại khỏi commit vì quyền phân phối lại nguồn chưa được xác nhận.

`ocr_chunks` chỉ phục vụ phân tích kỹ thuật; `ocr_review_status=unreviewed` nên không được dùng làm evidence cho câu trả lời pháp lý. `word_count` là số từ tách bằng khoảng trắng, **không phải tokenizer của embedding model**.

`candidate_congbao_all` là ứng viên **riêng** từ PDF có lớp chữ của Công báo: 10 văn bản, 552 trang có nội dung, 218.989 từ, 895 chunk. Ba trang trắng cuối tệp được loại và giữ ánh xạ trang PDF nguồn. Các tệp PDF tải về, trang, section và chunk ứng viên được `.gitignore` loại khỏi commit; chỉ inventory, hash, kiểm tra và tài liệu được giữ để tái lập. Mọi chunk ứng viên là `unreviewed`/`unverified`, chưa được đưa vào current QA index. Collector dùng kho chứng chỉ Windows để xác minh TLS của CDN, giới hạn hostname chính thức, kiểm tra PDF magic và ghi SHA-256; khi chạy lại, hash của bản tải mới phải khớp bản đã lưu.
