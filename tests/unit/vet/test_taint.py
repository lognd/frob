"""Unit tests for T-0781's SEC005 taint rule (`frob.vet._taint`,
`frob.gates._taint_gate`): repo-writable `.git`/`.frob` state reaching a
subprocess argv position with no validator hop or `--` terminator.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity
from frob.gates._taint_gate import taint_gate
from frob.vet._taint import taint_findings


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


class TestTaintFindings:
    """`frob.vet._taint.taint_findings` over small synthetic fixtures --
    the T-0781 acceptance criterion, both the firing and the clean side."""

    def test_unvalidated_state_read_reaching_argv_fires(self, tmp_path: Path) -> None:
        """A `.frob/`-sourced value in a subprocess argv list, no
        validator/`--` in between, is a finding naming source and sink."""
        path = _write(
            tmp_path,
            "unsafe.py",
            "import subprocess\n"
            "from pathlib import Path\n"
            "\n"
            "def run_it(root):\n"
            "    ref = (root / '.frob' / 'lease.json').read_text()\n"
            "    subprocess.run(['git', 'checkout', ref])\n",
        )
        findings = taint_findings(path)
        assert len(findings) == 1
        assert findings[0].source_line == 5
        assert findings[0].sink_line == 6
        assert findings[0].var_name == "ref"
        assert findings[0].sink_call == "run"

    def test_validated_value_does_not_fire(self, tmp_path: Path) -> None:
        """The same flow through a `validate_ref(...)` hop clears taint --
        no finding."""
        path = _write(
            tmp_path,
            "safe.py",
            "import subprocess\n"
            "from pathlib import Path\n"
            "\n"
            "def run_it(root):\n"
            "    ref = (root / '.frob' / 'lease.json').read_text()\n"
            "    ref = validate_ref(ref)\n"
            "    subprocess.run(['git', 'checkout', ref])\n",
        )
        assert taint_findings(path) == ()

    def test_dash_dash_terminator_clears_taint(self, tmp_path: Path) -> None:
        """A literal `'--'` element before the tainted element in the same
        argv list also clears the finding (the acceptance criterion's
        second discharge shape, alongside a validator hop)."""
        path = _write(
            tmp_path,
            "dashdash.py",
            "import subprocess\n"
            "from pathlib import Path\n"
            "\n"
            "def run_it(root):\n"
            "    ref = (root / '.git' / 'HEAD').read_text()\n"
            "    subprocess.run(['git', 'checkout', '--', ref])\n",
        )
        assert taint_findings(path) == ()

    def test_non_state_read_does_not_fire(self, tmp_path: Path) -> None:
        """A read with no `.git`/`.frob` marker in its own source text is
        not treated as a taint source at all."""
        path = _write(
            tmp_path,
            "unrelated.py",
            "import subprocess\n"
            "from pathlib import Path\n"
            "\n"
            "def run_it(root):\n"
            "    ref = (root / 'README.md').read_text()\n"
            "    subprocess.run(['cat', ref])\n",
        )
        assert taint_findings(path) == ()

    def test_dynamic_argv_list_is_not_falsely_cleared(self, tmp_path: Path) -> None:
        """A non-literal (dynamically built) argv argument is a disclosed
        gap -- no finding, but also not a claim of safety; this test
        pins the current honest boundary rather than a false all-clear."""
        path = _write(
            tmp_path,
            "dynamic.py",
            "import subprocess\n"
            "from pathlib import Path\n"
            "\n"
            "def run_it(root, argv):\n"
            "    ref = (root / '.frob' / 'lease.json').read_text()\n"
            "    argv.append(ref)\n"
            "    subprocess.run(argv)\n",
        )
        assert taint_findings(path) == ()

    def test_unparseable_file_returns_empty(self, tmp_path: Path) -> None:
        """A syntax-broken file returns `()`, not a crash -- PARSE001's
        problem, not this rule's."""
        path = _write(tmp_path, "broken.py", "def f(:\n")
        assert taint_findings(path) == ()


class TestTaintGate:
    """`frob.gates._taint_gate.taint_gate` -- the tracked-file-scan gate
    wrapper around `taint_findings`."""

    def test_taint_gate_no_findings_on_empty_tracked_set(self, tmp_path: Path) -> None:
        """An empty (non-git) directory yields zero violations, not a
        crash -- `git ls-files` failing is handled, not fatal."""
        assert taint_gate(tmp_path) == ()

    def test_taint_gate_emits_warn_severity_violation(self, tmp_path: Path) -> None:
        """A real git repo with one unsafe file produces exactly one
        `SEC005` `Violation` at `Severity.WARN`."""
        import subprocess as sp

        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(
            ["git", "config", "user.email", "t@example.com"],
            cwd=tmp_path,
            check=True,
        )
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        _write(
            tmp_path,
            "unsafe.py",
            "import subprocess\n"
            "from pathlib import Path\n"
            "\n"
            "def run_it(root):\n"
            "    ref = (root / '.frob' / 'lease.json').read_text()\n"
            "    subprocess.run(['git', 'checkout', ref])\n",
        )
        sp.run(["git", "add", "."], cwd=tmp_path, check=True)
        sp.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

        violations = taint_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "SEC005"
        assert violations[0].severity is Severity.WARN
        assert violations[0].file == "unsafe.py"
