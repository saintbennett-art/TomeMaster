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
