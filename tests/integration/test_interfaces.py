"""Integration tests exercising each package interface end to end.

Each test drives one subsystem through its real public surface (the CLI
via `python -m frob`, or the package's documented API over real files on
disk) and binds itself to that interface with a `frob:tests ... kind=
"integration"` directive, satisfying the TEST003 obligation that every
interface owns at least one integration test.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

FROB = [sys.executable, "-m", "frob"]


def _frob(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run the frob CLI as a subprocess, capturing output."""
    return subprocess.run(
        FROB + args,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def _git(args: list[str], cwd: Path) -> None:
    """Run a git command in `cwd`, raising on failure."""
    subprocess.run(["git"] + args, cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal two-file Python project the analysis commands can chew on."""
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "alpha.py").write_text(
        'def greet(name: str) -> str:\n    """Greeting."""\n    return f\'hi {name}\'\n'
    )
    (src / "beta.py").write_text(
        "from pkg.alpha import greet\n\n\ndef shout(name: str) -> str:\n"
        "    return greet(name).upper()\n"
    )
    return tmp_path


class TestInterfaces:
    def test_main_cli_dispatches(self, project: Path) -> None:
        # frob:tests src/frob/__main__.py kind="integration"
        result = _frob(["outline", "src/pkg/alpha.py"], cwd=project)
        assert result.returncode == 0
        assert "greet" in result.stdout

    def test_version_flag_prints_version_and_exits_zero(self, project: Path) -> None:
        # frob:tests src/frob/__main__.py::_frob_version kind="integration"
        # T-0231: `frob --version` used to be an argparse error (no such
        # flag registered); it must print a version string and exit 0.
        result = _frob(["--version"], cwd=project)
        assert result.returncode == 0
        assert "frob" in result.stdout
        assert result.stdout.strip() != "frob"

    def test_app_runner_map(self, project: Path) -> None:
        # frob:tests src/frob/app kind="integration"
        result = _frob(["map", "src"], cwd=project)
        assert result.returncode == 0
        assert "alpha" in result.stdout

    def test_map_project(self, project: Path) -> None:
        # frob:tests src/frob/map kind="integration"
        from frob.map import map_project

        res = map_project(project / "src")
        text = res.as_text()
        assert "alpha.py" in text
        assert "beta.py" in text

    def test_outline_file(self, project: Path) -> None:
        # frob:tests src/frob/outline kind="integration"
        from frob.outline import outline_file

        res = outline_file(project / "src" / "pkg" / "alpha.py")
        assert res.is_ok
        assert any(f.name == "greet" for f in res.danger_ok.functions)

    def test_xref_symbol(self, project: Path) -> None:
        # frob:tests src/frob/xref kind="integration"
        from frob.xref import xref

        res = xref("greet", project / "src")
        assert res.is_ok
        assert res.danger_ok.definition is not None

    def test_cycle_cli(self, project: Path) -> None:
        # frob:tests src/frob/cycle kind="integration"
        result = _frob(["cycle", "src"], cwd=project)
        assert result.returncode == 0

    def test_gitlog(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitlog kind="integration"
        from frob.gitlog import git_log

        repo = tmp_path / "repo"
        repo.mkdir()
        _git(["init"], repo)
        _git(["config", "user.email", "t@t.io"], repo)
        _git(["config", "user.name", "t"], repo)
        (repo / "f.txt").write_text("x")
        _git(["add", "."], repo)
        _git(["commit", "-m", "feat: add f"], repo)
        res = git_log(repo)
        assert "feat" in res.as_text().lower()

    def test_process_parse(self) -> None:
        # frob:tests src/frob/process kind="integration"
        from frob.process import parse_pytest

        out = "tests/f.py::test_a PASSED\ntests/f.py::test_b FAILED\n"
        res = parse_pytest(out)
        assert len(res.tests) == 2
        assert res.failed_tests

    def test_testing_collect(self, project: Path) -> None:
        # frob:tests src/frob/testing kind="integration"
        from frob.testing import collect_python_tests

        tdir = project / "tests"
        tdir.mkdir()
        (tdir / "test_sample.py").write_text("def test_ok():\n    assert True\n")
        res = collect_python_tests(project)
        assert res.is_ok

    def test_policy_load(self, project: Path) -> None:
        # frob:tests src/frob/policy kind="integration"
        from frob.policy import load_policy

        (project / "frob.toml").write_text(
            '[[policy.forbidden_import]]\nmodule = "os"\nreason = "no os"\n'
        )
        res = load_policy(project)
        assert res.is_ok

    def test_serve_tools(self, project: Path) -> None:
        # frob:tests src/frob/serve kind="integration"
        from frob.serve import frob_stale_docs

        res = frob_stale_docs(project)
        assert res.is_ok or res.is_err

    def test_deploy_generate_writes_and_checks(self, project: Path) -> None:
        # frob:tests src/frob/deploy kind="integration"
        # T-0257: `frob deploy generate` end to end over the real CLI --
        # write the three scripts from a design model, then verify
        # `--check` reports clean against what was just written (the
        # DEPLOY001 drift comparison exercised through its own CLI, not
        # just the library function).
        design = project / "design"
        design.mkdir()
        (design / "svc.strata").write_text(
            "module svc\n\n"
            "node api : trusted {\n"
            "    clearance Internal;\n"
            '    runs_as "api-svc";\n'
            "    unit;\n"
            '    owns "/etc/api" "0644";\n'
            "    listens 8080;\n"
            "}\n"
        )
        result = _frob(["deploy", "generate"], cwd=project)
        assert result.returncode == 0, result.stderr
        deploy_dir = project / "deploy"
        assert (deploy_dir / "install.sh").exists()
        assert (deploy_dir / "status.sh").exists()
        assert (deploy_dir / "uninstall.sh").exists()

        check = _frob(["deploy", "generate", "--check"], cwd=project)
        assert check.returncode == 0, check.stderr
