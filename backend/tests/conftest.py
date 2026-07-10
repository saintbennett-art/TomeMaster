"""Shared pytest fixtures. Imports the FastAPI app exactly as production does."""
import os
import sys

# Tests run from anywhere; ensure `backend/` is importable (so `import main` works).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(scope="session")
def client():
    return TestClient(main.app)


@pytest.fixture(scope="session")
def route_paths():
    """Every registered API path, e.g. '/api/v1/transcribe/status'."""
    return {getattr(r, "path", "") for r in main.app.routes}
