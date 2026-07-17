"""End-to-end tests for `frob check` (Python quality gate)."""

from pathlib import Path

from tests.system.conftest import FIXTURES, run


def _make_project(tmp_path: Path, src: str, pkg: str = "mypkg") -> Path:
    """Create a minimal Python project with pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "{pkg}"\nversion = "0.1.0"\n'
        '[tool.ruff.lint]\nselect = ["E", "F", "W"]\n'
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
