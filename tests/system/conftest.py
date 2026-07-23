"""
Shared helpers for system (CLI end-to-end) tests.
"""

import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]
FIXTURES = Path(__file__).parent.parent / "fixtures"


# frob:ticket T-0627
# frob:tests tests/system/test_cli_check.py::TestCheckAgentRefusal.test_bare_check_refuses_under_frob_agent  # noqa: E501
def run(*args, input=None, cwd=None, env=None):
    """Run the `frob` CLI as a subprocess and capture its result (T-0364:
    the one shared entry point every system test dispatches through).

    T-0627: `env`, when given, is merged ON TOP OF (never replacing) the
    current process's environment via `os.environ | env` -- the same
    inherit-plus-override shape every other subprocess call in this suite
    relies on implicitly (PATH, the venv, etc.), needed so a test can flip
    one variable (e.g. `FROB_AGENT`) without losing the rest.
    """
    import os

    merged_env = os.environ | env if env else None
    return subprocess.run(
        FROB + list(args),
        capture_output=True,
        text=True,
        input=input,
        cwd=cwd,
        env=merged_env,
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
