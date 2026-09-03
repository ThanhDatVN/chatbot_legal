# Corpus văn bản pháp luật liên quan đến thuế trong 10 năm

**Mốc dữ liệu:** 11/08/2026  
**Cửa sổ kiểm kê:** 11/08/2016 đến hết 11/08/2026  
**Nguồn chính:** Cổng Thông tin điện tử Chính phủ và Công báo điện tử Chính phủ  
**Trạng thái:** kiểm kê metadata đã hoàn tất; tải và sàng lọc toàn văn đang thực hiện theo shard; mọi bản ghi vẫn ở quarantine.

## 1. Định nghĩa “đầy đủ”

Không thể tìm đủ văn bản thuế chỉ bằng từ khóa ở tiêu đề. Một luật về đất đai, đầu tư,
công nghệ cao, thi hành án hoặc ngân sách có thể sửa trực tiếp một điều của luật thuế.
Vì vậy pipeline dùng bốn lớp kiểm soát:

1. Duyệt hết các trang danh mục chính thức cho sáu nhóm văn bản trong cửa sổ 10 năm.
2. Giữ **mọi** bản ghi vào hàng đợi tải/sàng lọc toàn văn; từ khóa tiêu đề chỉ quyết
   định thứ tự chạy, không phải điều kiện loại.
3. Từ toàn văn, phát hiện quy phạm thuế và quan hệ dẫn chiếu, sửa đổi, thay thế, bãi bỏ,
   hướng dẫn, hợp nhất và điều khoản chuyển tiếp.
4. Đi theo các quan hệ ra ngoài cửa sổ 10 năm khi văn bản cũ vẫn là căn cứ hoặc cần để
   giải quyết một sự kiện lịch sử.

Trong tài liệu này, “đầy đủ” có nghĩa là đầy đủ đối với các bản ghi mà hai cổng chính
thức công bố trong sáu nhóm đã nêu tại ngày chốt, cộng với dependency closure. Nó không
bao gồm dự thảo, văn bản cá biệt không được công bố tại hai nguồn, công văn nội bộ hoặc
cơ sở dữ liệu địa phương chưa tích hợp lên cổng.

## 2. Kết quả kiểm kê chính thức

Artifact master:
[`data/analysis/tax-document-master-inventory-2026-08-11.json`](../data/analysis/tax-document-master-inventory-2026-08-11.json).

| Nhóm nguồn | Số source record |
|---|---:|
| Luật/Pháp lệnh | 235 |
| Nghị định | 1.790 |
| Quyết định | 2.067 |
| Thông tư | 4.987 |
| Nghị quyết | 1.741 |
| Văn bản hợp nhất | 2.238 |
| **Tổng** | **13.058** |

Sau khi nhóm các phần Công báo của cùng một văn bản hợp nhất, có 13.052 semantic
document. Có 13.037/13.058 source record đã lộ URL tệp chính thức ngay từ trang danh
mục. Sau khi chỉ giữ định dạng PDF, cấu hình canonical prelist được 13.033 record với
14.737 URL; 25 record còn lại phải phát hiện PDF từ trang chi tiết hoặc ghi nhận nguồn
không cung cấp PDF.

Crawler đã lưu snapshot và hash của toàn bộ trang danh mục dùng để lập inventory:

- `data/crawl/government-law-inventory-2016-08-11-to-2026-08-11-v2`
- `data/crawl/government-decree-inventory-2016-08-11-to-2026-08-11`
- `data/crawl/government-decision-inventory-2016-08-11-to-2026-08-11`
- `data/crawl/government-circular-inventory-2016-08-11-to-2026-08-11-v3`
- `data/crawl/government-gazette-resolution-inventory-2016-08-11-to-2026-08-11`
- `data/crawl/government-gazette-consolidated-inventory-2016-08-11-to-2026-08-11`

`instrument_number` không được dùng làm khóa duy nhất. Có 1.010 số hiệu bị trùng giữa
các loại văn bản, cơ quan hoặc thời điểm. Source identity dùng `docid` của Cổng Chính
phủ hoặc `source_item_id` của Công báo; semantic identity được xử lý riêng.

## 3. Hàng đợi sàng lọc toàn văn

Hàng đợi đầy đủ nằm tại
[`data/analysis/tax-document-fulltext-screening-queue-2026-08-11.jsonl`](../data/analysis/tax-document-fulltext-screening-queue-2026-08-11.jsonl).

| Lớp lịch chạy | Số source record | Ý nghĩa |
|---|---:|---|
| `priority_fulltext_fetch` | 1.175 | Tiêu đề có tín hiệu thuế, phí, hóa đơn, hải quan rõ |
| `adjacent_fulltext_screening` | 1.153 | Lĩnh vực thường có quan hệ với thuế |
| `fulltext_screening_pending` | 10.730 | Không có tín hiệu tiêu đề nhưng vẫn bắt buộc đọc toàn văn |

Ba lớp cộng lại bằng 13.058 source record ở cấp cấu hình crawl; số semantic document
khác nhẹ do một số văn bản hợp nhất có nhiều phần Công báo. Không được gọi 1.175 bản
ưu tiên là “toàn bộ văn bản thuế”. Chỉ sau khi 13.058 bản ghi được sàng lọc và relation
closure hoàn tất mới được phát hành một corpus có completeness report.

Cấu hình đầy đủ được chia thành 131 shard độc lập, tối đa 100 source record/shard:
[`config/tax-document-all-fulltext-shards-v4/index.json`](../config/tax-document-all-fulltext-shards-v4/index.json).
Mỗi source record xuất hiện đúng một lần. Shard giúp retry, giới hạn tải, checkpoint và
đối chiếu hash mà không phải chạy lại cả corpus.

### 3.1 Lần chạy pilot shard 0001 với giới hạn cũ

Artifact:
[`data/crawl/tax-document-all-fulltext-shard-0001-2026-08-11-v3`](../data/crawl/tax-document-all-fulltext-shard-0001-2026-08-11-v3/).

| Chỉ số | Kết quả |
|---|---:|
| Trang nguồn | 100/100 thành công |
| PDF chính thức | 108/108 thành công |
| HTML/text quarantine | 100/100 mỗi loại |
| Validation issue | 0 |
| Tổng file | 311 |
| Tổng dung lượng | 491.935.712 byte |

SHA-256 của `manifest.jsonl` là
`8963389dccd958ed81ee0868d2aa8c3480bc3f4f6de20b787c5a80323edbf6b4`;
SHA-256 của `summary.json` là
`b838ea5ced0f09c89f1270096aa9649ecf5b79b53527c331b19843efab107c9c`.
Lần này chứng minh đường tải và hash hoạt động, nhưng **không được tính là shard đầy
đủ**: builder cũ chỉ giữ tối đa bốn attachment đã biết và crawler cũng chỉ tải tối đa
bốn tệp/văn bản. Cấu hình v4 giữ toàn bộ URL PDF đã biết, kể cả URL stream có tên
tệp trong query, cho phép tối đa 256 attachment và 256 MB/tệp. Với cùng 100 source
record, v4 có 119 attachment prelisted thay vì 94.
Artifact cũ được giữ để audit, không được nâng trạng thái.

### 3.2 Lần chạy canonical v4

Artifact:
[`data/crawl/tax-document-all-fulltext-run-v4-2026-08-11`](../data/crawl/tax-document-all-fulltext-run-v4-2026-08-11/).

| Chỉ số | Shard 0001 | Shard 0002 | Tổng |
|---|---:|---:|---:|
| Trang thành công | 100 | 100 | 200 |
| PDF thành công | 119 | 113 | 232 |
| Page/PDF lỗi hoặc skip | 0 | 0 | 0 |
| Trạng thái | `completed` | `completed` | 2/131 shard |

Hai shard có 639 file, tổng 1.047.941.595 byte. Manifest SHA-256 lần lượt là
`bf830c93804f7f345cdc8f14ceeb41cbb573c7ef7749e2da5b81db3cdf6358eb` và
`0708eddb2bb7968fedcb3dae445c20cdce286dcd09b892fdb86806d381282581`.
`run-state.json` xác nhận cả hai `gap_count=0`. Còn 129 shard, tương ứng 12.858
source record, chưa hoàn tất tải toàn văn.

Checkpoint sau đó đã hoàn tất đến shard 0006 rồi tạm dừng. Hai URL từng timeout là PDF
của `167/2026/NĐ-CP` và `08/2026/TT-BNV`; cả hai đã được tải lại trong artifact resume.
Kiểm toán cuối đối chiếu cấu hình với toàn bộ base/resume manifest, kiểm kích thước,
SHA-256, magic/EOF và cây trang PDF: 600/600 trang nguồn, 726/726 PDF, 33.527 trang PDF,
không còn gap hoặc lỗi integrity. Xem
[`crawl-completeness-shards-0001-0006-2026-08-11.json`](../data/analysis/crawl-completeness-shards-0001-0006-2026-08-11.json)
và [phương án xử lý dữ liệu lớn](large-data-processing-plan.md). Một job nền cũ đã đi vào shard
0007 trước khi bị dừng: artifact dở có 94/100 trang nguồn, 108/109 PDF thành công và không có
summary. Audit riêng xác định còn sáu trang nguồn và một PDF cần lấy tại
[`crawl-completeness-shard-0007-partial-2026-08-11.json`](../data/analysis/crawl-completeness-shard-0007-partial-2026-08-11.json).
Dữ liệu này được giữ nguyên; lần sau tạo `shard-0007-resume` cho phần thiếu, không ghi đè hoặc
gọi shard dở là hoàn tất.

## 4. Tiêu chí nhận văn bản liên quan thuế

Một văn bản được nhận khi toàn văn hoặc graph quan hệ cho thấy ít nhất một trong các
tín hiệu sau:

- quy định nghĩa vụ, đối tượng, căn cứ, giá tính, thuế suất, miễn/giảm/hoàn hoặc ưu đãi;
- quản lý thuế, đăng ký, khai, nộp, quyết toán, hóa đơn/chứng từ, cưỡng chế, xử phạt;
- phí, lệ phí, tiền thuê đất, tiền sử dụng đất, thu ngân sách hoặc nghĩa vụ hải quan;
- sửa đổi, bãi bỏ, thay thế, hướng dẫn hoặc hợp nhất văn bản thuế;
- điều khoản chuyển tiếp hoặc hiệu lực làm thay đổi kết quả của một case thuế;
- định nghĩa pháp lý từ lĩnh vực khác được một quy phạm thuế viện dẫn.

Phân loại máy chỉ tạo candidate. Để publish cần lưu đoạn bằng chứng, điều/khoản/điểm,
trang PDF, hash nguồn, loại relation, khoảng hiệu lực và trạng thái duyệt.

## 5. Ngày hiệu lực phải lấy từ nội dung

Ngày hiển thị trên cổng là metadata để đối chiếu, không phải bằng chứng thay cho điều
khoản trong văn bản. Pipeline tách riêng:

- ngày hiệu lực chung của văn bản;
- ngày hiệu lực riêng của một điều/khoản;
- khoảng áp dụng chính sách;
- ngày ban hành/thông qua;
- hiệu lực gốc và hiệu lực sau khi bị sửa đổi;
- thời điểm hệ thống biết mỗi phiên bản.

Đợt kiểm định 22 luật bằng PDF Công báo có text layer cho kết quả:

| Kết quả | Số lượng |
|---|---:|
| Nội dung xác nhận metadata | 19 |
| Metadata xung đột với điều khoản trong PDF | 2 |
| Không đủ text layer, phải OCR/duyệt tay | 1 |

Chi tiết có page provenance tại
[`data/analysis/tax-law-gazette-effective-date-evidence-2026-08-11-v3.json`](../data/analysis/tax-law-gazette-effective-date-evidence-2026-08-11-v3.json).

Các trường hợp fail-closed hiện tại:

| Văn bản | Metadata/lời dẫn | Nội dung điều khoản | Xử lý |
|---|---|---|---|
| `43/2024/QH15` | 29/06/2024 | Điều 5: 01/08/2024 | quarantine |
| `127/2025/QH15` | 07/01/2026 | Điều 179: 01/07/2026 | quarantine |
| `66/2025/QH15` | 01/01/2026 | PDF ảnh, coverage text 0% | OCR/duyệt tay |
| `67/2025/QH15` trong `113/VBHN-VPQH` | lời dẫn: 01/10/2026 | Điều 19: 01/10/2025 | quarantine |

Hồ sơ xung đột có cấu trúc nằm tại
[`data/analysis/tax-law-temporal-source-conflicts-2026-08-11.json`](../data/analysis/tax-law-temporal-source-conflicts-2026-08-11.json).
Hệ thống không tự chọn ngày “có vẻ đúng”; chuyên gia phải duyệt và quyết định nguồn
có thẩm quyền cho từng trường hợp.

Luật Đất đai `31/2024/QH15` phải lưu hai trạng thái: điều khoản hiệu lực trong bản gốc
và ngày sau khi Luật `43/2024/QH15` sửa đổi. Ba phần PDF gốc được cấu hình riêng tại
[`config/tax-law-land-original-effective-date-source.json`](../config/tax-law-land-original-effective-date-source.json).

## 6. Cách chạy

### 6.1 Môi trường

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check tools tests
```

Môi trường hiện tại dùng Python 3.12.10, `pypdf`, `truststore`, `pytest` và `ruff`.

### 6.2 Lập lại inventory và shard

```powershell
.\.venv\Scripts\python.exe tools\build_tax_document_inventory.py --help
.\.venv\Scripts\python.exe tools\shard_crawl_config.py `
  --config config\tax-document-all-fulltext.generated.json `
  --output config\tax-document-all-fulltext-shards-v4 `
  --shard-size 100
```

Inventory nguồn phải được crawl lại trước khi build master nếu mốc chốt thay đổi.
Không chỉnh artifact đã chốt tại chỗ; tạo version mới và so sánh hash.

### 6.3 Crawl một shard

```powershell
.\.venv\Scripts\python.exe tools\legal_crawler.py `
  --config config\tax-document-all-fulltext-shards-v4\shard-0001.json `
  --output data\crawl\tax-document-all-fulltext-shard-0001-YYYY-MM-DD `
  --download-official-pdfs
```

Chỉ chạy tuần tự với delay đã khai báo, tuân thủ `robots.txt`, giới hạn kích thước và
retry có backoff. Mỗi lần retry dùng thư mục output mới. Manifest được ghi tăng dần để
giữ bằng chứng của lỗi mạng hoặc nguồn.

Chạy tuần tự toàn bộ shard với checkpoint:

```powershell
.\.venv\Scripts\python.exe tools\run_crawl_shards.py `
  --shards-dir config\tax-document-all-fulltext-shards-v4 `
  --output-root data\crawl\tax-document-all-fulltext-run-YYYY-MM-DD `
  --download-official-pdfs `
  --min-free-gb 20
```

Runner xác minh hash của 131 config trước khi chạy và ghi `run-state.json` sau từng
shard. Shard terminal không có gap được bỏ qua; shard có page/attachment lỗi hoặc bị
skip mang trạng thái `completed_with_gaps` và mặc định làm runner dừng. Output dở dang
được giữ nguyên thay vì ghi đè. Có thể dùng `--start-shard` và `--end-shard` để chia ca.
`--min-free-gb` dừng trước shard tiếp theo nếu ổ đĩa không còn dung lượng dự phòng.

### 6.4 Trích bằng chứng ngày hiệu lực

```powershell
.\.venv\Scripts\python.exe tools\legal_effective_dates.py `
  --config config\tax-law-gazette-verification-sources.json `
  --crawl-root data\crawl\tax-law-gazette-effective-date-verification-2026-08-11 `
  --output data\analysis\tax-law-gazette-effective-date-evidence-YYYY-MM-DD.json
```

## 7. Gate để gọi là corpus đầy đủ

Corpus chỉ được gắn nhãn `complete_for_declared_scope` khi đồng thời đạt:

1. 131/131 shard kết thúc và mọi source record có terminal status.
2. Mọi PDF/HTML thành công có SHA-256, provenance và immutable storage path.
3. Lỗi tải đã retry; record không thể tải có lý do, bằng chứng và kế hoạch xử lý.
4. 100% toàn văn được sàng lọc hoặc có trạng thái OCR/manual review.
5. Quan hệ pháp lý được đi đến closure, kể cả dependency ngoài 10 năm.
6. Ngày hiệu lực ở cấp văn bản và điều khoản có evidence; xung đột bị quarantine.
7. Parser giữ page/bbox/text offset, không tách nhầm nhiều văn bản trong cùng số Công báo.
8. Chuyên gia duyệt sample theo risk và 100% candidate sửa đổi/bãi bỏ/xung đột thời gian.
9. Báo cáo completeness nêu rõ cả included, excluded, unresolved và source coverage.

Cho đến khi đủ chín gate trên, dữ liệu chỉ là evidence quarantine và không được đưa
thẳng vào RAG tư vấn cho người dùng cuối.
