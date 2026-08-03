import faulthandler
import os
import signal
from pathlib import Path

import pytest

from frob.lang import reset_parse_cache
from frob.mutate import restore_stale_journals

# frob:ticket T-1433
_STACKDUMP_ENV = "FROB_COVERAGE_STACKDUMP"
"""Opt-in env var (T-1433): when set to a nonempty, non-`0`/`false` value,
`pytest_configure` below installs a `SIGUSR1` handler that dumps every
live thread's stack (via `faulthandler.dump_traceback`) of the process
that receives it -- xdist controller AND every worker, since each is a
separate process and only the worker(s) actually holding a wedged
lock have anything interesting to dump. Off by default: the handler
itself is near-zero-cost once installed, but installing a signal handler
unconditionally in every ordinary test run (most of which never wedge)
is unnecessary surface area for an ordinary `pytest`/`frob test`
invocation that has no wedge-diagnosis need. The `coverage:` Makefile
recipe sets this for exactly the two phases T-1433's incidents wedged in
(the xdist phase and the `-n 0` serial rerun)."""


# frob:ticket T-1433
# frob:waive WIRE001 reason="registered as tests/conftest.py's SIGUSR1 signal handler \
# by _install_stackdump_handler (same module, called from pytest_configure below) -- \
# the call-graph analysis does not resolve a signal.signal(...) registration as a call \
# edge, so this reads as uncalled even though it is the live handler for every pytest \
# process this recipe spawns once FROB_COVERAGE_STACKDUMP=1 is set" \
# follow_up="T-1466"
def _dump_all_thread_stacks(_signum: int, _frame: object) -> None:
    """`SIGUSR1` handler (T-1433): write every live thread's stack in
    THIS process to a per-pid file under `.frob/stackdumps/` so a wedge
    self-diagnoses instead of leaving only a bare `wchan=futex_wait_queue`
    with no indication of which lock, in which function, on which of the
    controller/worker processes. Appends (`"a"`) rather than truncates --
    a wedge investigated by sending `SIGUSR1` more than once (e.g. once
    per suspect-narrowing probe) keeps every dump, timestamped by the
    surrounding `faulthandler.dump_traceback` call's own thread-id/frame
    text, not just the last one."""
    dump_dir = Path(".frob") / "stackdumps"
    dump_dir.mkdir(parents=True, exist_ok=True)
    dump_path = dump_dir / f"pid-{os.getpid()}.txt"
    with dump_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n--- SIGUSR1 stack dump, pid={os.getpid()} ---\n")
        faulthandler.dump_traceback(file=fh, all_threads=True)


# frob:ticket T-1433
# frob:tests tests/unit/test_conftest_stackdump.py::TestStackdumpHandler.test_sigusr1_writes_all_thread_stacks_when_enabled  # noqa: E501
# frob:tests tests/unit/test_conftest_stackdump.py::TestStackdumpHandler.test_handler_not_installed_when_env_unset  # noqa: E501
# frob:waive WIRE001 reason="called from pytest_configure below (same module) -- \
# WIRE001 reads that as having no caller OUTSIDE tests because pytest_configure is \
# itself only ever invoked by pytest's own hook machinery, never by frob's production \
# entrypoints; this is test-infrastructure code by design (tests/conftest.py), the \
# same shape as every other pytest_configure-only helper in this file" \
# follow_up="T-1466"
def _install_stackdump_handler() -> None:
    """Install `_dump_all_thread_stacks` as the `SIGUSR1` handler for THIS
    process (T-1433), gated on `_STACKDUMP_ENV` -- called from
    `pytest_configure` for BOTH the xdist controller and every worker
    (unlike the T-0885 journal-restore call above, which is
    controller-only): the wedge this exists to diagnose can live in
    either, and only sending the signal to the actually-stuck process
    produces a useful dump. `SIGUSR1` is POSIX-only (absent on Windows,
    where `signal.SIGUSR1` does not exist); silently a no-op there since
    the coverage recipe this serves is itself POSIX/Makefile-only."""
    # frob:waive SEC110 reason="FROB_COVERAGE_STACKDUMP is a boolean opt-in feature \
    # flag (same shape as the existing FROB_AGENT/FROB_NO_TELEMETRY precedent), gating \
    # whether a SIGUSR1 stack-dump handler is installed; it carries no \
    # secret/confidential value"
    value = os.environ.get(_STACKDUMP_ENV, "")
    if value.strip().lower() in ("", "0", "false"):
        return
    sigusr1 = getattr(signal, "SIGUSR1", None)
    if sigusr1 is None:  # pragma: no cover - POSIX-only, not exercised on Windows CI
        return
    signal.signal(sigusr1, _dump_all_thread_stacks)


# frob:ticket T-0885
#: This repo's own worktree root -- the same root `frob mutate`/
#: `run_mutations` journals backups under (`.frob/mutate-backup/`), so a
#: leftover journal from a PREVIOUS pytest session (an xdist worker crash
#: or an external SIGTERM killing the foreground pytest process, neither
#: of which reaches `run_mutations`' own normal-exit restore) gets picked
#: up here too.
_REPO_ROOT = Path(__file__).resolve().parent.parent


# frob:ticket T-0885
# frob:ticket T-1433
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
    worker that legitimately needs a clean target still gets one.

    T-1433: also installs `_install_stackdump_handler` -- UNLIKE the
    journal restore above, this runs on EVERY process (controller and
    every xdist worker alike, no early `workerinput` return), since a
    wedge's dead-lock-holder could be either."""
    _install_stackdump_handler()
    if hasattr(config, "workerinput"):
        return
    restore_stale_journals(_REPO_ROOT)


# frob:ticket T-0926
# frob:tests tests/unit/test_conftest_parse_reset.py::TestConftestParseReset.test_reset_before_each_test_isolates_partial_parse_state  # noqa: E501
@pytest.fixture(autouse=True)
def _reset_parse_cache_before_test() -> None:
    """Clear `frob.lang`'s process-lifetime parse memo/`partial_parse_files`
    set before EVERY test (T-0926), not just before a real `frob check`
    invocation.

    `frob.lang._partial_parse_files` (and the `_parse` memo it rides
    alongside) is a process-lifetime module-global, correctly reset once
    per real `frob check` run by `frob.check._run_check_with_skips`. That
    reset is never reached by a test that calls `frob.graph.build_graph`
    (or `frob.lang.parse_file`) directly -- so a test earlier in the same
    pytest-xdist worker process that parses a file with a syntax error
    leaves its display path in `_partial_parse_files` until some LATER
    test happens to call `reset_parse_cache()` itself, producing PARSE002-
    shaped assertion flakiness purely from pytest-xdist's file/test
    ordering (T-0926, filed during T-0905). An autouse fixture resetting
    before every test is the single, ordering-independent choke point:
    no test-collection order, xdist worker assignment, or file split can
    leak state across a test boundary again, without hand-adding a
    `reset_parse_cache()` call to every test that happens to touch
    parsing (the brittle, easy-to-forget pattern this replaces -- see
    `tests/test_lang.py`/`tests/test_gates.py`'s existing manual calls,
    now redundant but harmless).

    Deliberately NOT done inside `frob.graph.build_graph` itself: that
    function is `@memoize_per_run`-wrapped and called from many gate
    stages with distinct `(root, cache)` pairs inside one active `frob
    check` run (`ThreadPoolExecutor`-concurrent, per `frob.check._memo`).
    Resetting there on every real invocation would race against sibling
    stages that call `frob.lang.parse_file` directly in the same run and
    could silently drop an earlier stage's recorded partial-parse entry
    before `PARSE002` reads it -- trading test flakiness for production
    gate flakiness. The test suite's own state (this fixture) is the
    correct place to own test isolation; production's reset stays owned
    by `frob.check` alone.
    """
    reset_parse_cache()


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
