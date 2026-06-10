"""
Skippable executable tests: run real tools on fixtures, pipe output through
frob parse, and verify the compact summary.

Each test class is skipped if the external tool is not installed.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FROB = [sys.executable, "-m", "frob"]
FIXTURES = Path(__file__).parent / "fixtures"


def run_frob(*args, input=None):
    return subprocess.run(
        FROB + list(args),
        capture_output=True,
        text=True,
        input=input,
    )


def _run(cmd, cwd=None, check=False):
    """Run an external command and return CompletedProcess."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=check,
    )


# ---------------------------------------------------------------------------
# ruff
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not installed")
class TestRuffExecutable:
    def test_ruff_finds_errors_in_bad_python(self):
        fixture = FIXTURES / "bad_python"
        ruff = _run(
            ["ruff", "check", "--output-format", "json", str(fixture / "src")],
            cwd=str(fixture),
        )
        # ruff exits non-zero when it finds issues
        assert ruff.returncode != 0 or ruff.stdout.strip() not in ("", "[]")

        frob = run_frob(
            "parse", "ruff",
            "--exit-code", str(ruff.returncode),
            input=ruff.stdout,
        )
        assert frob.returncode == 0, frob.stderr
        # At minimum ruff should have found something (F401 unused import)
        assert "F401" in frob.stdout or "error" in frob.stdout.lower() or "warning" in frob.stdout.lower()

    def test_ruff_clean_on_simple_python(self):
        fixture = FIXTURES / "simple_python"
        ruff = _run(
            ["ruff", "check", "--output-format", "json", str(fixture / "src")],
            cwd=str(fixture),
        )
        frob = run_frob(
            "parse", "ruff",
            "--exit-code", str(ruff.returncode),
            input=ruff.stdout,
        )
        assert frob.returncode == 0, frob.stderr
        assert "no issues" in frob.stdout.lower()


# ---------------------------------------------------------------------------
# pytest (always available since we run under pytest)
# ---------------------------------------------------------------------------


class TestPytestExecutable:
    def test_pytest_runs_simple_python(self, tmp_path):
        fixture = FIXTURES / "simple_python"
        result = _run(
            [sys.executable, "-m", "pytest", str(fixture / "tests"), "-v", "--tb=short"],
            cwd=str(fixture),
        )
        frob = run_frob(
            "parse", "pytest",
            "--exit-code", str(result.returncode),
            input=result.stdout + result.stderr,
        )
        assert frob.returncode == 0, frob.stderr
        # All tests in simple_python should pass
        assert result.returncode == 0
        assert "PASS" in frob.stdout or "passed" in frob.stdout.lower()

    def test_pytest_compact_summary_has_tool_name(self):
        fixture = FIXTURES / "simple_python"
        result = _run(
            [sys.executable, "-m", "pytest", str(fixture / "tests"), "--tb=short"],
            cwd=str(fixture),
        )
        frob = run_frob(
            "parse", "pytest",
            "--exit-code", str(result.returncode),
            input=result.stdout + result.stderr,
        )
        assert frob.returncode == 0, frob.stderr
        assert "pytest" in frob.stdout


# ---------------------------------------------------------------------------
# ty
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("ty") is None, reason="ty not installed")
class TestTyExecutable:
    def test_ty_finds_type_errors(self):
        fixture = FIXTURES / "bad_python"
        ty = _run(
            ["ty", "check", str(fixture / "src")],
            cwd=str(fixture),
        )
        frob = run_frob(
            "parse", "ty",
            "--exit-code", str(ty.returncode),
            input=ty.stdout + ty.stderr,
        )
        assert frob.returncode == 0, frob.stderr
        # ty should report at least one issue in bad_python
        assert ty.returncode != 0 or "error" in frob.stdout.lower()

    def test_ty_clean_on_simple_python(self):
        fixture = FIXTURES / "simple_python"
        ty = _run(
            ["ty", "check", str(fixture / "src")],
            cwd=str(fixture),
        )
        frob = run_frob(
            "parse", "ty",
            "--exit-code", str(ty.returncode),
            input=ty.stdout + ty.stderr,
        )
        assert frob.returncode == 0, frob.stderr


# ---------------------------------------------------------------------------
# gcc / g++
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc not installed")
class TestGccExecutable:
    def test_gcc_reports_error_on_bad_cpp(self):
        fixture = FIXTURES / "bad_cpp"
        gcc = _run(
            ["gcc", "-c", "main.cpp", "-o", "/dev/null"],
            cwd=str(fixture),
        )
        # gcc should fail due to missing semicolon
        assert gcc.returncode != 0

        frob = run_frob(
            "parse", "gcc",
            "--exit-code", str(gcc.returncode),
            input=gcc.stderr,
        )
        assert frob.returncode == 0, frob.stderr
        assert "error" in frob.stdout.lower()

    def test_gcc_compact_summary_has_tool_name(self):
        fixture = FIXTURES / "bad_cpp"
        gcc = _run(
            ["gcc", "-c", "main.cpp", "-o", "/dev/null"],
            cwd=str(fixture),
        )
        frob = run_frob(
            "parse", "gcc",
            "--exit-code", str(gcc.returncode),
            input=gcc.stderr,
        )
        assert frob.returncode == 0, frob.stderr
        assert "gcc" in frob.stdout


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not installed")
class TestGppExecutable:
    def test_gpp_reports_error_on_bad_cpp(self):
        fixture = FIXTURES / "bad_cpp"
        gpp = _run(
            ["g++", "-c", "main.cpp", "-o", "/dev/null"],
            cwd=str(fixture),
        )
        assert gpp.returncode != 0

        frob = run_frob(
            "parse", "g++",
            "--exit-code", str(gpp.returncode),
            input=gpp.stderr,
        )
        assert frob.returncode == 0, frob.stderr
        assert "error" in frob.stdout.lower()
