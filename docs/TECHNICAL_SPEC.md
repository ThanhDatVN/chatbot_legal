# CiteAgent VN — đặc tả kỹ thuật MVP

Trạng thái: cập nhật sau [pilot 10 văn bản](PILOT_10_DOCUMENTS.md) · 2026-09-24. Tài liệu này cụ thể hóa [`ARCHITECTURE.md`](ARCHITECTURE.md); thứ tự thực hiện và tiêu chí từng task ở [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

## 1. Công nghệ và lý do chọn

| Vai trò | Lựa chọn MVP | Ghi chú |
| --- | --- | --- |
| Runtime | Python 3.12, lockfile với phiên bản xác định | kiểm tra hỗ trợ của từng dependency khi tạo `pyproject.toml` |
| API và schema | FastAPI, Pydantic v2 | typed request/response, OpenAPI, TestClient |
| UI | Streamlit | chat, source viewer, document browser, evaluation page |
| HTTP/HTML | HTTPX, BeautifulSoup | adapter VBPL và parser HTML tách riêng |
| PDF/OCR | PyMuPDF + Tesseract Vietnamese language data khi cần | phát hiện scan; OCR offline có cache và QA; kiểm tra điều kiện AGPL/commercial trước khi phân phối |
| Embedding | `BAAI/bge-m3` **candidate mặc định** | chạy thử tiếng Việt, CPU/RAM, và khóa model revision trước ingest |
| Sparse | `rank_bm25` và tokenizer xác định | artifact theo snapshot, không dùng tokenizer khác giữa ingest/query |
| Reranker | `BAAI/bge-reranker-v2-m3` **candidate** | interface thay được; đo latency trước chốt |
| Vector store | Qdrant | dense vectors, payload, filter theo metadata |
| Metadata/session | SQLite | manifest catalog, session, feedback; không dùng làm vector index |
| Agent | LangGraph graph nhỏ ở milestone 7 | hai business tools, không phụ thuộc ở baseline |
| Test | pytest, FastAPI TestClient | unit, integration, security, evaluation |
| Runtime packaging | Docker Compose | `api`, `ui`, `qdrant`, volumes cho DB/index/cache |

Các model trên là ứng viên, chưa có benchmark của project. Quyết định cuối cùng cần ghi model revision, kích thước vector, CPU/RAM, license và số đo trên tập eval. Một LLM provider được cấu hình qua `LLMClient` adapter; không khóa logic agent vào SDK. Khóa API lấy từ môi trường, không đưa vào log/repo.

## 2. Bố cục mã nguồn dự kiến

```text
app/
  api/{chat,search,sources,documents,feedback,health}.py
  agent/{graph,state,tools,prompts,policies}.py
  retrieval/{dense,sparse,hybrid,rrf,reranker}.py
  generation/{llm_client,answer,citation_validator}.py
  storage/{qdrant,metadata,sessions}.py
  schemas/{document,chunk,chat,citation,retrieval}.py
corpus/
  adapters/{vbpl,government_portal}.py
  {seeds,discover,relations,filter,review,snapshot}.py
ingestion/{pdf_parser,html_parser,normalize,chunk,index,manifest}.py
ui/{app,pages,components}/
eval/{dataset,retrieval,answers,citations,refusal,security,report}.py
tests/{unit,integration,security,fixtures}/
data/{seeds,review,snapshots,eval}/
scripts/
```

`corpus/` bổ sung cho cấu trúc gợi ý trong `details.md` theo quyết định ở `data.md`. CLI offline không chạy trong API process. Tên file có thể chỉnh khi code, nhưng ranh giới layer cần giữ.

## 3. Mô hình dữ liệu

### 3.1. `Document`

| Trường | Kiểu / yêu cầu |
| --- | --- |
| `document_id` | string ổn định từ số ký hiệu + cơ quan + loại; không lấy title làm ID |
| `document_number`, `title`, `document_type` | string; số ký hiệu có thể null cho trang hướng dẫn |
| `publisher`, `issuer`, `scope`, `language` | string; MVP `language=vi`, `scope=national` |
| `source_url`, `content_url` | HTTPS official, canonical URL và file/HTML thực tế |
| `source_type` | `pdf` hoặc `html` |
| `issued_date`, `effective_date`, `downloaded_at`, `verified_at` | ISO date/time; null nếu nguồn không cung cấp, không suy đoán |
| `legal_status` | `active`, `partially_expired`, `expired`, `unknown` |
| `license` | giá trị quan sát được hoặc `publicly_accessible_unknown_license` |
| `sha256` | SHA-256 của bytes nguồn tải, bắt buộc trước index |
| `relations` | danh sách `{type, target_document_id, source_url, verified_at}` |
| `review` | `{decision, reviewer, reviewed_at, reason}` |
| `corpus_snapshot_id` | ID snapshot bất biến |

Không tự suy ra license từ việc URL truy cập công khai. `Document` ghi status của trang nguồn **tại thời điểm kiểm tra**, không chứng minh mọi điều khoản đang có hiệu lực.

### 3.2. `Chunk`

```json
{
  "chunk_id": "uuid-v5-or-stable-hash",
  "corpus_snapshot_id": "2026-09-24-v1",
  "document_id": "45-2019-qh14-quoc-hoi",
  "section_path": ["Chương VII", "Điều 113"],
  "page_start": 57,
  "page_end": 58,
  "raw_text": "...",
  "normalized_text": "...",
  "source_start_char": 10230,
  "source_end_char": 11122,
  "token_count": 412,
  "source_url": "https://...",
  "content_sha256": "...",
  "currency_status": "verified_current",
  "text_quality_status": "verified",
  "source_text_method": "native_pdf",
  "section_kind": "main_text"
}
```

`page_start/page_end` và offset có thể null cho HTML nếu không có pagination/offset đáng tin. Offset tính trên text được trích từ nguồn, không trên bản chuẩn hóa. Với PDF scan, text OCR là **bản đọc máy**, không phải text gốc: giữ PDF/ảnh trang làm source of truth và `source_text_method=ocr_pdf`. `currency_status ∈ {verified_current, historical, unverified}`; `text_quality_status ∈ {verified, unreviewed, rejected}`; chỉ chunk `verified_current` **và** `verified` được dùng cho câu hỏi hiện hành. `section_kind ∈ {main_text, annex, quoted_amendment, unknown}`; không gắn nhãn Điều chính cho biểu mẫu/điều của luật khác được trích dẫn. Chunk ID là hash/UUIDv5 xác định từ `document_id`, source SHA-256, section path, page span, ordinal và hash normalized text; re-ingest cùng snapshot cho cùng ID. Khi nguồn đổi bytes, tạo snapshot mới và ID mới, giữ nguồn cũ để tái lập report.

### 3.3. `Evidence` và `Answer`

`ScoredChunk` lưu `dense_rank`, `bm25_rank`, `rrf_score`, `reranker_score` (có thể null), `chunk_id`, `snapshot_id`. Không gộp các score khác thang đo thành một confidence giả.

`AnswerResult` có `query_id`, `session_id`, `corpus_snapshot_id`, `decision`, `answer`, `claims`, `citations`, `reason`, `metrics`. Mỗi claim có ID, text, citation IDs. `reason` bắt buộc với `REFUSE`/`PARTIAL`; giá trị: `insufficient_evidence`, `out_of_scope`, `conflicting_sources`, `unsupported_prediction`, `source_unavailable`, `currency_unverified`. `answer` không được chứa factual claim thiếu citation; câu nói về giới hạn hệ thống được phép không có citation.

## 4. API contract

Tất cả endpoint JSON UTF-8, lỗi trả `{ "error": "code", "message": "câu tiếng Việt", "query_id": "..." }` khi có query. `query_id` không tiết lộ nội dung câu hỏi. Các schema Pydantic cấm field ngoài dự kiến ở tool input và giới hạn độ dài.

| Endpoint | Request | Response / điều kiện |
| --- | --- | --- |
| `GET /health` | — | 200 nếu process đang chạy |
| `GET /ready` | — | 200 nếu active snapshot, Qdrant, BM25, SQLite sẵn sàng; 503 nếu không |
| `POST /api/chat` | `{message, session_id?}` | `AnswerResult`; 400 invalid, 503 phụ thuộc không sẵn sàng |
| `POST /api/search` | `{query, top_k?, document_ids?}` | danh sách evidence preview; filter current corpus |
| `GET /api/sources/{chunk_id}` | query `snapshot_id?` | source text + metadata; mặc định active snapshot, 404 nếu ID/snapshot không tồn tại |
| `GET /api/documents` | query `q,type,year,publisher,limit,offset` | paginated catalog |
| `GET /api/documents/{document_id}` | — | metadata và indexed chunk count |
| `POST /api/feedback` | `{query_id,rating,reason?}` | 201; không sửa câu trả lời |

`POST /api/chat` ví dụ:

```json
{
  "query_id": "q_...",
  "session_id": "s_...",
  "corpus_snapshot_id": "2026-09-24-v1",
  "decision": "ANSWER",
  "answer": "... [1]",
  "claims": [{"claim_id": "c1", "text": "...", "citation_ids": [1]}],
  "citations": [{
    "citation_id": 1,
    "chunk_id": "...",
    "document_id": "...",
    "title": "...",
    "section": "Điều 113",
    "page_start": 57,
    "page_end": 57,
    "source_url": "https://..."
  }],
  "reason": null,
  "metrics": {"total_ms": 1730, "retrieval_ms": 210, "rerank_ms": 110, "generation_ms": 1300}
}
```

Metrics chi tiết có thể ẩn khỏi giao diện người dùng; log và eval vẫn lưu. Session lưu `question`, `answer`, `decision`, citations, timestamp, snapshot ID. `GET /api/sources/{chunk_id}` nhận ID và optional snapshot ID, không nhận URL; source viewer của chat cũ dùng snapshot ID đã lưu. Giữ artifact của snapshot cũ khi còn session tham chiếu tới nó. Text gốc cần hiển thị an toàn, không render HTML/Markdown từ nguồn như code thực thi.

## 5. Tool contract và agent state

```python
search_evidence(query: str, top_k: int = 5,
                document_ids: list[str] | None = None) -> list[EvidencePreview]
get_source(chunk_id: str) -> SourceEvidence
```

`query`: 1–1000 ký tự sau trim; `top_k`: 1–8; `document_ids`: tối đa 20 ID hợp lệ; `chunk_id` của tool chỉ thuộc snapshot đã ghim và kết quả truy xuất của request. Agent có tối đa 3 lần `search_evidence` và 8 lần `get_source` trong một request, cùng timeout cấu hình. Lỗi tool typed: `VectorStoreUnavailable`, `EmbeddingFailure`, `SourceNotFound`, `SourceUnavailable`.

```python
class AgentState:
    query_id: str
    question: str
    corpus_snapshot_id: str
    searches: list[SearchTrace]
    retrieved_ids: set[str]
    selected_sources: list[SourceEvidence]
    evidence_decision: str | None
    answer_draft: str | None
    final_result: AnswerResult | None
```

Graph: `classify_scope → search → inspect → [search_more | fetch_sources] → assess_evidence → [draft_answer | refuse] → validate → return`. Scope classification chỉ chọn tuyến xử lý, không trả lời factual từ trí nhớ model. LLM chỉ thấy dữ liệu nguồn qua khối riêng có nhãn untrusted.

## 6. Retrieval và grounding

1. Trước query, chọn `active_snapshot_id`, `currency_status=verified_current`, `text_quality_status=verified`, `section_kind` phù hợp và optional `document_ids`. Thực hiện cùng filter ở dense và BM25 để tránh RRF trộn dữ liệu khác phạm vi.
2. Dense `top 20`, BM25 `top 20`. Khử trùng theo `chunk_id`. RRF `score = Σ 1/(60 + rank)` với rank bắt đầu từ 1. Rerank tối đa 20 candidates, trả top 5 theo mặc định.
3. Nếu không có evidence hoặc score/coverage dưới threshold **đã hiệu chỉnh trên validation split**, từ chối sớm. Threshold không phải giá trị tùy ý; report cả false answer và false refusal.
4. LLM phân tách câu hỏi thành các yêu cầu/claims, đánh giá nguồn hỗ trợ và xung đột. Trả lời phần có đủ căn cứ nếu `PARTIAL`; từ chối khi có xung đột chưa giải quyết hoặc thiếu xác minh hiệu lực.
5. Citation ID do code ánh xạ tới `get_source` results. Validator kiểm tra ID, snapshot, `retrieved_ids`, URL, đoạn nguồn, và mỗi factual claim có citation. Kiểm tra semantic support bằng judge có cấu trúc/luật nhẹ; claim không được hỗ trợ bị loại hoặc hạ kết quả. Semantic judge không được coi là bằng chứng duy nhất; eval thủ công kiểm tra mẫu.

Baseline A cố ý không có BM25, reranker, agent và validator nhưng vẫn lưu mapping nguồn để đo citation; không để baseline truy cập nguồn ngoài corpus. Thay đổi tokenizer, threshold hoặc prompt đều được version trong benchmark.

## 7. Ingestion và index contract

- **PDF:** lưu file gốc và SHA-256; trích theo trang; phát hiện scan theo tỷ lệ trang có text và ảnh toàn trang (ngưỡng pilot phải được validation). Với scan, ghi `needs_ocr`, tìm HTML toàn văn chính thức, hoặc OCR offline. OCR giữ text/ảnh theo trang, model hash, ngôn ngữ, DPI và lỗi; đánh dấu `unreviewed` cho đến khi soát với ảnh nguồn. Nếu OCR thất bại, ghi `unsupported_scan`; không âm thầm index text rỗng hay text OCR chưa review.
- **HTML:** lưu HTML gốc và SHA-256; chỉ lấy nội dung chính, giữ heading/paragraph/list/table text; lưu URL và vị trí DOM/offset khi đáng tin.
- **Normalize:** Unicode và whitespace bảo thủ; lưu bản gốc cạnh bản chuẩn hóa; không tự sửa từ pháp lý.
- **Chunk:** ưu tiên một Điều thành một chunk nếu vừa ngưỡng; Điều dài chia theo khoản/đoạn ở mức 500–800 **model tokens**, overlap 80–120 khi cần; không ghép hai Điều khác nhau chỉ để đủ độ dài. Ghi page span từ vị trí từng dòng/từ thay vì lấy toàn bộ span của Điều. Nhận diện phụ lục/biểu mẫu và nội dung sửa luật được trích dẫn trước khi gán `section_path`; cảnh báo khi số Điều lùi hoặc trùng.
- **Cache:** key = source SHA-256 + chunker version + normalized text hash + embedding model revision. Cache invalidation phải xác định.
- **Index release:** kiểm tra `manifest.snapshot_id == bm25.snapshot_id == qdrant.collection_snapshot_id`; idempotent upsert; chỉ chuyển active sau integrity checks.

## 8. Cấu hình, vận hành và lỗi

`.env.example` chứa `LLM_PROVIDER`, `LLM_MODEL`, `QDRANT_URL`, `ACTIVE_CORPUS_SNAPSHOT`, `EMBEDDING_MODEL`, `RERANKER_MODEL`, `RETRIEVAL_TOP_K`, `RERANK_TOP_K`, `REFUSAL_THRESHOLD`, `SQLITE_PATH`, timeouts và log level. Dùng pinned dependency versions và lưu model revisions trong manifest. Secret chỉ qua môi trường.

Docker Compose có `qdrant` với volume, `api` với volume cho snapshot/cache/SQLite, `ui` gọi API qua network nội bộ. Healthcheck của API chỉ xem process; readiness xác thực phụ thuộc. UI có thông báo lỗi phụ thuộc và loading states, không hiện traceback.

Lỗi có thể phục hồi được log cùng `query_id`; `SourceNotFound` không được đổi thành câu trả lời không nguồn. Các log của câu hỏi người dùng mặc định lưu hash hoặc redacted text cho demo; eval có thể lưu câu hỏi test trong artifact riêng.

## 9. Điều kiện kỹ thuật trước khi chốt implementation

1. Kiểm tra license của PyMuPDF và model weights theo cách phát hành dự kiến; tài liệu PyMuPDF nêu lựa chọn AGPL hoặc commercial license, nên cần quyết định rõ khi công bố dự án.
2. Đo embedding/reranker trên máy mục tiêu để chốt phiên bản, batch size và khả năng đáp ứng p95.
3. Kiểm tra adapter VBPL bằng fixture thật, URL canonical, redirect, HTML structure và điều kiện truy cập của nguồn tại ngày thu thập.
4. Xây ít nhất một fixture văn bản bị sửa đổi một phần để kiểm thử `currency_unverified` và refusal.

Tham khảo chính thức: [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/), [FastAPI Docker](https://fastapi.tiangolo.com/deployment/docker/), [Qdrant payload](https://qdrant.tech/documentation/concepts/payload/), [Streamlit chat](https://docs.streamlit.io/develop/api-reference/chat), [PyMuPDF FAQ về giấy phép](https://pymupdf.readthedocs.io/en/latest/faq/index.html).
