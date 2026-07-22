# frob:waive SCOPE001 reason="T-0407's declared scope is src/frob/+docs/design/registry/; tests/** is leased in-progress by T-0160 so the scope cannot be formally extended here, same ad-hoc precedent as config.py's existing T-0458/T-0455 SCOPE001 waives -- this file is new pytest coverage for T-0407's own src/frob/registry change"  # noqa: E501
"""Tests for frob.registry._models -- the T-0407 unified registry schema
(docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407)."""

from __future__ import annotations

from pathlib import Path

from frob.registry._models import (
    DispositionKind,
    RegistryLoadError,
    audit_registry_file,
    load_registry_dir,
    parse_disposition,
)


class TestParseDisposition:
    """`parse_disposition` -- the one grammar every registry consumer shares."""

    def test_handled_by(self) -> None:
        d = parse_disposition("handled_by:REF001")
        assert d.kind is DispositionKind.HANDLED_BY
        assert d.target == "REF001"

    def test_deferred(self) -> None:
        d = parse_disposition("deferred:T-0001")
        assert d.kind is DispositionKind.DEFERRED
        assert d.target == "T-0001"

    def test_duplicate_of_underscore_and_hyphen(self) -> None:
        assert parse_disposition("duplicate_of:PAT-X").target == "PAT-X"
        assert parse_disposition("duplicate-of:PAT-X").target == "PAT-X"

    def test_out_of_scope_paren_form(self) -> None:
        d = parse_disposition("out-of-scope(manifest-extraction-artifact)")
        assert d.kind is DispositionKind.OUT_OF_SCOPE
        assert d.target == "manifest-extraction-artifact"

    def test_undispositioned_pending(self) -> None:
        assert parse_disposition("pending").kind is DispositionKind.UNDISPOSITIONED

    def test_undispositioned_none(self) -> None:
        assert parse_disposition(None).kind is DispositionKind.UNDISPOSITIONED

    def test_undispositioned_bare_addressed(self) -> None:
        assert parse_disposition("addressed").kind is DispositionKind.UNDISPOSITIONED

    def test_undispositioned_unparseable(self) -> None:
        assert (
            parse_disposition("some free text").kind is DispositionKind.UNDISPOSITIONED
        )


class TestLoadRegistryDir:
    """`load_registry_dir` -- the single loader every registry consumer shares."""

    def test_loads_typed_entries(self, tmp_path: Path) -> None:
        (tmp_path / "patterns.yaml").write_text(
            """\
schema_version: 1
total: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
            encoding="utf-8",
        )

        loaded = load_registry_dir(tmp_path, ("patterns.yaml",))

        assert "patterns.yaml" in loaded
        result = loaded["patterns.yaml"]
        assert result.is_ok
        registry_file = result.danger_ok
        assert registry_file.declared_totals == {"total": 1}
        entries = registry_file.entry_lists["entries"]
        assert len(entries) == 1
        assert entries[0].id == "PAT-EXAMPLE"
        assert entries[0].disposition.kind is DispositionKind.HANDLED_BY

    def test_absent_file_not_in_result(self, tmp_path: Path) -> None:
        loaded = load_registry_dir(tmp_path, ("nope.yaml",))

        assert loaded == {}

    def test_malformed_yaml_is_err(self, tmp_path: Path) -> None:
        (tmp_path / "bad.yaml").write_text(
            "entries: [this is: not: valid", encoding="utf-8"
        )

        loaded = load_registry_dir(tmp_path, ("bad.yaml",))

        assert loaded["bad.yaml"].is_err
        assert loaded["bad.yaml"].danger_err is RegistryLoadError.MalformedYaml

    def test_not_a_mapping_is_err(self, tmp_path: Path) -> None:
        (tmp_path / "list.yaml").write_text("- one\n- two\n", encoding="utf-8")

        loaded = load_registry_dir(tmp_path, ("list.yaml",))

        assert loaded["list.yaml"].is_err
        assert loaded["list.yaml"].danger_err is RegistryLoadError.NotAMapping

    def test_malformed_entry_counted(self, tmp_path: Path) -> None:
        (tmp_path / "patterns.yaml").write_text(
            """\
entries:
  - id: "PAT-OK"
    disposition: "handled_by:REF001"
  - "not a mapping"
  - name: "no id"
""",
            encoding="utf-8",
        )

        loaded = load_registry_dir(tmp_path, ("patterns.yaml",))

        registry_file = loaded["patterns.yaml"].danger_ok
        assert registry_file.malformed_count == 2
        assert len(registry_file.entry_lists["entries"]) == 1

    def test_split_entries_key_total(self, tmp_path: Path) -> None:
        (tmp_path / "weaknesses.yaml").write_text(
            """\
cwe_total: 1
cwe_entries:
  - id: "CWE-1"
    disposition: "handled_by:REF001"
""",
            encoding="utf-8",
        )

        loaded = load_registry_dir(tmp_path, ("weaknesses.yaml",))

        registry_file = loaded["weaknesses.yaml"].danger_ok
        assert registry_file.declared_totals == {"cwe_total": 1}


class TestAuditRegistryFile:
    """`audit_registry_file` -- the per-kind accounting `frob registry
    audit` reports."""

    def test_counts_each_kind(self, tmp_path: Path) -> None:
        (tmp_path / "patterns.yaml").write_text(
            """\
entries:
  - id: "PAT-HANDLED"
    disposition: "handled_by:REF001"
  - id: "PAT-DEFERRED"
    disposition: "deferred:T-0001"
  - id: "PAT-DUP"
    disposition: "duplicate_of:PAT-HANDLED"
  - id: "PAT-OOS"
    disposition: "out_of_scope:reason text"
  - id: "PAT-PENDING"
    disposition: pending
  - "not a mapping"
""",
            encoding="utf-8",
        )

        registry_file = load_registry_dir(tmp_path, ("patterns.yaml",))[
            "patterns.yaml"
        ].danger_ok
        audit = audit_registry_file(registry_file)

        assert audit.total == 6
        assert audit.handled == 1
        assert audit.deferred == 1
        assert audit.duplicate == 1
        assert audit.out_of_scope == 1
        assert audit.unaccounted == 1
        assert audit.malformed == 1
        assert audit.exhausted is False

    def test_fully_dispositioned_file_is_exhausted(self, tmp_path: Path) -> None:
        (tmp_path / "patterns.yaml").write_text(
            """\
entries:
  - id: "PAT-HANDLED"
    disposition: "handled_by:REF001"
""",
            encoding="utf-8",
        )

        registry_file = load_registry_dir(tmp_path, ("patterns.yaml",))[
            "patterns.yaml"
        ].danger_ok
        audit = audit_registry_file(registry_file)

        assert audit.exhausted is True
