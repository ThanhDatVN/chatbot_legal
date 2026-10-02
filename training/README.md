# Fine-tune reranker cho câu hỏi đời thường

Điểm yếu lớn nhất của chế độ extractive: câu hỏi đời thường ("công ty có được giữ bằng gốc không?") thường đưa đúng
Điều lên đầu nhưng điểm cross-encoder thấp hơn ngưỡng trả lời 0.8, nên hệ thống **từ chối nhầm** (10/28 câu trả lời
được trên held-out v2). Bộ xác minh `qwen3:4b` chỉ hòa vốn
([`docs/EVALUATION.md` §4c](../docs/EVALUATION.md#4c-model-nhỏ-trên-máy-bộ-xác-minh-vùng-xám-2026-10-02)).
Thư mục này tinh chỉnh chính reranker `BAAI/bge-reranker-v2-m3` (568M tham số) để điểm liên quan không phụ thuộc
cách nói, vẫn là model nhỏ chạy được trên laptop khi suy luận.

## Pipeline

| Bước | Lệnh | Làm gì |
| --- | --- | --- |
| 1 | `python -m training.generate_queries` | Model cục bộ (Ollama) viết 3 câu hỏi đời thường mà chunk trả lời được và 1 câu "gần đúng" (cùng chủ đề, chunk không trả lời), cho 861 chunk trong phạm vi. Bộ xác minh tự kiểm: bỏ câu hỏi chunk không trả lời và câu gần đúng chunk lại trả lời. Tiếp tục được nếu bị ngắt. |
| 2 | `python -m training.mine_negatives` | Bỏ câu gần trùng với **mọi** bộ đánh giá (Jaccard 4-gram ký tự ≥ 0.5 hoặc cosine bge-m3 ≥ 0.92). Negative khó lấy từ top 30 hybrid, không bao giờ là phần khác của cùng Điều hay Điều dẫn chiếu/được dẫn chiếu (Nghị định hướng dẫn trả lời cùng câu hỏi). Ứng viên reranker gốc chấm ≥ 0.5 (hoặc cao hơn positive) có thể là negative giả: model kiểm tra, còn lại bị bỏ. |
| 3 | `python -m training.train_reranker` | BCE từng cặp (giữ điểm sigmoid hiệu chỉnh cho ngưỡng tuyệt đối) + softmax CE positive so với negative (xếp hạng). Đóng băng ma trận embedding 250k token; fp16, gradient checkpointing, AdamW lr 1e-5, 1 epoch. Chọn epoch tốt nhất trên tập validation tổng hợp (~1/10 số Điều, chia theo hash). |
| 4 | `python -m training.compare` | Bảng so sánh reranker gốc và đã tinh chỉnh từ các báo cáo. |

Đầu ra: `data/training/queries.jsonl`, `pairs.jsonl`, `pairs_summary.json`; model ở `models/reranker-ft/`
(fp16, ~1,1 GB, kèm `training_meta.json`). Cả hai thư mục nằm ngoài git.

## Chạy ở đâu

- **Huấn luyện cần GPU ~12 GB** → Kaggle T4. Notebook [`kaggle/citeagent_reranker_finetune.ipynb`](../kaggle/citeagent_reranker_finetune.ipynb)
  gọi [`kaggle/finetune_reranker.sh`](../kaggle/finetune_reranker.sh) làm trọn: đo reranker gốc → sinh câu hỏi
  (`qwen3:8b`, ~1–2 giờ) → đào negative → huấn luyện (~1 giờ) → đo lại. Hướng dẫn: [`kaggle/README.md`](../kaggle/README.md).
- **Sinh câu hỏi có thể chạy trên laptop** (RTX 3050 4 GB, `qwen3:4b`, ~8 s/chunk ≈ 2 giờ), rồi tải
  `data/training/queries.jsonl` lên Kaggle làm input để bỏ qua bước 1. Chất lượng câu hỏi của model 4B kém hơn
  (hay giữ nguyên thuật ngữ luật), nên ưu tiên sinh trên Kaggle với 8B/14B.
- `GEN_BACKEND=openai` với `gpt-4o-mini` cũng được (~0,3 USD cho cả kho; ước tính in ra trước khi chạy).

## Dùng model đã tinh chỉnh

Giải nén `citeagent_reranker_ft.zip` vào `models/`, rồi trong `.env`:

```ini
RERANKER_MODEL=models/reranker-ft    # tính từ thư mục gốc repo, nơi chạy API/UI
```

Ngưỡng của chính sách bằng chứng được chọn cho reranker gốc. Với reranker mới, dùng ngưỡng mà
`python -m evaluation.tune_policy --tag _rr_ft` chọn trên dev v2 + paraphrase dev (`reports/policy_tuning_rr_ft.json`);
chỉ đổi mặc định trong [`app/agent/policy.py`](../app/agent/policy.py) sau khi so sánh trên held-out v3 cho thấy
cải thiện.

## Nguyên tắc chống rò rỉ

- Held-out v3 ([`evaluation/heldout_v3.py`](../evaluation/heldout_v3.py)) được commit **trước** khi pipeline này tồn
  tại (`9f46146`), không dùng để chọn bất cứ thứ gì; mỗi cấu hình đo một lần ở cuối.
- Câu hỏi đánh giá chỉ được đọc để **loại** câu huấn luyện gần trùng, không bao giờ để sinh hay chọn dữ liệu.
- Mô hình sinh câu hỏi chỉ thấy văn bản luật của một chunk, không thấy câu hỏi đánh giá.
- Validation tổng hợp tách theo Điều (không theo câu), để không có câu hỏi về cùng Điều ở cả hai phía.
