# Crawl artifacts

Run canonical hiện tại: [`pilot-canonical-2026-08-11`](pilot-canonical-2026-08-11/).

- `summary.json`: số liệu lần chạy;
- `manifest.jsonl`: provenance, checksum, robots, metadata và lỗi theo artifact;
- `config.snapshot.json`: cấu hình đóng băng;
- `quarantine/`: dữ liệu chưa được tax/legal reviewer phê duyệt.

Các thư mục `smoke-*`, `pilot-live-*`, `pilot-final-*` và `pilot-reviewed-*` là
evidence chẩn đoán trong quá trình hoàn thiện parser/transport, không phải run
canonical. Không index bất kỳ file nào trong thư mục này trực tiếp vào RAG.

Quy trình và kết quả: [docs/crawl-pilot.md](../../docs/crawl-pilot.md).
