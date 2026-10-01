"""Provision-level currency ledger: clause targeting, chunk splitting, status assignment and evidence checks."""

import hashlib
from datetime import date

import pymupdf
import pytest

from ingestion.chunk import chunk_document
from ingestion.currency import assign_currency
from ingestion.ledger import (AmendingSource, Coverage, CurrencyLedger, LedgerEntry, chunk_breaks, clause_spans,
                              entries_for_chunk, resolve_targets, verify_evidence)
from ingestion.models import CurrencyStatus
from ingestion.structure import parse_document
from ingestion.tokenizer import TokenCounter
from tests.unit.test_ingestion_structure import layout, line, para, registry_doc

AS_OF = date(2026, 10, 1)


def amending_lines():
    lines = [line(1, 60, "CHÍNH PHỦ", x0=250, x1=330)]
    lines += para(1, 90, "Căn cứ Bộ luật Lao động ngày 20 tháng 11 năm 2019;")
    lines += para(1, 120, "Điều 1. Phạm vi điều chỉnh")
    lines += para(1, 140, "Nghị định này quy định chi tiết một số điều của Bộ luật Lao động.")
    lines += para(1, 170, "Điều 2. Sửa đổi Điều 5 như sau:")
    lines += para(1, 190, "1. Sửa đổi khoản 1 Điều 5 như sau:")
    lines += para(1, 210, "“1. Người sử dụng lao động phải báo cáo định kỳ.")
    lines += para(1, 230, "2. Báo cáo gửi qua Cổng Dịch vụ công Quốc gia.”.")
    lines += para(1, 250, "2. Bãi bỏ khoản 3 Điều 5.")
    lines += para(2, 70, "Điều 3. Báo cáo sử dụng lao động")
    lines += para(2, 90, "1. Người sử dụng lao động lập sổ quản lý lao động.")
    lines += para(2, 110, "2. Định kỳ 06 tháng người sử dụng lao động báo cáo tình hình thay đổi lao động.")
    lines += para(2, 130, "3. Sở Lao động - Thương binh và Xã hội tổng hợp báo cáo.")
    lines += [line(2, 170, "TM. CHÍNH PHỦ", x0=350, x1=450), line(2, 190, "THỦ TƯỚNG", x0=360, x1=440),
              line(2, 210, "Nguyễn Văn A", x0=355, x1=445)]
    return lines


def entry(**kw) -> LedgerEntry:
    base = dict(entry_id="e1", target_document_id="doc", sections=["Điều 3"], clauses=["2"], change="amended",
                source="9/2025/NĐ-CP", source_provision="Điều 7", effective_from=date(2025, 7, 1),
                evidence_quote="Sửa đổi khoản 2 Điều 3", extracted_by="test")
    base.update(kw)
    return LedgerEntry.model_validate(base)


COVERAGE = Coverage(document_id="doc", instruments_checked=["9/2025/NĐ-CP"], checked_on=AS_OF, method="m",
                    limitations="l")


@pytest.fixture(scope="module")
def parsed():
    return parse_document(layout(amending_lines()))


def test_clause_spans_ignore_numbering_inside_quotes(parsed):
    art2 = next(s for s in parsed.sections if s.label == "Điều 2")
    spans = clause_spans(parsed, art2)
    assert list(spans) == ["1", "2"]
    clause1 = " ".join(parsed.text[slice(*spans["1"])].split())
    assert "2. Báo cáo gửi qua Cổng" in clause1  # quoted "2." stays inside top-level clause 1
    assert " ".join(parsed.text[slice(*spans["2"])].split()) == "2. Bãi bỏ khoản 3 Điều 5."


def test_targeted_clause_gets_its_own_chunk_and_status(parsed):
    doc = registry_doc()
    entries = [entry()]
    chunks = chunk_document(parsed, doc, "t", TokenCounter(), chunk_breaks(parsed, entries))
    art3 = [c for c in chunks if c.section_label == "Điều 3"]
    assert [c.text.split("\n")[0][:9] for c in art3] == ["Điều 3. B", "2. Định k", "3. Sở Lao"]
    spans, problems = resolve_targets(parsed, entries)
    assert problems == []
    statuses = []
    for c in art3:
        hits = entries_for_chunk(c, entries, spans)
        statuses.append(assign_currency(c, doc, [doc], AS_OF, {}, hits, COVERAGE))
    assert [s for s, _ in statuses] == [CurrencyStatus.PRESUMED_CURRENT, CurrencyStatus.SUPERSEDED_BY_AMENDMENT,
                                        CurrencyStatus.PRESUMED_CURRENT]
    assert statuses[1][1].startswith("Khoản 2 Điều 3 đã được sửa đổi theo Điều 7 Nghị định 9/2025/NĐ-CP")
    assert "đã đối chiếu 9/2025/NĐ-CP" in statuses[0][1]


def test_unknown_targets_are_reported(parsed):
    _, problems = resolve_targets(parsed, [entry(clauses=["9"]), entry(entry_id="e2", sections=["Điều 99"])])
    assert problems == ["e1: Điều 3 has no top-level khoản 9", "e2: doc has no section 'Điều 99'"]


def test_change_types_and_dates(parsed):
    doc = registry_doc()
    chunk = next(c for c in chunk_document(parsed, doc, "t", TokenCounter()) if c.section_label == "Điều 1")

    def status(e):
        return assign_currency(chunk, doc, [doc], AS_OF, {}, [e], COVERAGE)

    whole = dict(sections=["Điều 1"], clauses=[])
    assert status(entry(change="expired", **whole))[0] == CurrencyStatus.SUPERSEDED_BY_AMENDMENT
    assert status(entry(change="partially_affected", **whole))[0] == CurrencyStatus.UNVERIFIED
    added = status(entry(change="added", **whole))
    assert added[0] == CurrencyStatus.PRESUMED_CURRENT and "được bổ sung nội dung theo" in added[1]
    lapsed = entry(change="displaced", effective_until=date(2026, 3, 1), **whole)
    assert status(lapsed)[0] == CurrencyStatus.PRESUMED_CURRENT  # temporary rule no longer applies
    future = status(entry(change="expired", effective_from=date(2027, 1, 1), **whole))
    assert future[0] == CurrencyStatus.PRESUMED_CURRENT and "Sắp thay đổi" in future[1]
    # without a ledger coverage record a partially expired document stays unverified
    assert assign_currency(chunk, doc, [doc], AS_OF, {}, [], None)[0] == CurrencyStatus.UNVERIFIED


def test_verify_evidence_checks_hash_and_quote(tmp_path):
    pdf = tmp_path / "src.pdf"
    with pymupdf.open() as d:  # the built-in PDF font has no Vietnamese glyphs, so the fixture text is ASCII
        page = d.new_page()
        page.insert_text((72, 100), "Dieu 7. Sua doi khoan 2 Dieu 3")
        page.insert_text((72, 120), "cua Nghi dinh so 1/2020/ND-CP nhu sau:")
        page.insert_text((72, 800), "12")  # page-number lines are dropped
        d.save(pdf)
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()

    def ledger(quote: str, sha: str) -> CurrencyLedger:
        source = AmendingSource(document_number="9/2025/NĐ-CP", title="t", issued_date=date(2025, 6, 1),
                                congbao_id=1, source_url="https://congbao.chinhphu.vn/x", download_url="https://x",
                                path="src.pdf", sha256=sha, pages=1, effective_from=date(2025, 7, 1),
                                checked_on=AS_OF)
        return CurrencyLedger(ledger_version="t", sources=[source], coverage=[COVERAGE],
                              entries=[entry(evidence_quote=quote)])

    assert verify_evidence(ledger("Sua doi khoan 2 Dieu 3 cua Nghi dinh so 1/2020/ND-CP", digest), tmp_path) == []
    assert verify_evidence(ledger("Bai bo khoan 2 Dieu 3", digest), tmp_path) == \
        ["e1: evidence quote not found in 9/2025/NĐ-CP"]
    assert "does not match" in verify_evidence(ledger("x", "0" * 64), tmp_path)[0]
