"""
Frontend<->backend contract: every endpoint the frontend calls must exist.

This is the guard against the whole class of bugs the recovery branch fixed —
the UI calling routes that don't exist (phantom /transcribe/* endpoints,
/analysis/auto-configure, etc.). It parses the centralized API client and the
workstation context for their endpoint literals and asserts each resolves to a
registered route, so it stays correct as those files change.
"""
import os
import re

import pytest

_FRONTEND = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
)
_SOURCES = [
    os.path.join(_FRONTEND, "lib", "apiClient.ts"),
    os.path.join(_FRONTEND, "context", "WorkstationContext.tsx"),
]

# Matches `${API_BASE_HOLDER.current}/foo/bar` and `${activeBase}/foo/bar`,
# capturing the path up to the first query/template boundary.
_PATTERN = re.compile(r"\$\{(?:API_BASE_HOLDER\.current|activeBase)\}(/[A-Za-z0-9/_-]+)")


def _referenced_paths():
    paths = set()
    for src in _SOURCES:
        with open(src, "r", encoding="utf-8") as f:
            for m in _PATTERN.finditer(f.read()):
                paths.add(m.group(1))
    return sorted(paths)


def test_sources_exist():
    for src in _SOURCES:
        assert os.path.isfile(src), f"contract source missing: {src}"


def test_frontend_paths_have_routes(route_paths):
    referenced = _referenced_paths()
    assert referenced, "no endpoint literals parsed — regex or sources changed"
    missing = [p for p in referenced if f"/api/v1{p}" not in route_paths]
    assert not missing, (
        "Frontend calls endpoints with no backend route:\n  "
        + "\n  ".join(missing)
    )


def test_app_has_expected_router_surface(route_paths):
    # Sanity anchors so a gutted router fails loudly.
    for required in [
        "/api/v1/ai/status",
        "/api/v1/transcribe/status",
        "/api/v1/transcribe/abort",
        "/api/v1/document/upload",
        "/api/v1/analysis/convene",
        "/api/v1/license/status",
        "/api/v1/settings/",
    ]:
        assert required in route_paths, f"missing core route {required}"


def test_no_phantom_transcribe_duplicates(route_paths):
    # The consolidation removed the /document/transcribe/* twins.
    dupes = [p for p in route_paths if p.startswith("/api/v1/document/transcribe")]
    assert not dupes, f"duplicate transcription routes resurfaced: {dupes}"
