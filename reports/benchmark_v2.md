# Benchmark CiteAgent VN — v2

_Tệp này được sinh tự động bởi `python -m evaluation.report` từ các báo cáo JSON trong `reports/`._

## Điều kiện chạy

- Ngày chạy: 2026-10-01T08:18:46+00:00 · commit `33f11cc`
- Snapshot corpus: `corpus-2026-10-01` · chính sách hiệu lực: `pilot`
- Embedding: `BAAI/bge-m3` · reranker: `BAAI/bge-reranker-v2-m3`
- Truy xuất: dense top 20, BM25 top 20, RRF k=60
- Chế độ trả lời: `extractive` (LLM cấu hình: `claude-opus-5-5`)
- Chính sách bằng chứng: `{"answer_threshold": 0.8, "keep_ratio": 0.85, "stronger_margin": 0.15, "unverified_threshold": 0.5, "max_sources": 3, "superseded_margin": 0.0}`
- Dữ liệu đánh giá: `questions_v2.jsonl`, split `test`
- Phần cứng: NVIDIA GeForce RTX 3050 Laptop GPU · torch 2.14.0+cu126 · Windows-10-10.0.26300-SP0

## Bảng tổng hợp

| Hệ thống | Hit@5 | MRR | Citation precision | Correctness | Refusal accuracy | p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A — Dense + RAG đơn giản | 0.984 | 0.922 | 0.529 | 0.578 | 0.681 | 85 |
| B — Dense + BM25 + RRF | 0.984 | 0.947 | 0.549 | 0.547 | 0.681 | 90 |
| C — Hybrid + reranker | 1.000 | 0.982 | 0.578 | 0.562 | 0.681 | 1,016 |
| D — Hybrid + reranker + từ chối + kiểm tra citation | 1.000 | 0.982 | 0.634 | 0.891 | 0.957 | 4,202 |

Hit@5/MRR đo ở tầng truy xuất trên toàn bộ 64 câu trả lời được (D dùng cùng bộ truy xuất với C). Các cột còn lại đo đầu cuối trên split test. Correctness và citation precision là chỉ số tự động (proxy) — xem định nghĩa trong `docs/EVALUATION.md`.

## Truy xuất

| Hệ thống | Hit@5 | MRR | Recall@5 | Recall@10 | Đủ mọi bằng chứng@5 (multi) | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_dense | 0.984 | 0.922 | 0.932 | 0.969 | 0.700 | 54 | 70 |
| B_hybrid | 0.984 | 0.947 | 0.953 | 1.000 | 0.800 | 61 | 69 |
| C_rerank | 1.000 | 0.982 | 0.961 | 1.000 | 0.750 | 934 | 980 |

Câu bị trượt Hit@5: A_dense: dir_34; B_hybrid: dir_34; C_rerank: không

## Trả lời đầu cuối

| Hệ thống | Quyết định đúng | Refusal P / R / F1 | Trả lời sai | Từ chối nhầm | Correctness (0/1/2) | Citation precision | Groundedness | Vi phạm đối kháng | p50 / p95 ms | Chi phí LLM /100 |
| --- | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: |
| A — Dense + RAG đơn giản | 0.706 | 0.000 / 0.000 / 0.000 | 15 | 0 | 0.578 (10/7/15) | 0.529 | 1.000 | 3 | 70 / 85 | $0.00 |
| B — Dense + BM25 + RRF | 0.706 | 0.000 / 0.000 / 0.000 | 15 | 0 | 0.547 (11/7/14) | 0.549 | 1.000 | 3 | 81 / 90 | $0.00 |
| C — Hybrid + reranker | 0.706 | 0.000 / 0.000 / 0.000 | 15 | 0 | 0.562 (11/6/15) | 0.578 | 1.000 | 3 | 949 / 1,016 | $0.00 |
| D — Hybrid + reranker + từ chối + kiểm tra citation | 0.961 | 0.933 / 0.933 / 0.933 | 1 | 1 | 0.891 (2/3/27) | 0.634 | 1.000 | 0 | 1,433 / 4,202 | $0.00 |

Độ trễ của D theo bước (p50 / p95 ms): truy xuất 100 / 287, rerank 1,323 / 3,767, phần còn lại 52 / 196.

Tỷ lệ quyết định đúng theo loại câu hỏi (D): adversarial 5/5, ambiguous 2/2, direct 21/22, multi 10/10, out_of_scope 5/5, unanswerable 6/7.

Ca lỗi của D: dir_34, una_10.

## Hiệu chỉnh ngưỡng (chỉ trên split dev)

- Tham số chọn: `{"answer_threshold": 0.8, "keep_ratio": 0.85, "stronger_margin": 0.15, "unverified_threshold": 0.5, "max_sources": 3, "superseded_margin": 0.0}`
- Điểm của tham số chọn trên dev: `{"accuracy": 0.9623, "false_answers": 1, "false_refusals": 1, "objective": 0.9434}`
- Kết quả tốt nhất trên dev: độ chính xác 0.962, trả lời sai 1, từ chối nhầm 1
- chosen = PolicyConfig defaults used by the service; ties on stronger_margin are broken towards the middle value
- superseded_margin added with dataset v2: None -> 3 false answers on dev, 0.0 -> 1 with no extra false refusal; 0.0 chosen
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

