"""Unit tests for T-1150 `frob sys sync-interface`
(`frob.strata._sync_interface`): mechanical `interface=` attr upkeep
against the measured real public surface (module docstring)."""

from __future__ import annotations

from pathlib import Path

from frob.strata import StrataError
from frob.strata._code_binding import bind_code
from frob.strata._elaborate import elaborate
from frob.strata._parse import parse_module
from frob.strata._sync_interface import apply_sync_interface, sync_interface_report


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _write_design(root: Path, design_dir: str, rel: str, source: str) -> Path:
    path = root / design_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


class TestSyncInterfaceReport:
    """`sync_interface_report`'s pure-compute diff (never writes)."""

    def test_no_drift_reports_clean(self, tmp_path: Path):
        """A node whose declared `interface=` set already equals its real
        public surface reports zero drift and an unchanged file."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=public_fn;\n"
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not report.has_drift
        for file_result in report.files:
            assert not file_result.changed
            assert file_result.diffs == ()

    def test_addition_and_removal_detected(self, tmp_path: Path):
        """A node with an undeclared real symbol AND a declared-but-absent
        symbol reports both, sorted, and the rewritten text reflects the
        union of the real surface only."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "def public_fn():\n    pass\n\ndef new_fn():\n    pass\n",
        )
        design_path = _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=public_fn;\n"
            "    attr interface=phantom_fn;\n"
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        assert len(report.files) == 1
        file_result = report.files[0]
        assert file_result.changed
        assert file_result.path == "design/widget.strata"
        diffs = {d.node: d for d in file_result.diffs}
        assert diffs["widget"].added == ("new_fn",)
        assert diffs["widget"].removed == ("phantom_fn",)

        # The rewritten text declares exactly the real surface, sorted,
        # with every comment/other line untouched.
        new_text = file_result.new_text
        assert "attr interface=new_fn;" in new_text
        assert "attr interface=phantom_fn;" not in new_text
        assert "attr interface=public_fn;" in new_text
        assert 'code "src/frob/widget/**";' in new_text
        # Original file on disk is untouched (report never writes).
        assert design_path.read_text(encoding="utf-8") != new_text

    def test_missing_interface_block_is_inserted_after_header(self, tmp_path: Path):
        """A node with a non-empty real surface but zero declared
        `interface=` attrs yet gets its block inserted right after the
        node's opening line (module docstring's insertion convention)."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        file_result = report.files[0]
        lines = file_result.new_text.splitlines()
        header_idx = next(
            i for i, line in enumerate(lines) if line.strip().startswith("node widget")
        )
        assert "attr interface=public_fn;" in lines[header_idx + 1]

    # frob:tests \
    # tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_no_design_files_reports_empty
    def test_no_design_files_reports_empty(self, tmp_path: Path):
        """No `.strata` files at all under `design/` -- `Ok` with an empty
        file list, the same vacuous-but-honest posture every other
        design-loading entrypoint in this package takes, not an error."""
        (tmp_path / "design").mkdir()
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        assert result.danger_ok.files == ()

    # frob:tests \
    # tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_bad_design_file_propagates_load_error
    def test_bad_design_file_propagates_load_error(self, tmp_path: Path):
        """A `.strata` file that fails to parse surfaces as the
        underlying `DesignLoadError.error`, not silently skipped or
        folded into a clean report -- this is the REJECT path, distinct
        from every other case in this class which are all drift-clean or
        drift-dirty successes."""
        _write_design(tmp_path, "design", "bad.strata", "this is not valid strata {{{")
        result = sync_interface_report(tmp_path)
        assert result.is_err

    # frob:tests \
    # tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_ambiguous_code_binding_propagates_as_error
    def test_ambiguous_code_binding_propagates_as_error(self, tmp_path: Path):
        """Two nodes whose `code=` globs both match the same real file
        make `bind_code` itself fail -- `sync_interface_report` must
        propagate `Err(AmbiguousCodeBinding)` rather than silently
        computing drift off a partial/missing binding."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "}\n"
            "node widget_too : trusted {\n"
            '    code "src/frob/widget/*.py";\n'
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.AmbiguousCodeBinding

    # frob:tests \
    # tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_design_file_without_any_node_is_skipped
    def test_design_file_without_any_node_is_skipped(self, tmp_path: Path):
        """A `.strata` file present under `design/` but declaring no
        `node` at all (module-only) is skipped, not reported as a
        zero-node file result -- the `_NODE_HEADER_RE`/`"node "` early
        `continue` guard."""
        _write_design(tmp_path, "design", "empty.strata", "module empty\n")
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        assert result.danger_ok.files == ()


def test_report_and_apply_are_the_tier_a_ready_entry_points(tmp_path: Path):
    """T-1150 acceptance criterion 2 (disclosed deferral, see module
    docstring): `sync_interface_report` (pure compute) and
    `apply_sync_interface` (the only write) are the two functions a future
    T-1137 Tier-A fix-engine handler would call directly, with no
    intermediate CLI-only glue -- this pins that call shape so a future
    handler wiring does not have to rediscover it."""
    _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
    _write_design(
        tmp_path,
        "design",
        "widget.strata",
        'module widget\nnode widget : trusted {\n    code "src/frob/widget/**";\n}\n',
    )
    result = sync_interface_report(tmp_path)
    assert result.is_ok
    report = result.danger_ok
    written = apply_sync_interface(tmp_path, report)
    assert written == ("design/widget.strata",)


class TestApplySyncInterface:
    """`apply_sync_interface`'s write side effect."""

    def test_writes_only_changed_files(self, tmp_path: Path):
        """Only files whose report entry is `changed` get written back;
        an unchanged file's mtime/content is left alone."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "def public_fn():\n    pass\n\ndef new_fn():\n    pass\n",
        )
        design_path = _write_design(
            tmp_path,
            "design",
            "widget.strata",
            "module widget\n"
            "node widget : trusted {\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=public_fn;\n"
            "}\n",
        )
        result = sync_interface_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        written = apply_sync_interface(tmp_path, report)
        assert written == ("design/widget.strata",)
        on_disk = design_path.read_text(encoding="utf-8")
        assert "attr interface=new_fn;" in on_disk

        # Re-running now reports clean and writes nothing.
        result2 = sync_interface_report(tmp_path)
        assert result2.is_ok
        assert not result2.danger_ok.has_drift
        written2 = apply_sync_interface(tmp_path, result2.danger_ok)
        assert written2 == ()


# Sanity: the fixture designs above actually parse/elaborate/bind cleanly
# through the same pipeline `sync_interface_report` uses internally, so a
# regression in that pipeline's own contract fails loudly here too rather
# than only inside `sync_interface_report`'s own error branches.
def test_fixture_design_binds_cleanly(tmp_path: Path):
    """Smoke test: the minimal fixture `.strata` text used above parses,
    elaborates, and binds without error -- guards against the tests above
    silently exercising only the "design failed to load" early-return."""
    _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
    text = (
        "module widget\n"
        "node widget : trusted {\n"
        '    code "src/frob/widget/**";\n'
        "    attr interface=public_fn;\n"
        "}\n"
    )
    parsed = parse_module(text)
    assert parsed.is_ok
    elaborated = elaborate(parsed.danger_ok)
    assert elaborated.is_ok
    bound = bind_code(elaborated.danger_ok, tmp_path)
    assert bound.is_ok
