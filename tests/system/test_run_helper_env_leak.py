"""
T-0880 regression coverage: the shared `run()` helper in
`tests/system/conftest.py` must strip `FROB_AGENT`/`FROB_WORKTREE` from its
own base environment before merging, so a dispatched worktree agent's own
shell-level lease env (set per the agent playbook, for `frob check`/`frob
ticket` gate commands) never leaks into a system test's subprocess. These
tests simulate an end user invoking the CLI directly, never a dispatched
agent.
"""

import os
import sys
import time
from pathlib import Path

import pytest

import tests.system.conftest as _conftest_mod
from frob.process._reap import arm_parent_death_signal
from tests.system.conftest import DEFAULT_RUN_TIMEOUT_S, git, git_init_and_config, run


def _pid_alive(pid: int) -> bool:
    """`True` iff `pid` still names a live process -- `os.kill(pid, 0)`
    sends no signal, only checks existence/permission (POSIX-only, same
    as the T-2991 fix itself)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


PY_SOURCE = "def add(x: int, y: int) -> int:\n    return x + y\n"


def _make_project(tmp_path: Path, source: str, pkg: str = "mypkg") -> Path:
    """Build a minimal git-tracked Python frob project at `tmp_path` for a
    `frob check` subprocess call (mirrors `test_cli_check.py`'s own
    `_make_project` fixture shape, T-0806/T-0750: a real `pyproject.toml`
    and a committed git repo, so `frob check` recognizes the project type
    and its diff-scoped gates do not error on a git-less/uncommitted
    tree)."""
    git_init_and_config(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "{pkg}"\nversion = "0.1.0"\n'
        '[tool.ruff.lint]\nselect = ["E", "F", "W"]\n'
    )
    src_dir = tmp_path / "src" / pkg
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text(source)
    git("add", "-A", cwd=tmp_path)
    git("commit", "-q", "-m", "init", cwd=tmp_path)
    return tmp_path


class TestRunHelperEnvLeak:
    """`run()` must not let a dispatching agent's own FROB_AGENT/
    FROB_WORKTREE leak into the CLI subprocess it spawns for a test."""

    # frob:ticket T-0880
    def test_run_strips_dispatch_agent_env_vars(self, tmp_path, monkeypatch):
        # frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak.test_run_strips_dispatch_agent_env_vars  # noqa: E501
        monkeypatch.setenv("FROB_AGENT", "1")
        monkeypatch.setenv("FROB_WORKTREE", str(tmp_path))
        _make_project(tmp_path, PY_SOURCE)
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--only",
            "lint",
        )
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "FROB_AGENT" not in out

    # frob:ticket T-0880
    def test_run_explicit_env_can_still_set_frob_agent(self, tmp_path):
        # frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak.test_run_explicit_env_can_still_set_frob_agent  # noqa: E501
        _make_project(tmp_path, PY_SOURCE)
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            env={"FROB_AGENT": "1"},
        )
        out = r.stdout + r.stderr
        assert r.returncode == 1, out
        assert "FROB_AGENT" in out


class TestRunHelperDefaultTimeout:
    """T-2980: `run()` must never wait forever. `tests/system/conftest.py`'s
    `run(*args, ..., timeout=timeout)` used to pass `timeout=None`
    straight to `subprocess.run` whenever a caller omitted it, so any
    call that spawned a frob subprocess which itself wedged (a `frob
    check` invocation is the ubuntu-latest CI incident this ticket is
    named for) blocked the whole worker indefinitely. Under
    `--dist=loadgroup`, killing that worker at the outer
    `--timeout=120` wall clock does not end the run either: xdist
    redispatches the same wedging item to a fresh worker, which wedges
    and dies the same way, consuming workers one at a time forever --
    the exact mechanism reproduced locally for this ticket. Bounding
    the wait INSIDE `run()` raises a normal Python exception instead,
    so the test fails and the run moves on with no worker ever needing
    to be killed."""

    # frob:ticket T-2980
    def test_run_default_timeout_is_bounded_not_none(self):
        # frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout.test_run_default_timeout_is_bounded_not_none  # noqa: E501
        assert DEFAULT_RUN_TIMEOUT_S is not None
        assert DEFAULT_RUN_TIMEOUT_S > 0

    # frob:ticket T-2980
    def test_run_expiry_raises_a_named_loud_error(self):
        # frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout.test_run_expiry_raises_a_named_loud_error  # noqa: E501
        with pytest.raises(RuntimeError, match="timed out after"):
            run("--help", timeout=0.01)


@pytest.mark.skipif(
    sys.platform == "win32", reason="T-2991's process-group/PDEATHSIG fix is POSIX-only"
)
class TestRunHelperOrphanCleanup:
    """T-2991: `run()`'s subprocess child must not leave orphaned
    descendants behind on a `TimeoutExpired` -- the deeper defect T-2980's
    hang fix uncovered (see `run()`'s own docstring for the two
    independent mechanisms: `preexec_fn=arm_parent_death_signal` for a
    hard kill of `run()` itself never running its own `except` block, and
    `start_new_session`/`os.killpg` for a grandchild `subprocess.run`'s
    own default timeout kill never reaches)."""

    #: A minimal stand-in for "a `frob` invocation that spawns its own
    #: child" (a chunked `check`'s subprocess calls, a forkserver pool)
    #: -- writes the grandchild's pid to `sys.argv[1]` the instant it is
    #: spawned, then sleeps well past every timeout this test uses, same
    #: shape as `run()`'s real `python -m frob` target.
    _HELPER_SRC = (
        "import subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; "
        "time.sleep(300)'])\n"
        "with open(sys.argv[1], 'w') as f:\n"
        "    f.write(str(child.pid))\n"
        "time.sleep(300)\n"
    )

    # frob:ticket T-2991
    def test_timeout_kills_the_whole_process_group_not_just_the_direct_child(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/system/test_run_helper_env_leak.py::TestRunHelperOrphanCleanup.test_tim\
        # eout_kills_the_whole_process_group_not_just_the_direct_child
        helper = tmp_path / "helper.py"
        helper.write_text(self._HELPER_SRC)
        pidfile = tmp_path / "grandchild.pid"
        monkeypatch.setattr(_conftest_mod, "FROB", [sys.executable, str(helper)])

        with pytest.raises(RuntimeError, match="timed out after"):
            run(str(pidfile), timeout=2.0)

        deadline = time.monotonic() + 5.0
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pidfile.exists(), "helper never wrote its grandchild's pid in time"
        grandchild_pid = int(pidfile.read_text())

        # Give the SIGKILL a moment to actually reap the process (killpg
        # delivers the signal immediately; the kernel's own bookkeeping
        # is not instantaneous).
        deadline = time.monotonic() + 5.0
        while _pid_alive(grandchild_pid) and time.monotonic() < deadline:
            time.sleep(0.1)

        assert not _pid_alive(grandchild_pid), (
            f"grandchild pid={grandchild_pid} survived run()'s TimeoutExpired -- "
            "the process-group kill did not reach it"
        )

    # frob:ticket T-2991
    def test_run_arms_pdeathsig_and_uses_a_new_session(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/system/test_run_helper_env_leak.py::TestRunHelperOrphanCleanup.test_run\
        # _arms_pdeathsig_and_uses_a_new_session
        """Unlike the end-to-end kill test above, this pins the exact
        `Popen` kwargs `run()` passes -- so a future refactor that
        silently drops `preexec_fn`/`start_new_session` (e.g. "simplify"
        back to a bare `subprocess.run`) fails here even if it happens
        not to matter for this one helper script's timing."""
        import subprocess as _subprocess

        captured: dict[str, object] = {}
        real_popen = _subprocess.Popen

        class _RecordingPopen(real_popen):
            def __init__(self, *args, **kwargs):
                captured.update(kwargs)
                super().__init__(*args, **kwargs)

        monkeypatch.setattr(_subprocess, "Popen", _RecordingPopen)

        with pytest.raises(RuntimeError, match="timed out after"):
            run("--help", timeout=0.01)

        assert captured.get("preexec_fn") is arm_parent_death_signal
        assert captured.get("start_new_session") is True
