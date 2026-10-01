# Benchmark CiteAgent VN — v1

_Tệp này được sinh tự động bởi `python -m evaluation.report` từ các báo cáo JSON trong `reports/`._

## Điều kiện chạy

- Ngày chạy: 2026-10-01T02:40:42+00:00 · commit `ecfeb14-dirty`
- Snapshot corpus: `corpus-2026-09-30` · chính sách hiệu lực: `pilot`
- Embedding: `BAAI/bge-m3` · reranker: `BAAI/bge-reranker-v2-m3`
- Truy xuất: dense top 20, BM25 top 20, RRF k=60
- Chế độ trả lời: `extractive` (LLM cấu hình: `claude-opus-5-5`)
- Chính sách bằng chứng: `{"answer_threshold": 0.8, "keep_ratio": 0.85, "stronger_margin": 0.15, "unverified_threshold": 0.5, "max_sources": 3}`
- Dữ liệu đánh giá: `questions_v1.jsonl`, split `test`
- Phần cứng: NVIDIA GeForce RTX 3050 Laptop GPU · torch 2.14.0+cu126 · Windows-10-10.0.26300-SP0

## Bảng tổng hợp

| Hệ thống | Hit@5 | MRR | Citation precision | Correctness | Refusal accuracy | p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A — Dense + RAG đơn giản | 0.983 | 0.968 | 0.541 | 0.617 | 0.667 | 151 |
| B — Dense + BM25 + RRF | 1.000 | 0.983 | 0.561 | 0.583 | 0.667 | 164 |
| C — Hybrid + reranker | 1.000 | 1.000 | 0.582 | 0.600 | 0.667 | 1,043 |
| D — Hybrid + reranker + từ chối + kiểm tra citation | 1.000 | 1.000 | 0.708 | 0.917 | 0.978 | 4,292 |

Hit@5/MRR đo ở tầng truy xuất trên toàn bộ 60 câu trả lời được (D dùng cùng bộ truy xuất với C). Các cột còn lại đo đầu cuối trên split test. Correctness và citation precision là chỉ số tự động (proxy) — xem định nghĩa trong `docs/EVALUATION.md`.

## Truy xuất

| Hệ thống | Hit@5 | MRR | Recall@5 | Recall@10 | Đủ mọi bằng chứng@5 (multi) | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_dense | 0.983 | 0.968 | 0.967 | 0.992 | 0.900 | 74 | 91 |
| B_hybrid | 1.000 | 0.983 | 0.983 | 1.000 | 0.900 | 86 | 106 |
| C_rerank | 1.000 | 1.000 | 0.992 | 1.000 | 0.950 | 894 | 1,003 |

Câu bị trượt Hit@5: A_dense: dir_34; B_hybrid: không; C_rerank: không

## Trả lời đầu cuối

| Hệ thống | Quyết định đúng | Refusal P / R / F1 | Trả lời sai | Từ chối nhầm | Correctness (0/1/2) | Citation precision | Groundedness | Vi phạm đối kháng | p50 / p95 ms | Chi phí LLM /100 |
| --- | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: |
| A — Dense + RAG đơn giản | 0.694 | 0.000 / 0.000 / 0.000 | 15 | 0 | 0.617 (8/7/15) | 0.541 | 1.000 | 3 | 98 / 151 | $0.00 |
| B — Dense + BM25 + RRF | 0.694 | 0.000 / 0.000 / 0.000 | 15 | 0 | 0.583 (9/7/14) | 0.561 | 1.000 | 3 | 125 / 164 | $0.00 |
| C — Hybrid + reranker | 0.694 | 0.000 / 0.000 / 0.000 | 15 | 0 | 0.600 (9/6/15) | 0.582 | 1.000 | 3 | 975 / 1,043 | $0.00 |
| D — Hybrid + reranker + từ chối + kiểm tra citation | 0.980 | 0.938 / 1.000 / 0.968 | 0 | 1 | 0.917 (1/3/26) | 0.708 | 1.000 | 0 | 1,440 / 4,292 | $0.00 |

Độ trễ của D theo bước (p50 / p95 ms): truy xuất 135 / 412, rerank 1,279 / 3,826, phần còn lại 41 / 135.

Tỷ lệ quyết định đúng theo loại câu hỏi (D): adversarial 5/5, ambiguous 2/2, direct 19/20, multi 10/10, out_of_scope 5/5, unanswerable 7/7.

Ca lỗi của D: dir_34.

## Hiệu chỉnh ngưỡng (chỉ trên split dev)

- Tham số chọn: `{"answer_threshold": 0.8, "keep_ratio": 0.85, "stronger_margin": 0.15, "unverified_threshold": 0.5, "max_sources": 3}`
- Điểm của tham số chọn trên dev: `{"accuracy": 0.9608, "false_answers": 1, "false_refusals": 1, "objective": 0.9412}`
- Kết quả tốt nhất trên dev: độ chính xác 0.961, trả lời sai 1, từ chối nhầm 1
- chosen = PolicyConfig defaults used by the service; ties on stronger_margin are broken towards the middle value
- keep_ratio swept on dev with the full answer pipeline: 0.5/0.7 -> citation precision 0.818, correctness 0.917; 0.85 -> 0.844 / 0.917; 0.95 -> 0.891 / 0.883 (correctness drops). Chose 0.85.

## Bộ kiểm thử bảo mật: 30/30 ca đạt

| Nhóm | Số ca | Đạt |
| --- | ---: | ---: |
| prompt_injection | 3 | 3 |
| instruction_override | 2 | 2 |
| citation_fabrication | 4 | 4 |
| source_manipulation | 3 | 3 |
| data_exfiltration | 3 | 3 |
| out_of_domain | 2 | 2 |
| unsupported_factual | 2 | 2 |
| tool_misuse | 6 | 6 |
| indirect_injection | 5 | 5 |

