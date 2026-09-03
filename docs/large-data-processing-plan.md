# Phuong an xu ly du lieu phap luat lon

Ngay ra soat: **11/08/2026**. Pham vi so lieu thuc nghiem: shard 0001-0006 cua
inventory 10 nam, khong tinh shard 0007 dang tam dung.

## 1. Ket qua kiem toan crawl

Bao cao may doc duoc:
[`crawl-completeness-shards-0001-0006-2026-08-11.json`](../data/analysis/crawl-completeness-shards-0001-0006-2026-08-11.json).
Cong cu tai lap:
[`audit_crawl_completeness.py`](../tools/audit_crawl_completeness.py).

| Gate | Ket qua |
|---|---:|
| Ho so cau hinh | 600 |
| Trang nguon Chinh phu lay thanh cong | 600/600 |
| URL attachment tim thay tren trang nguon | 726 |
| PDF tai thanh cong | 726/726 |
| Tong trang PDF parser doc duoc | 33.527 |
| PDF ma hoa | 0 |
| Loi file HTML, content-length hoac SHA-256 | 0 |
| Loi magic `%PDF-`, marker `%%EOF` hoac cay trang | 0 |
| Dung luong artifact shard 0001-0006 va resume | 2.452.153.095 byte, 2,284 GiB |

Mot PDF `08/2026/TT-BNV` bi timeout trong shard goc. Audit phat hien dung URL nay;
lan khoi phuc rieng da tai du 8.188.494 byte va SHA-256
`e14a80342e6914629d7f34f3cfafc827c1685d728f511f03859a376acc3b3999`.

### Gioi han cua ket luan "khong thieu trang"

Ket qua tren chung minh **du trang nguon, du URL tep da duoc trang nguon cong bo va byte PDF
noi bo nhat quan**. No khong the tu no chung minh ban scan do co quan phat hanh dua len khong
bo sot mot trang vat ly, vi nguon khong cong bo page-count chuan cho tung tep. Cong bao cung co
the gom nhieu van ban trong mot PDF, nen 33.527 trang PDF khong dong nghia 33.527 trang cua 600
van ban doc lap.

Gate noi dung tiep theo phai:

1. tach ranh gioi van ban trong PDF Cong bao theo so hieu, tieu de va trang;
2. OCR so trang in, phat hien day so dut/nhay/lap va trang trang bat thuong;
3. doi chieu so hieu tim thay trong PDF voi inventory va dependency graph;
4. dua scan kho doc, OCR confidence thap va xung dot metadata vao quarantine cho reviewer.

## 2. Kich thuoc du kien

Mau 600 ho so co trung binh 3,90 MiB raw/ho so va 46,18 trang/PDF. Neu phan con lai co
phan bo tuong tu, 13.058 source record se tao khoang **49,7 GiB raw** va **730 nghin trang**.
Do lech do Cong bao nhieu trang va van ban co nhieu attachment, ngan sach crawl nen giu moc
50-65 GiB, du phong dia 75-80 GiB cho raw va file tam.

Khong nen luu anh render cua moi trang lau dai. Anh 300 DPI co the lam derived storage tang
nhieu lan. Chi luu anh trang khi OCR/layout that bai, can review hoac can lam evidence preview;
anh trung gian con lai dat lifecycle xoa sau 7-30 ngay.

Vi du kich thuoc vector, khong phai du bao chunk: 2 trieu chunk x 1.536 chieu ton khoang
11,4 GiB voi `float32`, hoac 5,7 GiB voi `float16`, chua tinh HNSW/IVF va metadata. Ngan sach
production ban dau hop ly la 300-500 GiB cho raw, derived, search index, staging va mot ban sao
luu; cap phat theo telemetry thuc te sau moi 10 shard.

## 3. Kien truc muc tieu

```text
Crawler streaming -> raw object store (immutable, sha256)
                  -> manifest/outbox PostgreSQL
                              |
                              v
            detect text/OCR/layout/page boundary
                              |
                              v
       normalized Parquet + legal AST + temporal relations
                    |                    |
                    v                    v
             DuckDB batch QA       PostgreSQL SoT
                    |                    |
                    +------> hybrid search index
                                      |
                                      v
                          RAG/GraphRAG + citation gate
```

### 3.1 He thong ban ghi

| Lop | Cong nghe giai doan nay | Vai tro |
|---|---|---|
| Raw/bronze | object storage S3-compatible; local filesystem chi cho dev | PDF/HTML goc bat bien, key theo SHA-256; khong luu BLOB/base64 trong DB |
| Metadata/SoT | PostgreSQL | source record, artifact, version, bitemporal validity, relation, review, job/outbox |
| Normalized/silver | Parquet + Zstandard | mot row/page/block/clause; de scan cot va tai lap batch |
| Legal/gold | PostgreSQL + Parquet release | dieu/khoan/diem, claim-evidence, quan he sua doi/bai bo/dan chieu, release da duyet |
| Search projection | pgvector luc nho; OpenSearch khi can hybrid/QPS | BM25 + vector; index la projection co the rebuild, khong phai SoT |
| Local QA | DuckDB tren Parquet | completeness, duplicate, OCR coverage, page anomaly, corpus diff ngoai RAM |

Object phai co `sha256`, byte length, MIME, source URL, final URL, `fetched_at`, HTTP validators,
pipeline version va provenance. S3 co the kiem checksum trong upload/download va luu checksum
voi object; production can versioning va Object Lock/WORM cho evidence can bao toan. Parquet la
dinh dang cot co compression/encoding, con DuckDB ho tro workload lon hon RAM bang spill ra dia,
nen du cho corpus du kien nay ma khong can cluster compute ngay.

### 3.2 Data contract toi thieu

Moi artifact co khoa noi dung va phien ban xu ly:

```text
artifact_id = sha256(raw_bytes)
derivation_key = sha256(raw_sha256 + pipeline_version + model_version + params_hash)
page_id = sha256(artifact_id + physical_page_index + boundary_version)
legal_node_id = stable(source_record_id + article/paragraph/point locator)
```

Raw khong bi ghi de. OCR, parser, chunk va embedding la derived artifact co the tai tao. Mot raw
hash co the gan voi nhieu URL/source record de khong nhan doi byte nhung van giu moi provenance.
Release chi tro den artifact da qua validation; rollback la doi release pointer, khong sua lich su.

## 4. Pipeline va dieu phoi

### 4.1 Crawl/download

Nut that hien tai nam tai `SafeFetcher.fetch`: response duoc dua vao `list[bytes]`, sau do
`b"".join(chunks)` va ghi file. Voi gioi han 256 MiB, mot worker co the tam giu hon 512 MiB do
chunks va ban copy luc join; curl fallback cung giu toan bo `stdout` trong RAM.

Uu tien ky thuat P0:

- stream 1-8 MiB/block vao file `.partial` cung luc cap nhat SHA-256 va byte count;
- kiem `Content-Length` truoc khi tai neu co, van enforce max byte trong khi stream;
- `fsync`, verify magic/EOF/hash, roi atomic rename vao content-addressed path;
- checkpoint `ETag`, `Last-Modified`, byte offset va chi resume bang `Range` khi server tra
  `206` voi validator khop; neu khong thi tai lai tu dau;
- exponential backoff co jitter cho timeout/429/5xx, khong retry 4xx vinh vien;
- gioi han concurrency theo host va tach queue network, CPU OCR, GPU layout/embedding.

Voi quy mo hien tai, dung PostgreSQL job table + `FOR UPDATE SKIP LOCKED`, lease, heartbeat,
idempotency key va outbox. Chua can Kafka. Moi stage ghi checkpoint theo artifact, nen worker chet
khong lam mat raw va khong tao side effect trung.

### 4.2 OCR/layout co chon loc

Khong OCR toan bo. Dau tien do text coverage, ky tu Viet hop le, trang chi co anh, thu tu doc va
bang bieu. PDF co text tot di thang den layout parser; image-only/coverage thap moi vao OCR.

- OCRmyPDF + Tesseract Vietnamese la baseline PDF search layer; gioi han so job de tranh hai
  tang parallelism cung chiem het CPU.
- PP-StructureV3 dung cho bang, bo cuc phuc tap, nhieu cot va reading order; chay sau router,
  khong mac dinh cho moi trang.
- Khong ghi de PDF goc. Luu OCR text, bbox, confidence, physical page, printed page va model
  version. Confidence thap hoac trang in dut day vao review queue.

### 4.3 Parse va chunk phap ly

Don vi truy xuat chinh la dieu/khoan/diem va span goc, khong phai chunk kich thuoc co dinh. Moi
node giu physical page, bbox, character offsets, source hash, ngay ban hanh, khoang hieu luc va
quan he phap ly. Chunk retrieval co the ghep heading + locator + noi dung, nhung citation phai tro
lai span goc.

Batch silver chia file Parquet 128-512 MiB, tranh file qua nho. Partition theo `dataset_release`
va nhom coarse nhu nam ban hanh/loai artifact; khong partition theo document ID. PostgreSQL chi
partition bang lon sau khi telemetry cho thay loi ich pruning/maintenance, vi partition qua muc
lam tang planning va van hanh.

### 4.4 Search va vector

Giai doan MVP co the dung PostgreSQL full-text + pgvector de giam so he thong. Phai benchmark
recall sau filter `as_of_date`, loai van ban, co quan, status va tenant: pgvector luu y approximate
index loc sau khi scan, co the tra it ket qua; iterative scan hoac partition/tach bang khac phuc
mot phan.

Chuyen sang OpenSearch khi co mot trong cac tin hieu: tren 1-5 trieu searchable chunk, QPS/latency
khong dat, can BM25+vector+faceting/typo/relevance tuning manh, hoac rebuild index anh huong DB.
Hybrid search ket hop lexical va semantic, phu hop so hieu/dieu khoan can exact match dong thoi
voi cau hoi ngon ngu tu nhien. Luon filter authority/effective interval truoc hoac trong retrieval;
reranker khong duoc phep dua van ban sai thoi diem tro lai.

## 5. Khi nao moi can he thong phan tan

| Nguong quan sat | Quyet dinh |
|---|---|
| Duoi 100 GiB raw, duoi 100 nghin PDF, batch dem | worker process/container + PostgreSQL + object store + Parquet/DuckDB |
| 100 GiB-1 TiB hoac hon 1 trieu trang/ngay | thu Ray Data cho OCR/embedding phan tan, streaming block va spill; benchmark chi phi truoc |
| Nhieu writer dataset, hon 500 GiB derived, can snapshot/time travel schema/partition | dua Iceberg vao silver/gold |
| Search tren 1-5 trieu chunk hoac SLA/QPS vuot PostgreSQL | tach OpenSearch cluster |

Iceberg ho tro snapshot, manifest va partition evolution, nhung cung keo theo catalog, compaction,
snapshot expiration va orphan-file maintenance. Voi corpus du kien 50-65 GiB raw, dua no vao ngay
se tang chi phi van hanh ma chua giai quyet nut that nao da do duoc.

## 6. Backpressure, bao mat va lifecycle

- Queue co quota theo tenant/source, weighted fairness va maximum in-flight bytes, khong chi dem job.
- Worker OCR/GPU nhan object reference, khong truyen PDF qua message broker.
- Antivirus/content validation va sandbox parser truoc OCR; cap egress chi cho crawler allowlist.
- Ma hoa at rest/in transit; matter data va corpus global tach bucket/prefix, IAM role va key.
- Raw legal evidence giu theo retention da duyet; temp render 7-30 ngay; index/cache co the xoa va rebuild.
- Backup metadata PostgreSQL va object inventory; dinh ky restore drill va hash sample.
- Metrics: byte/page throughput, RAM peak/worker, retry theo host, OCR coverage/confidence, queue age,
  duplicate ratio, cost/1.000 page, search recall va citation support.

## 7. Lo trinh thuc hien

### P0 - Truoc khi chay tiep shard

1. Dua audit completeness vao gate sau moi shard; output JSON va exit non-zero khi co gap.
2. Refactor attachment downloader thanh streaming temp-file + hash + atomic rename.
3. Them retry/backoff, HEAD/Range resume va test server gia lap mat ket noi giua file.
4. Ghi raw artifact catalog trong PostgreSQL hoac SQLite staging, deduplicate theo SHA-256.

Nghiem thu: peak RAM khong tang theo kich thuoc PDF; kill/restart tai lai khong tao object loi/trung;
100% source page va discovered attachment co terminal state; audit shard sach.

### P1 - Bronze/silver

1. Object storage S3-compatible, content-addressed keys va lifecycle.
2. Router text/OCR, page inventory, boundary detector va quarantine.
3. Parquet schema page/block/clause; DuckDB QA va corpus diff.

Nghiem thu: tai lap silver tu raw chi bang release manifest; moi page truy nguoc duoc source hash;
printed-page anomaly co review evidence.

### P2 - Corpus phap ly va retrieval

1. Parser dieu/khoan/diem, bitemporal resolver, dependency closure.
2. PostgreSQL FTS + pgvector benchmark; hybrid, temporal va counter-authority eval.
3. Citation verifier bat buoc span/page/source hash.

Nghiem thu: khong publish node thieu provenance/effective interval; recall va citation support dat
release gate trong bo test chuyen gia.

### P3 - Scale-out theo telemetry

Chi them OpenSearch, Ray Data hoac Iceberg khi cham nguong muc 5. Truoc va sau moi thay doi phai co
benchmark throughput, recall, p95 latency, chi phi va bai test rebuild/rollback.

## 8. Tai lieu ky thuat goc da kiem tra

- [AWS S3 - checking object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html): checksum upload/download, full/composite checksum.
- [AWS S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html): WORM va chong ghi de/xoa evidence.
- [Apache Parquet](https://parquet.apache.org/): columnar storage, compression va encoding.
- [DuckDB - larger-than-memory workloads](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads): spill to disk va gioi han out-of-core.
- [PostgreSQL - table partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html): partition pruning va trade-off partition.
- [pgvector README](https://github.com/pgvector/pgvector/blob/master/README.md?plain=1): HNSW/IVFFlat, filtering va iterative scans.
- [OpenSearch - vector search concepts](https://docs.opensearch.org/latest/vector-search/getting-started/concepts/): lexical, semantic va hybrid search.
- [Apache Iceberg specification](https://iceberg.apache.org/spec/?h=snapshot): snapshot, manifest va partition evolution.
- [OCRmyPDF - batch processing](https://ocrmypdf.readthedocs.io/en/stable/batch.html): parallelism va repair truoc OCR.
- [PaddleOCR PP-StructureV3](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html): layout, table va reading order.
