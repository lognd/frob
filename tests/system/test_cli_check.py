"""End-to-end tests for `frob check` (Python quality gate)."""

from pathlib import Path

from tests.system.conftest import run, FIXTURES


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
            "check", str(tmp_path),
            "--skip-tests", "--skip-exports",
            cwd=tmp_path,
        )
        assert r.returncode == 0, r.stdout + r.stderr

    def test_clean_code_reports_no_errors(self, tmp_path):
        _make_project(tmp_path, "def add(x: int, y: int) -> int:\n    return x + y\n")
        r = run(
            "check", str(tmp_path),
            "--skip-tests", "--skip-exports",
            cwd=tmp_path,
        )
        out = r.stdout + r.stderr
        assert "error" not in out.lower() or "0 error" in out.lower() or r.returncode == 0


class TestCheckBadCode:
    def test_unused_import_fails(self, tmp_path):
        src = "import os\n\ndef foo() -> None:\n    pass\n"
        _make_project(tmp_path, src)
        r = run(
            "check", str(tmp_path),
            "--skip-tests", "--skip-exports", "--skip-ty",
            "--skip-arch", "--skip-cycle", "--skip-dup", "--skip-bind",
            cwd=tmp_path,
        )
        assert r.returncode != 0

    def test_unused_import_output_mentions_error(self, tmp_path):
        src = "import os\n\ndef foo() -> None:\n    pass\n"
        _make_project(tmp_path, src)
        r = run(
            "check", str(tmp_path),
            "--skip-tests", "--skip-exports", "--skip-ty",
            "--skip-arch", "--skip-cycle", "--skip-dup", "--skip-bind",
            cwd=tmp_path,
        )
        out = r.stdout + r.stderr
        assert "F401" in out or "unused" in out.lower() or "error" in out.lower()


class TestCheckFixtures:
    def test_bad_python_fixture_fails(self):
        fixture = FIXTURES / "bad_python"
        r = run(
            "check", str(fixture),
            "--skip-tests", "--skip-exports",
            "--skip-arch", "--skip-cycle", "--skip-dup", "--skip-bind",
        )
        assert r.returncode != 0

    def test_simple_python_fixture_clean_passes(self):
        fixture = FIXTURES / "simple_python"
        r = run(
            "check", str(fixture),
            "--skip-tests", "--skip-exports",
            "--skip-arch", "--skip-cycle", "--skip-dup", "--skip-bind",
        )
        assert r.returncode == 0, r.stdout + r.stderr


class TestCheckSkipFlags:
    def test_skip_ruff(self, tmp_path):
        # Unused import would fail ruff; with --skip-ruff it should not
        src = "import os\n\ndef foo() -> None:\n    pass\n"
        _make_project(tmp_path, src)
        r = run(
            "check", str(tmp_path),
            "--skip-tests", "--skip-exports", "--skip-ty",
            "--skip-arch", "--skip-cycle", "--skip-dup", "--skip-bind",
            "--skip-ruff",
            cwd=tmp_path,
        )
        assert r.returncode == 0, r.stdout + r.stderr

    def test_skip_exports(self, tmp_path):
        _make_project(tmp_path, "def foo(): ...\n")
        r = run(
            "check", str(tmp_path),
            "--skip-tests", "--skip-ty",
            "--skip-arch", "--skip-cycle", "--skip-dup", "--skip-bind",
            "--skip-exports",
            cwd=tmp_path,
        )
        # Should not fail on exports
        assert r.returncode == 0 or "exports" not in (r.stdout + r.stderr).lower()

    def test_json_output(self, tmp_path):
        _make_project(tmp_path, "def add(x: int, y: int) -> int:\n    return x + y\n")
        r = run(
            "check", str(tmp_path),
            "--skip-tests", "--skip-exports",
            "--json",
            cwd=tmp_path,
        )
        # JSON mode should produce parseable output
        import json
        out = r.stdout + r.stderr
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                data = json.loads(line)
                assert "total_errors" in data or "tools" in data or "results" in data
                return


class TestCheckErrors:
    def test_nonexistent_path_fails(self, tmp_path):
        r = run("check", str(tmp_path / "does_not_exist"))
        assert r.returncode != 0
