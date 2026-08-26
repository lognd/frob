"""
Shared helpers for system (CLI end-to-end) tests.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

from frob.process._reap import arm_parent_death_signal

FROB = [sys.executable, "-m", "frob"]
FIXTURES = Path(__file__).parent.parent / "fixtures"

#: T-2980: the DEFAULT `run()` timeout, applied whenever a caller does not
#: pass its own `timeout=`. Before this, `timeout=None` meant "wait
#: forever" -- one such call (`test_ticket_readiness_is_not_an_arch001_finding`
#: spawning `frob check --only arch` with no timeout) hung the ubuntu-latest
#: CI job for 2+ hours with no traceback, and a repo-wide sweep
#: (`git grep -h "run(" -- tests/system/*.py | grep -vc "timeout="`) found
#: 468 other call sites with the same exposure.
#:
#: The mechanism, confirmed by local reproduction (minimal `-n`/
#: `--dist=loadgroup` fixture, not just theory): `pyproject.toml`'s outer
#: `--timeout=120 --timeout-method=thread` does NOT save you here. On
#: expiry it calls `os._exit(1)` on the whole worker process (see
#: `pytest_timeout.timeout_timer`) -- a hard kill that orphans the
#: worker's own subprocess child (this reproduces the exact
#: "Terminate orphan process" cleanup lines GitHub Actions printed for
#: the real incident) rather than raising inside the test. Worse, under
#: `--dist=loadgroup` (this repo's `addopts`), xdist's controller reacts
#: to "node down" by REDISPATCHING the same item to a fresh worker --
#: which wedges on the same unbounded wait and dies the same way,
#: consuming one worker after another until none are left, at which
#: point the run never terminates. `faulthandler_timeout = 100` only
#: dumps a diagnostic stack partway through this; it kills nothing.
#:
#: A timeout enforced INSIDE `run()` sidesteps the whole chain: expiry
#: raises a normal Python exception in the test itself, the worker
#: survives, xdist reports one FAILED test and moves on -- no kill, no
#: orphan, no redispatch loop. Chosen deliberately less than
#: `pyproject.toml`'s outer `--timeout=120` wall clock so this bound
#: fires first. Still generous enough that a real (loaded, 2-core) CI
#: runner's `frob check` does not flake on a slow-but-healthy run. A
#: test whose command legitimately needs longer passes its own explicit
#: `timeout=` at the call site.
DEFAULT_RUN_TIMEOUT_S = 100


# frob:ticket T-0627
# frob:ticket T-0880
# frob:ticket T-0909
# frob:ticket T-2980
# frob:tests tests/system/test_cli_check.py::TestCheckAgentRefusal.test_bare_check_refuses_under_frob_agent  # noqa: E501
# frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak.test_run_strips_dispatch_agent_env_vars  # noqa: E501
# frob:tests tests/system/test_cli_check.py::TestFrobTomlCheckDefaults.test_check_skip_from_frob_toml  # noqa: E501
# frob:tests tests/system/test_cli_ticket.py::TestTicketNewNonInteractive.test_new_does_not_prompt_or_hang_without_a_tty  # noqa: E501
# frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout.test_run_default_timeout_is_bounded_not_none  # noqa: E501
# frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout.test_run_expiry_raises_a_named_loud_error  # noqa: E501
def run(*args, input=None, cwd=None, env=None, timeout=None):
    """Run the `frob` CLI as a subprocess and capture its result (T-0364:
    the one shared entry point every system test dispatches through).

    T-0627: `env`, when given, is merged ON TOP OF (never replacing) the
    current process's environment via `os.environ | env` -- the same
    inherit-plus-override shape every other subprocess call in this suite
    relies on implicitly (PATH, the venv, etc.), needed so a test can flip
    one variable (e.g. `FROB_AGENT`) without losing the rest.

    T-0880: `FROB_AGENT`/`FROB_WORKTREE` are always stripped from the base
    environment before merging (unless a test explicitly sets them via
    `env`). System tests simulate an end user invoking the CLI directly --
    never a dispatched worktree agent -- so a *dispatching* agent's own
    lease env (set in its shell per the agent playbook, to satisfy `frob
    check`/`frob ticket` gate commands) must not leak into the subprocess
    under test, or it spuriously trips the T-0627 bare-check refusal / the
    T-0836 worktree-lease guard for tests that never asked for either.

    T-0909: `timeout` is passed straight through to `subprocess.run` so
    hang-guard tests (e.g. a non-interactive `ticket new` that must never
    block on a TTY prompt) can route through this shared helper too,
    instead of hand-rolling their own `subprocess.run` call and losing the
    env-stripping above.

    T-2980: when `timeout` is not given, `DEFAULT_RUN_TIMEOUT_S` applies --
    NEVER `None` (wait forever). Expiry raises a named `RuntimeError`
    naming the command and the budget, rather than letting a bare
    `subprocess.TimeoutExpired` (or, absent any timeout at all, an
    indefinite hang with no traceback) stand in for it.

    T-2991: T-2980 closed the HANG, but not the ORPHAN it uncovered.
    Two independent gaps, both closed here, matching the two ways a
    system test's `frob` subprocess child was measured surviving this
    process:

    1. **`preexec_fn=arm_parent_death_signal`**: arms `PR_SET_PDEATHSIG
       (SIGKILL)` on the freshly-forked child, before `exec`, using the
       SAME helper `frob.gates`'s own forkserver-helper self-arming
       already relies on (T-2849) -- no second implementation of "die
       with my parent" in this repo. This is the defense for the HARD
       kill: pytest-timeout's thread method calls `os._exit(1)` on the
       whole worker process on outer-timeout expiry (T-2980's own
       docstring), which never runs this function's `except` block at
       all -- nothing in Python ever gets a chance to kill the child,
       so only a kernel-level "my parent just died" signal can. Imported
       at MODULE scope (not inside `run()`) deliberately: `preexec_fn`
       runs in the child between `fork()` and `exec()`, and doing
       anything beyond a already-imported, already-resolved callable
       there risks deadlocking on an import lock some other thread holds
       at fork time (pytest-timeout's own timeout thread being exactly
       such a thread in this process).
    2. **`start_new_session=True` + `os.killpg` on `TimeoutExpired`**:
       `subprocess.run`'s own default timeout handling calls `.kill()`
       on ONLY the tracked child pid -- never its descendants. A `frob`
       invocation that itself spawns further children (a chunked
       `check`'s own subprocess calls, a `multiprocessing.forkserver`
       pool) leaves those completely unsignaled on an ordinary,
       run()-detected timeout, the exact "grandchildren spawned by a
       forkserver" gap this ticket's own plan named. `start_new_session`
       puts the child (and, by default inheritance, everything IT
       spawns that does not `setsid` itself) into its OWN process
       group headed by that child's pid; `os.killpg` on `TimeoutExpired`
       reaches every member of that group in one signal, not just the
       one pid `Popen` tracks.

    Neither mechanism alone is sufficient (case 1 has nothing to say
    about grandchildren case 2 has nothing to say about a hard kill
    this function's own code never runs for) -- see
    `arm_parent_death_signal`'s own docstring and
    `docs/modules/process.md#forkserver-reaping-t-2443` for the wider
    PDEATHSIG context this reuses rather than reinvents.
    """
    base_env = {
        k: v for k, v in os.environ.items() if k not in ("FROB_AGENT", "FROB_WORKTREE")
    }
    merged_env = base_env | env if env else base_env
    effective_timeout = DEFAULT_RUN_TIMEOUT_S if timeout is None else timeout

    # T-2991: `preexec_fn`/`start_new_session`/`os.killpg` are POSIX-only
    # (`Popen(preexec_fn=...)` raises outright on win32; this repo's CI
    # matrix includes windows-latest) -- PDEATHSIG has no Windows
    # equivalent anyway (`arm_parent_death_signal` itself already
    # degrades to a no-op there), so Windows keeps the pre-T-2991
    # `subprocess.run` shape unchanged rather than a fix that cannot
    # apply on that platform.
    if sys.platform == "win32":
        try:
            return subprocess.run(
                FROB + list(args),
                capture_output=True,
                text=True,
                input=input,
                cwd=cwd,
                env=merged_env,
                timeout=effective_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"system-test run() timed out after {effective_timeout}s waiting "
                f"on {FROB + list(args)!r} (T-2980: this command either hung, or "
                "legitimately needs longer -- pass an explicit timeout= at the "
                "call site rather than raising DEFAULT_RUN_TIMEOUT_S)"
            ) from exc

    proc = subprocess.Popen(
        FROB + list(args),
        stdin=subprocess.PIPE if input is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=merged_env,
        start_new_session=True,
        preexec_fn=arm_parent_death_signal,
    )
    try:
        stdout, stderr = proc.communicate(input=input, timeout=effective_timeout)
    except subprocess.TimeoutExpired as exc:
        # T-2991: kill the WHOLE process group, not just `proc` itself --
        # see this function's own docstring, point 2. Best-effort: the
        # group (or individual members of it) may already be gone by the
        # time this runs, which is success, not failure, so
        # ProcessLookupError is swallowed same as `Popen.kill()` already
        # does internally.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        raise RuntimeError(
            f"system-test run() timed out after {effective_timeout}s waiting on "
            f"{FROB + list(args)!r} (T-2980: this command either hung, or "
            "legitimately needs longer -- pass an explicit timeout= at the "
            "call site rather than raising DEFAULT_RUN_TIMEOUT_S)"
        ) from exc
    return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)


def git(*args: str, cwd: Path) -> None:
    """Run a `git` subcommand against `cwd`, raising on nonzero exit (T-0364:
    extracted from four system test modules that had copy-pasted this exact
    body -- see docs/modules/testing.md's system-test fixture note)."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


# frob:ticket T-0750
# frob:tests tests/system/test_cli_check.py::TestCheckCleanProject.test_clean_code_exits_zero  # noqa: E501
def git_init_and_config(path: Path, *, branch: str = "main") -> None:
    """Git-init `path` on `branch` with a fixed test identity (T-0750:
    extracted from the same three-line `git init` + two `git config` calls
    repeated inline across a dozen `test_cli_check.py` fixtures -- the
    gates a gitless `tmp_path` now errors loudly on, COV002/SCOPE001/
    TODO001, need a real git repo underneath, not just a working-tree diff
    that silently degrades)."""
    git("init", "-q", "-b", branch, cwd=path)
    git("config", "user.email", "test@example.com", cwd=path)
    git("config", "user.name", "Test", cwd=path)


def init_repo(tmp_path: Path, model: str) -> Path:
    """Build a minimal frob-enabled git repo (empty ledger, one `.strata`
    design file) and commit it -- the shared arrange step behind
    `frob sys doc`/`frob sys plan`'s CLI system tests (T-0364)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", cwd=repo)
    git("config", "user.email", "test@example.com", cwd=repo)
    git("config", "user.name", "Test", cwd=repo)
    (repo / "tickets.md").write_text("# Tickets\n")
    (repo / "design").mkdir()
    (repo / "design" / "m.strata").write_text(model)
    git("add", "-A", cwd=repo)
    git("commit", "-q", "-m", "init", cwd=repo)
    return repo


# ---------------------------------------------------------------------------
# Shared Python fixture source (matches tests/conftest.py PY_SAMPLE)
# ---------------------------------------------------------------------------

PY_FIXTURE = """\
import os
from pathlib import Path

def helper(x: int) -> str:
    return str(x) + "hello"

def another() -> None:
    do_something()
    do_more()

class MyClass:
    def process(self, data: bytes) -> list:
        return data.decode().splitlines()

    def _private(self) -> None:
        do_something()
        do_more()

class Other:
    def method(self) -> int:
        return 42
"""

CPP_FIXTURE = """\
#include <vector>
#include "local.h"

void helper(int x) {
    return;
}

class Engine {
public:
    void run(int cycles) {
        for (int i = 0; i < cycles; i++) {}
    }

    int status() {
        return 0;
    }
};
"""
