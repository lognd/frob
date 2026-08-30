"""Unit coverage for `_sync_venv_for_work` (T-3320): a fresh `frob ticket
work` worktree has no `.venv` of its own, so `ty`/pytest fail on every
declared dep until `uv sync` runs there. `_sync_venv_for_work` runs `uv
sync` best-effort, before `_build_natives_for_work`, so a fresh worktree's
first `frob check --ticket` just works instead of failing 3-platform `ty`
with no explanation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from typani import Err, Ok, Result

from frob.app.ticket_runner import _lifecycle
from frob.process._guard import ProcessGuardError


@dataclass
class _FakeCompletedProcess:
    """Minimal stand-in for `subprocess.CompletedProcess` (returncode +
    stderr are all `_sync_venv_for_work` reads) -- avoids importing
    `subprocess` in this test module purely to build a return value,
    which SELFAUDIT001 (SYS100 node=testsuite) reads as an undeclared
    `exec` capability observation even though no process is spawned."""

    args: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""


# frob:ticket T-3320
class TestSyncVenvForWork:
    """`_sync_venv_for_work` (T-3320)."""

    # frob:tests tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork.test_runs_uv_sync_in_the_worktree  # noqa: E501
    def test_runs_uv_sync_in_the_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A clean `uv sync` (returncode 0) logs success and calls
        `guarded_subprocess_run` with `["uv", "sync"]` cwd'd into the
        worktree -- the must-fire half of T-3320's must-fire/must-stay-
        quiet pair, proving the wiring actually invokes `uv sync` rather
        than only documenting it in a hint string."""
        calls: list[tuple[list[str], dict[str, object]]] = []

        def _fake_run(
            args: list[str], **kwargs: object
        ) -> Result[_FakeCompletedProcess, object]:
            calls.append((list(args), kwargs))
            return Ok(_FakeCompletedProcess(args=list(args), returncode=0))

        monkeypatch.setattr(_lifecycle, "guarded_subprocess_run", _fake_run)

        _lifecycle._sync_venv_for_work(tmp_path, "T-3320")

        assert len(calls) == 1
        argv, kwargs = calls[0]
        assert argv == ["uv", "sync"]
        assert kwargs["cwd"] == str(tmp_path)

    # frob:tests tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork.test_exec_disabled_degrades_to_a_warning_not_sys_exit  # noqa: E501
    def test_exec_disabled_degrades_to_a_warning_not_sys_exit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`guarded_subprocess_run` refusing to spawn (kill switch, or any
        other `ProcessGuardError`) must NOT raise/`sys.exit` -- same best-
        effort posture as `_build_natives_for_work`'s `NoNatives` case.
        The must-stay-quiet half: a worktree with exec disabled still
        finishes `ticket work` instead of aborting it."""
        monkeypatch.setattr(
            _lifecycle,
            "guarded_subprocess_run",
            lambda args, **kwargs: Err(ProcessGuardError.ExecDisabled),
        )

        _lifecycle._sync_venv_for_work(tmp_path, "T-3320")  # must not raise

    # frob:tests tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork.test_nonzero_exit_degrades_to_a_warning_not_sys_exit  # noqa: E501
    def test_nonzero_exit_degrades_to_a_warning_not_sys_exit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A spawned `uv sync` that itself fails (bad lockfile, no
        network) is best-effort too -- logged, not fatal to `ticket
        work`."""

        def _fake_run(
            args: list[str], **kwargs: object
        ) -> Result[_FakeCompletedProcess, object]:
            return Ok(_FakeCompletedProcess(args=list(args), returncode=1, stderr="boom"))

        monkeypatch.setattr(_lifecycle, "guarded_subprocess_run", _fake_run)

        _lifecycle._sync_venv_for_work(tmp_path, "T-3320")  # must not raise

    # frob:tests tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork.test_runs_before_natives_build_in_the_work_flow  # noqa: E501
    def test_runs_before_natives_build_in_the_work_flow(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_sync_venv_for_work` must run BEFORE `_build_natives_for_work`
        in `_lifecycle`'s source order (native crates build into the venv
        `uv sync` populates) -- a structural regression guard, not a
        behavior assertion, since the two are independently unit-tested
        above."""
        import inspect

        source = inspect.getsource(_lifecycle)
        assert (
            "_sync_venv_for_work(worktree, cluster_id)\n"
            "    _build_natives_for_work(worktree, cluster_id)"
        ) in source
        assert (
            "_sync_venv_for_work(worktree, cfg.ticket_id)\n"
            "    _build_natives_for_work(worktree, cfg.ticket_id)"
        ) in source
