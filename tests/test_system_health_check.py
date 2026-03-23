from types import SimpleNamespace

import scripts.system_health_check as sh


class _FakeTable:
    def __init__(self, row_count):
        self._row_count = row_count

    def count_rows(self):
        return self._row_count


class _FakeDb:
    def __init__(self, tables, row_count=1):
        self._tables = tables
        self._row_count = row_count

    def table_names(self):
        return self._tables

    def open_table(self, name):
        assert name == "document_aware_rag"
        return _FakeTable(self._row_count)


def test_probe_vector_index_reports_ready_without_loading_embeddings(monkeypatch, tmp_path):
    monkeypatch.setattr(sh, "LANCEDB_PATH", tmp_path)
    tmp_path.mkdir(exist_ok=True)

    fake_module = SimpleNamespace(connect=lambda _: _FakeDb(["document_aware_rag"], row_count=42))
    monkeypatch.setitem(__import__("sys").modules, "lancedb", fake_module)

    ok, detail = sh._probe_vector_index()

    assert ok is True
    assert "42 rows" in detail


def test_probe_vector_index_flags_missing_table(monkeypatch, tmp_path):
    monkeypatch.setattr(sh, "LANCEDB_PATH", tmp_path)
    tmp_path.mkdir(exist_ok=True)

    fake_module = SimpleNamespace(connect=lambda _: _FakeDb(["other_table"], row_count=0))
    monkeypatch.setitem(__import__("sys").modules, "lancedb", fake_module)

    ok, detail = sh._probe_vector_index()

    assert ok is False
    assert "document_aware_rag table missing" in detail


def test_probe_vector_index_flags_missing_path(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing"
    monkeypatch.setattr(sh, "LANCEDB_PATH", missing_path)

    ok, detail = sh._probe_vector_index()

    assert ok is False
    assert str(missing_path) in detail


def test_check_vector_db_reports_broken_on_empty_index(monkeypatch):
    monkeypatch.setattr(
        sh, "_probe_vector_index", lambda: (False, "document_aware_rag table empty")
    )

    result = sh.check_vector_db()

    assert result["status"] == "BROKEN"
    assert any("table empty" in detail for detail in result["details"])
