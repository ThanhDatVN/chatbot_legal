import pytest

from tools.shard_crawl_config import shard_config


def test_shards_preserve_order_and_cover_each_document_once() -> None:
    config = {
        "pilot_id": "all-documents",
        "documents": [{"id": f"D-{index}"} for index in range(5)],
    }
    shards = shard_config(config, 2)
    assert [len(item["documents"]) for item in shards] == [2, 2, 1]
    assert [doc["id"] for shard in shards for doc in shard["documents"]] == [
        "D-0",
        "D-1",
        "D-2",
        "D-3",
        "D-4",
    ]
    assert shards[0]["pilot_id"].endswith("shard-0001")


def test_shard_size_must_be_positive() -> None:
    with pytest.raises(ValueError):
        shard_config({"pilot_id": "x", "documents": []}, 0)
