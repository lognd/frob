import faulthandler
import os
import signal
from pathlib import Path

import pytest

import frob.lang as lang_mod
from frob.lang import PARSE_ARTIFACT_CACHE_ENV, reset_parse_cache
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


#: Substrings (matched against a collected item's own `.name`) that flag a
#: test as a full-repo self-scan: `build_graph`/`check_self_conformance`/
#: `sys_gate` invoked against THIS repo's own live source tree
#: (`_REPO_ROOT`), not a synthetic `tmp_path` fixture. Root-caused in
#: T-1433's live SIGUSR1 capture: a worker running one of these tests goes
#: down with "node down: Not properly terminated" and no faulthandler
#: fault trace in `.frob/last-coverage-run.log` -- the absence of a trace
#: rules out a caught fault (SIGSEGV/SIGABRT/SIGFPE, all of which
#: `faulthandler.enable()` intercepts and would have logged) and points at
#: an UNCATCHABLE SIGKILL, i.e. the kernel OOM-killer, matching this
#: repo's own documented WSL OOM-kill history (Makefile's own T-1353
#: comment: "-n auto workers ... oversubscribes this host's CPU and memory
#: ... 5+ workers went node down in a single invocation"). Each of these
#: tests independently parses/walks every file in `src/frob` in-process;
#: `loadgroup` scheduling has no reason to keep them apart, so several can
#: land on DIFFERENT workers at the same wall-clock moment, each paying
#: this same peak-memory cost concurrently. Named by substring (not exact
#: match) so a renamed/parametrized variant of any of these still groups
#: without needing this list edited in lockstep with the test files
#: themselves, which live outside this ticket's scope.
_SELF_SCAN_HEAVY_NAME_SUBSTRINGS = (
    "test_sys_gate_zero_violations",
    "test_repo_design_and_declarations_are_self_conformant",
    "test_repo_unrestricted_scan_is_clean",
)


# frob:ticket T-1433
# frob:tests tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping.test_self_scan_heavy_tests_share_one_xdist_group  # noqa: E501
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Force every full-repo self-scan test (`_SELF_SCAN_HEAVY_NAME_SUBSTRINGS`)
    into the SAME `pytest-xdist` group (T-1433) so `loadgroup` scheduling
    (this repo's `addopts`, `pyproject.toml`) runs them one after another
    on a single worker instead of scattering them across several workers
    that then all pay their full-repo-scan peak-memory cost at the same
    moment -- the scheduling shape the live incident capture points at as
    the OOM-kill trigger behind "node down: Not properly terminated". A
    no-op under plain `pytest` (no `-n`/`--dist`): `xdist_group` is inert
    without `pytest-xdist` actually distributing the run."""
    for item in items:
        if any(needle in item.name for needle in _SELF_SCAN_HEAVY_NAME_SUBSTRINGS):
            item.add_marker(pytest.mark.xdist_group(name="frob_self_scan_heavy"))


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


# frob:ticket T-1596
# frob:tests tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_prints_greppable_line_at_any_verbosity  # noqa: E501
# frob:tests tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_skips_on_xdist_worker  # noqa: E501
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Print an always-visible `SUITE-RESULT:` line at the end of every run
    (T-1596), independent of pytest's own verbosity-gated terminal summary.

    Root cause investigated for T-1596: three background full-suite runs
    appeared to "truncate" with no final `N passed, M failed in Ts` line and
    no crash trace -- reproduced deterministically and traced to pytest's
    verbosity stacking, NOT a crash/OOM/hang. This repo's own `addopts`
    (`pyproject.toml`) already bakes in one `-q`; the exact invocation this
    repo's own dispatch guidance recommends (`pytest tests/ -q ...`) adds a
    SECOND `-q`, taking verbosity to -2 ("very quiet"), at which point
    pytest's `TerminalReporter.summary_stats()` silently skips printing its
    own final summary line entirely -- confirmed by isolating the flag: the
    identical command with only one `-q` prints the summary, with two it
    does not, with no other difference. A caller that greps a captured log
    for that line to decide "did the suite finish" is silently fooled by
    this, exactly the shape three prior background runs hit.

    `TerminalReporter.write_line` (used here via the `terminalreporter`
    plugin) is a low-level write, not gated by the verbosity level that
    silences `summary_stats()` -- so this line survives `-q`, `-qq`, or any
    other verbosity stacking and is always safe to grep for as the
    "the run actually finished" signal, regardless of how the caller
    invoked pytest. Controller-only under `pytest-xdist` (mirrors
    `pytest_configure`'s own `workerinput` early-return above) -- printing
    once per worker would defeat the "exactly one greppable line" contract
    this exists to provide."""
    if hasattr(session.config, "workerinput"):
        return
    total = getattr(session, "testscollected", 0)
    failed = getattr(session, "testsfailed", 0)
    line = (
        f"SUITE-RESULT: exitstatus={exitstatus} collected={total} failed={failed}"
    )
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(line)
    else:  # pragma: no cover - defensive only, terminalreporter always registered
        print(line)


# frob:ticket T-1586
@pytest.fixture(autouse=True)
def _neutralize_inherited_color_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drop `FORCE_COLOR`/`NO_COLOR` inherited from the developer's shell
    before EVERY test.

    `frob.logging.color.should_color` honors both (no-color.org
    precedence), and a CLI subprocess a test spawns inherits the whole
    environment -- so a shell exporting `FORCE_COLOR=3` (Claude Code and
    several CI images do) makes every assertion on plain output text fail
    with ANSI escapes embedded, while the same suite passes on a shell
    without it. Deleting rather than setting `NO_COLOR` keeps the default
    honest (not a TTY -> no color) AND leaves a test free to monkeypatch
    either variable to exercise the color paths themselves."""
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)


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


# frob:ticket T-1591
@pytest.fixture(autouse=True)
def _reset_parse_artifact_cache_env_before_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drop `frob.lang.PARSE_ARTIFACT_CACHE_ENV` and reset the module's
    process-lifetime `_artifact_conn`/`_artifact_conn_path` cache-
    connection globals before EVERY test (T-1591).

    `frob.gates._stamp_worker_parse_artifact_cache_env` stamps this env
    var with `os.environ[PARSE_ARTIFACT_CACHE_ENV] = str(cache_path)`
    DIRECTLY (not via a context manager or restore-on-exit), because in
    its real production use it runs once per short-lived `frob check`
    CLI process right before spawning a `ProcessPoolExecutor` -- there is
    no "after" to restore to, the process exits soon after. That shape
    becomes a real cross-test leak in a long-lived pytest-xdist worker:
    any test that drives `frob.gates.run_gates` (or a wrapper that calls
    it) in-process leaves the env var pointing at THAT test's now-
    torn-down `tmp_path/.frob/parse-artifacts.db` for the rest of the
    worker's lifetime. Every LATER test in the same worker that calls
    `frob.lang.parse_file`/`walk_strata` then silently consults
    `_artifact_cache_connection()` -- which many tests never expect since
    the module docstring's own stated common case is "no persistent
    cache configured" -- and can return a stale, content-hash-keyed
    cache HIT for a real repo file (e.g. `design/litmus/*.strata`) that
    some earlier, unrelated test happened to parse for real, defeating a
    test that specifically monkeypatches the native parser unavailable
    and expects a fresh `Err` (T-1591 incident:
    `TestStrataNativeParserUnavailable`'s two `parse_file`/`outline_file`
    assertions saw an `Ok` cache hit instead of the expected `Err`).

    `monkeypatch.delenv` (not a bare `os.environ.pop`) so this itself
    never leaks past the test even if a later assertion in the SAME test
    sets the var again. The module-level connection globals are reset
    directly (not monkeypatch-tracked, mirroring
    `tests/unit/test_lang_artifact_cache.py`'s own manual reset pattern)
    since a stale open `sqlite3.Connection` object surviving in
    `_artifact_conn` would otherwise still be reused by
    `_artifact_cache_connection` for a NEW env-var path whose fresh
    connection was never actually opened."""
    monkeypatch.delenv(PARSE_ARTIFACT_CACHE_ENV, raising=False)
    lang_mod._artifact_conn = None
    lang_mod._artifact_conn_path = None


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
