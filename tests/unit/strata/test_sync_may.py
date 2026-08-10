"""Unit tests for T-1531 SYS100-core `may` grant auto-fix writer
(`frob.strata._sync_may`): widen (or create) a node's declared `may
"<kind>" via [...]` grant to cover an observed net/fs-write/exec effect
outside its current `via` surface (module docstring)."""

from __future__ import annotations

from pathlib import Path

from frob.strata import StrataError
from frob.strata._sync_may import (
    apply_sync_may,
    apply_sync_may_extended,
    node_body_span,
    sync_may_extended_report,
    sync_may_report,
)


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
        assert (
            'may "net.connect" via "api/net.py", "api/other.py";'
            in file_result.new_text
        )
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
            'module api\nnode Api : trusted {\n    code "api/**";\n}\n',
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
            'module api\nnode Api : trusted {\n    code "api/**";\n}\n',
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


class TestSyncMayExtendedReport:
    """T-1545: `sync_may_extended_report`'s pure-compute diff for SYS100
    EXTENDED (no per-file evidence -- always a whole-node, via-less
    grant insertion, module docstring)."""

    def test_inserts_whole_node_grant_for_extended_kind(self, tmp_path: Path):
        """A node with an observed `eval(` needle and no `may "eval"`
        declaration at all gets a bare, via-less grant inserted."""
        _write(tmp_path, "danger/run.py", "def f(x):\n    return eval(x)\n")
        design_path = _write_design(
            tmp_path,
            "design",
            "danger.strata",
            'module danger\nnode Danger : trusted {\n    code "danger/**";\n}\n',
        )
        result = sync_may_extended_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.has_drift
        assert len(report.files) == 1
        file_result = report.files[0]
        assert file_result.path == "design/danger.strata"
        assert len(file_result.diffs) == 1
        diff = file_result.diffs[0]
        assert diff.node == "Danger"
        assert diff.kind == "eval"
        assert 'may "eval";' in file_result.new_text
        # No `via` clause at all -- whole-node grant, module docstring's
        # deliberately conservative "never guess a file" posture.
        assert 'may "eval" via' not in file_result.new_text
        # Report never writes.
        assert design_path.read_text(encoding="utf-8") != file_result.new_text

    def test_no_drift_reports_clean(self, tmp_path: Path):
        """A node that already declares `may "eval";` (even via-less)
        reports zero drift -- `_extended_kind_violations` only fires when
        the kind is undeclared in ANY form."""
        _write(tmp_path, "danger/run.py", "def f(x):\n    return eval(x)\n")
        _write_design(
            tmp_path,
            "design",
            "danger.strata",
            "module danger\n"
            "node Danger : trusted {\n"
            '    code "danger/**";\n'
            '    may "eval";\n'
            "}\n",
        )
        result = sync_may_extended_report(tmp_path)
        assert result.is_ok
        assert not result.danger_ok.has_drift

    def test_no_design_files_reports_empty(self, tmp_path: Path):
        """No `.strata` files at all under `design/` -- `Ok` with an empty
        file list, mirroring `sync_may_report`'s own vacuous case."""
        (tmp_path / "design").mkdir()
        result = sync_may_extended_report(tmp_path)
        assert result.is_ok
        assert result.danger_ok.files == ()


class TestApplySyncMayExtended:
    """`apply_sync_may_extended`'s write side effect."""

    def test_writes_only_changed_files(self, tmp_path: Path):
        """Only a file whose report entry is `changed` gets written back;
        re-running afterwards reports clean and writes nothing."""
        _write(tmp_path, "danger/run.py", "def f(x):\n    return eval(x)\n")
        design_path = _write_design(
            tmp_path,
            "design",
            "danger.strata",
            'module danger\nnode Danger : trusted {\n    code "danger/**";\n}\n',
        )
        result = sync_may_extended_report(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        written = apply_sync_may_extended(tmp_path, report)
        assert written == ("design/danger.strata",)
        on_disk = design_path.read_text(encoding="utf-8")
        assert 'may "eval";' in on_disk

        result2 = sync_may_extended_report(tmp_path)
        assert result2.is_ok
        assert not result2.danger_ok.has_drift
        written2 = apply_sync_may_extended(tmp_path, result2.danger_ok)
        assert written2 == ()


# frob:ticket T-1895
class TestNodeBodySpan:
    """`node_body_span`'s brace-depth scan (T-1895: now the single shared
    home for this scanner -- `frob.gates._fix_engine_sync` imports it
    instead of keeping its own byte-identical copy)."""

    # frob:ticket T-1895
    def test_flat_body_returns_closing_brace_line(self):
        """A node body with no nested `{`/`}` closes at the first bare
        `}` line after the header."""
        lines = [
            "node Foo : trusted {",
            '    code "foo/**";',
            "}",
        ]
        assert node_body_span(lines, 0) == 2

    # frob:ticket T-1895
    def test_nested_braces_do_not_close_early(self):
        """A nested sub-block's own braces (e.g. `on crash { ... }`) must
        not terminate the scan before the node's own closing brace."""
        lines = [
            "node Foo : trusted {",
            '    code "foo/**";',
            "    on crash {",
            '        notify "team";',
            "    }",
            "}",
        ]
        assert node_body_span(lines, 0) == 5

    # frob:ticket T-1895
    def test_malformed_input_returns_last_line_best_effort(self):
        """No matching close brace at all: falls back to the last line
        index rather than raising."""
        lines = [
            "node Foo : trusted {",
            '    code "foo/**";',
        ]
        assert node_body_span(lines, 0) == 1
