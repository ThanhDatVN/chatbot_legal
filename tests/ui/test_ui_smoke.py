"""Headless Streamlit smoke tests against a running API (skipped when the API is not reachable)."""

from pathlib import Path

import pytest
import requests

UI = Path(__file__).resolve().parents[2] / "ui"
API = "http://127.0.0.1:8000"


def _api_up() -> bool:
    try:
        return requests.get(API + "/ready", timeout=3).ok
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(not _api_up(), reason="API not running on 127.0.0.1:8000")


def page_script(tmp_path: Path, body: str) -> str:
    script = tmp_path / "page.py"
    script.write_text(f"import sys\nsys.path.insert(0, r'{UI}')\n{body}\n", encoding="utf-8")
    return str(script)


def test_chat_flow_shows_badge_answer_and_citation():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI / "app.py"), default_timeout=180)
    at.run()
    assert not at.exception and at.title[0].value == "CiteAgent VN"
    at.chat_input[0].set_value("Người lao động làm đủ 12 tháng được nghỉ hằng năm bao nhiêu ngày?").run()
    assert not at.exception
    texts = [m.value for m in at.markdown]
    assert "**✅ Có căn cứ**" in texts
    assert any("12 ngày làm việc" in t for t in texts)
    assert any(b.label.startswith("[1] Điều 113") for b in at.button)


def test_refusal_is_rendered_as_warning():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI / "app.py"), default_timeout=180)
    at.run()
    at.chat_input[0].set_value("Thời tiết Hà Nội ngày mai thế nào?").run()
    assert not at.exception
    assert "**⚠ Chưa đủ căn cứ**" in [m.value for m in at.markdown]
    assert at.warning


def test_evaluation_dashboard(tmp_path):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(page_script(tmp_path, "from evaluation_view import evaluation_page\nevaluation_page()"),
                           default_timeout=120)
    at.run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert {"Hit@5", "MRR", "Citation precision", "Groundedness", "Refusal accuracy"} <= set(labels)
    assert len(at.dataframe) >= 2


def test_search_and_documents_pages(tmp_path):
    from streamlit.testing.v1 import AppTest

    body = ("import streamlit as st\nimport api_client as api\nfrom components import STATUS_LABEL\n"
            "data = api.documents()\nst.write(data['total'])\n"
            "res = api.search('nghỉ hằng năm', 3)\nst.write(len(res['results']))")
    at = AppTest.from_file(page_script(tmp_path, body), default_timeout=120)
    at.run()
    assert not at.exception
