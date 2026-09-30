from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.sparse import SparseIndex, tokenize


def test_rrf_scores_and_order():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "c", "d"]], k=60)
    scores = dict(fused)
    assert scores["b"] == 1 / 62 + 1 / 61
    assert scores["a"] == 1 / 61
    assert [d for d, _ in fused][:2] == ["b", "c"]


def test_rrf_is_deterministic_on_ties_and_ignores_duplicates():
    assert reciprocal_rank_fusion([["x", "y"], ["y", "x"]]) == reciprocal_rank_fusion([["x", "y"], ["y", "x"]])
    fused = dict(reciprocal_rank_fusion([["a", "a", "b"]], k=60))
    assert fused["a"] == 1 / 61


def test_rrf_empty_branch():
    assert reciprocal_rank_fusion([[], ["a"]]) == [("a", 1 / 61)]


def test_tokenizer_adds_syllable_bigrams_and_drops_stopwords():
    tokens = tokenize("Hợp đồng lao động của người lao động")
    assert "hợp_đồng" in tokens and "lao_động" in tokens
    assert "của" not in tokens


def test_bm25_respects_allowed_subset():
    index = SparseIndex.build(["c1", "c2", "c3"], ["nghỉ hằng năm 12 ngày", "thử việc 60 ngày", "nghỉ hằng năm"])
    top = index.search("nghỉ hằng năm", allowed=["c2", "c3"], top_k=5)
    assert [cid for cid, _ in top] == ["c3"]
    assert index.search("", allowed=["c1"], top_k=5) == []
