"""A published snapshot id can only be rebuilt with identical chunks."""

import json

import ingestion.build as build_mod


def _fake_build(content: str):
    def run(registry_path, snapshot_id, out_root, review_dir, fixtures_path, ledger_path, out):
        out.mkdir(parents=True, exist_ok=True)
        (out / "chunks.jsonl").write_text(content, encoding="utf-8", newline="\n")
        manifest = {"snapshot_id": snapshot_id, "chunks_sha256": build_mod.file_sha256(out / "chunks.jsonl")}
        (out / "snapshot.json").write_text(json.dumps(manifest), encoding="utf-8")
        return 0
    return run


def test_rebuild_must_reproduce_published_chunks(tmp_path, monkeypatch):
    args = (tmp_path / "registry.json", "snap", tmp_path, tmp_path, tmp_path / "f.json", tmp_path / "l.json")
    monkeypatch.setattr(build_mod, "_build", _fake_build('{"chunk_id": "a"}\n'))
    assert build_mod.build(*args) == 0  # first build publishes
    assert build_mod.build(*args) == 0  # identical rebuild is accepted
    monkeypatch.setattr(build_mod, "_build", _fake_build('{"chunk_id": "b"}\n'))
    assert build_mod.build(*args) == 3  # different content under the same id is refused
    assert (tmp_path / "snap" / "chunks.jsonl").read_text(encoding="utf-8") == '{"chunk_id": "a"}\n'
    assert not (tmp_path / ".staging-snap").exists()
    assert build_mod.build(*args, overwrite=True) == 0  # explicit overwrite for unpublished work
