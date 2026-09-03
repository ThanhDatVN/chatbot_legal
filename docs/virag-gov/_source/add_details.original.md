Nếu mục tiêu của bạn là làm một sản phẩm **thực sự gây ấn tượng trong CV/portfolio và với doanh nghiệp**, tôi nghĩ không nên xây dựng nó như một dự án:

> ❌ “Chatbot hỏi đáp luật thuế sử dụng RAG”

Mà nên định vị nó thành một **Tax Legal Intelligence Platform** có kiến trúc dữ liệu, AI và khả năng vận hành giống một sản phẩm thật.

Một người xem CV hoặc GitHub của bạn nên cảm nhận được rằng:

> **Bạn không chỉ biết gọi API LLM và làm chatbot. Bạn có khả năng thiết kế một hệ thống AI có dữ liệu sống, xử lý xung đột, versioning, temporal reasoning và triển khai production.**

---

# I. Định vị sản phẩm

Tôi đề xuất tên concept:

# **TaxLens AI**

### Vietnam Tax Intelligence Platform

Hoặc:

* **VietTax Intelligence**
* **TaxMind**
* **TaxGraph AI**
* **TaxScope**
* **VTax AI**

Sản phẩm không chỉ có một chatbot mà gồm **3 lớp giá trị**:

```text
┌──────────────────────────────────────────────┐
│                 USER LAYER                   │
│                                              │
│  💬 Ask AI                                   │
│  📅 Legal Time Machine                       │
│  🔄 Regulation Change Monitor                │
│  ⚖️ Conflict Explorer                        │
│  🔔 Personalized Tax Updates                 │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│                 AI LAYER                     │
│                                              │
│  Intent Detection                            │
│  Temporal Reasoning                          │
│  Hybrid Retrieval                            │
│  Legal Knowledge Graph                       │
│  Conflict Detection                          │
│  Citation Validation                         │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│                 DATA LAYER                   │
│                                              │
│  Official Sources                            │
│  Crawling Pipeline                           │
│  Document Processing                         │
│  Version Control                             │
│  PostgreSQL                                  │
│  Vector Database                             │
│  Graph Database                              │
│  Object Storage                              │
└──────────────────────────────────────────────┘
```

---

# II. Những tính năng thực sự tạo ấn tượng

## 1. AI Tax Assistant

Đây vẫn là tính năng trung tâm:

> “Doanh nghiệp mới thành lập cần thực hiện những nghĩa vụ thuế nào?”

Nhưng chatbot không trả lời ngay.

Nó thực hiện một pipeline:

```text
User Question
      ↓
Intent Classification
      ↓
Extract Tax Type
      ↓
Extract Entity Type
      ↓
Extract Time
      ↓
Check Missing Information
      ↓
Clarification Question
      ↓
Hybrid Retrieval
      ↓
Version Filtering
      ↓
Conflict Checking
      ↓
Answer Generation
      ↓
Citation Validation
```

Ví dụ:

> “Công ty tôi có phải nộp VAT không?”

Hệ thống nhận ra thiếu thông tin:

```text
Entity type: Unknown
Business sector: Unknown
Time: Unknown
Revenue: Unknown
```

Thay vì hallucinate:

> “Bạn cần cung cấp thêm một số thông tin…”

Sau đó chatbot hỏi theo dạng UI:

```text
🏢 Loại hình kinh doanh?
○ Công ty
○ Hộ kinh doanh
○ Cá nhân

📅 Thời điểm phát sinh?
○ Hiện tại
○ Quá khứ
○ Chưa xác định
```

### Đây là điểm UX rất tốt

Người dùng không cần biết cách đặt câu hỏi pháp luật chính xác.

---

# III. Legal Time Machine

Đây là một trong những tính năng tôi nghĩ có thể làm nổi bật sản phẩm.

Người dùng hỏi:

> “Năm 2021, doanh nghiệp của tôi áp dụng quy định VAT nào?”

UI:

```text
┌─────────────────────────────────────┐
│ Quy định pháp luật áp dụng          │
│                                     │
│ ◄──────●──────────────►             │
│ 2020   2021   2022   2023   2024    │
│                                     │
│ Selected: 15/06/2021                │
└─────────────────────────────────────┘
```

Hệ thống:

```text
Question
   +
Event Date
   ↓
Legal Version Resolver
   ↓
Find all applicable documents
   ↓
Filter by effective date
   ↓
Check amendments
   ↓
Retrieve applicable version
```

Người dùng có thể xem:

```text
📜 Điều luật hiện tại

🔄 Phiên bản năm 2021

🆚 So sánh thay đổi
```

---

# IV. Regulation Change Monitor

Đây là tính năng rất có giá trị với doanh nghiệp.

Ví dụ:

```text
New Circular Detected
        ↓
Document Processing
        ↓
Compare With Previous Documents
        ↓
Change Extraction
        ↓
Impact Analysis
```

Sau đó dashboard:

```text
🔴 3 thay đổi quan trọng

1. Thuế VAT
   ├── Điều chỉnh thuế suất
   └── Hiệu lực: 01/01/2027

2. Thuế TNDN
   ├── Bổ sung đối tượng áp dụng
   └── 12 doanh nghiệp profile có thể bị ảnh hưởng

3. Hóa đơn điện tử
   └── Thay đổi thủ tục
```

Đây chính là:

# **Legal Change Intelligence**

Khác rất nhiều so với chatbot thông thường.

---

# V. "What changed?" – Legal Diff

Một UX cực tốt:

```text
┌────────────────┬────────────────┐
│ OLD VERSION    │ NEW VERSION    │
├────────────────┼────────────────┤
│ Thuế suất 10%  │ Thuế suất 8%   │
│                │                │
│ Điều kiện A    │ Điều kiện B    │
│                │                │
│ Không có C     │ + Bổ sung C    │
└────────────────┴────────────────┘
```

AI highlight:

```text
🟢 Added
🟡 Modified
🔴 Removed
```

Ở backend:

```text
Document A
    ↓
Structure Parsing
    ↓
Article Alignment
    ↓
Semantic Diff
    ↓
LLM Classification
    ↓
Human-readable Change Summary
```

Điểm quan trọng:

> Không chỉ dùng LLM diff toàn bộ document.

Bạn nên thực hiện:

### Layer 1 – Exact Matching

```text
Hash comparison
```

### Layer 2 – Text Diff

```text
SequenceMatcher
Myers Diff
```

### Layer 3 – Semantic Matching

```text
Embedding Similarity
```

### Layer 4 – Legal Change Classification

```text
LLM
```

Kết quả:

```text
UNCHANGED
MODIFIED
ADDED
REMOVED
MOVED
REPEALED
```

---

# VI. Conflict Explorer

Người dùng có thể thấy:

```text
Question
   ↓
Relevant Legal Sources
   ↓
┌──────────────────────────┐
│ Law                      │
│ Decree                   │
│ Circular                 │
│ Administrative Guidance  │
└──────────────────────────┘
   ↓
Conflict Analysis
```

Ví dụ UI:

```text
⚖️ Possible Regulatory Conflict

Document A
↓
Document B

Reason:
Document B modifies Article 5 of Document A.

Resolution:
Document B applies from 01/01/2025.
```

Điều quan trọng là hệ thống **không được giả vờ rằng nó chắc chắn 100%**.

Có thể có:

```text
🟢 High Confidence

🟡 Requires Review

🔴 Potential Conflict
```

Đây là UX rất chuyên nghiệp.

---

# VII. Personalized Tax Profile

Người dùng có thể tạo:

```text
Business Profile
```

Ví dụ:

```text
Business Type:
☑ SME

Industry:
☑ Technology

Revenue Range:
☑ 10–50 billion VND

Location:
☑ Vietnam
```

Sau đó hệ thống:

```text
New Regulation
       ↓
Legal Impact Engine
       ↓
User Profiles
       ↓
Affected Users
       ↓
Notification
```

Ví dụ:

> 🔔 Một quy định mới có thể ảnh hưởng đến doanh nghiệp của bạn.

Điều này biến sản phẩm từ:

```text
Passive Search
```

thành:

```text
Proactive Legal Intelligence
```

---

# VIII. Kiến trúc Backend

Tôi khuyên không nên xây ngay microservices phức tạp.

Giai đoạn đầu:

# Modular Monolith

```text
Backend
│
├── API Layer
│
├── Auth Module
│
├── Chat Module
│
├── Retrieval Module
│
├── Document Module
│
├── Crawling Module
│
├── Legal Version Module
│
├── Conflict Module
│
└── Notification Module
```

Sau khi scale:

```text
                    API Gateway
                         │
       ┌─────────────────┼─────────────────┐
       ↓                 ↓                 ↓
    Chat API         Document API      User API
       │                 │
       ↓                 ↓
   AI Service       Processing Queue
       │                 │
       ↓                 ↓
 Retrieval         Document Workers
```

### Tech stack đề xuất

```text
Backend:
FastAPI

AI:
Python
LangGraph / custom orchestration

Database:
PostgreSQL

Vector:
pgvector ban đầu

Graph:
Neo4j

Cache:
Redis

Queue:
Celery / RabbitMQ

Object Storage:
MinIO / S3

Frontend:
Next.js

Deployment:
Docker
```

---

# IX. Database Architecture

Đây là phần có thể làm dự án của bạn rất khác biệt.

Không nên chỉ có:

```text
documents
chunks
embeddings
```

Nên thiết kế:

```text
Legal Document
       │
       ├── Document Version
       │
       ├── Article
       │
       │     └── Clause
       │           └── Point
       │
       ├── Legal Relations
       │
       └── Change Events
```

---

## PostgreSQL

### documents

```sql
documents
---------
id
document_number
document_type
issuer
title
issue_date
```

### document_versions

```sql
document_versions
-----------------
id
document_id
version_number

effective_from
effective_to

status

source_url
content_hash
```

### legal_articles

```sql
legal_articles
--------------
id
version_id
article_number
title
content
```

### legal_relations

```sql
legal_relations
---------------
source_id
target_id

relation_type

confidence
```

Các relation:

```text
AMENDS
REPEALS
REPLACES
REFERENCES
GUIDES
CONFLICTS
```

---

# X. Cách xử lý xung đột database

Đây là phần cực kỳ quan trọng.

Ví dụ crawler tải lại một văn bản.

Bạn không nên:

```text
DELETE old document
INSERT new document
```

Vì sẽ phá:

* citation cũ;
* lịch sử câu trả lời;
* legal version;
* embeddings.

Thay vào đó:

# Immutable Versioning

```text
Document
   │
   ├── Version 1
   │
   ├── Version 2
   │
   └── Version 3
```

Không sửa:

```text
Version 1
```

Chỉ:

```text
Create Version 2
```

---

## Hash-based Duplicate Detection

Khi crawl:

```text
Downloaded Document
        ↓
Normalize Text
        ↓
SHA256
        ↓
Compare Hash
```

```text
Same Hash
   ↓
Skip
```

```text
Different Hash
   ↓
Create New Version
```

---

# XI. Idempotent Crawling

Crawler có thể chạy:

```text
Today
Tomorrow
Next week
```

Nhưng chạy lại nhiều lần không được tạo duplicate.

```text
crawl_job_id
source_id
document_id
content_hash
```

Nguyên tắc:

```text
Same input
+
Same processing
=
Same result
```

Đây gọi là:

# Idempotency

---

# XII. Crawl định kỳ

Pipeline:

```text
Scheduler
    ↓
Source Monitor
    ↓
Detect Changes
    ↓
Download
    ↓
Validate
    ↓
Queue
    ↓
Parse
    ↓
Version
    ↓
Diff
    ↓
Index
    ↓
Notify
```

Có thể dùng:

```text
APScheduler
↓
MVP

Celery Beat
↓
Production
```

---

# XIII. Nguồn dữ liệu không nên crawl một cách "mù"

Bạn cần:

```text
Source Registry
```

```text
Source
├── Official
├── Semi-official
├── Reference
└── Community
```

Mỗi nguồn có:

```text
Authority Score
Update Frequency
Parsing Method
Trust Level
```

Ví dụ:

```text
OFFICIAL = 1.0

GOVERNMENT = 0.95

LEGAL DATABASE = 0.8

NEWS = 0.5

USER CONTENT = 0.2
```

Điểm này có thể đi vào ranking.

---

# XIV. Data Pipeline

Một kiến trúc khá đẹp:

```text
                  ┌──────────────┐
                  │ RAW DATA     │
                  │ PDFs / HTML  │
                  └──────┬───────┘
                         ↓
                  ┌──────────────┐
                  │ BRONZE LAYER │
                  │ Raw Storage  │
                  └──────┬───────┘
                         ↓
                  ┌──────────────┐
                  │ SILVER LAYER │
                  │ Parsed Docs  │
                  └──────┬───────┘
                         ↓
                  ┌──────────────┐
                  │ GOLD LAYER   │
                  │ Legal Data   │
                  └──────┬───────┘
                         ↓
              ┌──────────┼──────────┐
              ↓          ↓          ↓
         PostgreSQL   Vector DB   Graph DB
```

Đây chính là tư duy:

# Data Lakehouse / Medallion Architecture

Rất đẹp khi đưa vào portfolio.

---

# XV. Data Quality

Bạn cần một module:

# Data Quality Engine

Kiểm tra:

```text
1. Missing effective date
2. Invalid document number
3. Duplicate document
4. Broken legal references
5. Overlapping validity periods
6. Invalid hierarchy
```

Ví dụ:

```text
Version A
effective_from: 2024

Version B
effective_from: 2023
```

Nếu database tạo:

```text
Version A active: 2024 → NULL
Version B active: 2023 → NULL
```

→ conflict.

Database phải có constraint hoặc validation layer.

---

# XVI. Temporal Database

Đây là điểm bạn có thể nghiên cứu sâu.

Mỗi quy định có hai loại thời gian:

```text
VALID TIME
```

Quy định có hiệu lực trong thế giới thực khi nào?

```text
TRANSACTION TIME
```

Hệ thống biết về quy định đó khi nào?

Ví dụ:

```text
Law effective:
01/01/2025

System crawled:
05/01/2025
```

Điều này giúp bạn xây dựng:

# Bitemporal Database

```text
                 ┌──────────────┐
                 │ Legal Rule   │
                 └──────┬───────┘
                        │
        ┌───────────────┴───────────────┐
        ↓                               ↓
    Valid Time                    System Time
```

Đây là một điểm cực kỳ mạnh nếu muốn gây ấn tượng với kỹ sư data/backend.

---

# XVII. Vector Database Scaling

Ban đầu:

```text
PostgreSQL
+
pgvector
```

Là đủ.

Không nên nhảy ngay sang một hệ thống quá phức tạp.

Khi dữ liệu lớn:

```text
PostgreSQL
       ↓
Metadata

Qdrant / Milvus
       ↓
Embeddings
```

Bạn nên tách:

```text
Structured Search
      +
Semantic Search
      +
Keyword Search
```

Thành:

# Hybrid Retrieval

```text
Question
    ↓
├── BM25
├── Vector Search
└── Metadata Filtering
    ↓
Candidate Documents
    ↓
Reranker
```

---

# XVIII. Knowledge Graph

Neo4j có thể lưu:

```text
(Document)-[:AMENDS]->(Document)

(Document)-[:REPEALS]->(Document)

(Article)-[:REFERENCES]->(Article)

(Regulation)-[:AFFECTS]->(Taxpayer)
```

Điều này cho phép:

```text
New Law
    ↓
Graph Traversal
    ↓
Find affected documents
```

Ví dụ query:

```text
"Văn bản nào bị tác động bởi Thông tư X?"
```

Đây là thứ RAG thuần túy làm không tốt.

---

# XIX. Frontend nên có gì?

Đừng làm một màn hình:

```text
┌──────────────────────────┐
│      CHAT WINDOW         │
│                          │
│ User:                    │
│ AI:                      │
└──────────────────────────┘
```

Nên làm:

# 1. AI Chat

# 2. Explore Law

# 3. Change Monitor

# 4. Tax Timeline

# 5. Admin Data Dashboard

---

## AI Chat Experience

Khi AI trả lời:

```text
┌──────────────────────────────────┐
│ AI Answer                        │
│                                  │
│ Theo quy định hiện hành...       │
│                                  │
│ [Độ tin cậy: High]               │
│                                  │
│ 📜 3 căn cứ pháp lý              │
│                                  │
│ 🕒 Áp dụng từ: 01/01/2026        │
└──────────────────────────────────┘
```

Có thể click vào citation:

```text
Điều 5 Khoản 2
```

Mở:

```text
┌───────────────────────────┐
│ Document                  │
│                           │
│ Chapter                   │
│  └── Article              │
│       └── Clause          │
│            ↑              │
│          Highlight        │
└───────────────────────────┘
```

---

# XX. Citation Experience

Đây là điểm UX rất mạnh.

Mỗi câu AI trả lời có:

```text
Claim
  ↓
Citation
```

Người dùng click:

```text
AI:
"Thuế suất là X [1]"
```

Mở:

```text
[1] Document X

Điều 5
Khoản 2

"....."
```

Có thêm:

```text
📅 Effective: 2026
🔄 Updated: Yes
⚖️ Authority: Circular
```

---

# XXI. Legal Confidence UX

Không nên hiển thị:

```text
Confidence = 87.5%
```

vì có thể gây hiểu nhầm.

Nên:

```text
🟢 Có căn cứ rõ ràng

🟡 Có thể cần thêm thông tin

🔴 Có nhiều cách hiểu / cần chuyên gia kiểm tra
```

Kèm lý do:

> “Kết quả phụ thuộc vào thời điểm phát sinh giao dịch.”

Đây là **uncertainty explanation**.

---

# XXII. Admin Dashboard

Một dự án production phải có.

Dashboard:

```text
Total Documents

Active Documents

New Documents Today

Processing Queue

Embedding Queue

Failed Crawls

Potential Conflicts

Unresolved Legal Relations
```

Ví dụ:

```text
┌──────────────────┐
│ Documents: 8,241 │
├──────────────────┤
│ Active: 6,120    │
├──────────────────┤
│ Updated: 24      │
└──────────────────┘
```

---

# XXIII. Observability

Đây là thứ rất nhiều dự án AI bỏ qua.

Bạn nên theo dõi:

```text
API Latency

LLM Latency

Retrieval Latency

Reranker Latency

Crawler Failures

Queue Size

Database Errors
```

Architecture:

```text
Application
     ↓
Logs
     ↓
Metrics
     ↓
Tracing
```

Ví dụ:

```text
Prometheus
Grafana
OpenTelemetry
```

Một dashboard đẹp về hệ thống có thể tăng giá trị portfolio đáng kể.

---

# XXIV. AI Evaluation Dashboard

Đây là phần tôi rất khuyến nghị.

Không chỉ deploy chatbot mà phải chứng minh:

```text
Which model is better?
Which retriever works best?
Does new data improve performance?
```

Dashboard:

| Experiment | Retrieval | Citation | Temporal | Answer |
| ---------- | --------: | -------: | -------: | -----: |
| BM25       |       71% |      65% |      60% |    72% |
| Vector     |       75% |      68% |      58% |    76% |
| Hybrid     |       84% |      79% |      82% |    86% |

Tất nhiên đây là dữ liệu minh họa.

Có thể dùng:

```text
MLflow
Weights & Biases
hoặc custom dashboard
```

---

# XXV. API Design

Ví dụ:

```text
POST /chat

POST /documents

GET /documents/{id}

GET /documents/{id}/versions

GET /changes

GET /conflicts

POST /impact-analysis

POST /feedback
```

Điểm rất quan trọng:

```text
GET /legal-rules?date=2022-01-01
```

Cho phép hệ thống trở thành API service chứ không chỉ chatbot.

---

# XXVI. Authentication và User System

Nếu public deployment:

```text
Guest User
Registered User
Enterprise User
Admin
```

### Guest

* giới hạn câu hỏi;
* không lưu dài hạn.

### User

* lưu lịch sử;
* bookmark;
* theo dõi văn bản.

### Enterprise

* Business Profile;
* alerts;
* impact monitoring.

---

# XXVII. User Feedback Loop

Sau mỗi câu trả lời:

```text
👍 Hữu ích

👎 Không chính xác

⚠️ Không đúng thời điểm

⚠️ Sai căn cứ pháp luật
```

Feedback đi vào:

```text
Feedback Queue
       ↓
Human Review
       ↓
Dataset
       ↓
Evaluation Set
```

Điều này rất quan trọng.

# Production Data Flywheel

```text
User
 ↓
Feedback
 ↓
Error Dataset
 ↓
Evaluation
 ↓
Improve System
 ↓
Better User Experience
```

---

# XXVIII. Deployment thực tế

Tôi khuyên kiến trúc:

```text
                    Internet
                        ↓
                  Cloudflare
                        ↓
                    Nginx
                        ↓
                  Next.js Frontend
                        ↓
                    FastAPI
                        ↓
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
   PostgreSQL         Redis           Worker
        ↓                               ↓
    pgvector                      Crawler
                                        ↓
                                   Processing
```

---

## Giai đoạn đầu

Có thể dùng một server:

```text
Docker Compose
```

```text
services:

frontend

backend

postgres

redis

worker
```

Sau đó:

```text
Production
    ↓
Docker
    ↓
CI/CD
    ↓
Cloud
```

---

# XXIX. CI/CD

GitHub Actions:

```text
Push
 ↓
Test
 ↓
Lint
 ↓
Build Docker
 ↓
Deploy Staging
 ↓
Integration Test
 ↓
Production
```

Điều này rất đẹp trong CV.

---

# XXX. Testing

Một hệ thống như thế này cần nhiều loại test.

## Unit Test

```text
Date parsing
Version resolver
Conflict resolver
```

## Integration Test

```text
Crawler
↓
Parser
↓
Database
```

## RAG Evaluation

```text
Question
↓
Expected Evidence
↓
Retrieved Evidence
```

## Regression Test

Khi cập nhật hệ thống:

```text
Old Benchmark
↓
Run Again
↓
Performance Drop?
```

Đây rất quan trọng với AI.

---

# XXXI. Roadmap 4 tháng

## Month 1 — Foundation

```text
Week 1–2
```

* nghiên cứu domain;
* xác định nguồn dữ liệu;
* database schema;
* crawler đầu tiên.

```text
Week 3–4
```

* document parser;
* PostgreSQL;
* versioning;
* basic RAG.

---

## Month 2 — Intelligence

* Hybrid Retrieval;
* reranking;
* citation;
* temporal filtering;
* benchmark đầu tiên.

---

## Month 3 — Differentiation

* Legal Knowledge Graph;
* Change Detection;
* Conflict Detection;
* Impact Analysis.

---

## Month 4 — Production

* Next.js UI;
* authentication;
* feedback;
* monitoring;
* Docker;
* CI/CD;
* public deployment.

---

# XXXII. GitHub structure nên như thế nào?

```text
taxlens-ai/
│
├── apps/
│   ├── frontend/
│   └── backend/
│
├── services/
│   ├── crawler/
│   ├── document_processor/
│   ├── retrieval/
│   └── ai_engine/
│
├── packages/
│   ├── database/
│   └── shared/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── evaluation/
│
├── infrastructure/
│   ├── docker/
│   └── nginx/
│
├── experiments/
│
├── docs/
│
└── README.md
```

README nên có:

```text
1. Problem
2. Architecture
3. Features
4. Data Pipeline
5. Benchmark
6. Evaluation
7. Demo
8. Deployment
```

---

# XXXIII. Điều làm dự án này thực sự mạnh trên CV

Nếu CV chỉ ghi:

> Built an AI chatbot for Vietnamese tax law using RAG.

→ khá bình thường.

Nhưng nếu ghi:

> **Designed and deployed a production-oriented Vietnamese Tax Legal Intelligence Platform featuring temporal-aware retrieval, legal document versioning, hybrid search, automated regulation monitoring, change detection, conflict analysis, and citation-grounded LLM responses.**

Thì khác biệt rất lớn.

Đặc biệt bạn có thể chia thành các technical highlights:

### Data Engineering

* Automated crawling pipeline
* Document versioning
* Bitemporal data modeling
* Data quality validation
* Incremental indexing

### AI Engineering

* Hybrid RAG
* Temporal-aware retrieval
* Reranking
* Citation validation
* Hallucination detection

### Backend Engineering

* FastAPI
* PostgreSQL
* Redis
* Async workers
* REST APIs

### Data Systems

* pgvector
* Knowledge Graph
* Legal dependency graph
* Incremental embedding

### DevOps

* Docker
* CI/CD
* Monitoring
* Logging
* Production deployment

---

# XXXIV. Tôi nghĩ USP mạnh nhất của dự án nên là gì?

Nếu phải chọn **một câu duy nhất**:

> **“AI không chỉ tìm luật mới nhất, mà xác định chính xác quy định nào áp dụng cho một tình huống cụ thể tại một thời điểm cụ thể.”**

Sau đó mở rộng:

```text
Vietnam Tax Intelligence
          │
          ├── Ask
          ├── Search
          ├── Time Travel
          ├── Compare Versions
          ├── Detect Changes
          ├── Resolve Conflicts
          └── Monitor Updates
```

---

## Hướng tôi khuyến nghị mạnh nhất

Để dự án vừa **có giá trị nghiên cứu**, vừa **đẹp trong CV**, vừa **có khả năng trở thành sản phẩm**, tôi sẽ xây theo thứ tự:

### Phase 1 — Legal Data Infrastructure

**Crawler → Parser → Versioning → Database → Index**

### Phase 2 — Reliable Tax RAG

**Hybrid Retrieval → Temporal Filtering → Citation Validation**

### Phase 3 — Legal Intelligence

**Change Detection → Dependency Graph → Conflict Analysis**

### Phase 4 — Product Experience

**Chat → Timeline → Diff Viewer → Monitoring → Feedback**

### Phase 5 — Production Engineering

**Docker → CI/CD → Monitoring → Public Deployment**

Nếu làm đầy đủ đến mức này, sản phẩm của bạn sẽ không còn giống một **“chatbot demo”**, mà giống một **AI/data platform thu nhỏ**. Đó là điều tạo khác biệt lớn nhất khi đưa vào CV, portfolio hoặc phỏng vấn với doanh nghiệp.
