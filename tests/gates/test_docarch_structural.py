"""DOCARCH002 (T-4693) fixtures: the content-blind length cap (check 1)
and the ticket-citation-must-be-a-directive check (check 2), plus the
ratchet-severity integration -- every positive control T-4693's
acceptance criteria name, reproduced as a fixture."""

from __future__ import annotations

from pathlib import Path

from frob.gates._docarch_structural import (
    DOCARCH002_COMMENT_RUN_MAX_DEFAULT,
    DOCARCH002_DOCSTRING_MAX_DEFAULT,
    docarch002_violations,
    scan_citation_shape,
    scan_comment_length,
)
from frob.gates._ratchet import snapshot_ratchet


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs, mirroring the
    `_docstring_archaeology` test fixtures' own helper."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _git_init(root: Path) -> None:
    """Minimal git init so `_tracked_files` has a tree to walk."""
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "base", "--allow-empty"], cwd=root, check=True
    )


class TestScanCommentLength:
    """`scan_comment_length` -- check 1, the content-blind length cap."""

    # frob:tests src/frob/gates/_docarch_structural.py::scan_comment_length
    def test_flags_long_pure_algorithm_run(self) -> None:
        """MUST-FIRE: a 20-line pure-algorithm comment run with no ticket
        citation is flagged -- content-blind, no wording test. Placed
        after the module's own (short) header so the leading-header
        exemption (position-based, not content-based) does not apply."""
        text = "# short module header\n\n"
        text += "import os\n\n"
        text += "\n".join(f"# step {i}: pure algorithm prose" for i in range(20))
        text += "\ndef f():\n    pass\n"
        violations = scan_comment_length(Path("a.py"), text)
        assert any(v.rule == "DOCARCH002" for v in violations)

    # frob:tests src/frob/gates/_docarch_structural.py::scan_comment_length

    def test_short_run_is_quiet(self) -> None:
        """MUST-STAY-QUIET: a 5-line comment run stays under the cap."""
        text = "\n".join(f"# line {i}" for i in range(5)) + "\ndef f():\n    pass\n"
        violations = scan_comment_length(Path("a.py"), text)
        # frob:tests src/frob/gates/_docarch_structural.py::scan_comment_length
        assert violations == ()

    # frob:tests src/frob/gates/_docarch_structural.py::scan_comment_length
    def test_directive_run_is_exempt(self) -> None:
        """MUST-STAY-QUIET: a 20-line `frob:` directive block (a
        `# frob:tests \\` marker line alternating with its wrapped-path
        continuation payload, the real shape this repo's own directives
        take) is exempt by syntax, not by wording -- a majority (here,
        exactly half) of the run's lines carry the marker."""
        lines = []
        for i in range(10):
            lines.append("# frob:tests \\")
            lines.append(f"# tests/test_x.py::TestX.test_case_{i}")
        text = "\n".join(lines) + "\ndef f():\n    pass\n"
        violations = scan_comment_length(Path("a.py"), text)
        assert violations == ()

    # frob:tests src/frob/gates/_docarch_structural.py::scan_comment_length
    def test_leading_license_header_is_exempt(self) -> None:
        """MUST-STAY-QUIET: a 20-line module license header (the file's
        first comment run) is exempt by position, not by wording."""
        text = "\n".join(f"# License line {i}" for i in range(20))
        text += "\ndef f():\n    pass\n"
        violations = scan_comment_length(Path("a.py"), text)
        assert violations == ()

    # frob:tests src/frob/gates/_docarch_structural.py::scan_comment_length
    def test_long_docstring_flagged_short_is_quiet(self) -> None:
        """A 25-line docstring is flagged at the default `docstring_max`
        of 20; a 15-line one is not."""
        long_doc = "\n    ".join([f"line {i}" for i in range(25)])
        short_doc = "\n    ".join([f"line {i}" for i in range(15)])
        text = (
            f'def long_fn():\n    """{long_doc}\n    """\n    pass\n\n'
            f'def short_fn():\n    """{short_doc}\n    """\n    pass\n'
        )
        violations = scan_comment_length(Path("a.py"), text)
        assert any("long_fn" in (v.symref or "") for v in violations)
        assert not any("short_fn" in (v.symref or "") for v in violations)

    # frob:tests src/frob/gates/_docarch_structural.py::scan_comment_length
    def test_config_override_silences_default_fixture(self) -> None:
        """`comment_run_max = 30` silences the 20-line fixture, proving
        the config path is live and not just the built-in default."""
        text = "\n".join(f"# step {i}: pure algorithm prose" for i in range(20))
        text += "\ndef f():\n    pass\n"
        violations = scan_comment_length(Path("a.py"), text, comment_run_max=30)
        assert violations == ()

    def test_default_thresholds_match_spec(self) -> None:
        """The module constants match T-4693's stated defaults."""
        assert DOCARCH002_COMMENT_RUN_MAX_DEFAULT == 12
        assert DOCARCH002_DOCSTRING_MAX_DEFAULT == 20


class TestScanCitationShape:
    """`scan_citation_shape` -- check 2, citations must be directives."""

    # frob:tests src/frob/gates/_docarch_structural.py::scan_citation_shape
    def test_directive_and_pointer_are_quiet(self) -> None:
        """MUST-STAY-QUIET: `frob:ticket T-1234` and a single-line
        `# see T-1234` pointer are both quiet under check 2."""
        text = (
            "# frob:ticket T-1234\n"
            "def f():\n    pass\n\n"
            "# see T-1234\n"
            "def g():\n    pass\n"
        )
        violations = scan_citation_shape(Path("a.py"), text)
        assert violations == ()

    # frob:tests src/frob/gates/_docarch_structural.py::scan_citation_shape
    def test_bare_citation_with_prose_is_flagged(self) -> None:
        """MUST-FIRE: a `# T-1234:` line followed by 3 prose lines is
        flagged (2+ comment lines under a bare citation)."""
        text = (
            "# T-1234: this used to work differently\n"
            "# and then something changed\n"
            "# for a reason nobody wrote down\n"
            "def f():\n    pass\n"
        )
        violations = scan_citation_shape(Path("a.py"), text)
        assert len(violations) == 1
        assert violations[0].line == 1
        assert "frob narrative move" in violations[0].message


class TestDocarch002RatchetSeverity:
    """`docarch002_violations` -- ratchet-adjusted repo scan (T-0569)."""

    # frob:tests src/frob/gates/_docarch_structural.py::docarch002_violations
    def test_baselined_finding_stays_warn_new_one_errors(self, tmp_path: Path) -> None:
        """A finding already baselined into the DOCARCH002 pool stays
        WARN; a brand-new one at a different site reports ERROR."""
        _write(
            tmp_path,
            "src/old.py",
            "import os\n\n"
            + "\n".join(f"# step {i}" for i in range(20))
            + "\ndef f():\n    pass\n",
        )
        _write(
            tmp_path,
            "frob.toml",
            '[gates.ratchet]\nrules = ["DOCARCH002"]\n',
        )
        _git_init(tmp_path)

        pre = docarch002_violations(tmp_path)
        keys = [f"{v.file}:{v.line}" for v in pre]
        result = snapshot_ratchet(tmp_path, "DOCARCH002", keys)
        assert result.is_ok

        # Baselined finding: still WARN.
        after_baseline = docarch002_violations(tmp_path)
        assert all(v.severity == "warn" for v in after_baseline)

        # A brand-new over-cap run in a different file: ERROR.
        import subprocess

        _write(
            tmp_path,
            "src/new.py",
            "import os\n\n"
            + "\n".join(f"# fresh step {i}" for i in range(20))
            + "\ndef g():\n    pass\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        after_new = docarch002_violations(tmp_path)
        # T-5478: Violation.file is str(Path(rel)) -- native separator
        # (backslash on Windows) -- so the comparison literal must go
        # through the same Path(...) conversion, not stay POSIX-only.
        new_file_violations = [
            v for v in after_new if v.file == str(Path("src/new.py"))
        ]
        assert new_file_violations
        assert all(v.severity == "error" for v in new_file_violations)


class TestGateEntry:
    """`docarch_structural_gate` -- the `GATE_RUNNERS` entry point wrapper
    around `docarch002_violations` (T-4693)."""

    # frob:tests src/frob/gates/_docarch_structural.py::docarch_structural_gate
    def test_delegates(self, tmp_path: Path) -> None:
        """The gate entry point returns exactly what `docarch002_violations`
        reports for the same root, proving the wiring is a pure alias."""
        from frob.gates._docarch_structural import docarch_structural_gate

        _write(
            tmp_path,
            "src/mod.py",
            "import os\n\n"
            + "\n".join(f"# step {i}" for i in range(20))
            + "\ndef f():\n    pass\n",
        )
        _git_init(tmp_path)

        direct = docarch002_violations(tmp_path)
        via_gate = docarch_structural_gate(tmp_path)
        assert via_gate == direct
        assert via_gate
