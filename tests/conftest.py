from pathlib import Path

import pytest

from frob.mutate import restore_stale_journals

# frob:ticket T-0885
#: This repo's own worktree root -- the same root `frob mutate`/
#: `run_mutations` journals backups under (`.frob/mutate-backup/`), so a
#: leftover journal from a PREVIOUS pytest session (an xdist worker crash
#: or an external SIGTERM killing the foreground pytest process, neither
#: of which reaches `run_mutations`' own normal-exit restore) gets picked
#: up here too.
_REPO_ROOT = Path(__file__).resolve().parent.parent


# frob:ticket T-0885
# frob:tests tests/test_mutate_journal.py::test_pytest_session_start_restores_leftover_journal kind="unit"  # noqa: E501
def pytest_configure(config: pytest.Config) -> None:
    """Restore any leftover mutation-journal backup at the START of the
    whole pytest session (T-0885), generalizing T-0857's `run_mutations`-
    only crash restore: an xdist worker crash or an external SIGTERM
    killing pytest mid-mutation never reaches `run_mutations`' own
    normal-exit restore, so a stale journal in `.frob/mutate-backup/`
    would otherwise sit unused (and the corrupted target file un-restored)
    until someone happens to invoke `frob mutate` against that same
    target again. Runs only on the controller process under
    `pytest-xdist` (`config.workerinput` is absent there, present on every
    worker) -- every worker restoring the same journals concurrently would
    be redundant at best and a `write_journal`-style race at worst, and
    `run_mutations` itself already re-checks at its own call site so a
    worker that legitimately needs a clean target still gets one."""
    if hasattr(config, "workerinput"):
        return
    restore_stale_journals(_REPO_ROOT)


PY_SAMPLE = b"""\
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

CPP_SAMPLE = b"""\
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


RUST_SAMPLE = b"""\
pub fn helper(x: i32) -> String {
    x.to_string()
}

pub struct Engine {
    cycles: i32,
}

impl Engine {
    pub fn run(&self, cycles: i32) {
        for _ in 0..cycles {}
    }

    pub fn status(&self) -> i32 {
        0
    }
}
"""


@pytest.fixture
def py_sample():
    return PY_SAMPLE


@pytest.fixture
def cpp_sample():
    return CPP_SAMPLE


@pytest.fixture
def rust_sample():
    return RUST_SAMPLE
