"""Export round-trip smoke: each format returns a non-empty stream of the right type."""
import pytest

_BODY = {
    "content": "<p>The lighthouse keeper counted the ships.</p>",
    "chapters": [],
    "title": "Smoke Test",
    "author": "Tester",
    "format": "chicago",
}

_CASES = [
    ("/api/v1/document/export/docx",
     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("/api/v1/document/export/pdf", "application/pdf"),
    ("/api/v1/document/export/epub", "application/epub+zip"),
]


@pytest.mark.parametrize("url,content_type", _CASES)
def test_export_returns_stream(client, url, content_type):
    r = client.post(url, json=_BODY)
    assert r.status_code == 200, f"{url} -> {r.status_code}: {r.text[:200]}"
    assert content_type in r.headers.get("content-type", "")
    assert len(r.content) > 100, "export stream suspiciously small"


def test_export_rejects_empty_content(client):
    r = client.post("/api/v1/document/export/docx", json={**_BODY, "content": ""})
    assert r.status_code == 400
