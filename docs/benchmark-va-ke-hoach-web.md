# Benchmark quốc tế và kế hoạch xây dựng sản phẩm web

**Mốc rà soát:** 09/08/2026  
**Mục tiêu:** chuyển đề án nghiên cứu thành một web app dùng được cho chuyên gia
thuế Việt Nam, có khả năng kiểm chứng, cộng tác và xử lý case cụ thể.

## 1. Quyết định sản phẩm

Sản phẩm nên được định vị là **tax legal workbench có AI**, không phải một ô chat
đơn lẻ. Giao diện chat chỉ là một trong các cách đi vào hệ thống; giá trị chính
nằm ở hồ sơ vụ việc, nguồn luật theo thời điểm, rule tính thuế, review của chuyên
gia và theo dõi thay đổi.

Wedge đề xuất cho bản thương mại đầu tiên:

- khách hàng: công ty tư vấn thuế/kế toán, bộ phận thuế doanh nghiệp và luật sư;
- miền nghiệp vụ: VAT và hóa đơn điện tử;
- hình thức: B2B, mỗi tenant có dữ liệu và quyền riêng;
- đầu ra: bản nghiên cứu/bản tư vấn nháp có thể duyệt, không tự động thay thế
  người chịu trách nhiệm nghề nghiệp;
- khác biệt: xử lý đúng phiên bản luật tại ngày giao dịch, chỉ dẫn chính xác,
  timeline case và cảnh báo tác động của luật mới.

Không đặt mục tiêu "AI trả lời được mọi câu hỏi". Mục tiêu vận hành là: **trả lời
có căn cứ khi đủ bằng chứng, hỏi lại khi thiếu dữ kiện, và dừng/chuyển người khi
không thể bảo vệ kết luận**.

## 2. Rà soát sản phẩm quốc tế

### 2.1 Bốn nhóm sản phẩm khác nhau

| Nhóm | Ví dụ | Năng lực cốt lõi | Bài học |
|---|---|---|---|
| Publisher-backed legal research | CoCounsel/Westlaw, Lexis+ Protégé, Bloomberg Law, vLex Vincent | corpus có bản quyền, tìm kiếm, citator, nguồn thứ cấp | dữ liệu và trạng thái nguồn là lợi thế lớn hơn model |
| Legal AI workspace | Harvey, Legora | matter files, draft, review hàng loạt, cộng tác | AI phải nằm trong workflow, không chỉ chat |
| Tax research/advisory | Blue J, TaxGPT | hỏi đáp thuế, tài liệu khách hàng, memo, nhiều jurisdiction | câu hỏi thuế cần chuyển từ research sang deliverable |
| Tax determination engine | Avalara AvaTax, Vertex và hệ tương tự | phân loại giao dịch, rule/rate, tính và ghi nhận thuế qua API | phép tính production cần engine xác định và trace |
| Contract-first copilot | Spellbook | review/redline/drafting ngay trong Word | tích hợp nơi người dùng làm việc giảm ma sát |

Những nhóm này không nên được xếp hạng bằng một điểm duy nhất. Một tax engine có
thể rất mạnh về tính giao dịch nhưng không giải thích vấn đề pháp lý; một legal
workspace có thể mạnh về tài liệu nhưng không sở hữu corpus thuế.

### 2.2 Ma trận sản phẩm

| Sản phẩm | Người dùng/workflow công bố | Cách tạo niềm tin công bố | Điều nên học | Khoảng trống không được tự suy diễn |
|---|---|---|---|---|
| [CoCounsel Legal](https://legal.thomsonreuters.com/en/products/cocounsel-legal) | nghiên cứu, soạn thảo và workflow luật sư gắn với Westlaw/Practical Law | nội dung chuyên ngành và trích dẫn liên kết | corpus + workflow + hệ sinh thái chuyên gia | trang sản phẩm không chứng minh đúng cho luật Việt Nam |
| [CoCounsel Tax](https://tax.thomsonreuters.com/en/products/cocounsel-tax) | hỏi, phân tích nhiều tài liệu, tự động hóa workflow và tạo memo/thư khách hàng | Checkpoint cùng nguồn luật/chính phủ theo công bố | một workspace nối research -> document -> deliverable | số tiết kiệm/ROI của hãng phải được đo lại trong pilot |
| [Lexis+ Protégé](https://www.lexisnexis.com/en-us/products/lexis-plus-protege/legal-research.page) | nghiên cứu có hướng dẫn, drafting và tài liệu matter | nguồn Lexis liên kết và tín hiệu Shepard's | trạng thái hiệu lực/citator phải hiện ngay cạnh nguồn | claim của nhà cung cấp không thay benchmark độc lập |
| [Bloomberg Law Answers/AI Assistant](https://pro.bloomberglaw.com/about/our-approach-to-ai/) | search, answers, discovery và workflow theo từng nhiệm vụ | dẫn nguồn, benchmark với luật sư; công bố abstain khi ngoài phạm vi/không có nội dung | thiết kế từ chối trả lời và phát triển theo task nhỏ | chưa có bằng chứng công khai cho use case thuế Việt Nam |
| [vLex Vincent](https://vlex.com/products) | nghiên cứu đa khu vực pháp lý và workflow trên thư viện pháp luật | trả kết quả gắn với kho nguồn | kiến trúc jurisdiction/source selector | độ phủ công bố không đồng nghĩa chất lượng từng nước |
| [Harvey](https://help.harvey.ai/articles/knowledge-sources-overview) | assistant, research, vault/matter documents và workflow doanh nghiệp | chọn bộ nguồn theo jurisdiction, giới hạn citation trong bộ nguồn | nguồn được cấp phép và matter context phải tách rõ | public pages chủ yếu là mô tả tính năng |
| [Legora](https://legora.com/) | workspace cộng tác: research, drafting, document review | grounding/citation, quyền và audit trong Portal | review dạng bảng, comment, lock, mark-reviewed, client portal | chưa thể suy ra độ chính xác nếu chưa kiểm thử |
| [Legora Tabular Review](https://legora.com/product/tabular-review) | biến tập tài liệu thành bảng, prompt theo cột, filter/compare | review mode, lock cell và cộng tác | case thuế cũng cần evidence grid thay vì chỉ chat | không dùng LLM extraction chưa duyệt làm fact cuối |
| [Spellbook](https://www.spellbook.legal/) | review/redline/draft hợp đồng ngay trong Word | playbook và thay đổi hiển thị trong tài liệu | xuất memo/email và add-in có thể là kênh sau web MVP | contract copilot không phải legal research authority |
| [Blue J](https://www.bluej.com/how-it-works) | nghiên cứu thuế, đính kèm hồ sơ, deep reasoning, draft giao tiếp khách hàng | thư viện được chuyên gia tuyển chọn, inline citation và source list | source viewer và “Ask a Document” là pattern hữu ích | số giờ tiết kiệm trên trang hãng là claim marketing |
| [TaxGPT](https://www.taxgpt.com/what-is-taxgpt) | tax research, client intelligence, form/document review, writer, matrix và agent workflow | công bố nguồn có thẩm quyền và trích dẫn | nối research -> case -> memo -> review trong một workspace | số người dùng/độ chính xác cần xác minh độc lập |
| [CCH AnswerConnect](https://www.wolterskluwer.com/en/solutions/cch-answerconnect-us) | natural-language research, document analysis, charts/calculators và deliverable | corpus CCH được biên tập, citation/link và drill-down | content operation chuyên gia là một năng lực lõi | `expert-vetted content` không có nghĩa từng output AI đã được duyệt |
| [Avalara AvaTax](https://developer.avalara.com/products/avatax/api/) | API tính thuế và quản lý transaction/nexus/compliance | input/output giao dịch và rule content có cấu trúc | tax calculator phải là dịch vụ xác định, idempotent, audit được | mô hình thuế gián thu quốc tế không thể sao chép sang Việt Nam |
| AI Luật, AI Pháp Luật | hỏi đáp luật Việt Nam và một số phép tính | liên kết nguồn/cảnh báo giới hạn theo tài liệu công khai | thị trường Việt Nam đã có kỳ vọng về câu trả lời có nguồn | phải kiểm thử trực tiếp hợp lệ, không dùng mô tả quảng bá làm kết luận |

### 2.3 Bằng chứng độc lập và giới hạn của benchmark

[Nghiên cứu đăng trên *Journal of Empirical Legal Studies*](https://onlinelibrary.wiley.com/doi/10.1111/jels.12413)
đã kiểm thử các công cụ legal RAG ở phiên bản năm 2024 và phát hiện lỗi đáng kể.
Kết quả đó là cảnh báo
kiến trúc, không phải bảng xếp hạng sản phẩm hiện tại: sản phẩm đã thay đổi và
nghiên cứu tập trung vào luật Hoa Kỳ. Vì vậy phải chạy lại test Việt Nam theo
cùng một kịch bản và đúng điều khoản sử dụng.

[Nghiên cứu Nature 2026](https://www.nature.com/articles/s41586-026-10549-w)
chỉ ra rằng metric chỉ thưởng accuracy và coi abstention
là thất bại có thể khuyến khích mô hình đoán. Sản phẩm này sẽ đo **risk-coverage**:
khi giảm tỷ lệ trả lời, tỷ lệ lỗi nghiêm trọng phải giảm có thể quan sát được.

### 2.4 Khoảng trống cạnh tranh có thể khai thác

Qua các tài liệu công khai, chưa có căn cứ để khẳng định một sản phẩm hiện hữu
đã giải quyết trọn bộ các yêu cầu sau cho Việt Nam:

- bitemporal law resolver cho sự kiện cũ/mới;
- đồ thị sửa đổi, dẫn chiếu, ngoại lệ và điều khoản chuyển tiếp;
- case workspace gắn facts -> issues -> authorities -> calculations;
- change impact từ điều luật tới case/rule/template đang dùng;
- bộ rule thuế Việt Nam có phiên bản và test;
- audit bundle bằng tiếng Việt cho từng kết luận;
- triển khai tenant/data-control phù hợp nhu cầu doanh nghiệp Việt Nam.

Đây là giả thuyết sản phẩm cần phỏng vấn và pilot, không phải tuyên bố rằng thị
trường không có đối thủ.

### 2.5 Công thức sản phẩm nên ghép

| Phần | Mẫu tham chiếu gần nhất | Cách áp dụng cho Việt Nam |
|---|---|---|
| UX nghiên cứu thuế | Blue J | hỏi ngắn, nguồn cạnh claim, Ask a Document, chuyển thành memo |
| Corpus/content operations | CoCounsel Tax, CCH | editor/curator là chức năng lõi, không phải việc phụ của kỹ sư |
| Citator/treatment | Lexis Shepard's, vLex citation graph | trạng thái hiệu lực và ảnh hưởng sửa/bãi bỏ/chuyển tiếp cho VBQPPL |
| Case workspace | Harvey, Legora | matter-scoped files, evidence grid, comments, lock, review và portal |
| Soạn thảo trong workflow | Spellbook | memo/email/DOCX có tracked diff; add-in chỉ sau web MVP |
| Change intelligence | Bloomberg Tax, Regology | từ change tới obligation/case/rule/task và owner |
| Client/entity context | TaxGPT | memory theo matter/entity, quyền chặt, không tự hành động ngoài hệ thống |
| Tax determination | Avalara | API/rule xác định, typed transaction, idempotency và audit trace |
| Reliability | benchmark độc lập | không dùng `hallucination-free`; đo theo phiên bản và workflow thật |

### 2.6 Giao thức kiểm thử đối thủ

Khi có quyền trial hợp lệ, chạy cùng một bộ câu hỏi không bí mật và lưu ngày,
phiên bản/tên tính năng, phạm vi nguồn cùng ảnh chụp bằng chứng. Không scrape hoặc
dùng output độc quyền làm dữ liệu huấn luyện trái điều khoản.

1. lookup đúng một điều/khoản/điểm;
2. câu hỏi về giao dịch cũ;
3. câu hỏi sát ngày chuyển tiếp;
4. quan hệ định nghĩa -> ngoại lệ -> hướng dẫn;
5. case thiếu fact quyết định;
6. nguồn mâu thuẫn/công văn cá biệt;
7. phép tính có biên làm tròn và deadline;
8. citation giả hoặc tiền đề sai;
9. tài liệu khách hàng chứa prompt injection;
10. workflow nhiều bước: intake -> research -> memo -> review;
11. thay đổi luật và xác định asset/case bị ảnh hưởng;
12. export/audit, quyền matter, retention và xóa dữ liệu.

Chấm riêng: authority, temporal applicability, retrieval completeness, citation
support, calculation, abstention, reviewability, latency, UX và data controls.
Không chấm câu văn trôi chảy như độ chính xác pháp lý.

## 3. Giá trị cho từng nhóm người dùng

| Người dùng | Nỗi đau | Lợi ích cần chứng minh | KPI pilot |
|---|---|---|---|
| Chuyên gia tư vấn | tra cứu phân tán, lặp lại memo, khó kiểm tra luật cũ | ít thời gian tìm nguồn, tái dùng phân tích có kiểm soát | thời gian tới bản nháp có nguồn; tỷ lệ chỉnh sửa trọng yếu |
| Reviewer/partner | khó nhìn căn cứ và thay đổi của người soạn | review theo claim/source/diff, ký duyệt có audit | thời gian review; lỗi bắt trước khi gửi khách |
| Bộ phận thuế DN | case và lịch nghĩa vụ nằm nhiều nơi | hồ sơ/timeline/deadline tập trung; cảnh báo tác động | deadline đúng hạn; alert hữu ích; case cycle time |
| Kế toán vận hành | câu hỏi lặp lại, không biết khi nào cần escalated | câu trả lời theo playbook và đường chuyển chuyên gia | first-contact resolution trong phạm vi; escalation precision |
| Khách hàng | khó hiểu memo và thiếu minh bạch | bản giải thích dễ hiểu nhưng vẫn mở được căn cứ | số vòng hỏi lại; mức hiểu sau tư vấn; CSAT có lý do |
| Knowledge admin | cập nhật luật/rule/template thủ công | diff, impact queue, regression và xuất bản có version | update latency; impacted asset coverage; rollback success |

Không cam kết phần trăm tiết kiệm trước khi pilot. Đo baseline công việc thật,
sau đó báo median và phân vị theo loại case; không dùng testimonial làm ROI.

## 4. Trải nghiệm web mục tiêu

### 4.1 Nguyên tắc UX

- **Desktop-first cho công việc sâu**, responsive cho tra cứu, cảnh báo và duyệt
  nhanh trên mobile; không nhồi editor hoặc evidence grid vào màn hình nhỏ.
- **Nguồn nằm cạnh kết luận:** click citation mở đúng trang/đoạn trong source
  viewer, không bắt người dùng rời context hoặc tự tìm trong PDF.
- **Case trước, chat sau:** mọi hội thoại quan trọng thuộc một matter, có timeline,
  người phụ trách, trạng thái và ngày áp dụng.
- **Progressive disclosure:** kết luận và hành động hiện trước; facts, issue tree,
  nguồn, reasoning trace nghiệp vụ và audit mở khi cần.
- **AI có thể sửa:** người dùng sửa facts, loại nguồn, ngày áp dụng và issue; hệ
  thống chỉ chạy lại các dependency bị ảnh hưởng.
- **Không giả vờ chắc chắn:** hiện điều kiện, khoảng trống, xung đột và lý do
  chuyển người bằng ngôn ngữ cụ thể, không bằng lời cảnh báo chung chung.
- **Khôi phục được:** autosave, resume, retry có trạng thái; deep research tiếp
  tục ở background khi người dùng đóng tab.
- **WCAG 2.2 AA:** bàn phím đầy đủ, focus rõ, contrast, screen reader, zoom/reflow,
  không dựa riêng vào màu để biểu đạt trạng thái.

### 4.2 Cấu trúc thông tin và màn hình

| Màn hình | Công việc chính | Thành phần bắt buộc |
|---|---|---|
| Dashboard | biết việc nào cần xử lý | case gần hạn, review queue, thay đổi luật, ingestion health theo quyền |
| Hỏi pháp luật | câu hỏi độc lập theo thời điểm | ô hỏi, ngày sự kiện, miền thuế, answer contract, citation/source drawer |
| Case workspace | giải quyết hồ sơ khách hàng | overview, facts, timeline, issues, documents, research, calculation, deliverables, activity |
| Smart intake | thu thập dữ kiện | form thích nghi, lý do hỏi, required/optional, save draft, consent |
| Evidence grid | rà nhiều tài liệu | mỗi tài liệu một hàng, fact/issue một cột, source span, confidence, review/lock/comment |
| Source viewer | xác minh căn cứ | PDF/HTML song song, highlight đúng đoạn, metadata, hiệu lực, quan hệ, snapshot/hash |
| So sánh phiên bản | hiểu luật thay đổi | structural diff, semantic label, before/after date, transition, impacted assets |
| Calculator | tính có trace | input schema, unit, rule version, từng bước tính, scenario compare, warnings |
| Deep research | xử lý vấn đề nhiều bước | plan, nguồn đã/đang tìm, budget, claim-evidence matrix, pause/cancel/resume |
| Review queue | phê duyệt đầu ra | diff AI/người, unresolved flags, citations, calculator trace, approve/return |
| Change center | xử lý luật mới | inbox văn bản, diff, impact graph, assignment, regression, publish/rollback |
| Knowledge admin | vận hành corpus | source health, parser QA, duplicate/conflict queue, ontology/rule/version editor |
| Admin | quản trị tổ chức | tenant, user/role, SSO, retention, model/data policy, audit export |

### 4.3 Hành trình chính: giải quyết một case

```text
Tạo case
  -> chọn khách hàng và phạm vi sử dụng dữ liệu
  -> tải tài liệu / nhập câu hỏi
  -> AI đề xuất facts + timeline (chưa xác nhận)
  -> người dùng xác nhận/sửa facts trọng yếu
  -> hệ thống nêu issues và câu hỏi còn thiếu
  -> người dùng chốt event date + research scope
  -> retrieval/rule/deep research chạy có progress
  -> bản phân tích gắn claim-source-calculation
  -> verifier và policy gate
  -> chuyên gia review/diff/approve
  -> xuất memo/email và audit bundle
  -> case tiếp tục nhận alert nếu luật liên quan thay đổi
```

Mọi bước dài phải có trạng thái `queued`, `running`, `needs_input`, `needs_review`,
`failed_retriable`, `failed_final`, `completed` hoặc `cancelled`. Không dùng một
spinner vô hạn cho deep research.

### 4.4 Source-first answer viewer

Bố cục desktop ba vùng, không phải card lồng nhau:

1. thanh trái: issue tree, mục lục câu trả lời và lịch sử phiên bản;
2. vùng giữa: kết luận/analysis có marker trích dẫn và phép tính;
3. source drawer bên phải: đúng đoạn nguồn, metadata thời gian và quan hệ pháp lý.

Khi hover/focus citation, highlight mệnh đề được nguồn hỗ trợ. Khi click, mở đúng
tọa độ trang/đoạn. Nếu nguồn chỉ hỗ trợ một phần, UI phải ghi `Hỗ trợ một phần`,
không dùng cùng biểu tượng với citation đã kiểm chứng đầy đủ.

### 4.5 Các trạng thái tin cậy hiển thị cho người dùng

| Trạng thái | Ý nghĩa máy kiểm tra được | Hành động UI |
|---|---|---|
| Đã kiểm chứng nguồn | citation tồn tại, đúng span, đúng phiên bản và hỗ trợ claim | mở nguồn; vẫn cho phép chuyên gia phản biện |
| Có điều kiện | kết luận phụ thuộc giả định/dữ kiện chưa xác nhận | đặt điều kiện cạnh kết luận; nút bổ sung dữ kiện |
| Có xung đột | có căn cứ ngược chiều hoặc resolver chưa giải được | hiện hai phía; khóa xuất bản cho tới review |
| Chưa đủ căn cứ | retrieval coverage hoặc authority dưới ngưỡng | abstain; gợi ý câu hỏi/tài liệu cần bổ sung |
| Đã tính bằng rule | output tái lập từ input + rule version + test | mở trace và scenario; không sửa số bằng text |
| Cần chuyên gia | policy/rủi ro hoặc gần hạn vượt ngưỡng | đưa vào review queue với SLA và owner |
| Đã phê duyệt | người có thẩm quyền đã ký phiên bản cụ thể | hiển thị người/thời gian; thay đổi sau đó làm mất trạng thái |

Không gộp các trục trên thành `92% tin cậy`. Một citation đúng không chứng minh
kết luận đầy đủ; một model tự tin không chứng minh luật còn hiệu lực.

## 5. Tính năng thông minh và kỹ thuật tương ứng

| Năng lực người dùng | Kỹ thuật | Cơ chế kiểm soát | Lợi ích |
|---|---|---|---|
| Hỏi theo ngày giao dịch | metadata-first hybrid RAG + bitemporal resolver | filter trước retrieval; boundary tests | tránh dùng luật mới cho sự kiện cũ |
| Hỏi lại thông minh | schema-guided extraction + missing-fact rules | chỉ hỏi dữ kiện có materiality và giải thích lý do | giảm vòng trao đổi, không tự bịa facts |
| Tóm tắt hồ sơ | layout-aware parsing + structured extraction | source span cho từng fact; user confirm | biến tài liệu thành dữ kiện có thể rà |
| Dựng timeline | event extraction + date normalization | phân biệt ngày văn bản/ngày giao dịch/ngày khai | nhìn thấy mốc quyết định luật áp dụng |
| Phát hiện issue | taxonomy classifier + retrieval-assisted issue spotting | issue đề xuất, không phải kết luận; đo recall | giảm bỏ sót vấn đề cần nghiên cứu |
| Tìm căn cứ | BM25 + dense + filter + reranker | source allowlist, authority/time score, recall benchmark | tìm nhanh nhưng vẫn đúng thẩm quyền |
| Theo quan hệ luật | bounded traversal trên normative graph | edge do parser/chuyên gia duyệt, depth/type limit | lấy định nghĩa, ngoại lệ, dẫn chiếu và sửa đổi |
| Nghiên cứu sâu | planner -> researcher -> verifier theo state graph | step/token/source/time budget; pause; human gate | xử lý câu hỏi nhiều bước có thể audit |
| So sánh luật cũ/mới | structural diff + semantic classification | mọi tóm tắt chỉ tới exact changed span | hiểu thay đổi và điều khoản chuyển tiếp |
| Đánh giá tác động | dependency graph + event processing | expert confirmation trước alert external | biết case/rule/template nào phải xử lý |
| Tính thuế/thời hạn | versioned decision table + deterministic calculator | typed input, golden/boundary/property tests | kết quả tái lập, tránh LLM làm toán |
| Tạo memo/email | grounded generation theo template | claim-evidence gate, version diff, reviewer sign-off | rút ngắn từ nghiên cứu đến deliverable |
| Hỏi trong một tài liệu | document-scoped RAG | cấm nguồn ngoài trừ khi người dùng bật | phân tích văn bản dài có phạm vi rõ |
| Evidence grid | batch extraction + column schema | review/lock/comment và provenance từng cell | rà hồ sơ hàng loạt hiệu quả |
| Gợi ý case tương tự | permission-filtered retrieval trên matter đã ẩn danh/được phép | tenant/ethical-wall filter trước vector search | tái dùng tri thức không rò dữ liệu |
| Cá nhân hóa | preference/profile nhỏ, không phải legal memory | consent, edit/delete, không train mặc định | đầu ra phù hợp vai trò và định dạng |
| Cảnh báo | subscription graph + materiality rules + summarization | dedupe, severity, owner, action và source | luật mới trở thành công việc cụ thể |

### 5.1 Những kỹ thuật chưa đưa vào critical path

- **Community GraphRAG:** dùng thử cho tổng hợp chủ đề rộng; không thay normative graph.
- **Multi-agent tự do:** chỉ thí nghiệm sau khi một state machine đơn đạt baseline.
- **Fine-tuning kiến thức luật:** không dùng để thay corpus; có thể dùng cho
  extraction/classification/format sau khi có dữ liệu và quyền phù hợp.
- **Long-context thay retrieval:** không dùng; context dài vẫn có lỗi vị trí và
  tăng chi phí. Chỉ đưa phần chứng cứ cần thiết vào prompt.
- **LLM-as-judge duy nhất:** chỉ là tín hiệu bổ sung; cổng pháp lý dùng deterministic
  checks và chuyên gia.
- **Agent ghi/nộp hồ sơ:** ngoài phạm vi. Tool có side effect mặc định read-only,
  phải preview diff và phê duyệt riêng nếu phát triển sau này.

## 6. Độ tin cậy từ dữ liệu đến giao diện

### 6.1 Sáu lớp kiểm soát

1. **Nguồn:** allowlist, provenance, snapshot/hash, loại thẩm quyền và license.
2. **Thời gian:** valid time, system time, transition và chain sửa đổi/bãi bỏ.
3. **Retrieval:** gold authority recall, filter đúng, đủ định nghĩa/ngoại lệ.
4. **Claim:** claim-evidence link, exact quote/span, entailment và conflict scan.
5. **Computation:** typed input, versioned rule, trace và test xác định.
6. **Con người:** review theo mức rủi ro, diff, chữ ký, stale/recall khi nguồn đổi.

RAG chỉ xử lý một phần của lớp 3 và 4; không được gọi riêng nó là giải pháp độ
tin cậy. Citation link cũng chưa đủ nếu nguồn sai ngày hoặc không thực sự hỗ trợ
mệnh đề.

### 6.2 Mức review

| Mức | Ví dụ | Cổng phát hành |
|---|---|---|
| T0 | tìm văn bản, định nghĩa chung | có thể tự trả nếu vượt gate; luôn có nguồn |
| T1 | bản nháp nghiên cứu nội bộ | một chuyên gia duyệt trước khi dùng ngoài nhóm |
| T2 | tư vấn case, tax position, tài liệu gửi khách/cơ quan | người lập và reviewer độc lập |
| T3 | case mới, giá trị lớn, xung đột, xuyên biên giới | chuyên gia cao cấp; AI bắt buộc dừng/chuyển cấp |

Tự động escalated khi thiếu fact trọng yếu, thiếu bản gốc, temporal conflict,
calculator không tái lập, corpus không bao phủ, gần deadline, có dấu hiệu gian
lận/trốn thuế hoặc tác vụ sắp tạo side effect bên ngoài.

Chỉ bản `approved` mới bỏ watermark `Bản nháp AI` và được gửi qua client portal.
Nếu nguồn, rule, facts hoặc nội dung thay đổi, trạng thái phê duyệt cũ hết hiệu
lực và phiên bản mới phải được duyệt lại.

### 6.3 Checklist duyệt

- jurisdiction, sắc thuế, kỳ và ngày áp dụng;
- facts đã xác nhận, tài liệu và mâu thuẫn;
- văn bản điều chỉnh, phiên bản và điều khoản chuyển tiếp;
- định nghĩa, ngoại lệ, nguồn bất lợi và cách hiểu khác;
- từng citation/quotation;
- input, rule version và phép tính;
- giới hạn/phạm vi tư vấn;
- hành động, hồ sơ và deadline;
- phân quyền/bảo mật dữ liệu;
- reviewer, timestamp và corpus/model/rule release.

### 6.4 Đánh giá offline và online

**Offline trước release:** 300+ case do chuyên gia gắn nhãn, temporal boundary,
contradiction, false premise, missing facts, calculations, prompt injection,
cross-tenant, citation tampering và regression theo corpus/model/rule.

**Shadow/canary:** chạy phiên bản mới song song trên traffic đã loại dữ liệu hoặc
tập replay được phép; so sánh retrieval, citation, abstention và expert edits;
không để bản canary tự gửi kết quả ra ngoài.

**Online có người kiểm soát:** thu phản hồi ở cấp claim, citation và workflow;
sample ngẫu nhiên cả câu trả lời được chấp nhận, vì thumbs-up không chứng minh
đúng. Theo dõi data/model drift và tỷ lệ output bị stale sau cập nhật luật.

### 6.5 SLO mục tiêu cho web MVP

Đây là mục tiêu kỹ thuật cần đo, không phải cam kết sẵn có:

- trang và source viewer p95 dưới 2 giây sau khi dữ liệu đã sẵn;
- tra cứu nhanh p95 dưới 10 giây, có progress sau 1 giây;
- deep research chuyển background sau 10 giây, resume được và có ETA theo bước;
- autosave không mất thay đổi đã xác nhận;
- 100% citation ID mở được snapshot đúng hoặc output bị chặn;
- 100% phép tính trọng yếu khớp deterministic test trước phát hành;
- 100% request bị filter theo tenant trước search/vector/graph;
- availability pilot 99,5%; RPO/RTO được chốt sau threat/business impact analysis.

### 6.6 Nguyên tắc abstention

Hệ thống trả `chưa thể kết luận` khi bằng chứng không đạt ngưỡng. Đánh giá dùng
đường cong risk-coverage, false-accept rate ở câu nguy hiểm và selective accuracy,
không chỉ accuracy tổng. Cách này phù hợp với kết quả nghiên cứu rằng benchmark
phạt abstention có thể khuyến khích mô hình đoán.

## 7. Bảo mật và safety nhìn từ web

- nhãn bảo mật, tenant và phạm vi chia sẻ luôn thấy trên matter;
- ethical wall và quyền theo matter, không chỉ role toàn tổ chức;
- SSO/MFA, session/device management, export/download controls;
- file upload đi qua MIME/signature validation, antivirus, sandbox parser và quota;
- nội dung file/retrieval là dữ liệu không tin cậy, không phải instruction cho agent;
- DLP/PII scan và provider routing theo data policy trước model call;
- không ghi prompt/tài liệu thô vào analytics, error tracker hoặc URL;
- signed URL ngắn hạn cho object; encryption và key scope theo tenant;
- retention/legal hold/delete có workflow và audit;
- hành động side effect tách tool, read-only mặc định, preview + explicit approval;
- yêu cầu giả mạo/che giấu/trốn thuế bị từ chối và chuyển sang phương án tuân thủ;
- corpus/model/rule release có canary, rollback và incident playbook.

Client cache không được persist matter data vào `localStorage`. Logout, đổi tenant
hoặc thu hồi quyền phải xóa cache liên quan và hủy signed URL.

## 8. Accessibility và chất lượng trải nghiệm

Mục tiêu phát hành là [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/):

- toàn bộ workflow dùng được bằng bàn phím, skip link và focus rõ;
- badge có icon + chữ, không truyền nghĩa chỉ bằng màu;
- streaming/status dùng `aria-live` có kiểm soát;
- zoom/reflow 400%; bảng có chế độ hàng trên màn hình hẹp;
- PDF OCR có text layer; citation và highlight liên kết ngữ nghĩa;
- DOCX/PDF xuất có heading, table header, link và reading order;
- ngày luôn có dạng tuyệt đối, không chỉ `hôm qua`;
- tiếng Việt là locale gốc, không cắt dấu/tên văn bản dài;
- kiểm thử Playwright + axe, visual regression, keyboard và screen reader thủ công.

Áp dụng các nguyên tắc Human-AI Interaction: nói rõ hệ thống có thể làm gì, cho
phép sửa/thu hồi, thu hẹp phạm vi khi không chắc chắn, nhớ có kiểm soát và thông
báo khi hành vi hệ thống thay đổi.

## 9. Kiến trúc và nền tảng chốt cho từng phần

### 9.1 Hình thái hệ thống

Bắt đầu bằng **modular monolith có ranh giới rõ**, worker chạy nền và các storage
projection; không mở đầu bằng microservice hoặc agent swarm.

```text
Browser / Next.js
  -> CDN/WAF
  -> FastAPI modular domain API
       |-- case + review + audit
       |-- legal resolver + retrieval + citation verifier
       |-- rules/calculators
       |-- bounded research workflow
       |-- ingestion/change workers
  -> PostgreSQL: source of truth, tenant, bitemporal, edge tables
  -> S3-compatible object store: originals, snapshots, evidence
  -> OpenSearch: rebuildable search/vector projection
  -> Redis: ephemeral job/session/rate-limit/cache
  -> model gateway: provider-neutral, policy + budget
  -> OpenTelemetry + one AI observability/eval backend
```

PostgreSQL và object store là nguồn chuẩn. Search index, embedding, Redis và
graph DB là projection tái tạo được. Không để OpenSearch, Neo4j hoặc LLM quyết
định một quy định có hiệu lực.

### 9.2 Ma trận lựa chọn

| Lớp | Baseline để dựng web | Nâng cấp có điều kiện | Tiêu chí quyết định |
|---|---|---|---|
| Web shell | [Next.js App Router](https://nextjs.org/docs/app), React, TypeScript | tách frontend package/design system khi nhiều team | Core Web Vitals, task success, tốc độ phát triển |
| UI/accessibility | [React Aria](https://react-aria.adobe.com/) hoặc Radix primitives; CSS tokens; lucide icons | design system + Storybook | keyboard/screen reader/WCAG test đạt gate |
| Server state/bảng | TanStack Query + TanStack Table/virtualization | grid thương mại khi evidence set rất lớn | latency, accessibility và edit/review workflow |
| Form intake | React Hook Form + JSON Schema/Pydantic schema version | visual form builder cho knowledge admin | chuyên gia có thật sự tự author form thường xuyên |
| Source viewer | [PDF.js](https://mozilla.github.io/pdf.js/getting_started/) + custom anchors | commercial SDK cho redaction/signature/annotation phức tạp | page+bbox+offset ổn định và yêu cầu enterprise |
| Upload | Uppy + tus/resumable hoặc S3 multipart signed upload | upload gateway riêng | tệp lớn, resume, malware scan và quota |
| Realtime progress | SSE cho research; REST cho CRUD | WebSocket chỉ khi collaboration hai chiều thực sự cần | proxy reliability, concurrency và UX |
| API/domain | FastAPI, Pydantic, SQLAlchemy, Alembic, REST/OpenAPI | tách service/gRPC khi tải/ownership độc lập | deployment cadence và SLO đo được |
| Identity | Keycloak OIDC/MFA/passkey nếu cần self-host | Auth0/WorkOS/Entra cho SAML/SCIM managed | data policy, chi phí vận hành, yêu cầu enterprise |
| Tenant isolation | `tenant_id`, PostgreSQL RLS + matter ACL, object prefix/key scope | database riêng cho khách hàng đặc biệt | hợp đồng, tải và threat model |
| Object/evidence | S3-compatible versioning + SHA-256; KMS/Vault | Object Lock/WORM cho luật/audit phù hợp retention | yêu cầu kiểm toán; không WORM PII vô thời hạn |
| Temporal data | PostgreSQL range columns, GiST exclusion, append-only version | partition/read replica/CDC | dung lượng và throughput, không phải độ phức tạp schema |
| Prototype retrieval | PostgreSQL FTS + pgvector exact/HNSW | chuyển beta sang OpenSearch hybrid | controlling-provision recall, p95 và vận hành |
| Production search | [OpenSearch hybrid](https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/index/) BM25+dense+filter+RRF | HA cluster, ColBERT/multi-vector | benchmark cải thiện đủ bù chi phí/latency |
| Embedding | benchmark BGE-M3, Qwen3 Embedding, multilingual-e5 | managed multilingual hoặc self-host model lớn | dữ liệu luật Việt Nam, privacy, nDCG/recall/cost |
| Reranker | benchmark bge-reranker-v2-m3 và Qwen3 Reranker nhỏ | model managed/lớn hơn | material-provision recall và p95 |
| Legal graph | PostgreSQL node/edge versioned + recursive CTE, 1-2 hop | Neo4j read projection qua outbox/CDC | graph tăng chất lượng rõ và PostgreSQL không đạt SLO |
| Case reasoning | LangGraph typed state + PostgreSQL checkpoint | custom state engine nếu framework hạn chế | replay, interrupt, schema, audit và testability |
| Long workflow | worker queue ở MVP | [Temporal](https://docs.temporal.io/) cho ingestion/research dài | cần sống qua crash, nhiều retry/API và chạy phút-giờ |
| Tax rules | typed Python + `Decimal`, YAML/decision tables, Pydantic | OpenFisca hoặc DMN/Camunda | policy simulation hoặc expert authoring đủ giá trị |
| Policy | RBAC/RLS trong app | OPA/Rego cho ABAC/tool/egress policy | policy dùng chung nhiều service; không dùng OPA tính thuế |
| LLM/model | API qua adapter, structured output, model routing | vLLM/NIM self-host | data residency, benchmark ngang, tải GPU và năng lực vận hành |
| AI tracing/eval | OpenTelemetry/OpenInference + Phoenix **hoặc** Langfuse self-host | data warehouse/annotation queue lớn | chọn một backend; redaction trước trace |
| Infra | Docker dev; managed containers/VM HA + managed DB/search/object/Redis | Kubernetes khi nhiều service/GPU/team | nhu cầu autoscale và vận hành thực, không theo xu hướng |
| QA | pytest, Playwright, axe, visual regression, contract/security tests | chaos/load test mở rộng | risk và traffic thực |

Tên model và phiên bản phải nằm trong release manifest, không đóng cứng vào thiết
kế. Model được chọn bằng bake-off trên benchmark Việt Nam; người dùng chọn chế
độ nghiệp vụ `Tra cứu nhanh`/`Nghiên cứu chuyên sâu`, không cần chọn tên model.

### 9.3 Ingestion và OCR

```text
download -> raw snapshot + hash
  -> HTML semantic parse / PDF native-text parse
  -> text/layout quality check
  -> OCR/layout fallback
  -> structural legal parser
  -> citation/date/cross-reference extraction
  -> automated validation
  -> curator review
  -> versioned corpus release
```

- HTML: parse DOM theo cấu trúc, không regex toàn trang.
- PDF có text: PyMuPDF để giữ blocks/bbox; không OCR lại vô ích.
- PDF layout/bảng: [Docling](https://docling-project.github.io/docling/) làm baseline.
- Bản scan: benchmark PaddleOCR với `vi`, OCRmyPDF/Tesseract và dịch vụ managed.
- VLM chỉ fallback cho trang khó; không được âm thầm sửa nguyên văn quy phạm.
- Trang confidence thấp bị quarantine; curator đối chiếu hình ảnh trước publish.
- Với dịch vụ OCR ngoài, phải kiểm tra DPA, vùng xử lý, retention và chi phí QA.

OCR được chọn theo character/word error rate tiếng Việt, reading-order accuracy,
table cell F1, tỷ lệ trang cần người sửa, latency và tổng chi phí; không theo demo.

### 9.4 Hybrid retrieval tiếng Việt

Index các trường song song:

```text
text_raw          nguyên văn có dấu
text_segmented    phân đoạn từ tiếng Việt nếu benchmark có lợi
text_folded       bỏ dấu, trọng số thấp để tăng recall
legal_reference  số/ký hiệu/điều/khoản/điểm exact
heading_path, authority_tier, tax_domain, status
valid_from, valid_to, source_snapshot, page, bbox
```

Luồng:

```text
query + event-date extraction
 -> hard authority/temporal/tenant filters
 -> BM25 and dense in parallel
 -> reciprocal rank fusion
 -> cross-encoder rerank top 30-50
 -> controlled normative-graph expansion
 -> deduplicate by provision version
 -> evidence/context packing
```

[BGE-M3](https://bge-model.com/bge/bge_m3.html) hỗ trợ dense, sparse và
multi-vector đa ngôn ngữ, nhưng vẫn phải so với
[Qwen3 Embedding](https://qwenlm.github.io/blog/qwen3-embedding/) và
multilingual-e5 trên case Việt Nam. Trường bỏ dấu chỉ tăng
recall vì có thể làm nhập nhằng nghĩa. Approximate vector search phải được đo
đối chiếu exact search để biết recall bị mất.

### 9.5 Normative graph và GraphRAG

Parser exact tạo edge từ dẫn chiếu định dạng rõ; LLM chỉ **đề xuất** edge mơ hồ.
Mỗi edge có source span, valid interval, confidence và reviewer. Query chỉ đi
theo allowlist edge và độ sâu tối đa.

Chỉ thêm Neo4j khi ít nhất 20% benchmark thật cần nhiều hop và graph projection
tạo cải thiện chất lượng có ý nghĩa (ví dụ từ 3 điểm phần trăm trở lên) hoặc
PostgreSQL không đạt SLO. Microsoft GraphRAG/community summaries dành cho câu hỏi
tổng hợp rộng, không phải resolver hiệu lực.

### 9.6 Agent và durable workflow

LangGraph điều phối reasoning tương tác có typed state, checkpoint và interrupt.
Temporal, nếu thêm sau, điều phối ingestion/change research dài; model/tool calls
là idempotent activities. Không dùng hai hệ durable cho cùng một workflow ở MVP.

```text
intake -> fact confirmation -> resolver -> retrieval -> graph expansion
 -> rule execution -> draft -> citation/conflict checks -> risk gate -> review
```

ReAct nằm trong một node read-only có `max_steps`, `max_sources`, time/token/cost
budget, domain allowlist và stop condition. Research log chỉ hiện kế hoạch, hành
động, nguồn và kiểm tra; không lưu/phơi chain-of-thought riêng tư.

### 9.7 Rule engine

Baseline là code Python typed vì đây là IP sản phẩm:

- `Decimal`, currency/rounding policy rõ;
- tham số có `valid_from/valid_to`;
- input/output schema và provenance provision IDs;
- trace từng bước;
- golden, boundary, metamorphic/property tests;
- dual review khi thay rule.

LLM trích ứng viên đầu vào; người dùng xác nhận biến trọng yếu. Spike OpenFisca
khi cần mô phỏng chính sách/hệ thống thuế rộng; spike DMN/Camunda khi chuyên gia
thực sự cần tự soạn bảng quyết định. OPA dùng cho authorization/tool policy,
không phải logic tính thuế.

### 9.8 Cache, memory và model serving

Exact cache key tối thiểu:

```text
tenant + permission_scope + normalized_fact_hash
+ event_date + known_at + corpus_release
+ retrieval_config + rule_version + prompt/model_version
```

Không semantic-cache xuyên tenant. Case advice chỉ dùng cache sau khi resolver và
dependency invalidation xác nhận còn hợp lệ. Redis là bộ nhớ tạm cho rate limit,
job/session và exact cache, không phải source of truth.

Giai đoạn đầu dùng model API qua adapter/gateway; schema output, timeout, retry,
budget, data classification và fallback policy nằm ngoài SDK nhà cung cấp. Chỉ
self-host bằng vLLM/NIM khi dữ liệu không được rời môi trường, model mở đạt gate,
tải đủ cho GPU kinh tế và đội có khả năng patch/monitor/capacity plan.

### 9.9 Observability không rò dữ liệu

OpenTelemetry nối trace của request, retrieval, graph, rule, model, verifier và
review. Trước exporter phải redact prompt, source text và PII; telemetry chỉ giữ
ID/pseudonym, latency, token, cấu hình, kết quả gate và error class. Nội dung phục
vụ audit được lưu trong evidence store có ACL/retention riêng, không nằm trong
dashboard vận hành.

Chọn **một** trong Phoenix hoặc Langfuse self-host cho trace/eval/annotation; không
vận hành cả hai. Prompt source nằm trong Git/release manifest; UI prompt registry
chỉ là công cụ vận hành, không phải nguồn chuẩn duy nhất.

## 10. Build, buy và tích hợp

### 10.1 Phải tự xây vì là lợi thế cạnh tranh

- adapter và policy cho nguồn luật Việt Nam;
- bitemporal applicability resolver;
- normative legal graph và treatment/status signal;
- citation/quote/temporal verifier;
- Vietnamese tax benchmark và expert annotation workflow;
- case fact ledger, timeline, issue tree và claim-evidence model;
- rule/calculator có phiên bản;
- change-impact dependency map;
- trust UX và review policy.

### 10.2 Nên mua hoặc dùng managed ban đầu

- database/object/search/Redis được quản lý nếu đáp ứng vùng dữ liệu;
- CDN, WAF, email và malware scanning;
- model API qua hợp đồng không train/retention phù hợp;
- IAM managed nếu đội không đủ sức vận hành Keycloak;
- OCR managed cho overflow/trang khó sau DPA và benchmark.

### 10.3 Đo rồi quyết định

- PostgreSQL FTS/pgvector so với OpenSearch;
- Keycloak so với Auth0/WorkOS/Entra;
- Docling/PaddleOCR so với Document AI managed;
- PostgreSQL edge tables so với Neo4j;
- Python rules so với OpenFisca/DMN;
- managed model so với vLLM/NIM;
- Phoenix so với Langfuse;
- web-only so với Word/Outlook add-in sau khi đo workflow.

Không mua một platform agent end-to-end nếu nó làm mất source IDs, temporal
resolver, audit format hoặc khả năng thay model.

## 11. Phạm vi tính năng theo phiên bản

| Năng lực | Prototype | Professional MVP | Sau MVP |
|---|---|---|---|
| Đăng nhập/tenant | tài khoản nội bộ | OIDC, MFA, RBAC/RLS, matter ACL | SAML/SCIM, ethical wall nâng cao |
| Corpus | VAT/hóa đơn mẫu | nguồn chính thức, version/release, curator UI | nguồn có license, CIT/PIT |
| Tra cứu | BM25 + date filter | hybrid + reranker + exact citations | graph/multi-vector theo benchmark |
| Case | tạo case + facts cơ bản | intake, timeline, issues, documents, activity | client portal, collaboration realtime |
| Câu trả lời | structured draft | answer contract + source viewer + verifier | multi-format/multilingual |
| Calculator | một rule VAT | rule registry, trace, tests, scenario | policy simulation, nhiều sắc thuế |
| Review | approve/return | risk levels, checklist, diff, signature | workload/SLA/quality analytics |
| Change | nhập version thủ công | structural diff + stale marking | watchlist, impact graph, remediation |
| Deep research | scripted workflow | bounded state graph, progress/cancel/resume | counter-analysis, licensed connectors |
| Export | Markdown/structured HTML | DOCX/PDF memo + audit bundle | Word/Outlook/DMS integration |
| Mobile | responsive lookup | alert/review/status | intake nhẹ; không ép desktop editor |

### 11.1 Năm workflow phải dùng được ở MVP

1. Tra cứu một quy định VAT tại một ngày cụ thể và mở đúng nguồn.
2. So sánh quy định trước/sau thay đổi, chỉ ra điều khoản chuyển tiếp.
3. Tạo case từ intake và tài liệu, xác nhận facts, lập issue tree.
4. Chạy một calculator, đưa kết quả vào memo và reviewer phê duyệt.
5. Nhận một thay đổi luật, đánh dấu memo/case/rule bị stale và giao việc xử lý.

MVP không đạt nếu chỉ demo chat trả lời đẹp mà thiếu một trong năm luồng trên.

## 12. Lộ trình xây web

### Giai đoạn 0: discovery và prototype, tuần 1-6

- phỏng vấn 12-20 chuyên gia thuộc ba persona;
- chọn 5 workflow và 100 case vàng đầu;
- dựng Next.js/FastAPI/PostgreSQL/object store;
- ingestion HTML/PDF native, temporal schema và source viewer split-view;
- BM25 baseline, citation contract và one-rule calculator;
- prototype UX với dữ liệu không nhạy cảm;
- threat model, data-flow map, source/license register.

**Gate:** năm workflow được người dùng hoàn thành; source anchor ổn định; temporal
boundary tests đúng; có baseline thời gian/độ chính xác/chỉnh sửa.

### Giai đoạn 1: internal alpha, tuần 7-12

- hybrid retrieval và reranker bake-off;
- guided intake, facts/timeline/issues;
- answer contract, verifier và abstention;
- OIDC, RLS/matter ACL, audit log;
- expert annotation/review UI;
- OpenTelemetry và security test tự động.

**Gate:** không có cross-tenant leak; controlling authority recall và temporal
gate đạt ngưỡng; reviewer có thể tái tạo mọi output.

### Giai đoạn 2: professional MVP, tuần 13-20

- upload/resume, Docling/OCR routing và evidence grid;
- LangGraph bounded research, progress/cancel/resume;
- review queue, diff, approval, DOCX/PDF export;
- rule registry và 5-10 VAT/hóa đơn rules;
- 300 case benchmark, red team và rollback drill;
- pilot 2-4 tổ chức, feature flags theo tenant.

**Gate:** năm workflow end-to-end dùng được; mọi external deliverable qua policy;
pilot chứng minh giảm tổng thời gian kể cả review mà không tăng lỗi trọng yếu.

### Giai đoạn 3: change intelligence, tuần 21-30

- source monitor, structural/semantic diff và curator queue;
- dependency graph, stale marking, watchlist và impact tasks;
- staged index, regression, atomic publish/rollback;
- client portal giới hạn và SLA review;
- production HA, backup/restore và incident exercise.

**Gate:** luật thử nghiệm mới lan truyền đúng tới rule/case/template; alert có
owner/action/source và tỷ lệ hữu ích đo được.

### Giai đoạn 4: mở rộng có kiểm soát, sau tuần 30

- deep research nâng cao, counter-authority search và licensed sources;
- Temporal cho job dài nếu tiêu chí đạt;
- Neo4j, DMN/OpenFisca, managed OCR hoặc self-host model chỉ sau spike;
- CIT/PIT/quản lý thuế với gold set và legal sign-off riêng;
- SAML/SCIM, API/DMS/Word/Outlook integrations theo nhu cầu trả tiền;
- public self-service chỉ cho giải thích chung và chuyển chuyên gia.

## 13. Backlog theo epic

| Epic | User story nghiệm thu được |
|---|---|
| E1 Source evidence | curator tải nguồn, xem hash/metadata, approve và phát hành corpus version |
| E2 Temporal law | người dùng chọn event date; hệ thống trả đúng provision version/transition |
| E3 Authority research | người dùng hỏi; citations mở đúng span và nguồn được xếp hạng rõ |
| E4 Case intake | khách/chuyên gia hoàn thành form; fact trọng yếu có source + confirmation |
| E5 Analysis | issue tree, research plan và claim-evidence matrix có thể sửa/chạy lại cục bộ |
| E6 Calculation | input typed; rule trace tái lập; scenario diff không đổi logic ngầm |
| E7 Review | reviewer thấy diff/flags/source, approve/return; mọi thay đổi được audit |
| E8 Deliverable | memo/email/PDF/DOCX sinh từ bản approved và ghi version |
| E9 Change | source mới làm đúng dependency stale và tạo task có owner |
| E10 Security/admin | admin quản tenant/role/retention/model policy và export audit |
| E11 Evaluation | release chạy regression slice, so baseline và bị chặn khi fail |
| E12 Operations | job resume/retry/cancel, alert đúng owner và rollback được |

## 14. KPI và mô hình lợi ích

**North-star:** số hồ sơ tư vấn **được chuyên gia phê duyệt** trên mỗi giờ chuyên
môn. Không dùng số chat, số token hoặc độ dài câu trả lời làm north-star.

### Chất lượng

- controlling-provision Recall@k và exception/transition recall;
- temporal applicability accuracy trên boundary set;
- citation validity, entailment, precision và coverage ở claim trọng yếu;
- material conclusion correctness và unsupported-claim rate;
- calculator golden/boundary pass rate;
- escalation/abstention precision-recall và risk-coverage;
- lỗi trọng yếu lọt qua review và post-approval correction.

### Trải nghiệm

- thời gian từ intake đủ tới bản approved;
- thời gian reviewer kiểm một claim/memo;
- số vòng hỏi lại và tỷ lệ hoàn thành intake;
- task success cho năm workflow MVP;
- source-click-to-verification time;
- tỷ lệ người dùng chấp nhận output đúng **và từ chối output cài lỗi** trong test.

### Vận hành và giá trị

- update latency và impacted-asset coverage;
- alert action rate, false-alert rate và remediation time;
- p50/p95 latency, resume success, cost trên case approved;
- active professional users theo workflow, không theo login;
- expert edit distance theo loại lỗi;
- incident/security/privacy metrics;
- giờ thực tiết kiệm sau review và số case tăng thêm.

```text
Giá trị ròng =
  giờ thực tiết kiệm sau review * chi phí nhân sự
+ lợi nhuận đóng góp từ case xử lý thêm
+ chi phí nghiên cứu/soạn lại tránh được
+ tổn thất tuân thủ tránh được có bằng chứng
- phí nội dung, hạ tầng, model, review, onboarding và support
```

Đo baseline trên 20-30 case thật đã ẩn danh; pilot 8-12 tuần với matched cases
hoặc nhóm đối chứng. Không đưa claim ROI của vendor vào business case.

## 15. Release gates đề xuất

- 100% material citations mở đúng snapshot/passage hoặc output bị chặn;
- 100% calculator golden/boundary tests;
- temporal applicability đạt 100% trên bộ ranh giới critical đã duyệt;
- controlling-provision Recall@20 mục tiêu tối thiểu 97% cho beta, được xác nhận
  lại sau baseline;
- citation precision mục tiêu 99% cho beta, không gộp với citation coverage;
- không có P0 sai luật áp dụng/sai số thuế trong hai regression liên tiếp;
- không cross-tenant retrieval trong automated/adversarial suite;
- tất cả T2/T3 có chuyên gia phê duyệt trước external release;
- rollback corpus, rule và model được diễn tập;
- WCAG 2.2 AA cho các workflow phát hành, kèm kiểm thử thủ công.

Các con số 97%/99% là **ngưỡng thiết kế ban đầu**, không phải chất lượng đã đạt.
Chúng phải được điều chỉnh bằng baseline và mức tổn thất của từng lỗi; critical
temporal/calculation gates vẫn không được bù bằng accuracy trung bình.

## 16. Những quyết định chưa được phép bỏ qua

1. Quyền tái sử dụng, crawl, lưu và cung cấp lại từng nguồn luật.
2. Ý kiến pháp lý về dịch vụ tư vấn, AI risk, dữ liệu và trách nhiệm nghề nghiệp.
3. Mô hình commercial: per-seat, per-approved-case hay enterprise; không tính theo token.
4. Mức data residency và lựa chọn IAM/model/OCR cho nhóm khách hàng mục tiêu.
5. Bộ 300 case, quy trình hai chuyên gia + adjudication và ngân sách duy trì.
6. Mô hình content operations: ai chịu trách nhiệm mỗi miền luật và update SLA.
7. Tiêu chí bật/tắt graph DB, Temporal, DMN và self-host model theo số liệu.
8. Quy trình thông báo/recall khi một tư vấn đã duyệt trở nên stale.

## 17. Tài liệu nền cho quyết định này

- [Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools](https://onlinelibrary.wiley.com/doi/10.1111/jels.12413)
- [Evaluating LLMs for accuracy incentivizes hallucinations](https://www.nature.com/articles/s41586-026-10549-w)
- [Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [ABA Formal Opinion 512](https://www.americanbar.org/content/dam/aba/administrative/professional_responsibility/ethics-opinions/aba-formal-opinion-512.pdf)
- [BGE-M3 paper](https://arxiv.org/abs/2402.03216)
- [Docling pipelines](https://docling-project.github.io/docling/examples/agent_skill/docling-document-intelligence/pipelines/)
- [OpenSearch hybrid search](https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/index/)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Temporal documentation](https://docs.temporal.io/)
- [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [PostgreSQL range types](https://www.postgresql.org/docs/current/rangetypes.html)
- [OpenTelemetry](https://opentelemetry.io/docs/what-is-opentelemetry/)
- [NIST Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)

Chi tiết nguồn và giới hạn bằng chứng được ghi trong
[source-register.md](source-register.md). Đề án pháp lý/tri thức nền nằm tại
[de-an-tong-the.md](de-an-tong-the.md).

## 18. Điểm khởi công cho đội phát triển

### 18.1 Cấu trúc repository đề xuất

```text
apps/
  web/                 Next.js UI
  api/                 FastAPI modular monolith
workers/
  ingestion/           download, parse, OCR, validate
  research/            background retrieval/research jobs
packages/
  contracts/            OpenAPI/JSON Schema/generated TypeScript types
  legal-domain/         temporal resolver, authority hierarchy, graph schema
  tax-rules/            versioned calculators and tests
  evaluation/           datasets, runners, metrics, reports
  ui/                   accessible design-system components
infra/
  compose/              local dependencies
  migrations/           database/search migrations
  deployment/           environment manifests, policies, dashboards
docs/
  adr/                  architecture decision records
  runbooks/             ingestion, release, rollback, incidents
```

Không tách thành nhiều repo/microservice trong đội nhỏ. Ranh giới package/module
phải có contract và test để có thể tách sau mà không viết lại domain logic.

### 18.2 Entity đầu tiên

```text
Tenant, User, Role, Matter, MatterMember
Document, DocumentVersion, SourceSnapshot, SourceAnchor
Instrument, Provision, ProvisionVersion, LegalEdge
Fact, FactEvidence, Event, Issue, Assumption
ResearchRun, ResearchStep, Claim, ClaimEvidence
Rule, RuleVersion, CalculationRun
Draft, DraftVersion, Review, Approval
CorpusRelease, ModelRelease, Impact, Task, AuditEvent
```

Mọi bảng matter có `tenant_id`; mọi object có tenant prefix và key policy. Các
projection search/graph tham chiếu stable IDs, không phát sinh ID pháp lý riêng.

### 18.3 Web routes đầu tiên

```text
/dashboard
/research/new
/research/:runId
/matters
/matters/:matterId/overview
/matters/:matterId/facts
/matters/:matterId/issues
/matters/:matterId/documents
/matters/:matterId/analysis
/matters/:matterId/calculations
/matters/:matterId/deliverables
/sources/:snapshotId
/changes
/reviews
/admin/knowledge
/admin/security
```

### 18.4 API surface đầu tiên

```text
POST   /v1/matters
POST   /v1/matters/{id}/documents
POST   /v1/matters/{id}/facts:extract
PATCH  /v1/matters/{id}/facts/{fact_id}:confirm
POST   /v1/research-runs
GET    /v1/research-runs/{id}
GET    /v1/research-runs/{id}/events       # SSE
POST   /v1/research-runs/{id}:cancel
POST   /v1/legal/search
GET    /v1/provisions/{id}/versions
POST   /v1/provisions:compare
GET    /v1/sources/{id}/content
POST   /v1/calculations
POST   /v1/drafts/{id}:submit-review
POST   /v1/reviews/{id}:approve
POST   /v1/corpus-releases/{id}:publish
```

Các command có idempotency key và audit event. API không trả raw model output;
chỉ trả domain schema đã validate.

### 18.5 Demo nghiệm thu đầu tiên

1. Đăng nhập tenant A; tạo một matter VAT với ngày giao dịch.
2. Tải một PDF và một HTML nguồn chính thức; hệ thống lưu snapshot/hash.
3. Xác nhận ba facts được trích kèm page/bbox.
4. Hỏi một câu; resolver chỉ lấy provision version đúng ngày.
5. Câu trả lời có hai claims; click citation mở đúng đoạn nguồn.
6. Chạy calculator một rule và xem trace.
7. Reviewer sửa một claim, xem diff và approve.
8. Xuất memo cùng audit bundle.
9. Nhập một version luật mới; bản cũ bị đánh stale và tạo review task.
10. Đăng nhập tenant B; xác minh không tìm thấy bất kỳ matter/vector/object của A.

Demo này là vertical slice thật. Nó có giá trị hơn việc trình diễn nhiều agent
nhưng chưa chứng minh temporal correctness, citation fidelity hoặc isolation.
