"""T-3887/T-4125: `frob.process._project_tool`, the one mechanism every
project-toolchain spawn (`ty`/`ruff`/`pytest`) routes through instead of
a bare PATH-resolved name or a hand-rolled `["uv", "run", ...]`."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from typani import Err, Ok

from frob.process._project_tool import (
    ProjectToolError,
    ToolIdentity,
    project_tool_argv,
    resolve_project_tool,
)


class TestProjectToolArgv:
    """`project_tool_argv` -- the one correct argv shape."""

    def test_shape(self, tmp_path: Path) -> None:
        """`uv run --no-sync --project <root> <tool> <*args>`, in that
        order -- T-4163: `--no-sync` stops a read-only tool spawn from
        lazily writing an untracked uv.lock/.venv into the target's own
        working tree."""
        argv = project_tool_argv(tmp_path, "ty", "check", "x.py")
        assert argv == [
            "uv",
            "run",
            "--no-sync",
            "--project",
            str(tmp_path),
            "ty",
            "check",
            "x.py",
        ]

    def test_no_args(self, tmp_path: Path) -> None:
        """Works with zero trailing args too."""
        argv = project_tool_argv(tmp_path, "pytest")
        assert argv == [
            "uv",
            "run",
            "--no-sync",
            "--project",
            str(tmp_path),
            "pytest",
        ]


class TestToolIdentity:
    def test_describe(self) -> None:
        """`describe()` renders `<path> (<version>)`."""
        identity = ToolIdentity(path="/x/ty", version="ty 0.0.46")
        assert identity.describe() == "/x/ty (ty 0.0.46)"


class TestResolveProjectTool:
    """`resolve_project_tool` -- resolved path + version, both Ok/Err."""

    def test_ok_resolves_path_and_version(self, tmp_path: Path) -> None:
        """Two successful spawns yield `Ok(ToolIdentity(...))` built from
        their stdout."""
        which_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="/proj/.venv/bin/ty\n", stderr=""
        )
        version_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ty 0.0.46\n", stderr=""
        )
        with patch(
            "frob.process._project_tool.guarded_subprocess_run",
            side_effect=[Ok(which_proc), Ok(version_proc)],
        ):
            result = resolve_project_tool(tmp_path, "ty")
        assert result.is_ok
        identity = result.danger_ok
        assert identity.path == "/proj/.venv/bin/ty"
        assert identity.version == "ty 0.0.46"

    def test_which_spawn_failure_is_err(self, tmp_path: Path) -> None:
        """A failed `which`-probe spawn is `Err(ResolveFailed)`, never a
        raised exception."""
        with patch(
            "frob.process._project_tool.guarded_subprocess_run",
            return_value=Err("boom"),
        ):
            result = resolve_project_tool(tmp_path, "ty")
        assert result.is_err
        assert result.danger_err == ProjectToolError.ResolveFailed

    def test_version_spawn_failure_is_err(self, tmp_path: Path) -> None:
        """A failed `--version` spawn (after a successful which-probe)
        is also `Err(ResolveFailed)`."""
        which_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="/proj/.venv/bin/ty\n", stderr=""
        )
        with patch(
            "frob.process._project_tool.guarded_subprocess_run",
            side_effect=[Ok(which_proc), Err("boom")],
        ):
            result = resolve_project_tool(tmp_path, "ty")
        assert result.is_err
        assert result.danger_err == ProjectToolError.ResolveFailed

    def test_nonzero_version_exit_is_still_ok(self, tmp_path: Path) -> None:
        """A `--version` spawn that RAN but exited nonzero still yields
        `Ok` -- the tool is still named, which is this function's whole
        purpose (T-4125: name the tool regardless)."""
        which_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="/proj/.venv/bin/ty\n", stderr=""
        )
        version_proc = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="unexpected flag"
        )
        with patch(
            "frob.process._project_tool.guarded_subprocess_run",
            side_effect=[Ok(which_proc), Ok(version_proc)],
        ):
            result = resolve_project_tool(tmp_path, "ty")
        assert result.is_ok
        assert result.danger_ok.version == "unexpected flag"

    def test_empty_which_output_uses_placeholder(self, tmp_path: Path) -> None:
        """An empty which-probe stdout (tool not found inside the
        project's own environment) yields a placeholder path, not a
        blank string a message would silently swallow."""
        which_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        version_proc = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr=""
        )
        with patch(
            "frob.process._project_tool.guarded_subprocess_run",
            side_effect=[Ok(which_proc), Ok(version_proc)],
        ):
            result = resolve_project_tool(tmp_path, "ty")
        assert result.is_ok
        assert result.danger_ok.path == "<unresolved:ty>"
