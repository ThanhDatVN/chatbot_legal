ếu làm nghiêm túc thì khâu tạo corpus phải trở thành một module riêng của project, chứ không phải “tải vài PDF luật về rồi RAG”. Và để nhanh hoàn thành, mình khuyên không crawl toàn bộ Internet mà dùng chiến lược seed → expand → filter → review → snapshot.

1. Nguồn chính nên lấy ở đâu?

Nguồn số 1 mình chọn là Cơ sở dữ liệu quốc gia về văn bản pháp luật — vbpl.vn. Đây là CSDL quốc gia, có văn bản trung ương và địa phương; một trang văn bản có thể cung cấp toàn văn, thuộc tính, lịch sử hiệu lực, văn bản liên quan, lược đồ và file PDF.

Điều này rất hợp CiteAgent vì bạn cần metadata kiểu:

{
  "document_number": "145/2020/NĐ-CP",
  "title": "...",
  "document_type": "Nghị định",
  "issued_date": "...",
  "effective_date": "...",
  "status": "Hết hiệu lực một phần",
  "issuer": "Chính phủ",
  "scope": "Toàn quốc",
  "field": "Lao động - Thương binh và Xã hội"
}

Ví dụ trang Nghị định 145/2020/NĐ-CP trên CSDL này đã có cả Ngành: Lao động - Thương binh và Xã hội, trạng thái hiệu lực và thông tin các văn bản làm nó hết hiệu lực một phần.

Nguồn thứ hai dùng để cross-check, không nhất thiết crawl toàn bộ, là Cổng văn bản Chính phủ vanban.chinhphu.vn. Ví dụ Bộ luật Lao động 45/2019/QH14 có số hiệu, ngày ban hành, ngày hiệu lực và PDF chính thức ở đây.

Đáng chú ý, đến năm 2026 còn có Văn bản hợp nhất 18/VBHN-VPQH ngày 12/02/2026 về Bộ luật Lao động. Đây là nguồn rất hữu ích để xây corpus hiện hành, nhưng nên lưu nó là consolidated_document, không coi nó là một “luật mới”.

2. Không nên crawl theo keyword "lao động"

Nếu bạn search:

lao động

thì sẽ dính đủ thứ:

lao động
bảo hiểm
công chức
tổ chức Chính phủ
quốc phòng
đầu tư
doanh nghiệp
an toàn lao động
người lao động nước ngoài
thủ tục hành chính
...

Thậm chí ngay CSDL của khối lao động có thể chứa các văn bản về cơ cấu tổ chức hoặc lĩnh vực lân cận. Ví dụ danh sách của CSDL ngành lao động có cả nghị định về BHXH, an toàn vệ sinh lao động và các nhóm khác.

Vì vậy hãy coi bài toán này là:

Legal corpus construction

chứ không phải:

Web crawling.

3. Cách mình sẽ làm: Seed-and-expand

Bắt đầu bằng vài văn bản mà ta biết chắc chắn thuộc phạm vi.

Ví dụ:

SEED
│
├── 18/VBHN-VPQH
│   Bộ luật Lao động hợp nhất
│
├── 45/2019/QH14
│   Bộ luật Lao động gốc
│
├── 145/2020/NĐ-CP
│   điều kiện lao động + quan hệ lao động
│
└── 135/2020/NĐ-CP
    tuổi nghỉ hưu

Nghị định 145/2020/NĐ-CP có trích yếu rất rõ là quy định chi tiết một số điều của Bộ luật Lao động về điều kiện lao động và quan hệ lao động.

Sau đó không search web tự do nữa.

Ta đi theo graph:

seed document
     │
     ├── văn bản sửa đổi
     ├── văn bản bổ sung
     ├── văn bản thay thế
     ├── văn bản quy định chi tiết
     ├── văn bản hướng dẫn
     └── văn bản được dẫn chiếu

VBPL đã có các tab:

Lịch sử
VB liên quan
Lược đồ

để khai thác các quan hệ này.

Tức là crawler của bạn giống:

                  ┌──────────────┐
                  │ Bộ luật LĐ   │
                  └──────┬───────┘
                         │
                  discover relations
                         │
            ┌────────────┼─────────────┐
            ▼            ▼             ▼
        Nghị định     Thông tư      VB sửa đổi
            │            │             │
            └────────────┼─────────────┘
                         ▼
                    candidates
                         │
                         ▼
                      filter

Đây cũng là một phần rất đẹp để trình bày trong CV.

4. Crawler không tải PDF ngay

Một trick quan trọng.

Pass 1 chỉ crawl metadata.

Ví dụ:

{
  "item_id": 152668,
  "number": "145/2020/NĐ-CP",
  "title": "Quy định chi tiết ... Bộ luật Lao động ...",
  "document_type": "Nghị định",

  "field": "Lao động - Thương binh và Xã hội",

  "issued_date": "2020-12-14",
  "effective_date": "2021-02-01",

  "status": "partially_expired",

  "issuer": "Chính phủ",

  "source_url": "...",

  "relations": [
    {
      "type": "basis",
      "document": "45/2019/QH14"
    }
  ]
}

Sau khi lọc xong mới download:

HTML
PDF
DOC

Như vậy 1.000 candidate cũng không thành vấn đề.

Có thể cuối cùng chỉ giữ 40 văn bản.

5. Filter tầng 1: nguồn

Hard filter đầu tiên:

ALLOWED_DOMAINS = {
    "vbpl.vn",
    "vanban.chinhphu.vn",
}

Có thể thêm các nguồn chính thức chuyên ngành sau.

Nhưng MVP:

vbpl.vn
+
vanban.chinhphu.vn

là đủ.

Không đưa vào corpus chính:

thuvienphapluat
luatvietnam
blog luật
bài báo
forum
Facebook
SEO sites

Không phải vì các nguồn đó vô dụng, mà vì mục tiêu project của bạn là:

evidence-grounded QA từ nguồn chính thức.

6. Filter tầng 2: loại văn bản

MVP của mình chỉ giữ:

ALLOWED_TYPES = {
    "Bộ luật",
    "Luật",
    "Nghị định",
    "Thông tư",
    "Thông tư liên tịch",
    "Văn bản hợp nhất",
}

Có thể thêm:

Nghị quyết
Quyết định

sau nếu evaluation chỉ ra cần.

Loại mặc định loại:

Tin tức
Công văn trao đổi
Dự thảo
Bài phổ biến pháp luật
Thông báo
Kế hoạch
Tờ trình
Quyết định nhân sự
Quyết định cơ cấu tổ chức

Như vậy corpus không bị phình vô ích.

7. Filter tầng 3: tình trạng hiệu lực

Đây là điểm rất quan trọng.

CSDL chính thức ghi rõ trường hợp:

Còn hiệu lực

Hết hiệu lực một phần

Hết hiệu lực toàn bộ

Ví dụ Bộ luật Lao động 45/2019/QH14 hiện được CSDL VBPL ghi nhận là hết hiệu lực một phần.

Nghị định 145/2020 cũng được ghi là hết hiệu lực một phần, kèm lý do và những văn bản sửa đổi/bãi bỏ một phần.

Do đó không được làm:

if status != "valid":
    discard()

Vì như vậy bạn sẽ vứt luôn các văn bản cực kỳ quan trọng.

Nên normalize thành:

class LegalStatus(Enum):
    ACTIVE = "active"
    PARTIALLY_EXPIRED = "partially_expired"
    EXPIRED = "expired"
    UNKNOWN = "unknown"

Sau đó:

if status == EXPIRED:
    exclude_from_current_corpus()

elif status == PARTIALLY_EXPIRED:
    include_but_require_version_tracking()
8. Nên có hai corpus logic khác nhau

Không nhất thiết hai vector database, nhưng metadata phải phân biệt.

Current corpus

Dùng trả lời:

Quy định hiện nay là gì?

Bao gồm:

active
partially_expired + amendment information
consolidated versions
Historical corpus

Dùng trả lời:

Năm 2020 quy định như thế nào?

Bao gồm cả:

expired documents
previous versions

MVP có thể chỉ support current law.

Khi user hỏi lịch sử:

Quy định năm 2018 thế nào?

agent trả:

Phiên bản hiện tại của CiteAgent VN chỉ hỗ trợ quy định hiện hành.

Scope giảm rất nhiều.

9. Filter tầng 4: quan hệ với Bộ luật Lao động

Đây là filter mạnh nhất.

Nếu candidate:

quy định chi tiết Bộ luật Lao động

→ giữ.

Nếu:

sửa đổi Nghị định 145/2020/NĐ-CP

→ giữ.

Nếu:

thay thế văn bản đang trong corpus

→ giữ.

Có thể chấm điểm:

score = 0

if directly_guides_labor_code:
    score += 10

if modifies_document_in_corpus:
    score += 10

if replaces_document_in_corpus:
    score += 10

if cites_labor_code:
    score += 5

if field == "Lao động - Thương binh và Xã hội":
    score += 4

Đây là graph relevance.

Nó đáng tin hơn embedding rất nhiều.

10. Filter tầng 5: title/trích yếu

Sau đó mới dùng keyword.

Không dùng một keyword "lao động".

Dùng taxonomy.

Ví dụ:

LABOR_TOPICS = {
    "employment_contract": [
        "hợp đồng lao động",
        "thử việc",
        "chấm dứt hợp đồng",
        "đơn phương chấm dứt"
    ],

    "working_time": [
        "thời giờ làm việc",
        "thời giờ nghỉ ngơi",
        "làm thêm giờ",
        "nghỉ hằng năm"
    ],

    "wages": [
        "tiền lương",
        "lương tối thiểu",
        "trả lương"
    ],

    "labor_relations": [
        "quan hệ lao động",
        "thỏa ước lao động tập thể",
        "đối thoại tại nơi làm việc"
    ],

    "termination": [
        "sa thải",
        "trợ cấp thôi việc",
        "trợ cấp mất việc"
    ],

    "retirement": [
        "tuổi nghỉ hưu"
    ],

    "foreign_workers": [
        "người lao động nước ngoài",
        "giấy phép lao động"
    ]
}

Candidate title:

Quy định về tuổi nghỉ hưu

→ match retirement.

Candidate:

Quy định chức năng, nhiệm vụ, quyền hạn và cơ cấu tổ chức...

→ reject.

11. Thêm negative keywords

Cái này rất hữu dụng.

Ví dụ:

NEGATIVE_TOPICS = [
    "chức năng nhiệm vụ quyền hạn",
    "cơ cấu tổ chức",
    "thành lập",
    "phân công",
    "bổ nhiệm",
    "dự toán ngân sách",
    "kế hoạch công tác"
]

Nếu:

positive score thấp
+
negative term xuất hiện mạnh

→ loại.

12. Semantic filtering chỉ là tầng cuối

Sau rule filter có thể còn:

150 candidates

Lúc đó dùng embedding.

Tạo mô tả domain:

Các quy định điều chỉnh quan hệ giữa người lao động và người
sử dụng lao động, bao gồm hợp đồng lao động, tiền lương,
thời giờ làm việc, thời giờ nghỉ ngơi, kỷ luật lao động,
chấm dứt hợp đồng, quan hệ lao động, lao động nước ngoài
và tuổi nghỉ hưu.

Embedding:

domain_embedding = embed(DOMAIN_DESCRIPTION)

document_embedding = embed(
    document.title + "\n" + document.summary
)

Sau đó:

similarity(document, domain)

Nhưng không auto include chỉ dựa vào similarity.

Nó chỉ là thêm signal.

13. Mình sẽ dùng scoring thay cho yes/no

Ví dụ:

def relevance_score(doc):

    score = 0

    # pháp lý
    if doc.direct_relation_to_seed:
        score += 10

    if doc.modifies_included_document:
        score += 10

    # metadata
    if doc.field == "Lao động - Thương binh và Xã hội":
        score += 4

    # lexical
    score += labor_keyword_score(doc.title)

    # semantic
    if doc.semantic_similarity > 0.75:
        score += 3

    # negative
    if contains_org_structure_terms(doc.title):
        score -= 6

    if doc.status == "expired":
        score -= 10

    return score

Sau đó:

score >= 10
→ AUTO INCLUDE

5–9
→ HUMAN REVIEW

< 5
→ EXCLUDE

Đây là workflow rất thực tế.

14. Human review không phải điểm yếu

Ngược lại, với project pháp luật, mình cố ý giữ human-in-the-loop.

Crawler xuất:

data/review/candidates.csv

Ví dụ:

Văn bản	Quan hệ	Score	Decision
145/2020/NĐ-CP	guides BLLD	25	Include
135/2020/NĐ-CP	labor topic	14	Include
XXX/QĐ-BNV	organization	-2	Exclude
YYY/NĐ-CP	semantic	7	Review

Bạn chỉ review khoảng:

20–50 ambiguous docs

chứ không review 5.000 văn bản.

Đây là trade-off rất hợp lý cho project cá nhân.

15. Corpus không cần lớn

Đây là chỗ mình nghĩ bạn đang lo hơi quá.

CiteAgent không cần toàn bộ luật Việt Nam.

Scope có thể tuyên bố rõ:

CiteAgent VN currently covers employment relationships governed by the Vietnamese Labour Code and directly related implementing instruments.

Không support toàn bộ:

BHXH
thuế TNCN
công chức
viên chức
công đoàn
an toàn vệ sinh lao động
việc làm
giáo dục nghề nghiệp

ở MVP.

Chỉ:

QUAN HỆ LAO ĐỘNG

├── hợp đồng lao động
├── thử việc
├── tiền lương
├── thời giờ làm việc
├── nghỉ phép
├── làm thêm
├── kỷ luật
├── chấm dứt HĐ
├── trợ cấp
├── đối thoại
├── thỏa ước
└── nghỉ hưu

Khi corpus đạt khoảng:

20–60 văn bản tốt

đã quá đủ cho portfolio.

16. Mình còn thu scope nhỏ hơn nữa ở version 1

Thậm chí phiên bản đầu:

CiteAgent VN
Vietnamese Employment Relations Assistant

chỉ ingest:

Bộ luật Lao động
        ↓
các văn bản sửa đổi nó
        ↓
các Nghị định trực tiếp hướng dẫn
        ↓
các văn bản sửa đổi những Nghị định đó
        ↓
các Thông tư trực tiếp cần thiết

Không crawl theo:

"ngành lao động"

nữa.

Corpus graph lúc này sẽ kiểu:

                   Bộ luật Lao động
                          │
         ┌────────────────┼────────────────┐
         │                │                │
       guides           amends          consolidates
         │                │                │
         ▼                ▼                ▼
    Nghị định A       Luật sửa đổi       VBHN
         │
         ├──── amended by ────► NĐ B
         │
         └──── detailed by ───► TT C

Cực kỳ sạch.

17. Data pipeline mình đề xuất cuối cùng
              Official sources
                    │
        ┌───────────┴───────────┐
        │                       │
     vbpl.vn           vanban.chinhphu.vn
        │
        ▼
┌─────────────────────┐
│ Seed documents      │
│ Labour Code etc.    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Relation crawler    │
│                     │
│ amend               │
│ replace             │
│ guide               │
│ consolidate         │
└──────────┬──────────┘
           │
           ▼
      Candidate pool
           │
           ▼
┌─────────────────────┐
│ Hard filters        │
│                     │
│ domain              │
│ document type       │
│ status              │
│ national scope      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Relevance scoring   │
│                     │
│ legal graph         │
│ metadata            │
│ keywords            │
│ semantic similarity │
└──────────┬──────────┘
           │
           ▼
   ┌─────────────────┐
   │     decision    │
   └───┬─────┬───────┘
       │     │
 include   review    exclude
       │     │
       └──┬──┘
          ▼
      Download
      PDF / HTML
          │
          ▼
       Parsing
          │
          ▼
       Chunking
          │
          ▼
        Qdrant
18. Nó còn làm project của bạn mạnh hơn

Thực ra vấn đề bạn vừa nêu nên trở thành một feature của project.

Trong README:

Corpus construction

Instead of crawling documents using keyword matching alone, CiteAgent VN starts from authoritative seed legislation and expands through amendment, implementation, replacement, and consolidation relationships. Candidate documents are then filtered using legal metadata, topic taxonomy, semantic relevance, validity status, and a human-review queue.

Câu này tốt hơn rất nhiều so với:

Downloaded 50 PDF files from the Internet.

Bạn vừa có thêm một phần để interviewer hỏi:

“How do you ensure your legal corpus is relevant and current?”

và bạn có câu trả lời kỹ thuật thực sự.

Nếu ưu tiên nhanh hoàn thành, mình sẽ sửa specification trước đó theo hướng này: không yêu cầu generic PDF/HTML crawler nữa, mà làm hẳn Corpus Builder chỉ crawl vbpl.vn từ khoảng 3–5 seed documents, BFS tối đa depth 2, scoring + human review, rồi đóng băng một corpus khoảng 30–50 văn bản để làm phần RAG. Đây là scope hợp lý hơn nhiều.