"""Regression test for T-0884: `_run_pytest_directly` (`frob ticket
evidence`'s no-`[[test.runner]]` fallback path in
`frob.app.ticket_runner`) must strip the caller's `FROB_WORKTREE`/
`FROB_AGENT` worktree-lease env before spawning the verification pytest
subprocess, so a recording agent's own lease never leaks into the tests
being verified (docs/guides/agent-playbook.md section 1/3).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typani.result import Ok

from frob.app import ticket_runner
from frob.app.ticket_runner import _run_pytest_directly


class TestRunPytestDirectlyStripsLeaseEnv:
    """`_run_pytest_directly` must never forward `FROB_WORKTREE`/`FROB_AGENT`
    into the spawned pytest subprocess env."""

    def test_strips_worktree_and_agent_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A caller with FROB_WORKTREE/FROB_AGENT set must not leak either
        into the env dict handed to the spawned subprocess."""
        monkeypatch.setenv("FROB_WORKTREE", "/some/leased/worktree")
        monkeypatch.setenv("FROB_AGENT", "1")
        monkeypatch.setenv("SOME_OTHER_VAR", "kept")

        captured: dict = {}

        def fake_guarded_subprocess_run(args, **kwargs):  # noqa: ANN001
            captured["env"] = kwargs.get("env")
            return Ok(
                subprocess.CompletedProcess(
                    args=args, returncode=0, stdout="", stderr=""
                )
            )

        monkeypatch.setattr(
            ticket_runner, "guarded_subprocess_run", fake_guarded_subprocess_run
        )

        result = _run_pytest_directly(tmp_path, ["tests/test_x.py::test_y"])

        assert result is True
        env = captured["env"]
        assert env is not None
        assert "FROB_WORKTREE" not in env
        assert "FROB_AGENT" not in env
        assert env.get("SOME_OTHER_VAR") == "kept"

    def test_missing_lease_env_is_fine(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the caller never set the lease vars, the spawn still
        succeeds and the env dict simply omits them (no KeyError)."""
        monkeypatch.delenv("FROB_WORKTREE", raising=False)
        monkeypatch.delenv("FROB_AGENT", raising=False)

        captured: dict = {}

        def fake_guarded_subprocess_run(args, **kwargs):  # noqa: ANN001
            captured["env"] = kwargs.get("env")
            return Ok(
                subprocess.CompletedProcess(
                    args=args, returncode=0, stdout="", stderr=""
                )
            )

        monkeypatch.setattr(
            ticket_runner, "guarded_subprocess_run", fake_guarded_subprocess_run
        )

        result = _run_pytest_directly(tmp_path, ["tests/test_x.py::test_y"])

        assert result is True
        assert "FROB_WORKTREE" not in captured["env"]
        assert "FROB_AGENT" not in captured["env"]
