"""Tests for frob.registry._corpus -- the T-0429
corpus-emit mechanism (append_entry / format_entry_block)."""

from __future__ import annotations

from pathlib import Path

from frob.registry._corpus import CorpusError, append_entry, format_entry_block

# frob:ticket T-0429
_FIXTURE = """\
# frob:used-by tests/test_registry_corpus.py
schema_version: 1
total: 2
entries:
  - id: "EX-ONE"
    name: "Example One"
    disposition: "pending"
    cross_refs: []
  - id: "EX-TWO"
    name: "Example Two"
    disposition: "pending"
    cross_refs: []
"""


# frob:ticket T-0429
def _write_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "example.yaml"
    path.write_text(_FIXTURE)
    return path


# frob:ticket T-0429
class TestFormatEntryBlock:
    # frob:tests \
    # tests/test_registry_corpus.py::TestFormatEntryBlock.test_pending_disposition_alwa\
    # ys
    # frob:ticket T-0429
    def test_pending_disposition_always(self) -> None:
        block = format_entry_block("EX-THREE", "Example Three")
        assert 'disposition: "pending"' in block
        assert 'id: "EX-THREE"' in block
        assert 'name: "Example Three"' in block

    # frob:ticket T-0429
    def test_source_doc_included_when_given(self) -> None:
        block = format_entry_block("EX-THREE", "Example Three", source_doc="doc.md")
        assert 'source_doc: "doc.md"' in block

    # frob:ticket T-0429
    def test_source_doc_omitted_when_blank(self) -> None:
        block = format_entry_block("EX-THREE", "Example Three")
        assert "source_doc" not in block


# frob:ticket T-0429
class TestAppendEntry:
    # frob:tests \
    # tests/test_registry_corpus.py::TestAppendEntry.test_append_adds_entry_and_bumps_t\
    # otal
    # frob:ticket T-0429
    def test_append_adds_entry_and_bumps_total(self, tmp_path: Path) -> None:
        path = _write_fixture(tmp_path)

        result = append_entry(path, "entries", "EX-THREE", "Example Three")

        assert result.is_ok
        text = path.read_text()
        assert 'id: "EX-THREE"' in text
        assert "total: 3" in text

    # frob:ticket T-0429
    def test_append_always_pending_never_a_real_disposition(
        self, tmp_path: Path
    ) -> None:
        path = _write_fixture(tmp_path)
        append_entry(path, "entries", "EX-THREE", "Example Three")
        text = path.read_text()
        new_block = text.split('id: "EX-THREE"')[1]
        assert 'disposition: "pending"' in new_block

    # frob:ticket T-0429
    def test_duplicate_id_rejected(self, tmp_path: Path) -> None:
        path = _write_fixture(tmp_path)

        result = append_entry(path, "entries", "EX-ONE", "Duplicate")

        assert result.is_err
        assert result.danger_err == CorpusError.DuplicateId
        # T-0429: a rejected write must not touch the file at all.
        assert path.read_text() == _FIXTURE

    # frob:ticket T-0429
    def test_missing_file_rejected(self, tmp_path: Path) -> None:
        result = append_entry(
            tmp_path / "nope.yaml", "entries", "EX-THREE", "Example Three"
        )
        assert result.is_err
        assert result.danger_err == CorpusError.FileNotFound

    # frob:ticket T-0429
    def test_missing_key_rejected(self, tmp_path: Path) -> None:
        path = _write_fixture(tmp_path)

        result = append_entry(path, "no_such_key", "EX-THREE", "Example Three")

        assert result.is_err
        assert result.danger_err == CorpusError.KeyNotFound

    # frob:ticket T-0429
    def test_no_declared_total_left_untouched(self, tmp_path: Path) -> None:
        path = tmp_path / "no_total.yaml"
        path.write_text(
            "schema_version: 1\n"
            "entries:\n"
            '  - id: "EX-ONE"\n'
            '    name: "Example One"\n'
            '    disposition: "pending"\n'
            "    cross_refs: []\n"
        )

        result = append_entry(path, "entries", "EX-TWO", "Example Two")

        assert result.is_ok
        assert "total:" not in path.read_text()
