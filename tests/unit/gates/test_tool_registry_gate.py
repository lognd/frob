"""Tests for `frob.gates.tool_registry_gate`/`bare_shutil_which_gate`
(TOOL001-003, T-5139/T-5267): the doctor.py `_RELEVANT_TOOLS` registry
wired into `frob check`'s gate set."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from frob.doctor import RelevantToolEntry, RelevantToolFailureKind, RelevantToolFinding
from frob.gates import bare_shutil_which_gate, tool_registry_gate
from frob.gates._models import Severity


class TestToolRegistryGate:
    """`tool_registry_gate` -- TOOL001 (missing) / TOOL002 (failed)."""

    # frob:tests src/frob/gates/__init__.py::tool_registry_gate
    def test_missing_relevant_tool_is_tool001(self, tmp_path: Path) -> None:
        """A relevant-and-missing tool reports one ERROR-severity TOOL001
        violation per rule it serves, message naming its install remedy."""
        entry = RelevantToolEntry(
            name="cargo-audit",
            rules_it_serves=("VET005",),
            install_remedy="cargo install x",
        )
        finding = RelevantToolFinding(
            entry=entry, kind=RelevantToolFailureKind.MISSING, detail="not on PATH"
        )
        with patch("frob.gates.relevant_tool_findings", return_value=[finding]):
            violations = tool_registry_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "TOOL001"
        assert violations[0].severity == Severity.ERROR
        assert "VET005" in violations[0].message
        assert "cargo install x" in violations[0].message

    # frob:tests src/frob/gates/__init__.py::tool_registry_gate
    def test_failed_relevant_tool_is_tool002(self, tmp_path: Path) -> None:
        """A relevant tool that was REACHED but failed (any
        `RelevantToolFailureKind` other than `MISSING`) is TOOL002, not
        TOOL001 -- a distinct, more actionable remedy."""
        entry = RelevantToolEntry(
            name="cargo-audit",
            rules_it_serves=("VET005",),
            install_remedy="cargo install x",
        )
        finding = RelevantToolFinding(
            entry=entry,
            kind=RelevantToolFailureKind.TIMEOUT,
            detail="timed out after 30s",
        )
        with patch("frob.gates.relevant_tool_findings", return_value=[finding]):
            violations = tool_registry_gate(tmp_path)
        assert [v.rule for v in violations] == ["TOOL002"]

    # frob:tests src/frob/gates/__init__.py::tool_registry_gate
    def test_allow_missing_tool_suppresses_tool001(self, tmp_path: Path) -> None:
        """`[tool_registry].allow_missing = ["cargo-audit"]` in
        `frob.toml` acks the finding: zero violations."""
        (tmp_path / "frob.toml").write_text(
            '[tool_registry]\nallow_missing = ["cargo-audit"]\n'
        )
        entry = RelevantToolEntry(
            name="cargo-audit",
            rules_it_serves=("VET005",),
            install_remedy="cargo install x",
        )
        finding = RelevantToolFinding(
            entry=entry, kind=RelevantToolFailureKind.MISSING, detail="not on PATH"
        )
        with patch("frob.gates.relevant_tool_findings", return_value=[finding]):
            assert tool_registry_gate(tmp_path) == ()

    # frob:tests src/frob/gates/__init__.py::tool_registry_gate
    def test_no_findings_is_clean(self, tmp_path: Path) -> None:
        """No relevant/missing tools at all: zero violations, never a
        crash on a missing frob.toml."""
        with patch("frob.gates.relevant_tool_findings", return_value=[]):
            assert tool_registry_gate(tmp_path) == ()


class TestBareShutilWhichGate:
    """`bare_shutil_which_gate` -- TOOL003."""

    # frob:tests src/frob/gates/__init__.py::bare_shutil_which_gate
    def test_flags_bare_shutil_which(self, tmp_path: Path) -> None:
        """A tracked file calling `shutil.which(...)` outside
        frob.doctor reports one WARN-severity TOOL003 violation."""
        (tmp_path / "mod.py").write_text("import shutil\nshutil.which('ripgrep')\n")
        with patch(
            "frob.gates._tool_registry_tracked_python_files", return_value=("mod.py",)
        ):
            violations = bare_shutil_which_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "TOOL003"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "mod.py"
        assert violations[0].line == 2

    # frob:tests src/frob/gates/__init__.py::bare_shutil_which_gate
    def test_registry_module_itself_is_exempt(self, tmp_path: Path) -> None:
        """`src/frob/doctor.py` (the registry's own home) is the one
        permitted caller and is never flagged."""
        doctor_dir = tmp_path / "src" / "frob"
        doctor_dir.mkdir(parents=True)
        (doctor_dir / "doctor.py").write_text(
            "import shutil\nshutil.which('cargo-audit')\n"
        )
        with patch(
            "frob.gates._tool_registry_tracked_python_files",
            return_value=("src/frob/doctor.py",),
        ):
            assert bare_shutil_which_gate(tmp_path) == ()

    # frob:tests src/frob/gates/__init__.py::bare_shutil_which_gate
    def test_clean_file_reports_nothing(self, tmp_path: Path) -> None:
        """A tracked file with no `shutil.which` call reports zero
        violations."""
        (tmp_path / "mod.py").write_text("x = 1\n")
        with patch(
            "frob.gates._tool_registry_tracked_python_files", return_value=("mod.py",)
        ):
            assert bare_shutil_which_gate(tmp_path) == ()
