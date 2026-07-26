"""
Shared helpers for system (CLI end-to-end) tests.
"""

import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]
FIXTURES = Path(__file__).parent.parent / "fixtures"


# frob:ticket T-0627
# frob:ticket T-0880
# frob:ticket T-0909
# frob:tests tests/system/test_cli_check.py::TestCheckAgentRefusal.test_bare_check_refuses_under_frob_agent  # noqa: E501
# frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak.test_run_strips_dispatch_agent_env_vars  # noqa: E501
# frob:tests tests/system/test_cli_check.py::TestFrobTomlCheckDefaults.test_check_skip_from_frob_toml  # noqa: E501
# frob:tests tests/system/test_cli_ticket.py::TestTicketNewNonInteractive.test_new_does_not_prompt_or_hang_without_a_tty  # noqa: E501
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
    """
    import os

    base_env = {
        k: v for k, v in os.environ.items() if k not in ("FROB_AGENT", "FROB_WORKTREE")
    }
    merged_env = base_env | env if env else base_env
    return subprocess.run(
        FROB + list(args),
        capture_output=True,
        text=True,
        input=input,
        cwd=cwd,
        env=merged_env,
        timeout=timeout,
    )


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
