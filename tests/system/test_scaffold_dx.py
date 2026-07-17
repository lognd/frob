"""End-to-end DX acceptance test for `frob scaffold`.

Renders the python-tool template into a temp dir and runs the real
lint/typecheck/test/frob-check pipeline `make check` would run, verifying
a freshly scaffolded project is green with zero manual fixups -- the
"minimal boilerplate" bar the scaffold overhaul exists to hit.

Slow (spawns `uv sync` + a real venv): skip with `-m "not slow"` for a
fast local loop; CI runs it in full.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from frob.scaffold.project import render_project

pytestmark = pytest.mark.slow


def _uv_available() -> bool:
    return shutil.which("uv") is not None


def _subprocess_env() -> dict[str, str]:
    """Parent env minus VIRTUAL_ENV/UV_PROJECT_ENVIRONMENT.

    This test suite itself runs under `uv run pytest` inside frob's own
    dev venv, which sets VIRTUAL_ENV -- inherited by every subprocess.run
    call by default. `uv run`/`ty` prefer that env var over the
    scaffolded project's own `.venv`, so the child tools would silently
    typecheck against frob's dependencies (missing `dotenv`, etc.)
    instead of the freshly scaffolded project's. A real terminal driving
    `make check` never has this var set, so strip it to match.
    """
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    return env


@pytest.mark.skipif(not _uv_available(), reason="uv not on PATH")
def test_python_tool_scaffold_passes_check_immediately(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    result = render_project("python-tool", "demo", project_dir)
    assert result.is_ok, result

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project_dir, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "add", "-A"],
        cwd=project_dir,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t.com",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "init",
        ],
        cwd=project_dir,
        check=True,
    )

    sync = subprocess.run(
        ["uv", "sync"], cwd=project_dir, capture_output=True, text=True
    )
    assert sync.returncode == 0, sync.stdout + sync.stderr

    lint = subprocess.run(
        ["uv", "run", "ruff", "check", "src/", "tests/"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr

    fmt = subprocess.run(
        ["uv", "run", "ruff", "format", "--check", "src/", "tests/"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    assert fmt.returncode == 0, fmt.stdout + fmt.stderr

    typecheck = subprocess.run(
        ["uv", "run", "ty", "check", "src/"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    assert typecheck.returncode == 0, typecheck.stdout + typecheck.stderr

    test = subprocess.run(
        ["uv", "run", "pytest", "tests/", "--cov=src", "--cov-report=xml"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    assert test.returncode == 0, test.stdout + test.stderr

    # A user's `frob` is the globally installed uv tool (`uv tool install
    # frob`), which wraps its own subprocess calls (ruff/ty) through that
    # tool's own resolution -- not this repo's dev checkout, whose `frob`
    # on PATH during `uv run pytest` runs against frob's OWN venv/deps and
    # would report false failures (e.g. `dotenv` unresolved) for a
    # scaffolded project's separate venv. Prefer the global install; skip
    # if this environment never installed one.
    global_frob = Path.home() / ".local" / "bin" / "frob"
    frob_bin = str(global_frob) if global_frob.exists() else shutil.which("frob")
    if frob_bin is None:
        pytest.skip("frob binary not on PATH (dev install only)")

    stamp = subprocess.run(
        [frob_bin, "check", "--stamp-coverage"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    assert stamp.returncode == 0, stamp.stdout + stamp.stderr

    check = subprocess.run(
        [frob_bin, "check"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert "0 errors" in (check.stdout + check.stderr)


def test_all_registered_types_render_without_error(tmp_path: Path) -> None:
    from frob.scaffold.project import list_project_types

    for project_type in list_project_types():
        out = tmp_path / project_type.replace("-", "_")
        result = render_project(project_type, "demo", out)
        assert result.is_ok, f"{project_type}: {result}"
