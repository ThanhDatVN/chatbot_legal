# Pilot thu thập dữ liệu pháp luật thuế

**Pilot:** `vat-invoice-2026-08-11`  
**Lần chạy canonical:** 11/08/2026  
**Phạm vi:** thuế GTGT, quản lý thuế và hóa đơn cho doanh nghiệp  
**Trạng thái:** đã thu thập metadata có provenance; toàn bộ artifact vẫn ở
`pending_human_review`, chưa được phép đưa vào corpus/RAG production.

Pilot 15 văn bản này đã được mở rộng bằng
[corpus thuế chọn lọc 10 năm](crawl-tax-law-10y.md) gồm 50 trang nguồn Chính phủ
và 6 PDF Công báo. Giữ pilot này làm baseline hẹp để so sánh hồi quy crawler.

## 1. Mục tiêu và giới hạn

Pilot chứng minh đường đi tối thiểu:

```text
allowlist được duyệt
  -> robots/content signal
  -> fetch có rate limit và giới hạn byte/redirect/host
  -> parse metadata + SHA-256 + provenance
  -> kiểm số hiệu/ngày/loại văn bản
  -> quarantine
  -> tax/legal reviewer
  -> candidate provision/version/edge
  -> corpus release đã kiểm thử
```

Đây là selective crawl, không phải quét site. Crawler không tự đi theo kết quả
tìm kiếm, sitemap hoặc liên kết ngoài allowlist; không vượt đăng nhập, paywall,
CAPTCHA, `403` hay lỗi chứng thư TLS.

HTML từ Cổng Chính phủ chủ yếu là trang thuộc tính và liên kết attachment. Text
trích từ HTML còn chứa navigation, không phải nguyên văn sạch để chunk/index.
PDF/HTML chỉ là evidence snapshot; quan hệ sửa đổi và hiệu lực ở mức điều/khoản
vẫn phải được parser chuyên biệt và chuyên gia xác nhận.

## 2. Chính sách nguồn

### 2.1 Cổng Chính phủ/Công báo

- Vai trò: nguồn chính thức để xác minh số hiệu, loại, cơ quan, ngày ban hành,
  ngày hiệu lực, trích yếu và attachment.
- `robots.txt` của `chinhphu.vn` cho phép crawl; crawler vẫn kiểm robots theo
  từng hostname thực tế trước request.
- Có thể lưu HTML/PDF chính thức với attribution, hash, thời điểm fetch và URL.
- Mọi bản lưu vào quarantine; chỉ release sau kiểm checksum, chữ ký/nội dung,
  completeness và quan hệ hiệu lực.
- Khi phát hành lại nội dung Công báo phải ghi rõ nguồn theo thông báo trên site.

Nguồn kiểm tra: [Hệ thống văn bản](https://chinhphu.vn/he-thong-van-ban),
[robots](https://chinhphu.vn/robots.txt),
[Công báo điện tử](https://congbao.chinhphu.vn/).

### 2.2 Thư Viện Pháp Luật

- Vai trò dự kiến: discovery/reference và đối chiếu số hiệu/link, không phải
  evidence điều chỉnh cuối cùng.
- [robots.txt](https://thuvienphapluat.vn/robots.txt) công bố content signal
  `search=yes`, `ai-train=no`, `use=reference`; do đó cấu hình cấm lưu raw HTML,
  full visible text, attachment và cấm dùng cho training.
- Request pilot nhận `HTTP 403`. Crawler mở circuit breaker ngay sau lần đầu và
  bỏ qua 10 URL còn lại; không đổi user-agent để giả trình duyệt và không bypass.
- Nếu sản phẩm cần dữ liệu trạng thái/quan hệ của nguồn này, phải có API/license
  hoặc chấp thuận bằng văn bản. Nếu không, dùng cổng chính thức và nguồn nhà nước.

## 3. Allowlist đã chạy

| Nhóm | Văn bản | Ngày hiệu lực | Quan hệ seed |
|---|---|---|---|
| Luật VAT | `48/2024/QH15` | 01/07/2025 | luật gốc |
| Sửa Luật VAT | `90/2025/QH15` | 01/07/2025 | sửa `48/2024` |
| Sửa Luật VAT | `149/2025/QH15` | 01/01/2026 | sửa `48/2024` |
| Sửa bốn luật thuế | `09/2026/QH16` | 24/04/2026 | tiếp tục sửa `48/2024` |
| Hướng dẫn VAT | `181/2025/NĐ-CP` | 01/07/2025 | thi hành `48/2024` |
| Sửa hướng dẫn | `359/2025/NĐ-CP` | 01/01/2026 | sửa `181/2025` |
| Sửa hướng dẫn | `144/2026/NĐ-CP` | 20/06/2026 | sửa `181/2025`, tham chiếu `359/2025` |
| Hướng dẫn VAT | `69/2025/TT-BTC` | 01/07/2025 | thi hành Luật và `181/2025` |
| Giảm VAT | `204/2025/QH15` | 01/07/2025 | chính sách tạm thời đến hết 2026 |
| Thi hành giảm VAT | `174/2025/NĐ-CP` | 01/07/2025 | thi hành `204/2025` |
| Quản lý thuế lịch sử | `38/2019/QH14` | 01/07/2020 | giữ cho event date lịch sử |
| Quản lý thuế hiện hành | `108/2025/QH15` | 01/07/2026 | thay `38/2019` có transition |
| Hóa đơn | `123/2020/NĐ-CP` | 01/07/2022 | thi hành quản lý thuế |
| Sửa hóa đơn | `70/2025/NĐ-CP` | 01/06/2025 | sửa `123/2020` |
| Hướng dẫn hóa đơn | `32/2025/TT-BTC` | 01/06/2025 | thi hành `123/2020`, `70/2025` |

Các relation trên là seed do người lập allowlist khai báo, chưa phải graph edge
`approved`. Ingestion phải tạo candidate edge với source anchor; curator kiểm
đúng loại quan hệ, phạm vi điều khoản và khoảng hiệu lực trước publish.

## 4. Kết quả lần chạy canonical

Artifact chuẩn nằm tại
[`data/crawl/pilot-canonical-2026-08-11`](../data/crawl/pilot-canonical-2026-08-11/).

| Chỉ số | Kết quả |
|---|---:|
| Văn bản trong allowlist | 15 |
| Trang nguồn chính thức thành công | 15/15 |
| Sai lệch số hiệu/ngày/loại văn bản | 0 |
| Request discovery thành công | 0 |
| Request discovery `403` | 1 |
| Discovery bỏ qua sau circuit breaker | 10 |
| PDF chính thức thành công | 1/7 |
| Attachment fail-closed | 6/7 |

PDF Công báo chứa `09/2026/QH16`:

```text
path: quarantine/official-attachments/tax-law-09-2026-1.pdf
bytes: 2267180
sha256: 020d48792da1876713929bff7d81ff02fafb75885b798e771c951659a625a265
status: pending_human_review
```

Sáu attachment chưa tải gồm năm endpoint `datafiles.chinhphu.vn` trả `403` khi
GET bằng client crawler và một endpoint `g7.cdnchinhphu.vn` không xác minh được
chuỗi chứng thư trong Python. Không dùng `verify=False`. Hướng xử lý là ưu tiên
URL Công báo/CDN chính thức đã kiểm chứng, làm việc với chủ nguồn về quyền/API,
hoặc cấu hình trust store doanh nghiệp; mọi thay đổi transport phải giữ nguyên
host allowlist, robots, rate limit, hash và audit.

## 5. Hợp đồng artifact

| Artifact | Nội dung | Được index? |
|---|---|---|
| `config.snapshot.json` | allowlist và policy đúng tại lần chạy | không |
| `manifest.jsonl` | một record/page hoặc attachment; URL, robots, HTTP, hash, metadata, lỗi | không, dùng audit |
| `summary.json` | tổng hợp kết quả và validation | không |
| `quarantine/official-html/*.html` | response chính thức bất biến theo hash | chưa |
| `quarantine/official-text/*.txt` | text thô để QA parser, còn navigation | chưa |
| `quarantine/official-attachments/*.pdf` | attachment chính thức đã kiểm MIME/magic/hash | chưa |
| `reference/*.json` | metadata/excerpt discovery tối thiểu | chỉ search metadata sau license review |

Record tối thiểu gồm `pilot_id`, `document_id`, `instrument_number`, source/role,
requested/final URL, robots/content signal, fetch time, HTTP/MIME/bytes, SHA-256,
metadata, validation issues, stored path và quarantine status.

## 6. Cách chạy

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check tools tests
.\.venv\Scripts\python.exe tools\legal_crawler.py --dry-run
.\.venv\Scripts\python.exe tools\legal_crawler.py `
  --output data\crawl\pilot-YYYY-MM-DD `
  --download-official-pdfs
```

Không chạy lại vào thư mục output đã có dữ liệu. Mỗi run dùng thư mục mới để
manifest và evidence bất biến; so sánh hash giữa các run để phát hiện thay đổi.

## 7. Kiểm soát đã cài

- HTTPS only, exact hostname allowlist, cấm credential trong URL;
- phân giải DNS và chặn IP không public để giảm SSRF;
- kiểm robots theo host; ghi hash robots và content signal;
- delay 1,5 giây/host, timeout, giới hạn redirect;
- HTML tối đa 5 MiB, PDF tối đa 30 MiB, tối đa hai attachment/văn bản;
- revalidate host ở mỗi redirect;
- MIME + magic `%PDF`, SHA-256 và provenance;
- discovery chỉ giữ reference nhỏ, không lưu/training full content;
- mỗi lỗi source/attachment được cô lập và ghi manifest;
- `403` của discovery mở circuit để tránh request lặp;
- mọi output mặc định quarantine và fail-closed.

## 8. Việc tiếp theo trước RAG

1. Tax/legal reviewer đối chiếu 15 trang với attachment chính thức, chữ ký, số
   hiệu, issuer, ngày, trích yếu và phạm vi transition.
2. Giải quyết kênh tải attachment chính thức bằng phương thức được chủ nguồn cho
   phép; không hạ TLS hoặc giả lập người dùng để vượt kiểm soát.
3. Parse PDF/DOCX theo layout; giữ page/bbox/offset; đo OCR/table quality và
   đối chiếu exact text cho điều khoản critical.
4. Tách instrument -> điều -> khoản -> điểm; tạo version/assertion bitemporal,
   candidate relation và source anchor bất biến.
5. Dựng gold fixture cho các mốc 01/07/2025, 01/01/2026, 24/04/2026,
   20/06/2026 và 01/07/2026; kiểm không trộn luật cũ/mới.
6. Chỉ publish corpus release khi `T-001..005`, `T-008`, `T-012`, `T-015` và
   reviewer gate đạt; projection search/graph được tạo từ release đã duyệt.
