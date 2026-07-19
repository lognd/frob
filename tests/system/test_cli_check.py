"""End-to-end tests for `frob check` (Python quality gate)."""

import shutil
from pathlib import Path

import pytest

from tests.system.conftest import FIXTURES, run

# The TS system test needs a real `typescript` install to exercise `tsc`
# without hitting the network (npx would otherwise try to fetch it and
# hang/fail offline) -- reuse whatever node_modules a sibling checkout
# already has, and skip cleanly everywhere else (CI without node included).
_TS_NODE_MODULES = Path("/home/logan/projects/logand.app/frontend/node_modules")
_HAS_TS_TOOLCHAIN = (
    shutil.which("npx") is not None and (_TS_NODE_MODULES / ".bin" / "tsc").exists()
)


def _make_project(tmp_path: Path, src: str, pkg: str = "mypkg") -> Path:
    """Create a minimal Python project with pyproject.toml + a warn-severity
    frob.toml (the adoption baseline every real repo has, so the obligation
    gates run non-blocking while these tests exercise the code-quality tools)."""
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "{pkg}"\nversion = "0.1.0"\n'
        '[tool.ruff.lint]\nselect = ["E", "F", "W"]\n'
    )
    (tmp_path / "frob.toml").write_text(
        "[gates.severity]\n"
        'COV001 = "warn"\nTEST001 = "warn"\nTEST002 = "warn"\n'
        'TEST003 = "warn"\nTEST005 = "warn"\nTEST006 = "warn"\n'
    )
    src_dir = tmp_path / "src" / pkg
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text(src)
    return tmp_path


class TestCheckCleanProject:
    def test_clean_code_exits_zero(self, tmp_path):
        _make_project(tmp_path, "def add(x: int, y: int) -> int:\n    return x + y\n")
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            cwd=tmp_path,
        )
        assert r.returncode == 0, r.stdout + r.stderr

    def test_clean_code_reports_no_errors(self, tmp_path):
        _make_project(tmp_path, "def add(x: int, y: int) -> int:\n    return x + y\n")
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            cwd=tmp_path,
        )
        out = r.stdout + r.stderr
        assert (
            "error" not in out.lower() or "0 error" in out.lower() or r.returncode == 0
        )


class TestCheckVerbosity:
    """T-0202: default check output has no per-file/per-symbol log chatter;
    -v restores it."""

    def test_default_has_no_dispatch_or_digest_lines(self, tmp_path):
        """No -v: `dispatching`/`parsed`/`digested` lines must not appear."""
        _make_project(tmp_path, "def add(x: int, y: int) -> int:\n    return x + y\n")
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            cwd=tmp_path,
        )
        out = r.stdout + r.stderr
        assert "dispatching path=" not in out
        assert not any(line.startswith("parsed ") for line in out.splitlines())
        assert "digested " not in out

    def test_verbose_restores_dispatch_and_parse_lines(self, tmp_path):
        """-v: the per-file INFO firehose (at least `parsed ...`) is back."""
        _make_project(tmp_path, "def add(x: int, y: int) -> int:\n    return x + y\n")
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            "-v",
            cwd=tmp_path,
        )
        out = r.stdout + r.stderr
        assert any(line.startswith("parsed ") for line in out.splitlines())


class TestCheckBadCode:
    def test_unused_import_fails(self, tmp_path):
        src = "import os\n\ndef foo() -> None:\n    pass\n"
        _make_project(tmp_path, src)
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            "--skip-ty",
            "--skip-arch",
            "--skip-cycle",
            "--skip-dup",
            "--skip-bind",
            cwd=tmp_path,
        )
        assert r.returncode != 0

    def test_unused_import_output_mentions_error(self, tmp_path):
        src = "import os\n\ndef foo() -> None:\n    pass\n"
        _make_project(tmp_path, src)
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            "--skip-ty",
            "--skip-arch",
            "--skip-cycle",
            "--skip-dup",
            "--skip-bind",
            cwd=tmp_path,
        )
        out = r.stdout + r.stderr
        assert "F401" in out or "unused" in out.lower() or "error" in out.lower()


class TestCheckFixtures:
    def test_bad_python_code_fails(self, tmp_path):
        # bad_python fixture has noqa/type:ignore markers; use a raw bad file instead
        src = "import os\nimport sys\n\ndef foo() -> None:\n    pass\n"
        _make_project(tmp_path, src)
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            "--skip-ty",
            "--skip-arch",
            "--skip-cycle",
            "--skip-dup",
            "--skip-bind",
            cwd=tmp_path,
        )
        assert r.returncode != 0

    def test_simple_python_fixture_clean_passes(self):
        fixture = FIXTURES / "simple_python"
        r = run(
            "check",
            str(fixture),
            "--skip-tests",
            "--skip-exports",
            "--skip-arch",
            "--skip-cycle",
            "--skip-dup",
            "--skip-bind",
            # This fixture lives inside frob's own git repo, so `frob.gates`
            # resolves a real repo context and reports real (expected, by
            # design) obligation-graph violations -- irrelevant to what this
            # test checks (a clean ruff/ty/frob-cycle pass).
            "--skip-gates",
        )
        assert r.returncode == 0, r.stdout + r.stderr


class TestCheckSkipFlags:
    def test_skip_ruff(self, tmp_path):
        # Unused import would fail ruff; with --skip-ruff it should not
        src = "import os\n\ndef foo() -> None:\n    pass\n"
        _make_project(tmp_path, src)
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            "--skip-ty",
            "--skip-arch",
            "--skip-cycle",
            "--skip-dup",
            "--skip-bind",
            "--skip-ruff",
            cwd=tmp_path,
        )
        assert r.returncode == 0, r.stdout + r.stderr

    def test_skip_exports(self, tmp_path):
        _make_project(tmp_path, "def foo(): ...\n")
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-ty",
            "--skip-arch",
            "--skip-cycle",
            "--skip-dup",
            "--skip-bind",
            "--skip-exports",
            cwd=tmp_path,
        )
        # Should not fail on exports
        assert r.returncode == 0 or "exports" not in (r.stdout + r.stderr).lower()

    def test_json_output(self, tmp_path):
        import json

        _make_project(tmp_path, "def add(x: int, y: int) -> int:\n    return x + y\n")
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            "--json",
            cwd=tmp_path,
        )
        data = json.loads(r.stdout)
        assert "results" in data


class TestCheckErrors:
    def test_nonexistent_path_fails(self, tmp_path):
        r = run("check", str(tmp_path / "does_not_exist"))
        assert r.returncode != 0


class TestCheckTicketScopedAlwaysReportsOnFailure:
    def test_ticket_scoped_nonzero_exit_has_diagnostic_output(self, tmp_path):
        # frob:tests src/frob/app/check_runner.py::run kind="e2e"
        # T-0124: `frob check --ticket <id>` must never exit nonzero with no
        # diagnostic/summary output -- regression guard for the swallowed-
        # failure symptom reported against T-0075 (root-caused as already
        # fixed by T-0122/T-0125's logging-race repair; this pins the
        # behavior so it cannot silently regress).
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "pkg.py").write_text(
            "def add(x: int, y: int) -> int:\n    return x + y\n"
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)

        new = run(
            "ticket",
            "new",
            "--title",
            "unbound add()",
            "--kind",
            "bug",
            "--scope",
            "pkg.py",
            "--path",
            str(tmp_path),
        )
        assert new.returncode == 0, new.stdout + new.stderr
        ticket_id = "T-0001"
        assert ticket_id in (new.stdout + new.stderr)

        r = run("check", str(tmp_path), "--ticket", ticket_id, "--only", "gates")
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert out.strip(), "nonzero exit must never be silent"
        assert ticket_id in out or "TEST001" in out


def _git(*args, cwd):
    import subprocess

    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class TestCheckGatesStage:
    def test_only_gates_reports_violation_with_remedy(self, tmp_path):
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "pkg.py").write_text(
            "def add(x: int, y: int) -> int:\n    return x + y\n"
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)

        r = run("check", str(tmp_path), "--only", "gates")
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "TEST001" in out
        assert "frob:tests" in out  # every violation embeds its remedy

    def test_only_gates_passes_once_bound_and_tested(self, tmp_path):
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "pkg.py").write_text(
            "def add(x: int, y: int) -> int:\n    return x + y\n"
        )
        (tmp_path / "test_pkg.py").write_text(
            "from pkg import add\n\n"
            "def test_add() -> None:\n"
            "    # frob:tests pkg.py::add\n"
            "    assert add(1, 2) == 3\n"
        )
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0" ?><coverage line-rate="1.0"></coverage>'
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "bound", cwd=tmp_path)

        stamp = run("check", str(tmp_path), "--stamp-coverage")
        assert stamp.returncode == 0, stamp.stdout + stamp.stderr

        r = run("check", str(tmp_path), "--only", "gates")
        out = r.stdout + r.stderr
        assert "TEST001" not in out
        assert "TEST006" not in out
        assert r.returncode == 0, out


class TestCheckStampCoverage:
    def test_stamp_coverage_writes_stamp(self, tmp_path):
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0" ?><coverage line-rate="1.0"></coverage>'
        )
        r = run("check", str(tmp_path), "--stamp-coverage")
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        stamp = tmp_path / ".frob" / "coverage-stamp"
        assert stamp.exists()


class TestCheckStampBaselineAndDelta:
    """`frob check --stamp-baseline`/`--delta` CLI round trip (T-0107)."""

    def test_stamp_baseline_writes_stamp(self, tmp_path):
        # frob:tests tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta.test_stamp_baseline_writes_stamp
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "pkg.py").write_text(
            "def add(x: int, y: int) -> int:\n    return x + y\n"
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)

        r = run("check", str(tmp_path), "--stamp-baseline")
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        stamp = tmp_path / ".frob" / "baseline"
        assert stamp.exists()

    def test_delta_reports_only_new_violation(self, tmp_path):
        # frob:tests tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta.test_delta_reports_only_new_violation
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "pkg.py").write_text(
            "def add(x: int, y: int) -> int:\n    return x + y\n"
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)

        stamp = run("check", str(tmp_path), "--stamp-baseline")
        assert stamp.returncode == 0, stamp.stdout + stamp.stderr

        # Undelta'd run still sees the pre-existing violation.
        full = run("check", str(tmp_path), "--only", "gates")
        assert "add" in (full.stdout + full.stderr)

        # A genuinely new violation appears alongside the baselined one.
        (tmp_path / "pkg2.py").write_text(
            "def sub(x: int, y: int) -> int:\n    return x - y\n"
        )

        delta = run("check", str(tmp_path), "--only", "gates", "--delta")
        out = delta.stdout + delta.stderr
        assert delta.returncode != 0, out
        # Reported diagnostic lines (as opposed to internal debug logging,
        # which still names every violation while computing them) carry the
        # "[gates]" tag -- that's the set `--delta` actually filters.
        reported = [line for line in out.splitlines() if "[gates]" in line]
        assert any("pkg2.py" in line for line in reported)
        assert not any("pkg.py:" in line for line in reported)

    def test_delta_falls_back_to_full_set_when_no_baseline(self, tmp_path):
        # frob:tests tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta.test_delta_falls_back_to_full_set_when_no_baseline
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "pkg.py").write_text(
            "def add(x: int, y: int) -> int:\n    return x + y\n"
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)

        r = run("check", str(tmp_path), "--only", "gates", "--delta")
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "TEST001" in out


class TestFrobTomlCheckDefaults:
    def test_check_skip_from_frob_toml(self, tmp_path):
        """[check] skip in frob.toml disables stages without CLI flags."""
        import subprocess
        import sys

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text("def f():\n    return 1\n")
        (tmp_path / "frob.toml").write_text(
            '[check]\nskip = ["ty", "ruff", "gates", "dup", "arch", "cycle", '
            '"bind", "exports"]\n',
            encoding="utf-8",
        )
        r = subprocess.run(
            [sys.executable, "-m", "frob", "check", str(tmp_path), "--json"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        # every stage skipped -> no tool results at all
        import json

        data = json.loads(r.stdout)
        assert data.get("results") == []


class TestCheckPolyglot:
    """T-0229: polyglot repos must not silently skip a detected stage.

    Unpinned auto-detect runs every detected language's stage (gates
    included); pinning `check_type` is the deliberate, honest opt-out and
    must report a `SKIPPED: ...` line naming what it excludes."""

    def _make_polyglot_project(self, tmp_path: Path) -> Path:
        # frob:tests tests/system/test_cli_check.py::TestCheckPolyglot._make_polyglot_project
        """A repo with both a Rust and a Python marker file present."""
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "polyfix"\nversion = "0.1.0"\nedition = "2021"\n'
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.rs").write_text("fn main() {}\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "polyfix"\nversion = "0.1.0"\n'
        )
        (tmp_path / "frob.toml").write_text(
            "[gates.severity]\n"
            'COV001 = "warn"\nTEST001 = "warn"\nTEST002 = "warn"\n'
            'TEST003 = "warn"\nTEST005 = "warn"\nTEST006 = "warn"\n'
        )
        src_dir = tmp_path / "srcpy" / "polyfix"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text(
            "def add(x: int, y: int) -> int:\n    return x + y\n"
        )
        return tmp_path

    def test_unpinned_polyglot_runs_python_stage(self, tmp_path):
        """Auto-detect (no --type, no frob.toml check_type) still runs the
        python stage's tools even with a Cargo.toml also present -- the
        JSON tool list must not be limited to rust-only tools."""
        self._make_polyglot_project(tmp_path)
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--skip-exports",
            "--json",
            cwd=tmp_path,
        )
        import json

        data = json.loads(r.stdout)
        tools = {res["tool"] for res in data["results"]}
        # ruff-check only runs as part of the python stage -- its presence
        # proves the python stage actually ran, not just the rust stage
        # that `detect_project_type` alone would have picked (Cargo.toml
        # wins in the single-winner priority order).
        assert "ruff-check" in tools, tools

    def test_pinned_check_type_reports_skipped_line(self, tmp_path):
        """`--type python` on the same polyglot repo must name the rust
        stage it is deliberately excluding, not just go quiet about it."""
        self._make_polyglot_project(tmp_path)
        r = run(
            "check",
            str(tmp_path),
            "--type",
            "python",
            "--skip-tests",
            "--skip-exports",
            cwd=tmp_path,
        )
        out = r.stdout + r.stderr
        assert "SKIPPED" in out
        assert "rust" in out


@pytest.mark.skipif(
    not _HAS_TS_TOOLCHAIN, reason="no local typescript toolchain (node_modules) found"
)
class TestCheckTypescript:
    """End-to-end `frob check --type typescript` against a real tsc/npx.

    Reuses the sibling logand.app/frontend node_modules (via symlink) so
    `npx tsc` resolves locally instead of hitting the network -- keeps the
    test hermetic-ish while still exercising the real subprocess + parser
    path, not just parse_tsc in isolation."""

    def _make_ts_project(self, tmp_path: Path, src: str) -> Path:
        (tmp_path / "node_modules").symlink_to(_TS_NODE_MODULES)
        (tmp_path / "package.json").write_text(
            '{"name": "tsfixture", "private": true, "type": "module"}\n'
        )
        (tmp_path / "tsconfig.json").write_text(
            '{"compilerOptions": {"strict": true, "noEmit": true, '
            '"target": "ES2020", "module": "ESNext", "moduleResolution": '
            '"Bundler"}}\n'
        )
        (tmp_path / "src.ts").write_text(src)
        return tmp_path

    def test_clean_ts_passes_tsc(self, tmp_path):
        self._make_ts_project(
            tmp_path,
            "export function add(a: number, b: number): number {\n    return a + b;\n}\n",
        )
        r = run(
            "check",
            str(tmp_path),
            "--type",
            "typescript",
            "--skip-eslint",
            "--skip-prettier",
            "--skip-tests",
            cwd=tmp_path,
        )
        out = r.stdout + r.stderr
        assert r.returncode == 0, out

    def test_type_error_fails_tsc(self, tmp_path):
        self._make_ts_project(tmp_path, "export const x: number = 'not a number';\n")
        r = run(
            "check",
            str(tmp_path),
            "--type",
            "typescript",
            "--skip-eslint",
            "--skip-prettier",
            "--skip-tests",
            cwd=tmp_path,
        )
        out = r.stdout + r.stderr
        assert r.returncode == 1, out
        assert "TS2322" in out or "not assignable" in out
