#!/usr/bin/env python3
"""
Tests for scripts/submit_to_search_console.py

We don't hit Google endpoints in tests; we monkeypatch google-auth to validate
that the code path is wired correctly and deterministic.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


@pytest.fixture(scope="module")
def submitter():
    return _load_module("submit_to_search_console", "scripts/submit_to_search_console.py")


def test_load_service_account_info_from_json_env(submitter, monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_KEY", json.dumps({"client_email": "x@example.com"}))
    assert submitter._load_service_account_info() == {"client_email": "x@example.com"}


def test_load_service_account_info_from_file_path(submitter, monkeypatch, tmp_path: Path):
    p = tmp_path / "sa.json"
    p.write_text(json.dumps({"client_email": "y@example.com"}), encoding="utf-8")
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_KEY", str(p))
    assert submitter._load_service_account_info() == {"client_email": "y@example.com"}


def test_get_access_token_uses_google_auth(submitter, monkeypatch):
    # Minimal payload; actual validation is handled by google-auth in production.
    monkeypatch.setenv(
        "GOOGLE_SEARCH_CONSOLE_KEY",
        json.dumps({"type": "service_account", "client_email": "z@example.com"}),
    )

    import google.oauth2.service_account as sa

    class DummyCreds:
        token = "dummy-token"

        def refresh(self, _request):
            return None

    monkeypatch.setattr(
        sa.Credentials,
        "from_service_account_info",
        staticmethod(lambda _info, scopes=None: DummyCreds()),
    )

    assert submitter.get_access_token() == "dummy-token"
