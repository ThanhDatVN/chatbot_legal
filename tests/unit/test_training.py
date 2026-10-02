"""Reranker fine-tuning data rules: cross-references, negatives that must not be used, cleaning and splits."""

from types import SimpleNamespace

from tests.unit.helpers import make_chunk
from training.common import LABOUR_CODE, Corpus, char_ngrams, is_validation, jaccard, references
from training.generate_queries import clean
from training.train_reranker import build_pairs

NUMBERS = {"145/2020/NĐ-CP": "145_2020_nd_cp", "18/VBHN-VPQH": LABOUR_CODE}


def test_references_resolve_to_articles_of_the_right_document():
    decree = make_chunk("a" * 24, "Điều 67. Tiền tàu xe\n1. Theo khoản 6 Điều 113 của Bộ luật Lao động và khoản 2 "
                        "Điều 64 Nghị định này.", document_id="145_2020_nd_cp", section="Điều 67", article=67)
    code = make_chunk("b" * 24, "Điều 37. Trường hợp\n1. Trừ trường hợp quy định tại Điều 36 của Bộ luật này.",
                      section="Điều 37", article=37)
    later = make_chunk("c" * 24, "Điều 79. Giải quyết\nTheo quy định tại Điều 112 Nghị định số 145/2020/NĐ-CP.",
                       document_id="129_2025_nd_cp", section="Điều 79", article=79)
    assert references(decree, NUMBERS) == {(LABOUR_CODE, "Điều 113"), ("145_2020_nd_cp", "Điều 64")}
    assert references(code, NUMBERS) == {(LABOUR_CODE, "Điều 36")}
    assert references(later, NUMBERS) == {("145_2020_nd_cp", "Điều 112")}


def test_related_chunks_are_never_negatives():
    article = make_chunk("a" * 24, "Điều 113. Nghỉ hằng năm\n1. Được nghỉ 12 ngày làm việc.")
    part_two = make_chunk("b" * 24, "6. Khi nghỉ hằng năm, nếu đi đường trên 02 ngày.")
    decree = make_chunk("c" * 24, "Điều 67. Tiền tàu xe\nTheo khoản 6 Điều 113 của Bộ luật Lao động.",
                        document_id="145_2020_nd_cp", section="Điều 67", article=67)
    other = make_chunk("d" * 24, "Điều 25. Thời gian thử việc\nKhông quá 60 ngày.", section="Điều 25", article=25)
    chunks = {c.chunk_id: c for c in (article, part_two, decree, other)}
    documents = {"18": SimpleNamespace(document_number="18/VBHN-VPQH", document_id=LABOUR_CODE),
                 "145": SimpleNamespace(document_number="145/2020/NĐ-CP", document_id="145_2020_nd_cp")}
    corpus = Corpus(SimpleNamespace(chunks=chunks, documents=documents))
    assert corpus.related(article, part_two)  # another part of the same article
    assert corpus.related(article, decree) and corpus.related(decree, article)  # the decree details the article
    assert not corpus.related(article, other)


def test_generated_questions_are_cleaned():
    raw = ["  - Công ty có được giữ bằng gốc của tôi không?", "Theo Điều 17 thì công ty có được giữ bằng không?",
           "What is the probation period?", "Ngắn quá?", "Công ty có được giữ bằng gốc của tôi không?",
           "Nghỉ ngang thì có phải đền tiền cho công ty không?"]
    assert clean(raw, 3) == ["Công ty có được giữ bằng gốc của tôi không?",
                             "Nghỉ ngang thì có phải đền tiền cho công ty không?"]


def test_validation_split_is_by_article_and_about_one_in_ten():
    keys = [(LABOUR_CODE, f"Điều {i}") for i in range(1, 1001)]
    share = sum(is_validation(k) for k in keys) / len(keys)
    assert 0.06 < share < 0.14
    assert is_validation(keys[5]) == is_validation(keys[5])


def test_near_duplicate_detection():
    a = char_ngrams("Công ty có được giữ bằng gốc của tôi không?")
    assert jaccard(a, char_ngrams("công ty  có được giữ bằng gốc của tôi không")) > 0.9
    assert jaccard(a, char_ngrams("Làm thêm giờ tối đa bao nhiêu giờ một tháng?")) < 0.2


def test_groups_put_the_positive_first():
    texts = {"p": "positive", "n1": "neg one", "n2": "neg two"}
    pairs, labels = build_pairs({"query": "q", "pos": ["p"], "neg": ["n1", "n2"]}, texts)
    assert pairs == [("q", "positive"), ("q", "neg one"), ("q", "neg two")] and labels == [1.0, 0.0, 0.0]
    pairs, labels = build_pairs({"query": "q", "pos": [], "neg": ["n1"]}, texts)
    assert labels == [0.0]
