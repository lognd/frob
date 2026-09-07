"""Tests for `frob.vet._bare_toolchain` (finder) and `frob.gates.
_bare_toolchain.bare_toolchain_gate` (BARETOOL001 wiring), T-3887/T-4125."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from frob.gates._bare_toolchain import bare_toolchain_gate
from frob.gates._models import Severity
from frob.vet._bare_toolchain import bare_toolchain_findings


class TestBareToolchainFindings:
    """`bare_toolchain_findings` -- the AST finder."""

    def test_flags_bare_argv_literal(self, tmp_path: Path) -> None:
        """A `cmd = ["ty", "check", ...]` literal, spawned lines later
        (T-4125's own measured `_land_cmd.py` shape), is flagged."""
        f = tmp_path / "mod.py"
        f.write_text(
            "import subprocess\ncmd = ['ty', 'check', 'x.py']\nsubprocess.run(cmd)\n"
        )
        findings = bare_toolchain_findings(f)
        assert len(findings) == 1
        assert findings[0].tool == "ty"
        assert findings[0].line == 2

    def test_flags_bare_argv_at_call_site(self, tmp_path: Path) -> None:
        """A bare name built directly at the spawn call site is also
        flagged, not only the intermediate-variable shape."""
        f = tmp_path / "mod.py"
        f.write_text("import subprocess\nsubprocess.run(['ruff', 'check', '.'])\n")
        findings = bare_toolchain_findings(f)
        assert [fi.tool for fi in findings] == ["ruff"]

    def test_clean_on_project_tool_argv_spelling(self, tmp_path: Path) -> None:
        """The correct `['uv', 'run', '--project', ..., 'ty', ...]`
        shape (first element `'uv'`, not a bare tool name) is not
        flagged."""
        f = tmp_path / "mod.py"
        f.write_text(
            "import subprocess\n"
            "subprocess.run(['uv', 'run', '--project', str(root), 'ty', 'check'])\n"
        )
        assert bare_toolchain_findings(f) == []

    def test_clean_on_dynamic_first_element(self, tmp_path: Path) -> None:
        """A non-string-constant first element (a variable, `sys.
        executable`) is never flagged -- this pass only proves a
        HARDCODED bare name."""
        f = tmp_path / "mod.py"
        f.write_text(
            "import subprocess, sys\nsubprocess.run([sys.executable, '-m', 'pytest'])\n"
        )
        assert bare_toolchain_findings(f) == []

    def test_unrelated_list_literal_is_ignored(self, tmp_path: Path) -> None:
        """A list literal whose first element is a string but not in
        `BARE_TOOLCHAIN_NAMES` is not flagged."""
        f = tmp_path / "mod.py"
        f.write_text("xs = ['apple', 'banana']\n")
        assert bare_toolchain_findings(f) == []

    def test_syntax_error_yields_empty(self, tmp_path: Path) -> None:
        """An unparsable file yields `[]`, not a raised exception."""
        f = tmp_path / "broken.py"
        f.write_text("def f(:\n")
        assert bare_toolchain_findings(f) == []

    def test_missing_file_yields_empty(self, tmp_path: Path) -> None:
        """An unreadable/missing file yields `[]`, not a raised
        exception."""
        assert bare_toolchain_findings(tmp_path / "does_not_exist.py") == []


class TestBareToolchainGate:
    """`bare_toolchain_gate` -- the tracked-file-scan wiring."""

    def test_flags_bare_argv_literal(self, tmp_path: Path) -> None:
        """A tracked file with a bare-name argv literal reports one
        WARN-severity BARETOOL001 violation naming the file and line."""
        (tmp_path / "mod.py").write_text("cmd = ['pytest', '-q']\n")
        with patch("frob.gates._bare_toolchain._tracked_python_files") as mocked:
            mocked.return_value = ("mod.py",)
            violations = bare_toolchain_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "BARETOOL001"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "mod.py"
        assert violations[0].line == 1

    def test_clean_on_project_tool_argv_spelling(self, tmp_path: Path) -> None:
        """A tracked file using the correct `project_tool_argv` spelling
        (`'uv'` first) reports zero violations."""
        (tmp_path / "mod.py").write_text(
            "cmd = ['uv', 'run', '--project', '.', 'ruff', 'check']\n"
        )
        with patch("frob.gates._bare_toolchain._tracked_python_files") as mocked:
            mocked.return_value = ("mod.py",)
            violations = bare_toolchain_gate(tmp_path)
        assert violations == ()

    def test_empty_tracked_set_is_clean(self, tmp_path: Path) -> None:
        """No tracked files at all reports zero violations, never a
        crash."""
        with patch("frob.gates._bare_toolchain._tracked_python_files") as mocked:
            mocked.return_value = ()
            assert bare_toolchain_gate(tmp_path) == ()
