# Chạy CiteAgent VN trên Kaggle

Dùng khi laptop không đủ GPU/RAM cho model lớn hơn (laptop phát triển: RTX 3050 4 GB, chạy được `qwen3:4b` làm bộ
xác minh). Kaggle cho GPU T4 ×2 (16 GB mỗi card) hoặc P100, đủ cho `qwen3:8b` hoặc `qwen3:14b`. Không dùng API key
nào: mọi model chạy trong notebook.

## Chuẩn bị trên máy của bạn (một lần)

```powershell
python scripts/download_sources.py                  # đủ 21 PDF chính thức, kiểm SHA-256
python scripts/pack_sources.py --with-embeddings    # dist/citeagent_sources.zip (~26 MB, kèm cache embedding)
```

Trên kaggle.com: *Datasets → New Dataset*, tải `dist/citeagent_sources.zip` lên, để **Private** (PDF là văn bản
công khai nhưng dự án không phân phối lại chúng). Bước này tránh việc Kaggle không truy cập được CDN của Chính phủ;
nếu bỏ qua, script sẽ thử tải trực tiếp.

## Chạy

1. *Create → New Notebook → File → Import Notebook*, chọn [`citeagent_kaggle.ipynb`](citeagent_kaggle.ipynb).
2. *Settings*: **Accelerator = GPU T4 x2** (hoặc P100), **Internet = On**.
3. *Add Input*: dataset `citeagent_sources.zip` vừa tạo.
4. Sửa `VERIFIER_MODEL` trong ô thứ 4 nếu muốn (`qwen3:4b` để so với laptop, `qwen3:8b`, `qwen3:14b`).
5. *Run All*. Thời gian ước tính: cài đặt và tải model 10–15 phút, build + index 3–5 phút, tinh chỉnh và đo 20–60
   phút tùy model.
6. Tải `citeagent_results.zip` ở mục *Output* và giải nén vào `reports/` của repo trên máy để so sánh.

Notebook chỉ gọi [`run_on_kaggle.sh`](run_on_kaggle.sh), có thể chạy trực tiếp trong một ô:

```bash
VERIFIER_MODEL=qwen3:8b SOURCES_ZIP=/kaggle/input/<dataset>/citeagent_sources.zip bash kaggle/run_on_kaggle.sh
```

## Script làm gì

| Bước | Lệnh | Ghi chú |
| --- | --- | --- |
| 1 | `pip install -r requirements/api.txt` | torch dùng bản có sẵn của Kaggle |
| 2 | tải `BAAI/bge-m3`, `BAAI/bge-reranker-v2-m3` | tokenizer phải có trước khi chia chunk |
| 3 | giải nén zip, `scripts/download_sources.py` | kiểm SHA-256 từng PDF |
| 4 | `ingestion.build --snapshot-id corpus-2026-10-01-r2`, `app.indexing` | build phải tái tạo đúng `chunks_sha256` đã công bố; nếu khác, script build `…-kaggle` và báo |
| 5 | cài Ollama, `ollama pull $VERIFIER_MODEL` | |
| 6 | `scripts/run_verifier_eval.py --model $VERIFIER_MODEL` | chỉnh `verifier_floor`/`verifier_veto` trên dev v2 + paraphrase dev, rồi đo **một lần** trên test v2, held-out v2, held-out v1; thêm một lần đo held-out v2 không có bộ xác minh để so |
| 7 | in tóm tắt, nén `reports/` | |

Kết quả nằm ở `reports/verifier_tuning_ollama_<model>.json` và `reports/answers_<split>_extractive_verifier_<model>.json`.
Báo cáo ghi commit, snapshot, model và phần cứng của lần chạy.

## Sự cố thường gặp

- **`build did not reproduce`**: môi trường Kaggle cho text khác (thường do thiếu tokenizer). Kết quả vẫn dùng được
  với snapshot `…-kaggle`, nhưng ghi rõ khi so sánh với laptop.
- **Ollama không cài được**: kiểm tra Internet đã bật; script cần `zstd` (tự cài bằng apt).
- **Hết thời gian phiên** (12 giờ): chạy lại ô cuối với `VERIFIER_MODEL` nhỏ hơn hoặc bỏ bước tinh chỉnh
  (`python scripts/run_verifier_eval.py --model qwen3:8b --skip-tune --floor 0.05`).
