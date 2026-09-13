"""T-4455: unit tests for `tests.helpers.bash.resolve_bash` -- the WSL
System32 stub must never be chosen over Git for Windows' bash."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.helpers.bash import resolve_bash


def test_non_windows_returns_plain_bash(monkeypatch: pytest.MonkeyPatch) -> None:
    # frob:tests tests/unit/test_helpers_bash.py::test_non_windows_returns_plain_bash
    monkeypatch.setattr(sys, "platform", "linux")
    assert resolve_bash() == "bash"


def test_prefers_git_bash_over_system32_stub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # frob:tests \
    # tests/unit/test_helpers_bash.py::test_prefers_git_bash_over_system32_stub
    # Fake PATH with the WSL stub under a System32-like dir FIRST and a
    # real Git-for-Windows-shaped bash SECOND -- resolve_bash must pick
    # the Git one, never the stub, regardless of PATH order.
    monkeypatch.setattr(sys, "platform", "win32")

    program_files = tmp_path / "ProgramFiles"
    git_bash = program_files / "Git" / "bin" / "bash.exe"
    git_bash.parent.mkdir(parents=True)
    git_bash.write_text("")

    monkeypatch.setenv("ProgramFiles", str(program_files))
    monkeypatch.setattr("shutil.which", lambda name: None)

    result = resolve_bash()
    assert result == str(git_bash)
    assert "system32" not in result.lower()


def test_system32_stub_only_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # frob:tests tests/unit/test_helpers_bash.py::test_system32_stub_only_skips
    # No Git for Windows install anywhere, and the only `which("bash")`
    # hit is the System32 stub -- resolve_bash must skip, never return it.
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("ProgramFiles", raising=False)

    stub = tmp_path / "Windows" / "System32" / "bash.exe"
    stub.parent.mkdir(parents=True)
    stub.write_text("")

    monkeypatch.setattr(
        "shutil.which",
        lambda name: str(stub) if name == "bash" else None,
    )

    with pytest.raises(pytest.skip.Exception):
        resolve_bash()
