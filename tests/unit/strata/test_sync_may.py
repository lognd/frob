"""Unit tests for T-1531 SYS100-core `may` grant auto-fix writer
(`frob.strata._sync_may`): widen (or create) a node's declared `may
"<kind>" via [...]` grant to cover an observed net/fs-write/exec effect
outside its current `via` surface (module docstring)."""

from __future__ import annotations

from pathlib import Path

from frob.strata import StrataError
from frob.strata._sync_may import apply_sync_may, sync_may_report


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _write_design(root: Path, design_dir: str, rel: str, source: str) -> Path:
    path = root / design_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


class TestSyncMayReport:
    """`sync_may_report`'s pure-compute diff (never writes)."""

    def test_no_drift_reports_clean(self, tmp_path: Path):
        """A node whose `via` list already covers every observed-effect
        file for that kind reports zero drift."""
        _write(tmp_path, "api/net.py", "requests.get('https://x')\n")
        _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            '    may "net.connect" via "api/net.py";\n'
            "}\n",
        )
        result = sync_may_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not report.has_drift

    def test_widens_existing_via_list(self, tmp_path: Path):
        """A second file exercising an already-granted kind outside the
        existing `via` list widens it to the sorted union, never dropping
        the original entry."""
        _write(tmp_path, "api/net.py", "requests.get('https://x')\n")
        _write(tmp_path, "api/other.py", "requests.get('https://y')\n")
        design_path = _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            '    may "net.connect" via "api/net.py";\n'
            "}\n",
        )
        result = sync_may_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        assert len(report.files) == 1
        file_result = report.files[0]
        assert file_result.path == "design/api.strata"
        assert len(file_result.diffs) == 1
        diff = file_result.diffs[0]
        assert diff.node == "Api"
        assert diff.kind == "net.connect"
        assert diff.added_files == ("api/other.py",)
        assert diff.created is False
        assert 'may "net.connect" via "api/net.py", "api/other.py";' in file_result.new_text
        # Original file on disk is untouched (report never writes).
        assert design_path.read_text(encoding="utf-8") != file_result.new_text

    def test_inserts_new_grant_when_none_declared(self, tmp_path: Path):
        """A node with no `may "<kind>"` declaration at all for an
        observed kind gets a brand-new via-scoped grant line inserted."""
        _write(tmp_path, "api/net.py", "requests.get('https://x')\n")
        _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\nnode Api : trusted {\n    code \"api/**\";\n}\n",
        )
        result = sync_may_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        file_result = report.files[0]
        diff = file_result.diffs[0]
        assert diff.node == "Api"
        assert diff.created is True
        assert diff.added_files == ("api/net.py",)
        assert 'may "net.connect" via "api/net.py";' in file_result.new_text

    def test_no_design_files_reports_empty(self, tmp_path: Path):
        """No `.strata` files at all under `design/` -- `Ok` with an empty
        file list, the same vacuous-but-honest posture `sync_interface_
        report` takes."""
        (tmp_path / "design").mkdir()
        result = sync_may_report(tmp_path)
        assert result.is_ok
        assert result.danger_ok.files == ()

    def test_bad_design_file_propagates_load_error(self, tmp_path: Path):
        """A `.strata` file that fails to parse surfaces the underlying
        `DesignLoadError.error`, not silently skipped."""
        _write_design(tmp_path, "design", "bad.strata", "this is not valid strata {{{")
        result = sync_may_report(tmp_path)
        assert result.is_err

    def test_ambiguous_code_binding_propagates_as_error(self, tmp_path: Path):
        """Two nodes whose `code=` globs both match the same real file
        make `bind_code` fail -- `sync_may_report` propagates
        `Err(AmbiguousCodeBinding)` rather than computing drift off a
        partial binding."""
        _write(tmp_path, "api/net.py", "requests.get('https://x')\n")
        _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\n"
            "node Api : trusted {\n"
            '    code "api/**";\n'
            "}\n"
            "node ApiToo : trusted {\n"
            '    code "api/*.py";\n'
            "}\n",
        )
        result = sync_may_report(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.AmbiguousCodeBinding


class TestApplySyncMay:
    """`apply_sync_may`'s write side effect."""

    def test_writes_only_changed_files(self, tmp_path: Path):
        """Only a file whose report entry is `changed` gets written back;
        re-running afterwards reports clean and writes nothing."""
        _write(tmp_path, "api/net.py", "requests.get('https://x')\n")
        design_path = _write_design(
            tmp_path,
            "design",
            "api.strata",
            "module api\nnode Api : trusted {\n    code \"api/**\";\n}\n",
        )
        result = sync_may_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        written = apply_sync_may(tmp_path, report)
        assert written == ("design/api.strata",)
        on_disk = design_path.read_text(encoding="utf-8")
        assert 'may "net.connect" via "api/net.py";' in on_disk

        result2 = sync_may_report(tmp_path)
        assert result2.is_ok
        assert not result2.danger_ok.has_drift
        written2 = apply_sync_may(tmp_path, result2.danger_ok)
        assert written2 == ()
