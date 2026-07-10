"""Security guards: path traversal, key masking, friendly rejects."""
import io

import pytest

# A path that is unambiguously outside the user's home tree on this box.
_OUTSIDE = "C:/Windows/System32"


@pytest.mark.parametrize("url", [
    f"/api/v1/transcribe/ingest?folder_path={_OUTSIDE}",
    f"/api/v1/transcribe/resort?folder_path={_OUTSIDE}",
    f"/api/v1/analysis/ledger?folder_path={_OUTSIDE}",
])
def test_folder_endpoints_reject_traversal(client, url):
    r = client.get(url)
    assert r.status_code == 403, f"{url} should 403, got {r.status_code}"


def test_start_pipeline_rejects_traversal(client):
    r = client.post("/api/v1/transcribe/start-pipeline", json={"folder_path": _OUTSIDE})
    assert r.status_code == 403


def test_settings_masks_api_keys(client):
    r = client.get("/api/v1/settings/")
    assert r.status_code == 200
    keys = r.json().get("api_keys", {})
    # Any non-empty key value must be masked (****abcd), never raw.
    leaked = {k: v for k, v in keys.items() if v and not v.startswith("****")}
    assert not leaked, f"raw API keys leaked over the wire: {list(leaked)}"


def test_upload_stream_rejects_unsupported_extension(client):
    r = client.post(
        "/api/v1/document/upload/stream",
        files={"file": ("book.epub", io.BytesIO(b"fake"), "application/epub+zip")},
    )
    assert r.status_code == 400
    assert "Unsupported format" in str(r.json().get("detail", ""))


# ─── #5: upload size cap ─────────────────────────────────────────────────────

def test_upload_rejects_oversized(client, monkeypatch):
    from services import security
    monkeypatch.setattr(security, "MAX_UPLOAD_BYTES", 50)  # 50-byte cap for the test
    r = client.post(
        "/api/v1/document/upload",
        files={"file": ("big.txt", io.BytesIO(b"x" * 5000), "text/plain")},
    )
    assert r.status_code == 413, f"oversized upload should 413, got {r.status_code}"


def test_upload_accepts_small(client):
    r = client.post(
        "/api/v1/document/upload",
        files={"file": ("ok.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert r.status_code == 200


def test_snapshot_rejects_oversized(client, tmp_path, monkeypatch):
    import base64
    from services import security
    monkeypatch.setattr(security, "MAX_UPLOAD_BYTES", 10)
    payload = base64.b64encode(b"x" * 500).decode()
    r = client.post(
        "/api/v1/analysis/save-snapshot",
        json={"data_url": f"data:image/png;base64,{payload}", "folder_path": str(tmp_path)},
    )
    assert r.status_code == 413


# ─── #6: /keys mask leaks nothing beyond the last 4 ──────────────────────────

def test_keys_endpoint_masks_last4_only(client):
    r = client.get("/api/v1/settings/keys/gemini")
    assert r.status_code == 200
    masked = r.json()["key_masked"]
    if masked != "NOT_FOUND":
        # Last-4 mask only — no head...tail form that would leak the prefix.
        assert masked.startswith("****"), f"unexpected mask form: {masked}"
        assert "..." not in masked, f"prefix leaked: {masked}"


# ─── #7: /read is a typed, size-capped text viewer ───────────────────────────

def test_read_rejects_disallowed_extension(client, tmp_path):
    p = tmp_path / "secret.key"
    p.write_text("PRIVATE")
    r = client.get("/api/v1/document/read", params={"path": str(p)})
    assert r.status_code == 415, f"non-text /read should 415, got {r.status_code}"


def test_read_allows_text_file(client, tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("hello")
    r = client.get("/api/v1/document/read", params={"path": str(p)})
    assert r.status_code == 200
    assert r.json()["content"] == "hello"
