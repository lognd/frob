import ctypes
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import threading
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

import pytest

import frob.lang as lang_mod
from frob.gates import Severity, Violation
from frob.gitio import Hunk
from frob.graph import build_graph
from frob.lang import PARSE_ARTIFACT_CACHE_ENV, reset_parse_cache
from frob.mutate import restore_stale_journals
from frob.testing._stackdump import STACKDUMP_ENV as _STACKDUMP_ENV  # noqa: F401
from frob.testing._stackdump import (
    install_stackdump_handler as _install_stackdump_handler,
)
from frob.tickets import Origin, Ticket, TicketKind, TicketState
from frob.tickets._store import write_ticket
from frob.tickets._worktree_guard import (
    FROB_AGENT_ENV,
    FROB_WORKTREE_ENV,
    PYTEST_XDIST_AUTO_NUM_WORKERS_ENV,
)

if TYPE_CHECKING:
    from frob.graph import GraphSnapshot


#: T-3582 (Windows round 5): the DEFAULT bound for `run_bounded_subprocess`
#: whenever a caller does not pass its own `timeout=` -- never `None`
#: (wait forever). Mirrors `tests/system/conftest.py`'s
#: `DEFAULT_RUN_TIMEOUT_S`/`run()` (T-2980/T-3577): that helper only
#: covers `tests/system/`, but the SAME `subprocess.run(..., timeout=...)`
#: double-communicate hazard on win32 (a still-open grandchild pipe makes
#: the untimed post-timeout drain read block forever) applies to any
#: unbounded `subprocess.run`/`Popen` call anywhere in the suite --
#: `tests/integration/*.py` had 13 such call sites with no timeout at all
#: when this was added (a windows-latest run died with `KeyboardInterrupt`
#: at collection position ~130, inside `tests/integration/test_gitlog.py`
#: territory, with no exception raised in-process -- the exact "hung
#: forever, no bound at all" shape `DEFAULT_RUN_TIMEOUT_S` was invented to
#: close for `tests/system/`).
DEFAULT_RUN_TIMEOUT_S = 100


# frob:ticket T-3582
# frob:tests tests/integration/test_gitlog.py::TestGitlogGrouping.test_features_grouped_separately  # noqa: E501
def run_bounded_subprocess(
    args: list[str], *, cwd: "Path | str | None" = None, timeout: float | None = None
) -> subprocess.CompletedProcess:
    """Run `args` as a subprocess and capture stdout/stderr, bounded on
    every platform -- the shared home for a test's git/frob subprocess
    helpers, so no call site needs its own timeout handling. On `win32`,
    drives `Popen`/`communicate` directly so BOTH the first read and any
    post-timeout drain are bounded, and kills the WHOLE process tree
    (`taskkill /T /F`) on expiry rather than relying on `Popen.kill()`'s
    single-pid reach -- `subprocess.run`'s own internal timeout handling
    retries `communicate()` a second time with NO timeout, and Windows
    inherits pipe handles into every grandchild a command spawns, so a
    live grandchild can keep that second, untimed read blocked forever.
    On POSIX, plain `subprocess.run(..., timeout=...)` is sufficient
    (close-on-exec is the default there, so a killed child cannot keep
    the pipe open past its own death). See `tests/system/conftest.py::run`
    for the sibling helper this mirrors, and T-3582 for the incident that
    motivated it."""
    effective_timeout = DEFAULT_RUN_TIMEOUT_S if timeout is None else timeout

    if sys.platform == "win32":
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
        )
        try:
            stdout, stderr = proc.communicate(timeout=effective_timeout)
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
            try:
                proc.communicate(timeout=effective_timeout)
            except subprocess.TimeoutExpired:
                pass
            raise RuntimeError(
                f"run_bounded_subprocess timed out after {effective_timeout}s "
                f"waiting on {args!r} (T-3582: this command either hung, or "
                "legitimately needs longer -- pass an explicit timeout= at "
                "the call site rather than raising DEFAULT_RUN_TIMEOUT_S)"
            ) from None
        return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)

    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=effective_timeout,
            start_new_session=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"run_bounded_subprocess timed out after {effective_timeout}s "
            f"waiting on {args!r} (T-3582: this command either hung, or "
            "legitimately needs longer -- pass an explicit timeout= at the "
            "call site rather than raising DEFAULT_RUN_TIMEOUT_S)"
        ) from exc


"""T-1433/T-1466: the SIGUSR1 stack-dump handler itself now lives in
`frob.testing._stackdump` (any frob process can opt in, not just pytest --
see that module's docstring for the WIRE001/reachability motivation).
`_STACKDUMP_ENV`/`_install_stackdump_handler` are re-exported here under
their ORIGINAL private names purely for source-compat with this file's
own pre-existing callers below and `tests/unit/test_conftest_stackdump.py`
-- `pytest_configure`'s install timing (every xdist worker, unlike the
controller-only journal restore) is still real, pytest-specific wiring
this file owns."""


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
#: T-1635: `test_no_reg008_findings_for_arch_checks_yaml`/`..._system_
#: design_yaml` (`tests/test_registry_exhaustiveness.py`) join this list
#: on the SAME evidence shape, not a speculative addition -- both call
#: `build_graph(root, ...)` against `_REPO_ROOT` directly (`root =
#: Path(__file__).resolve().parents[1]`), by design: they verify the
#: real, live `docs/design/registry/*.yaml` against this repo's actual
#: code graph, so isolating them onto a synthetic `tmp_path` fixture
#: (the alternative to grouping) is not available -- there is no fixture
#: copy of "this repo's own registry" to check instead. Reproduced under
#: a real `pytest -n auto` full-suite run: both timed out at pytest-
#: timeout's per-test budget with a faulthandler thread dump showing one
#: blocked inside `derived_state_lock`/`derived_state_write_lock`
#: (`src/frob/process/_lock.py`, an unbounded `fcntl.flock` over
#: `.frob/derived.lock` at the real repo root) and the other still
#: inside `load_file_data`, immediately followed by "node down: Not
#: properly terminated" -- the identical contention/OOM shape T-1433
#: diagnosed for the three tests already below, just not yet extended to
#: these two. `derived_state_lock` is a real cross-process exclusive
#: lock over a shared on-disk resource (there is exactly one `.frob/`
#: per checkout); `loadgroup` scheduling has no reason on its own to
#: keep these five apart, so several full-repo scans can still land on
#: different workers at the same moment and queue on that lock (or pay
#: peak-memory cost concurrently) unless explicitly grouped.
#: T-2762: `TestWaive006RealRepo.test_zero_errors_on_real_repo`/
#: `TestWaive007RealRepo.test_zero_findings_on_real_repo`
#: (`tests/test_waive_gate.py`) and `TestProtocolSummaryGate.
#: test_real_repo_scan_runs_end_to_end_without_crashing`/`TestOptInGates.
#: test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses`
#: (`tests/test_gates.py`) join this list on the IDENTICAL evidence bar
#: T-1635 set, not speculatively: T-1654's audit read all `build_graph`/
#: `_load_inputs` call sites in the six files T-1433/T-1635 flagged as
#: unaudited and found these four are the only OTHER real-repo-root
#: scans among them (the other two files' calls all target an isolated
#: `tmp_path` fixture, already safe). A scoped 4-test/2-worker run alone
#: did not reproduce contention (T-1654's own measurement) -- T-2762
#: then ran these four TOGETHER with the five names already above (9
#: heavy real-repo scans, `-n 9`, no grouping override) and reproduced
#: the exact T-1635 shape directly: 3 workers went down with "node down:
#: Not properly terminated", and the `PYTHONFAULTHANDLER=1` thread dump
#: caught `test_zero_errors_on_real_repo` blocked inside `derived_state_
#: lock`/`derived_state_write_lock` (`src/frob/process/_lock.py`) via
#: `build_graph` <- `_load_inputs`, the identical call chain the other
#: five block on. Same fix, same reasoning: group them onto the shared
#: worker so a real full-suite run cannot schedule more than one of the
#: whole nine onto different workers at once.
_SELF_SCAN_HEAVY_NAME_SUBSTRINGS = (
    "test_sys_gate_zero_violations",
    "test_repo_design_and_declarations_are_self_conformant",
    "test_repo_unrestricted_scan_is_clean",
    "test_no_reg008_findings_for_arch_checks_yaml",
    "test_no_reg008_findings_for_system_design_yaml",
    # frob:ticket T-2762
    "test_zero_errors_on_real_repo",
    "test_zero_findings_on_real_repo",
    "test_real_repo_scan_runs_end_to_end_without_crashing",
    "test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses",
)


# frob:ticket T-2099
#: Marker a HEAVY test module self-declares (`pytestmark = pytest.mark.
#: heavy_subprocess` at module scope) when its tests spawn real `git`/
#: subprocesses against real temp repos -- the T-2099 root cause was
#: `tests/test_ticket_land.py` (275 tests) having NO grouping at all, so
#: its tests scattered across xdist workers that then contended over real
#: git processes and exceeded the 540s foreground budget even though the
#: SAME file finishes in ~420s run serially. T-1433's
#: `_SELF_SCAN_HEAVY_NAME_SUBSTRINGS` list solved one instance of this by
#: hardcoding five test NAMES here in conftest -- deliberately NOT
#: repeated for this case, because a remote name list is exactly the kind
#: of enforcement that has to be individually remembered per file (T-2099
#: traced the same repo-wide pattern to four unrelated defects the same
#: day: a primitive wired into too few call sites). A `pytestmark` is
#: declared IN the heavy file itself, next to the real-subprocess code
#: that justifies it, so the next author adding a heavy file discovers
#: the convention by reading a sibling file rather than by remembering to
#: edit conftest.
_HEAVY_SUBPROCESS_MARKER = "heavy_subprocess"


# frob:ticket T-1433
# frob:ticket T-2099
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping.test_self_scan_heavy\
# _tests_share_one_xdist_group
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestHeavySubprocessGrouping.test_heavy_subproc\
# ess_marker_groups_per_file
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
    without `pytest-xdist` actually distributing the run.

    Also (T-2099): any item in a module carrying the `heavy_subprocess`
    marker is grouped by its OWN MODULE NAME, one `xdist_group` per file
    rather than one shared group across every heavy file -- keeping each
    file's real-git tests on a single worker (no cross-worker contention
    within the file) without concentrating every heavy file's peak memory
    onto the same worker at once (the OOM constraint T-1433's docstring
    above warns about)."""
    for item in items:
        if any(needle in item.name for needle in _SELF_SCAN_HEAVY_NAME_SUBSTRINGS):
            item.add_marker(pytest.mark.xdist_group(name="frob_self_scan_heavy"))
            # T-3525: raised per-test budget for the group's shared
            # frob_self_scan_artifacts fixture -- see that fixture's own
            # docstring and _cached_self_scan for why (a fixture that can
            # exceed the default --timeout gets its worker os._exit()d
            # mid-scan, restarting from scratch on the next worker). SAME
            # hook assigns both markers, so they can never desync.
            item.add_marker(pytest.mark.timeout(1200))
        elif item.get_closest_marker(_HEAVY_SUBPROCESS_MARKER) is not None:
            # `item.nodeid`'s file-path prefix (before the first `::`) is
            # declared on the base `pytest.Item` type, unlike `.module`
            # (only present on the `Function`/`Module`-derived subclasses
            # pytest actually constructs at runtime) -- statically typed
            # and just as unique per file for grouping purposes.
            module_path = item.nodeid.split("::", 1)[0]
            item.add_marker(
                pytest.mark.xdist_group(name=f"heavy_subprocess::{module_path}")
            )


# frob:ticket T-0885
# frob:ticket T-1433
# frob:tests \
# tests/test_mutate_journal.py::test_pytest_session_start_restores_leftover_journal \
# kind="unit"
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
    wedge's dead-lock-holder could be either.

    T-3577: the T-3560 round-3 `_install_sigbreak_faulthandler` diagnostic
    (installed here, same every-process timing as the stackdump handler
    above) is REVERTED in this same land -- T-3560's own contract required
    reverting it once the named windows-latest hang culprit was fixed; see
    T-3577's Done report for the root-cause fix this revert accompanies.

    T-3246: also resets `_last_internal_error` to `None` at the start of
    every session, so a value stashed by `pytest_internalerror` during an
    earlier in-process run (e.g. a prior `pytest.main()` call within the
    same interpreter) can never leak into a later run's `SUITE-RESULT:`
    line.

    T-3516: also stashes `config` into the module-level `_worker_crash_
    hook_config` (every process, controller and worker alike --
    `pytest_runtest_logstart`/`pytest_runtest_logfinish`/`pytest_
    handlecrashitem` all need it and none of them receive it as a hook
    argument) and, controller only, resets the crash-report state left
    over from any earlier in-process run and installs
    `_harden_dsession_active_nodes`'s vanished-`WorkerController` guard
    before any worker can crash."""
    global _last_internal_error, _worker_crash_hook_config
    global _last_progress_ts, _stall_watchdog_stop, _stall_watchdog_thread
    global _last_node_death_ts
    global _midrun_watchdog_stop, _midrun_watchdog_thread
    global _midrun_watchdog_started_ts
    _last_internal_error = None
    _install_stackdump_handler()
    _install_test_console_ctrl_ignore_guard()
    _worker_crash_hook_config = config
    if hasattr(config, "workerinput"):
        return
    _worker_crash_entries.clear()
    _worker_crash_causes.clear()
    _worker_crash_rerun_counts.clear()
    _last_node_death_ts = None
    _harden_dsession_active_nodes()
    restore_stale_journals(_REPO_ROOT)
    # T-3608: only under pytest-xdist is a "worker died, nothing ever
    # rescheduled or ended the session" stall even possible -- plain serial
    # pytest has no separate controller/worker split for a stall to hide in.
    if getattr(getattr(config, "option", None), "numprocesses", None):
        import time

        _last_progress_ts = time.time()
        _stall_watchdog_stop = threading.Event()
        _stall_watchdog_thread = threading.Thread(
            target=_run_stall_watchdog,
            args=(config, _stall_watchdog_stop),
            name="frob-xdist-stall-watchdog",
            daemon=True,
        )
        _stall_watchdog_thread.start()
    # T-3683: unlike the xdist-only stall watchdog above, this one needs
    # neither xdist nor a recorded worker crash -- gated purely on
    # FROB_TEST_MIDRUN_WATCHDOG_SECONDS, so it also covers the current
    # `-p no:xdist` serial windows Test step (see FROB_TEST_MIDRUN_
    # WATCHDOG_SECONDS_ENV's own docstring for the mid-run wedge this
    # answers).
    midrun_threshold = _midrun_watchdog_threshold_s()
    # T-3707 Part B: the same watchdog thread also carries the
    # total-elapsed-wall-clock trigger -- see FROB_TEST_TOTAL_BUDGET_
    # SECONDS_ENV's docstring for why this needs to be a SEPARATE knob
    # from the stall threshold above rather than reusing it (a stall
    # detector and a wall-clock cap answer different questions and a
    # suite may want either, both, or neither armed independently).
    total_budget_threshold = _total_budget_threshold_s()
    if midrun_threshold is not None or total_budget_threshold is not None:
        import time

        _midrun_watchdog_started_ts = time.time()
        _midrun_watchdog_stop = threading.Event()
        _midrun_watchdog_thread = threading.Thread(
            target=_run_midrun_watchdog,
            args=(
                config,
                _midrun_watchdog_stop,
                midrun_threshold,
                total_budget_threshold,
            ),
            name="frob-midrun-watchdog",
            daemon=True,
        )
        _midrun_watchdog_thread.start()
        # T-3692: an ARM-time confirmation, printed unconditionally (not
        # diagnostic-gated -- this line is as cheap as the FIRE-time
        # SUITE-RESULT line it mirrors) -- CI run 33625622797's windows
        # Test step showed the 180s watchdog (T-3689) never firing with
        # no way to tell whether it was ever armed at all (env var not
        # reaching this process) versus armed-but-blind-to-the-observed
        # stall shape. This line answers "was FROB_TEST_MIDRUN_WATCHDOG_
        # SECONDS even seen by pytest_configure" directly from the next
        # run's own stdout, independent of whether the watchdog ever
        # needs to fire.
        reporter = config.pluginmanager.get_plugin("terminalreporter")
        arm_line = (
            f"FROB-TEST-MIDRUN-WATCHDOG: armed threshold="
            f"{midrun_threshold if midrun_threshold is not None else 'unset'!s}s "
            f"(env {FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV}="
            f"{os.environ.get(FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV)!r}) "
            f"total_budget="
            f"{total_budget_threshold if total_budget_threshold is not None else 'unset'!s}s "
            f"(env {FROB_TEST_TOTAL_BUDGET_SECONDS_ENV}="
            f"{os.environ.get(FROB_TEST_TOTAL_BUDGET_SECONDS_ENV)!r})"
        )
        if reporter is not None:
            reporter.write_line(arm_line)
        else:  # pragma: no cover - defensive only, terminalreporter always registered
            print(arm_line)


def pytest_unconfigure(config: pytest.Config) -> None:
    """T-3673: mirror-image of `pytest_configure`'s `_install_test_
    console_ctrl_ignore_guard` -- unregisters the session-lifetime
    `SetConsoleCtrlHandler` callback, if one was installed, so it never
    outlives this pytest process. A no-op whenever nothing was
    installed (non-win32, or `FROB_TEST_IGNORE_CONSOLE_CTRL` unset)."""
    del config
    _uninstall_test_console_ctrl_ignore_guard()


_SUITE_RESULT_MAX_NODE_IDS = 50
"""T-1673: cap on how many failing node ids `pytest_sessionfinish` lists by
name before collapsing the remainder into an 'and N more' tail -- keeps the
always-visible summary bounded even on a suite with hundreds of failures."""

_SUITE_RESULT_MAX_NODE_IDS_ENV = "FROB_TEST_SUITE_RESULT_MAX_NODE_IDS"
"""T-3755: env override for the node-id cap above. A platform-drain drive
(e.g. the win32 test-portability drain, T-3076) needs the FULL failing set
from ONE CI run, not the first 50 + 'and N more'; the CI Test steps set this
high so the whole list is emitted. Defaults to _SUITE_RESULT_MAX_NODE_IDS."""


# frob:waive WIRE001 reason="called from pytest_sessionfinish (below), a \
# name-discovered pytest hook the best-effort callgraph does not trace as an in-repo \
# caller -- the same hook-discovery gap this file's other WIRE001/DEAD001 waivers \
# already cover (T-3755)" follow_up="T-3381"
def _suite_result_max_node_ids() -> int:
    """The effective SUITE-RESULT-FAILED node-id cap: the
    `FROB_TEST_SUITE_RESULT_MAX_NODE_IDS` env value if it is a positive int,
    else `_SUITE_RESULT_MAX_NODE_IDS` (T-3755)."""
    import os

    raw = os.environ.get(_SUITE_RESULT_MAX_NODE_IDS_ENV)
    if raw:
        try:
            value = int(raw)
        except ValueError:
            return _SUITE_RESULT_MAX_NODE_IDS
        if value > 0:
            return value
    return _SUITE_RESULT_MAX_NODE_IDS


_COMPLETED_EXIT_STATUSES = frozenset({0, 1})
"""T-3246: pytest's own documented exit codes for a run that actually
finished collecting and executing its full item set -- 0 (all passed) and 1
(tests failed, but the session ran to completion). Every other documented
code (2 interrupted, 3 internal error, 4 usage error, 5 no tests collected)
means the session did NOT run to completion, so `session.testscollected`/
`session.testsfailed` are partial counts of unknown looseness, not a real
total -- see `_EXIT_STATUS_LABELS` and `pytest_sessionfinish` below."""

_EXIT_STATUS_LABELS: dict[int, str] = {
    0: "OK",
    1: "TESTS-FAILED",
    2: "INTERRUPTED",
    3: "INTERNAL-ERROR",
    4: "USAGE-ERROR",
    5: "NO-TESTS-COLLECTED",
}
"""T-3246: human-readable name for each of pytest's documented exit codes,
named in the `SUITE-RESULT:` line so a reader distinguishes a completed run
(status 0/1) from an aborted one (2/3/4/5) without memorizing pytest's exit
code table. An undocumented/future code falls back to `f"CODE-{exitstatus}"`
in `pytest_sessionfinish` rather than raising or silently omitting a label."""

FROB_TEST_IGNORE_CONSOLE_CTRL_ENV = "FROB_TEST_IGNORE_CONSOLE_CTRL"
"""T-3673 (win32 round 17): env-gated, OFF by default everywhere except
the CI workflow's windows Test step -- when truthy on win32, installs a
`SetConsoleCtrlHandler` callback for the whole pytest session that
swallows `CTRL_C_EVENT`/`CTRL_BREAK_EVENT`, the same mechanism
`src/frob/process/_guard.py::win32_console_ctrl_ignore_scope` uses for
`frob check` itself (T-3657). This is a SEPARATE env var from
`FROB_WIN32_IGNORE_CONSOLE_CTRL_ENV` -- the suite's session lifetime is
not the same scope as one `run_check` call, so it gets its own gate
rather than piggybacking on the check-pipeline one. Rationale: 3
consecutive CI runs measured the suite dying at teardown
(threading.py join at session end) from the SAME injected-SIGINT class
tracked across the whole T-3648/T-3651/T-3657/T-3670/T-3673 ticket
family, at ~100% completion -- a real result already computed, thrown
away by a signal with no legitimate source in a non-interactive CI
runner. Masking is a deliberate, documented symptom-mitigation, NOT a
claim that the sender identity question is closed; see
docs/modules/process.md for the full rationale and
`.github/workflows/ci.yml`'s windows Test step for the one place this
is ever set."""

_test_console_ctrl_handler_holder: list[object] = []
"""T-3673: holds the live `ctypes.WINFUNCTYPE` handler object (if any)
between `pytest_configure` installing it and `pytest_unconfigure`
removing it -- a bare local would be garbage-collected the moment
`pytest_configure` returns, which would silently unregister nothing
(the callback trampoline must outlive the `SetConsoleCtrlHandler`
registration) or crash on a stale pointer if Windows ever invoked it
after collection."""


def _test_console_ctrl_ignore_requested() -> bool:
    """True exactly when `FROB_TEST_IGNORE_CONSOLE_CTRL` is set to a
    truthy value AND this process is running on win32 -- mirrors
    `_win32_ignore_console_ctrl_requested`'s posture in
    `src/frob/process/_guard.py` (checked once, fresh, before any win32
    API is touched)."""
    if sys.platform != "win32":
        return False
    value = os.environ.get(FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _install_test_console_ctrl_ignore_guard() -> None:
    """T-3673: install the session-lifetime `SetConsoleCtrlHandler`
    guard when `_test_console_ctrl_ignore_requested()` -- a no-op call
    on every other platform/env combination. Stashes the handler in
    `_test_console_ctrl_handler_holder` so `_uninstall_test_console_ctrl_
    ignore_guard` can unregister the SAME callback object at session
    end; only ever called once per process, from `pytest_configure`."""
    if not _test_console_ctrl_ignore_requested():
        return
    kernel32 = getattr(ctypes, "windll").kernel32  # noqa: B009
    handler_type = getattr(ctypes, "WINFUNCTYPE")(ctypes.c_bool, ctypes.c_ulong)  # noqa: B009

    def _handler(ctrl_type: int) -> bool:
        """Swallow `CTRL_C_EVENT` (0) / `CTRL_BREAK_EVENT` (1) for the
        whole pytest session; let every other console control code fall
        through to Windows' default handling, same posture as
        `win32_console_ctrl_ignore_scope`'s handler."""
        if ctrl_type in (0, 1):
            return True
        return False

    handler = handler_type(_handler)
    kernel32.SetConsoleCtrlHandler(handler, True)
    _test_console_ctrl_handler_holder.append(handler)


def _uninstall_test_console_ctrl_ignore_guard() -> None:
    """T-3673: unregister the handler `_install_test_console_ctrl_ignore_
    guard` installed, if any -- called from `pytest_unconfigure` so a
    real console ctrl event delivered AFTER the pytest process exits
    (e.g. to a parent shell) is never suppressed by a handler this
    process leaked."""
    if not _test_console_ctrl_handler_holder:
        return
    handler = _test_console_ctrl_handler_holder.pop()
    kernel32 = getattr(ctypes, "windll").kernel32  # noqa: B009
    kernel32.SetConsoleCtrlHandler(handler, False)


FROB_TEST_HARD_EXIT_ENV = "FROB_TEST_HARD_EXIT"
"""T-3675 (win32 round 18): env-gated, OFF by default everywhere except
the CI workflow's windows Test step -- when truthy, `pytest_sessionfinish`
hard-exits the controller process via `os._exit` right after this file's
own `SUITE-RESULT:` line and exit-status handling finish, instead of
letting pytest's normal `wrap_session` teardown run. T-3673's round-17
evidence (run 33556847222) is why this exists: with the suite's console-
ctrl-ignore guard armed, the injected SIGINT this whole ticket family has
chased stopped killing the windows Test step -- and the step instead HUNG
past its own 1500s budget with orphan pytest/python processes still
alive. Read together, the two findings say the injected SIGINT was
MASKING a real teardown wedge (a non-daemon thread or unreaped child
blocking interpreter/session shutdown) the whole time; the interrupt
breaking that stuck join was an ACCIDENT of how it used to die, not
evidence teardown itself was ever clean. `os._exit` is the same escape
hatch `_announce_stall_and_abort` (T-3608) already uses in this file for
an unrelated but structurally identical problem (a wedge with no
reachable graceful exit) -- reused here, not reinvented, and printed
with the exact same flush-before-`os._exit` ordering so the SUITE-RESULT
line this hook already wrote is never lost to an unflushed buffer."""


def _hard_exit_requested() -> bool:
    """True exactly when `FROB_TEST_HARD_EXIT` is set to a truthy value --
    no platform restriction (unlike the win32-only guards above): a
    teardown wedge from a non-daemon thread or unreaped child is not a
    win32-specific hazard, only round 17's win32 CI evidence is what
    surfaced it."""
    value = os.environ.get(FROB_TEST_HARD_EXIT_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _describe_teardown_blockers() -> str:
    """T-3675: one line inventorying every live non-daemon thread
    (`threading.enumerate()`, name + daemon flag) and known child
    process (`multiprocessing.active_children()`, name + pid) at the
    moment `pytest_sessionfinish` is about to hard-exit -- so a run that
    takes this path documents WHAT was still alive and blocking normal
    interpreter/session teardown, not merely that something was. Every
    thread is listed (not only non-daemon ones) since a daemon thread
    the reader assumed was harmless is itself useful signal if it shows
    up here; the label calls out non-daemon ones explicitly because
    THOSE are what `threading._shutdown`'s own join actually waits on."""
    threads = [f"{t.name!r}(daemon={t.daemon})" for t in threading.enumerate()]
    children = [f"{p.name!r}(pid={p.pid})" for p in multiprocessing.active_children()]
    return (
        f"FROB-TEST-HARD-EXIT: threads=[{', '.join(threads)}] "
        f"children=[{', '.join(children)}]"
    )


def _maybe_hard_exit_after_session_finish(
    session: pytest.Session, exitstatus: int
) -> None:
    """T-3675: the tail `pytest_sessionfinish` calls once its own
    `SUITE-RESULT:`/failing-id reporting is done and `session.exitstatus`
    (possibly mutated by the worker-crash branch above) reflects the
    real outcome. A no-op unless `_hard_exit_requested()` -- see
    `FROB_TEST_HARD_EXIT_ENV`'s docstring for the full rationale. Prints
    `_describe_teardown_blockers()`'s inventory line, flushes both
    streams (same ordering as T-3608's `_announce_stall_and_abort` --
    `os._exit` skips Python's normal buffered-stream flush, so this is
    the only reason either line survives to the captured log), then
    `os._exit`s with the session's real exit status instead of letting
    pytest's own `wrap_session` teardown (and whatever wedges inside it)
    ever run."""
    if not _hard_exit_requested():
        return
    print(_describe_teardown_blockers(), flush=True)
    real_exitstatus = session.exitstatus
    if not isinstance(real_exitstatus, int):
        real_exitstatus = exitstatus
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(real_exitstatus)


FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV = "FROB_TEST_MIDRUN_WATCHDOG_SECONDS"
"""T-3683 (win32 round 19): env-gated, unset/non-positive/non-numeric =
disabled -- when set to a positive number of seconds, `pytest_configure`
starts a background watchdog thread that hard-exits the process (same
`os._exit` shape as `_maybe_hard_exit_after_session_finish` above and
T-3608's `_announce_stall_and_abort`) if no test call-phase reports
progress for that long. T-3675's own hard-exit only fires from `pytest_
sessionfinish`, which a MID-RUN wedge never reaches at all: round 18's
own CI evidence (run 33582058515) measured the windows Test step hitting
its 1500s budget again with NO `FROB-TEST-HARD-EXIT:` line printed --
the suite hangs before session finish, not at teardown, once T-3673's
FROB_TEST_IGNORE_CONSOLE_CTRL guard is masking the in-pipeline SIGINT a
subprocess `frob check` a test spawns would otherwise die from cleanly.
Unlike T-3608's own stall watchdog (xdist-only, requires a recorded
worker crash), this one needs neither: it is gated purely on elapsed
wall-clock time since the last observed `pytest_runtest_logreport`, so
it also covers the current `-p no:xdist` SERIAL windows Test step."""

_midrun_watchdog_stop: "threading.Event | None" = None
"""T-3683: signals the mid-run watchdog thread to stop -- set by `pytest_
sessionfinish` on a normal end-of-run, same posture as T-3608's `_stall_
watchdog_stop`."""

_midrun_watchdog_thread: "threading.Thread | None" = None
"""T-3683: the running mid-run watchdog thread, started by `pytest_
configure` whenever `_midrun_watchdog_threshold_s()` is not `None`;
`None` otherwise."""

_midrun_watchdog_started_ts: float | None = None
"""T-3683: wall-clock time the watchdog thread itself started -- used as
the progress baseline until the FIRST `pytest_runtest_logreport` ever
sets `_last_progress_ts`, so a wedge during collection or the very first
test (before any progress has ever been recorded) is still caught."""


def _midrun_watchdog_threshold_s() -> float | None:
    """The configured `FROB_TEST_MIDRUN_WATCHDOG_SECONDS` threshold, or
    `None` if unset/non-positive/not a valid float (T-3683) -- disabled
    is the default in every case, exactly one CI workflow step opts in."""
    raw = os.environ.get(FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV, "")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


FROB_TEST_TOTAL_BUDGET_SECONDS_ENV = "FROB_TEST_TOTAL_BUDGET_SECONDS"
"""T-3707 (win32 round 23, Part B): env-gated, unset/non-positive/non-
numeric = disabled -- when set to a positive number of seconds, the same
watchdog thread `_midrun_watchdog_threshold_s` arms also hard-exits once
that many seconds have elapsed since the SUITE started, regardless of
whether individual tests are still reporting progress. T-3683's own
mid-run watchdog answers "no test call-phase progress for N seconds" --
a *stall* detector -- but AM's T-3692 finding was that a suite making
slow-but-CONTINUOUS progress (never stalling long enough to trip the
180s mid-run threshold) can still sum past the external CI step's own
1500s budget and get killed with zero diagnostic output, the exact
"silent 1500s step timeout" this repo's whole watchdog lineage
(T-3608/T-3675/T-3683) exists to prevent. This is a plain wall-clock
cap with no progress signal involved, so it catches that class too."""


# frob:waive WIRE001 reason="genuinely wired -- called directly by pytest_configure \
# above (total_budget_threshold = _total_budget_threshold_s()), same call shape as its \
# pre-existing sibling _midrun_watchdog_threshold_s; WIRE001 flags it anyway purely \
# because it is new in this diff, not because the callgraph misses the call" \
# follow_up="T-3381"
def _total_budget_threshold_s() -> float | None:
    """The configured `FROB_TEST_TOTAL_BUDGET_SECONDS` threshold, or
    `None` if unset/non-positive/not a valid float (T-3707) -- disabled
    by default, same parse/validate shape as `_midrun_watchdog_
    threshold_s` (its sibling env var)."""
    raw = os.environ.get(FROB_TEST_TOTAL_BUDGET_SECONDS_ENV, "")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


# frob:waive WIRE001 reason="genuinely wired -- called only by _run_midrun_watchdog \
# below, itself reached exclusively via threading.Thread(target=...), same class of \
# gap this file's pre-existing T-3608 WIRE001 waivers already cover, not a direct \
# in-repo call site" follow_up="T-3381"
def _total_budget_exceeded(
    now: float, suite_started_ts: float, budget_s: float
) -> bool:
    """Pure predicate (T-3707): true once `budget_s` seconds have elapsed
    since `suite_started_ts` (the watchdog thread's own start time, used
    as the whole-suite wall-clock baseline) -- unlike `_midrun_stall_
    detected`, this has no progress signal in it at all: a suite making
    slow-but-continuous progress still trips this the moment total
    elapsed time crosses `budget_s`, which is the entire point (T-3692's
    finding that the mid-run stall watchdog alone cannot catch that
    shape)."""
    return (now - suite_started_ts) >= budget_s


# frob:waive WIRE001 reason="genuinely wired -- called by every \
# _announce_*_and_hard_exit below (T-3608's _announce_stall_and_abort included), each \
# reached only via a background threading.Thread(target=...), same class of gap this \
# file's pre-existing T-3608 WIRE001 waivers already cover, not a direct in-repo call \
# site" follow_up="T-3381"
def _emit_hard_exit_lines(config: pytest.Config, lines: list[str]) -> None:
    """T-3726: the shared tail every `_announce_*_and_hard_exit` in this
    file calls immediately before its own `os._exit(1)` -- prints each of
    `lines` through the terminal reporter (falling back to `print` if the
    plugin is somehow absent) and flushes both streams, exactly as each
    call site used to do inline, EXCEPT it now also suspends pytest's
    own capture manager first when one is registered.

    Root cause this fixes (T-3726, reproduced locally: a short
    FROB_TEST_TOTAL_BUDGET_SECONDS + a sleeping test hard-exits with NO
    SUITE-RESULT line ever reaching the redirected log, even though
    `reporter.write_line` raised no exception and `sys.stdout.flush()`
    ran before `os._exit`): pytest's default capture method is `fd`,
    which duplicates the real stdout/stderr file descriptors for the
    ENTIRE session (`CaptureManager._global_capturing`, method='fd') and
    points fd 1/2 at its own tmpfile for as long as capturing is active.
    Every one of this file's `_announce_*_and_hard_exit` functions runs
    from a background watchdog thread with NO pytest hook wrapping it,
    so `capman.suspend_global_capture` is never invoked on this path the
    way it is for pytest's own hook-driven output -- a write issued here
    (`reporter.write_line`, `print`, even a raw `sys.stdout.write`) lands
    in the captured tmpfile instead of the real stdout/stderr fd, and
    `sys.stdout.flush()` cannot rescue it: it flushes the SAME
    already-captured fd, not the real one underneath it. `os._exit`
    then skips the teardown step that would otherwise copy captured
    output back out, so the line is lost outright -- exactly the "armed
    but the fire line never shows up" symptom this ticket's brief named.
    `capman.suspend_global_capture(in_=True)` restores the real fd
    before the write so the line reaches the actual terminal/redirect
    target; no matching resume is needed since the process exits right
    after."""
    capman = config.pluginmanager.get_plugin("capturemanager")
    if capman is not None:
        try:
            capman.suspend_global_capture(in_=True)
        except (
            Exception
        ):  # pragma: no cover - defensive only, must never block the exit
            pass
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    for line in lines:
        if reporter is not None:
            reporter.write_line(line)
        else:  # pragma: no cover - defensive only, terminalreporter always registered
            print(line)
    sys.stdout.flush()
    sys.stderr.flush()


# frob:waive WIRE001 reason="genuinely wired -- called only by _run_midrun_watchdog \
# below, itself reached exclusively via threading.Thread(target=...), same class of \
# gap this file's pre-existing T-3608 WIRE001 waivers already cover, not a direct \
# in-repo call site" follow_up="T-3381"
def _announce_total_budget_exceeded_and_hard_exit(
    config: pytest.Config, now: float, suite_started_ts: float, budget_s: float
) -> None:
    """T-3707: the total-wall-clock twin of `_announce_midrun_stall_and_
    hard_exit` -- prints a `SUITE-RESULT: TOTAL-BUDGET-EXCEEDED` line
    plus the same `_describe_teardown_blockers()` inventory, flushes both
    streams, then `os._exit(1)`s. Fires purely on elapsed wall-clock
    time since `suite_started_ts`, independent of whether any test is
    still making progress -- see `FROB_TEST_TOTAL_BUDGET_SECONDS_ENV`'s
    docstring for why this exists as a THIRD, distinct trigger alongside
    the mid-run stall watchdog and the external CI step timeout."""
    elapsed = now - suite_started_ts
    lines = [
        f"SUITE-RESULT: TOTAL-BUDGET-EXCEEDED suite has run for "
        f"{elapsed:.1f}s, at/past the {budget_s:g}s FROB_TEST_TOTAL_"
        f"BUDGET_SECONDS wall-clock cap (T-3707) -- aborting now instead "
        f"of waiting for the external CI step budget to kill this job "
        f"with zero diagnostic output",
        _describe_teardown_blockers(),
        "SUITE-RESULT: exitstatus=1 collected=0 (partial, total-budget) "
        "failed=0 (partial, total-budget)",
    ]
    _emit_hard_exit_lines(config, lines)
    os._exit(1)


# frob:waive WIRE001 reason="genuinely wired -- called only by _run_midrun_watchdog \
# below, itself reached exclusively via threading.Thread(target=...), same class of \
# gap this file's pre-existing T-3608 _stall_detected/_announce_stall_and_abort \
# WIRE001 waivers already cover, not a direct in-repo call site" follow_up="T-3381"
def _midrun_stall_detected(
    now: float, last_progress_ts: float, threshold_s: float
) -> bool:
    """Pure predicate (T-3683): true once `threshold_s` seconds have
    elapsed since `last_progress_ts` (either the watchdog's own start
    time, if no test has ever reported progress yet, or the most recent
    `pytest_runtest_logreport`). Deliberately requires NEITHER an xdist
    worker crash NOR `pytest-xdist` at all -- unlike T-3608's `_stall_
    detected`, which needs both -- since a mid-run subprocess wedge has
    no crash marker to key off of."""
    return (now - last_progress_ts) >= threshold_s


# frob:waive WIRE001 reason="genuinely wired -- called only by _run_midrun_watchdog \
# below, itself reached exclusively via threading.Thread(target=...), same class of \
# gap this file's pre-existing T-3608 WIRE001 waivers already cover, not a direct \
# in-repo call site" follow_up="T-3381"
def _announce_midrun_stall_and_hard_exit(
    config: pytest.Config, now: float, threshold_s: float
) -> None:
    """T-3683: the mid-run twin of T-3608's `_announce_stall_and_abort` --
    prints a `SUITE-RESULT: MIDRUN-WATCHDOG-STALL` line plus T-3675's own
    `_describe_teardown_blockers()` inventory line (reused, not
    duplicated: the whole point is naming what is still alive when a
    wedge with no xdist crash marker and no session-finish hook ever
    reached is declared), flushes both streams, then `os._exit(1)`s --
    the SAME hard-exit shape every other wedge-response in this file
    uses, applied to a THIRD wedge class this file did not previously
    have any answer for at all."""
    lines = [
        f"SUITE-RESULT: MIDRUN-WATCHDOG-STALL no test call-phase has "
        f"reported progress for >={threshold_s:g}s (T-3683) -- aborting "
        f"now instead of waiting for the external CI step budget to kill "
        f"this job with zero diagnostic output",
        _describe_teardown_blockers(),
        "SUITE-RESULT: exitstatus=1 collected=0 (partial, midrun-stall) "
        "failed=0 (partial, midrun-stall)",
    ]
    _emit_hard_exit_lines(config, lines)
    os._exit(1)


# frob:waive WIRE001 reason="genuinely wired -- passed as threading.Thread(target=...) \
# by pytest_configure below (a runtime indirection, not a direct in-repo call WIRE's \
# static callgraph can trace), same class of gap this file's pre-existing T-3608 \
# _run_stall_watchdog WIRE001 waiver already covers" follow_up="T-3381"
def _run_midrun_watchdog(
    config: pytest.Config,
    stop_event: "threading.Event",
    threshold_s: float | None,
    total_budget_s: float | None = None,
) -> None:
    """T-3683: the background thread body `pytest_configure` starts
    whenever `_midrun_watchdog_threshold_s()`/`_total_budget_threshold_
    s()` is not `None`. Wakes every `min(30.0, threshold_s / 3)` seconds
    (a finer poll than T-3608's fixed 5s default, scaled to the
    stall-detection threshold when one is armed so a short test-only
    threshold still gets several checks before firing; falls back to a
    flat 30s poll -- `threshold_s is None` -- when only the T-3707 total
    budget is armed, since that check has no "3 checks before firing"
    shape to scale against) and checks TWO independent triggers every
    wake, in this order:

    1. `_total_budget_exceeded` (T-3707), when `total_budget_s` is not
       `None` -- elapsed wall-clock time since the watchdog thread's own
       start (`_midrun_watchdog_started_ts`), with NO progress signal
       involved at all. Checked FIRST because it is the coarser, more
       final trigger: a suite that is genuinely still making progress
       trips this the instant total elapsed time crosses the cap,
       exactly the "slow-but-continuous-progress" shape T-3692 found
       the stall watchdog blind to.
    2. `_midrun_stall_detected` (T-3683), when `threshold_s` is not
       `None` -- unchanged from before this ticket, checked against
       whichever of `_last_progress_ts`/`_midrun_watchdog_started_ts` is
       the more recent baseline.

    The first one to fire calls its own `_announce_*_and_hard_exit` and
    returns (the process is gone by then). `stop_event` is set by
    `pytest_sessionfinish` on a normal end-of-run."""
    import time

    poll_s = min(30.0, threshold_s / 3) if threshold_s else 30.0
    while not stop_event.wait(poll_s):
        now = time.time()
        baseline = _last_progress_ts
        if baseline is None:
            baseline = _midrun_watchdog_started_ts
        if baseline is None:
            continue
        if total_budget_s is not None and _total_budget_exceeded(
            now, _midrun_watchdog_started_ts or baseline, total_budget_s
        ):
            _announce_total_budget_exceeded_and_hard_exit(
                config, now, _midrun_watchdog_started_ts or baseline, total_budget_s
            )
            return
        if threshold_s is not None and _midrun_stall_detected(
            now, baseline, threshold_s
        ):
            _announce_midrun_stall_and_hard_exit(config, now, threshold_s)
            return


_last_internal_error: str | None = None
"""T-3246: the most recent `pytest_internalerror` cause, stashed here because
`pytest_sessionfinish` receives only the exit status, not the exception --
`pytest_internalerror` fires (when it fires) strictly before
`pytest_sessionfinish` in the same process, so this is populated by the time
the `SUITE-RESULT:` line is written for an `exitstatus=3` (INTERNAL-ERROR)
run. Reset at the start of every session (`pytest_configure`) so a stale
value from an earlier in-process run can never leak into a later one."""


# frob:ticket T-3246
# frob:waive WIRE001 reason="genuinely wired -- pytest calls pytest_internalerror via \
# its plugin hook protocol (name-based discovery, like the pre-existing \
# pytest_configure/pytest_sessionfinish hooks in this same file), not a direct in-repo \
# call site" follow_up="T-3381"
def pytest_internalerror(
    excrepr: object, excinfo: pytest.ExceptionInfo[BaseException]
) -> None:
    """Record an INTERNALERROR's cause (T-3246) so the always-visible
    `SUITE-RESULT:` line can name it instead of just reporting
    `exitstatus=3` with no context -- pytest calls this hook, when it fires
    at all, before `pytest_sessionfinish` in the same process."""
    global _last_internal_error
    _last_internal_error = f"{excinfo.typename}: {excinfo.value}"


# frob:ticket T-3516
_XDIST_CRASH_MARKER_DIR = _REPO_ROOT / ".frob" / "xdist-crash-marker"
"""T-3516: per-worker \"what is this worker running right now\" marker
directory -- one small file per xdist worker id (`gw0.json` etc), written
by the WORKER just before each test's call phase and cleared right after,
so a CONTROLLER-side crash handler (`pytest_handlecrashitem`) can infer
whether a dead worker was mid-timeout (elapsed since the marker's
`started` timestamp is at/above the run's configured `--timeout`) or died
long before any timeout could have fired (more likely an OOM-kill or a
hard segfault) -- the crash itself never sends a report back to the
controller (that is what "crashed" means), so this marker is the only
signal available once the worker is gone."""

_WORKER_CRASH_RERUN_CAP = 0
"""T-3516: how many times `pytest_handlecrashitem` will ask xdist to
reschedule a crashed test onto a fresh worker before giving up and
leaving it as a plain failure. Defaults to 0 (no automatic reschedule) --
xdist does not retry a crashed test on its own (only a
`pytest_handlecrashitem` implementation that calls `sched.mark_test_
pending` does), and a DETERMINISTIC crasher (a real bug, not a transient
OOM) rescheduled once would just crash its fresh worker too, turning one
`WORKER-CRASH-REPORT` entry into a cascade -- exactly what MUST-FIRE's
"exactly one entry" acceptance bar rules out. The cap mechanism itself is
real and tested (`TestWorkerCrashReport.test_handlecrashitem_respects_a_
raised_rerun_cap`) for a future ticket to raise past 0 once there is a
reliable way to tell "transient" from "deterministic" apart; until then,
capped at 0 is the honest -- never silently-retrying-into-green -- default
this ticket's own MUST-FIRE bar requires."""

_worker_crash_entries: list[str] = []
"""T-3516: one formatted `WORKER-CRASH-REPORT:` line per worker crash
this session observed, appended by `pytest_handlecrashitem` (controller
process only) and flushed by `pytest_sessionfinish`. Module-level because
xdist hooks have no session-scoped storage of their own that survives
from the crash callback to the end-of-run summary."""

_worker_crash_causes: dict[str, str] = {}
"""T-3516: nodeid -> one-line inferred cause, so `pytest_sessionfinish`
can suffix the existing `SUITE-RESULT-FAILED:` line for a crashed test
with WHY it failed, without changing that line's pinned format for an
ordinary (non-crash) failure."""

_worker_crash_rerun_counts: dict[str, int] = {}
"""T-3516: nodeid -> how many times this session has already asked xdist
to reschedule it after a crash -- consulted and incremented by
`pytest_handlecrashitem`, capped at `_WORKER_CRASH_RERUN_CAP`."""

_worker_crash_hook_config: pytest.Config | None = None
"""T-3516: `config` stashed by `pytest_configure` (every process, worker
and controller alike) for `pytest_runtest_logstart`/`pytest_runtest_
logfinish`/`pytest_handlecrashitem` to read -- none of those three hooks
receive `config` as an argument of their own."""


# frob:ticket T-3608
_last_node_death_ts: float | None = None
"""T-3608: wall-clock time of the most recent `pytest_testnodedown` this
controller observed -- xdist's own `DSession.worker_errordown` fires this
hook FIRST, before its own (sometimes-buggy) reschedule/crash-report
bookkeeping, so it is a signal of "a worker died" independent of whether
`pytest_handlecrashitem` (T-3516's own `WORKER-CRASH-REPORT`) ever actually
ran -- run 33451274911's own incident is exactly a death where the latter
never fired at all. The stall watchdog treats either this OR a recorded
`WORKER-CRASH-REPORT` entry as "a crash happened"."""


# frob:ticket T-3608
_STALL_POLL_SECONDS = float(os.environ.get("FROB_XDIST_STALL_POLL_SECONDS", "5"))
"""T-3608: how often the controller-only stall watchdog thread wakes up to
re-check for forward progress. Env-overridable so a test can shrink it to
make the watchdog's own loop observable in bounded time."""

_STALL_ABORT_SECONDS = float(os.environ.get("FROB_XDIST_STALL_ABORT_SECONDS", "180"))
"""T-3608: how long the controller may see NO completed test (`pytest_
runtest_logreport` with `when==\"call\"`) after at least one recorded
worker crash before the watchdog declares a stall and aborts. Run
33451274911's incident idled ~20 minutes before the CI budget killed it;
180s is a deliberately small default so a real stall costs minutes, not a
whole job's budget -- env-overridable for a slower CI image or a test."""

_last_progress_ts: float | None = None
"""T-3608: wall-clock time of the most recent `pytest_runtest_logreport`
(`when==\"call\"`) the controller observed, updated by `pytest_runtest_
logreport` and read by the stall watchdog -- `None` until the first such
report or when the watchdog is not running (plain serial pytest)."""

_stall_watchdog_stop: "threading.Event | None" = None
"""T-3608: signals the stall watchdog thread to stop -- set by `pytest_
sessionfinish` on a normal (non-stalled) end-of-run so the daemon thread
never fires a spurious abort after the session has already finished
cleanly."""

_stall_watchdog_thread: "threading.Thread | None" = None
"""T-3608: the running stall watchdog thread, started by `pytest_configure`
controller-only under `pytest-xdist`; `None` under plain serial pytest."""


# frob:ticket T-3608
# frob:waive WIRE001 reason="genuinely wired -- called only by _run_stall_watchdog \
# below, itself reached exclusively via threading.Thread(target=...) (a runtime \
# indirection WIRE's static callgraph cannot trace, the same class of gap this file's \
# pre-existing pytest_internalerror/pytest_handlecrashitem waivers already cover), not \
# a direct in-repo call site" follow_up="T-3381"
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestStallWatchdog.test_stall_detected_requires\
# _both_a_crash_and_a_progress_gap
def _stall_detected(
    now: float, last_progress_ts: float | None, has_crash: bool, abort_seconds: float
) -> bool:
    """Pure predicate (T-3608): true only when the controller has recorded
    at least one worker crash (`has_crash`, i.e. `_worker_crash_entries` is
    non-empty) AND no test has completed for at least `abort_seconds` --
    exactly the shape of run 33451274911's incident (every surviving
    worker idle in xdist's own `remote.py:run_one_test -> get`, forever,
    with no forward progress and no session end). Requiring BOTH keeps a
    merely-slow (but still progressing) suite from ever tripping this --
    only a stall that started at or after a crash is the deadlock this
    exists to break."""
    if not has_crash or last_progress_ts is None:
        return False
    return (now - last_progress_ts) >= abort_seconds


# frob:ticket T-3608
# frob:waive WIRE001 reason="genuinely wired -- called only by \
# _announce_stall_and_abort below, itself reached exclusively via \
# _run_stall_watchdog's threading.Thread(target=...) indirection, same gap this file's \
# own _stall_detected WIRE001 waiver above already covers, not a direct in-repo call \
# site" follow_up="T-3381"
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestStallWatchdog.test_format_stalled_item_lin\
# es_reads_surviving_markers
def _format_stalled_item_lines(marker_dir: Path, now: float) -> list[str]:
    """T-3608: one `STALL-CRASH-REPORT:` line per T-3516 per-worker marker
    file still present in `marker_dir` at the moment a stall is declared.
    `pytest_runtest_logstart` writes a marker just before a worker starts a
    test and `pytest_runtest_logfinish` clears it on normal completion, so
    a marker still on disk here names a nodeid that was in flight on some
    worker when the whole session stopped making progress -- extending
    T-3516's `WORKER-CRASH-REPORT` naming to a death whose own
    `pytest_handlecrashitem` was never called (the exact gap run
    33451274911 exposed: no `WORKER-CRASH-REPORT` line was emitted at
    all)."""
    lines: list[str] = []
    if not marker_dir.is_dir():
        return lines
    import json

    for marker_path in sorted(marker_dir.glob("*.json")):
        worker_id = marker_path.stem
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        nodeid = marker.get("nodeid", "<unknown>")
        started = marker.get("started", now)
        lines.append(
            f"STALL-CRASH-REPORT: worker={worker_id} nodeid={nodeid} "
            f"in-flight for {now - started:.1f}s when the session stalled"
        )
    return lines


# frob:ticket T-3608
# frob:waive WIRE001 reason="genuinely wired -- called only by _run_stall_watchdog \
# below, itself reached exclusively via threading.Thread(target=...), same gap this \
# file's own _stall_detected WIRE001 waiver above already covers, not a direct in-repo \
# call site" follow_up="T-3381"
def _announce_stall_and_abort(config: pytest.Config, now: float) -> None:
    """T-3608: builds and prints the loud stall report (a `SUITE-RESULT:
    STALL-DETECTED` line, one `STALL-CRASH-REPORT:` per still-in-flight
    marker, and every `WORKER-CRASH-REPORT:` entry recorded so far), then
    hard-exits the controller process via `os._exit`. A clean pytest
    teardown is not attempted on purpose: the failure mode this responds
    to is every surviving worker permanently blocked in xdist's own
    `remote.py:run_one_test -> get` -- there is no reachable graceful path
    out of that, only an external kill, which is exactly the ~20 minute
    CI-budget kill this replaces with a prompt, self-inflicted, and
    NAMED one."""
    lines = [
        f"SUITE-RESULT: STALL-DETECTED no test has completed for "
        f">={_STALL_ABORT_SECONDS:g}s after a worker crash -- aborting now "
        f"instead of waiting for an external budget to kill this job (T-3608)",
    ]
    lines.extend(_format_stalled_item_lines(_XDIST_CRASH_MARKER_DIR, now))
    lines.extend(_worker_crash_entries)
    lines.append(
        "SUITE-RESULT: exitstatus=1 collected=0 (partial, stall-abort) "
        "failed=0 (partial, stall-abort)"
    )
    # T-3608/T-3726: `os._exit` skips Python's normal buffered-stream
    # flush, AND (T-3726) a plain `sys.stdout.flush()` alone cannot
    # rescue a write made while pytest's own fd-level capture manager is
    # still active -- see `_emit_hard_exit_lines`'s docstring for the
    # full root-cause writeup this shared helper fixes for every
    # hard-exit site in this file, this one included.
    _emit_hard_exit_lines(config, lines)
    os._exit(1)


# frob:ticket T-3608
# frob:waive WIRE001 reason="genuinely wired -- passed as threading.Thread(target=...) \
# by pytest_configure below (a runtime indirection, not a direct in-repo call WIRE's \
# static callgraph can trace), same class of gap this file's pre-existing \
# pytest_internalerror/pytest_handlecrashitem waivers already cover" follow_up="T-3381"
def _run_stall_watchdog(config: pytest.Config, stop_event: "threading.Event") -> None:
    """T-3608: the controller-only background thread body, started by
    `pytest_configure` under `pytest-xdist`. Wakes every `_STALL_POLL_
    SECONDS` and checks `_stall_detected`; the first time it fires, calls
    `_announce_stall_and_abort` and returns (the process is gone by then).
    `stop_event` is set by `pytest_sessionfinish` on a normal end-of-run so
    this loop exits quietly instead of polling a session that no longer
    exists."""
    import time

    while not stop_event.wait(_STALL_POLL_SECONDS):
        now = time.time()
        has_crash = bool(_worker_crash_entries) or _last_node_death_ts is not None
        if _stall_detected(now, _last_progress_ts, has_crash, _STALL_ABORT_SECONDS):
            _announce_stall_and_abort(config, now)
            return


# frob:ticket T-3608
# frob:ticket T-3643
# frob:waive WIRE001 reason="genuinely wired -- pytest-xdist calls this via its own \
# newhooks.py pytest_testnodedown hookspec (DSession.worker_errordown/worker_ \
# workerfinished), name-based plugin discovery like this file's pre-existing \
# pytest_handlecrashitem waiver, not a direct in-repo call site" follow_up="T-3381"
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestStallWatchdog.test_testnodedown_marks_a_de\
# ath_controller_only
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestStallWatchdog.test_pytest_testnodedown_is_\
# optionalhook
@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node: object, error: object) -> None:
    """T-3608: records that SOME worker went down, independent of whether
    `pytest_handlecrashitem` (T-3516's `WORKER-CRASH-REPORT`) ever actually
    ran for it -- xdist's own `DSession.worker_errordown`/`worker_
    workerfinished` fire this hook first, ahead of their own reschedule/
    crash-report bookkeeping, so it is the one signal that survives even
    the exact gap run 33451274911 exposed (a death for which no
    `WORKER-CRASH-REPORT` line was ever emitted). Controller-only (mirrors
    every other controller-only hook in this file).

    T-3643: `@pytest.hookimpl(optionalhook=True)` -- this is an xdist-only
    hookspec (`xdist.newhooks`), so without this decorator pytest's own
    plugin validation refuses to even START under `-p no:xdist` (Windows
    CI's Test step, run 33491468339: `PluginValidationError: unknown hook
    'pytest_testnodedown' in plugin tests.conftest`, `SUITE-RESULT: DID-
    NOT-COMPLETE exitstatus=3`, `collected=0` -- the ENTIRE Windows suite
    dead before a single test ran). Matches this file's pre-existing
    `pytest_handlecrashitem` waiver's same optionalhook posture."""
    config = _worker_crash_hook_config
    if config is not None and hasattr(config, "workerinput"):
        return
    global _last_node_death_ts
    import time

    _last_node_death_ts = time.time()


# frob:ticket T-3608
# frob:waive WIRE001 reason="genuinely wired -- pytest calls pytest_runtest_logreport \
# via its own core hookspec (name-based plugin discovery), same gap this file's \
# pre-existing pytest_internalerror/pytest_runtest_logstart hooks already have a \
# waiver for, not a direct in-repo call site" follow_up="T-3381"
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """T-3608: marks forward progress for the stall watchdog -- updates
    `_last_progress_ts` to now whenever a test's call phase finishes
    (`report.when == \"call\"`), on the controller only (`workerinput`
    absent there; a worker's own local notion of progress is not what the
    watchdog needs -- it needs to know the CONTROLLER is still hearing
    from *some* worker). A no-op under plain serial pytest (the watchdog
    is never started there, but the hook still fires harmlessly)."""
    config = _worker_crash_hook_config
    if config is not None and hasattr(config, "workerinput"):
        return
    if report.when != "call":
        return
    global _last_progress_ts
    import time

    _last_progress_ts = time.time()


# frob:waive WIRE001 reason="genuinely wired -- called by pytest_runtest_logstart/ \
# pytest_runtest_logfinish/_infer_worker_crash_cause below, all of which are \
# themselves reached only via pytest's own name-based hook discovery (not a direct \
# in-repo call site WIRE001's callgraph can trace into), the same gap this file's \
# pre-existing pytest_internalerror waiver already covers" follow_up="T-3381"
def _xdist_crash_marker_path(worker_id: str) -> Path:
    """The per-worker \"currently running\" marker file `worker_id`
    (e.g. `\"gw3\"`) writes to and `pytest_handlecrashitem` reads from
    (T-3516)."""
    return _XDIST_CRASH_MARKER_DIR / f"{worker_id}.json"


# frob:ticket T-3516
# frob:waive WIRE001 reason="genuinely wired -- pytest calls pytest_runtest_logstart \
# via its own core hookspec (name-based plugin discovery, same gap this file's \
# pre-existing pytest_internalerror/pytest_configure/pytest_sessionfinish hooks \
# already have a waiver for), not a direct in-repo call site" follow_up="T-3381"
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_logstart_writes_mar\
# ker_only_on_worker
def pytest_runtest_logstart(nodeid: str, location: object) -> None:
    """Worker-side half of T-3516's timeout-vs-OOM crash heuristic: record
    `nodeid` and the current time to this worker's own marker file just
    before pytest runs it, so a controller-side crash handler can later
    infer how long the worker had been running when it died. A no-op on
    the controller process itself (`workerinput` absent there) and under
    plain serial pytest (no `-n`) -- `config.workerinput["workerid"]` is
    only present on an actual xdist worker."""
    config = _worker_crash_hook_config
    if config is None or not hasattr(config, "workerinput"):
        return
    worker_id = config.workerinput.get("workerid")
    if not worker_id:
        return
    import json
    import time

    _XDIST_CRASH_MARKER_DIR.mkdir(parents=True, exist_ok=True)
    marker = {"nodeid": nodeid, "started": time.time()}
    _xdist_crash_marker_path(worker_id).write_text(json.dumps(marker), encoding="utf-8")


# frob:ticket T-3516
# frob:waive WIRE001 reason="genuinely wired -- pytest calls pytest_runtest_logfinish \
# via its own core hookspec (name-based plugin discovery), same gap this file's \
# pre-existing pytest_internalerror waiver already covers, not a direct in-repo call \
# site" follow_up="T-3381"
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_logfinish_clears_ma\
# rker
def pytest_runtest_logfinish(nodeid: str, location: object) -> None:
    """Clear T-3516's per-worker marker once `nodeid` finishes normally
    (any outcome, including a plain failure) -- only a worker that dies
    WITHOUT reaching this hook leaves a stale marker for
    `pytest_handlecrashitem` to find, which is exactly the "worker crashed
    mid-test" signal this pair of hooks exists to capture."""
    config = _worker_crash_hook_config
    if config is None or not hasattr(config, "workerinput"):
        return
    worker_id = config.workerinput.get("workerid")
    if not worker_id:
        return
    _xdist_crash_marker_path(worker_id).unlink(missing_ok=True)


# frob:ticket T-3516
# frob:waive WIRE001 reason="genuinely wired -- called only by pytest_handlecrashitem \
# above, itself reached exclusively via pytest-xdist's own name-based hook discovery \
# (see that function's own WIRE001 waiver), not a direct in-repo call site" \
# follow_up="T-3381"
def _infer_worker_crash_cause(worker_id: str, timeout_seconds: float | None) -> str:
    """One-line inferred cause for a crashed worker (T-3516): reads
    `worker_id`'s marker file (written by `pytest_runtest_logstart`,
    T-3516) to see how long the crashed test had been running. At or past
    the run's configured `--timeout`/`PYTEST_TIMEOUT` value, this matches
    pytest-timeout's own `--timeout-method=thread` shape (dump stacks,
    then `os._exit`) closely enough to name it directly; well short of
    that budget (or no timeout configured at all), a hard death this
    early is more consistent with an OOM-kill or a genuine segfault than
    a timeout, so this says so instead of guessing a specific cause it
    cannot actually observe (the crashed worker sent no report, so there
    is no captured dump text to inspect here, only elapsed time)."""
    import json
    import time

    marker_path = _xdist_crash_marker_path(worker_id)
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "worker died without a running-test marker -- suspect OOM or a hard crash before any test started"
    finally:
        marker_path.unlink(missing_ok=True)
    elapsed = time.time() - marker.get("started", time.time())
    if timeout_seconds is not None and elapsed >= timeout_seconds:
        return (
            f"exceeded {timeout_seconds:g}s timeout (thread-method os._exit, "
            f"{elapsed:.1f}s elapsed)"
        )
    return f"worker died without a timeout dump ({elapsed:.1f}s elapsed) -- suspect OOM"


# frob:ticket T-3516
# frob:waive WIRE001 reason="genuinely wired -- pytest-xdist calls this via its own \
# newhooks.py pytest_handlecrashitem hookspec \
# (xdist.dsession.DSession.handle_crashitem), name-based plugin discovery like this \
# file's pre-existing pytest_internalerror/ pytest_sessionfinish hooks, not a direct \
# in-repo call site" follow_up="T-3381"
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_handlecrashitem_rec\
# ords_one_entry_and_marks_failed
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport.test_handlecrashitem_res\
# pects_a_raised_rerun_cap
@pytest.hookimpl(optionalhook=True)
def pytest_handlecrashitem(crashitem: str, report: Any, sched: Any) -> None:
    """pytest-xdist's crashed-item hook (T-3516): a worker died running
    `crashitem` (a nodeid) with no report of its own ever reaching the
    controller, so `report` here is the SYNTHETIC failure xdist's own
    `DSession.handle_crashitem` builds in its place. Collects one
    `WORKER-CRASH-REPORT` entry (worker id, nodeid, inferred cause,
    rerun disposition) into the module-level list `pytest_sessionfinish`
    flushes at end-of-run, and asks xdist to reschedule the test onto a
    fresh worker ONCE (`_WORKER_CRASH_RERUN_CAP`) via
    `sched.mark_test_pending` -- but always LEAVES `report.outcome`
    as `\"failed\"` (xdist's own default) regardless of whether a
    reschedule was requested, so the crash is never a silent skip: it
    shows up in `SUITE-RESULT-FAILED` this run even if a later retry on
    a fresh worker happens to pass."""
    worker = getattr(report, "node", None)
    gateway = getattr(worker, "gateway", None)
    worker_id = getattr(gateway, "id", None) or "unknown"
    config = _worker_crash_hook_config
    timeout_seconds = None
    if config is not None:
        raw_timeout = config.getoption("timeout", default=None)
        if raw_timeout is None:
            ini_timeout = config.getini("timeout") if config.getini("timeout") else None
            raw_timeout = ini_timeout
        if raw_timeout:
            try:
                timeout_seconds = float(raw_timeout)
            except (TypeError, ValueError):
                timeout_seconds = None
    cause = _infer_worker_crash_cause(worker_id, timeout_seconds)
    rerun_count = _worker_crash_rerun_counts.get(crashitem, 0)
    if rerun_count < _WORKER_CRASH_RERUN_CAP:
        _worker_crash_rerun_counts[crashitem] = rerun_count + 1
        try:
            sched.mark_test_pending(crashitem)
        except Exception as exc:  # noqa: BLE001 -- reschedule is best-effort
            disposition = f"rerun requested but reschedule failed ({exc})"
        else:
            disposition = f"rescheduled ({rerun_count + 1}/{_WORKER_CRASH_RERUN_CAP})"
    else:
        disposition = f"not rescheduled (rerun cap {_WORKER_CRASH_RERUN_CAP} reached)"
    message = f"worker {worker_id} died running {crashitem}: {cause} -- {disposition}"
    _worker_crash_causes[crashitem] = f"{cause} -- {disposition}"
    _worker_crash_entries.append(
        f"WORKER-CRASH-REPORT: worker={worker_id} nodeid={crashitem} cause={cause} "
        f"disposition={disposition}"
    )
    try:
        report.longrepr = message
    except Exception:  # noqa: BLE001 -- best-effort annotation only
        pass


# frob:ticket T-3516
_dsession_hardened = False
"""T-3516: guards `_harden_dsession_active_nodes` so the monkeypatch below
is applied at most once per process even though `pytest_configure` can in
principle run more than once in the same interpreter (T-3246's own
`_last_internal_error` reset comment notes the same possibility)."""


# frob:waive WIRE001 reason="genuinely wired -- called only from pytest_configure \
# above, itself reached exclusively via pytest's own name-based hook discovery (same \
# gap this file's pre-existing pytest_internalerror waiver already covers), not a \
# direct in-repo call site" follow_up="T-3381"
def _harden_dsession_active_nodes() -> None:
    """Patch `xdist.dsession.DSession.worker_workerfinished`/
    `worker_errordown` (T-3516) so a SECOND crash-adjacent callback for
    the same already-removed `WorkerController` calls `set.discard`
    instead of `set.remove` -- the observed `INTERNALERROR> KeyError:
    <WorkerController gwN>` (run 33291796476-adjacent local repro cited
    in this ticket) traces to exactly this: xdist's own
    `self._active_nodes.remove(node)` at the tail of both methods raises
    `KeyError` when the SAME node has already been removed by the other
    callback firing first for the same dying worker -- a real race in
    xdist's own bookkeeping, not this repo's code, but one this repo can
    absorb without waiting on an upstream fix. Controller-only (mirrors
    every other controller-only hook in this file); silently a no-op if
    `pytest_xdist` is not installed/importable or its internals have
    changed shape (never blocks collection over a best-effort hardening
    patch)."""
    global _dsession_hardened
    if _dsession_hardened:
        return
    try:
        from xdist.dsession import DSession
    except ImportError:  # pragma: no cover - pytest-xdist always installed here
        return

    original_workerfinished = DSession.worker_workerfinished
    original_errordown = DSession.worker_errordown

    def _safe_workerfinished(self: Any, node: Any) -> None:
        try:
            original_workerfinished(self, node)
        except KeyError:
            self._active_nodes.discard(node)  # noqa: SLF001

    def _safe_errordown(self: Any, node: Any, error: Any = None) -> None:
        try:
            original_errordown(self, node, error)
        except KeyError:
            self._active_nodes.discard(node)  # noqa: SLF001

    DSession.worker_workerfinished = (  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
        _safe_workerfinished
    )
    DSession.worker_errordown = (  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
        _safe_errordown
    )
    _dsession_hardened = True


# frob:ticket T-1596
# frob:ticket T-1673
# frob:ticket T-3246
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_prints_\
# greppable_line_at_any_verbosity
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_skips_o\
# n_xdist_worker
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_lists_f\
# ailing_node_ids
# frob:tests \
# tests/unit/test_conftest_stackdump.py::TestSuiteResultLine.test_sessionfinish_caps_fa\
# iling_node_ids_with_and_n_more
# frob:tests \
# tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_s\
# essionfinish_labels_did_not_complete_runs
# frob:waive FMT001 reason="single-line frob:tests directive naming a long test node \
# id -- already at frob fmt's own canonical form (verified: `frob fmt` reports it \
# unchanged), same unwrappable shape as src/frob/app/_json_guard.py's existing FMT001 \
# waivers"
# frob:tests \
# tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_s\
# essionfinish_marks_failing_set_incomplete_on_abort
# frob:waive FMT001 reason="single-line frob:tests directive naming a long test node \
# id -- already at frob fmt's own canonical form (verified: `frob fmt` reports it \
# unchanged), same unwrappable shape as src/frob/app/_json_guard.py's existing FMT001 \
# waivers"
# frob:tests \
# tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_s\
# essionfinish_names_internalerror_cause
# frob:waive FMT001 reason="single-line frob:tests directive naming a long test node \
# id -- already at frob fmt's own canonical form (verified: `frob fmt` reports it \
# unchanged), same unwrappable shape as src/frob/app/_json_guard.py's existing FMT001 \
# waivers"
# frob:tests \
# tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete.test_s\
# essionfinish_completed_run_format_is_unchanged
# frob:waive FMT001 reason="single-line frob:tests directive naming a long test node \
# id -- already at frob fmt's own canonical form (verified: `frob fmt` reports it \
# unchanged), same unwrappable shape as src/frob/app/_json_guard.py's existing FMT001 \
# waivers"
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Print an always-visible `SUITE-RESULT:` line at the end of every run
    (T-1596), independent of pytest's own verbosity-gated terminal summary,
    followed by each failing test's node id (T-1673) so the line is
    actionable without a second full run.

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
    this exists to provide.

    T-1673 root cause: the count alone ("failed=5") was not actionable --
    under stacked `-q`, pytest's own "short test summary info" section
    (which normally lists failing node ids) is also suppressed, so a
    reader had no way to learn WHICH five tests failed short of re-running
    the entire suite. `terminalreporter.stats` is populated regardless of
    verbosity (it drives the summary section, it is not gated by it), so
    reading it here and writing each node id via the same unsuppressed
    `write_line` channel makes the failing set visible without a second
    run.

    T-3246 root cause: an ABORTED run (pytest exit code 2/3/4/5 -- e.g. an
    xdist worker crash producing `INTERNALERROR> KeyError` at exitstatus=3)
    rendered in the EXACT SAME line shape as a completed run with real
    failures, differing only in the unlabelled `exitstatus=` digit --
    `session.testscollected`/`testsfailed` are themselves partial counts of
    unknown looseness on an aborted run (collection/execution stopped
    mid-way), not a real total, and the `SUITE-RESULT-FAILED:` node ids
    that follow are only whatever had been recorded before the abort, not
    the suite's actual failing set. A reader (including the author of
    T-3246, by their own account) mistook the partial list for a complete
    failure count. Fixed by branching on `exitstatus` via
    `_COMPLETED_EXIT_STATUSES`: a completed run (0/1) keeps the EXACT
    pre-existing line format (pinned by
    `tests/unit/test_conftest_stackdump.py`, deliberately unchanged); a
    did-not-complete run instead gets a `DID-NOT-COMPLETE` line naming the
    exit status via `_EXIT_STATUS_LABELS`, marks both counts as partial,
    and -- if any failing ids are collected at all -- prefixes them with an
    explicit `SUITE-RESULT: failing set INCOMPLETE` line so the partial
    list can never again be read as the real one. Per the ticket: the
    partial information is NOT suppressed (it is the only record of what
    ran before the abort) -- only the missing label is fixed."""
    if hasattr(session.config, "workerinput"):
        return
    # T-3608: the session is ending normally (or aborting through a path
    # OTHER than the stall watchdog's own os._exit) -- stop the watchdog
    # thread so it never fires a spurious abort against a session that has
    # already finished.
    if _stall_watchdog_stop is not None:
        _stall_watchdog_stop.set()
    # T-3683: same posture for the mid-run watchdog -- reaching this hook
    # at all proves the run did NOT wedge mid-run, so stop it before it
    # can ever fire a spurious hard-exit against a session already ending
    # normally.
    if _midrun_watchdog_stop is not None:
        _midrun_watchdog_stop.set()
    total = getattr(session, "testscollected", 0)
    failed = getattr(session, "testsfailed", 0)
    completed = exitstatus in _COMPLETED_EXIT_STATUSES
    if completed:
        line = (
            f"SUITE-RESULT: exitstatus={exitstatus} collected={total} failed={failed}"
        )
    else:
        label = _EXIT_STATUS_LABELS.get(exitstatus, f"CODE-{exitstatus}")
        # T-3246: keep the bare `collected={total}`/`failed={failed}`
        # substrings intact (partial-ness noted as a trailing annotation,
        # not folded into the key name) -- `src/frob/gates/_bug_repro.py`'s
        # `_classify_designated_test_exit` already regex-matches the
        # literal `\bcollected=0\b` substring against this line to detect
        # a "test does not exist" repro run (T-2025); reshaping the key
        # would silently break that sibling consumer.
        line = (
            f"SUITE-RESULT: DID-NOT-COMPLETE exitstatus={exitstatus} ({label}) "
            f"collected={total} (partial) failed={failed} (partial, lower-bound)"
        )
        if _last_internal_error is not None:
            line += f" cause={_last_internal_error}"
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(line)
        stats = getattr(reporter, "stats", None)
        if stats:
            failing_ids: list[str] = []
            for outcome in ("failed", "error"):
                for report in stats.get(outcome, []):
                    nodeid = getattr(report, "nodeid", None)
                    if nodeid is not None:
                        node_line = f"{nodeid} ({outcome})"
                        # T-3516: a crashed test's own FAILED line gets its
                        # inferred cause appended -- an ordinary (non-crash)
                        # failure's line is byte-for-byte unchanged, so this
                        # never disturbs the pinned completed-run format.
                        cause = _worker_crash_causes.get(nodeid)
                        if cause is not None:
                            node_line += f" -- {cause}"
                        failing_ids.append(node_line)
            if failing_ids and not completed:
                reporter.write_line(
                    "SUITE-RESULT: failing set INCOMPLETE -- run aborted before "
                    "collecting/executing all tests, this is NOT the full failing set"
                )
            shown = failing_ids[: _suite_result_max_node_ids()]
            for node_line in shown:
                reporter.write_line(f"SUITE-RESULT-FAILED: {node_line}")
            remaining = len(failing_ids) - len(shown)
            if remaining > 0:
                reporter.write_line(f"SUITE-RESULT-FAILED: and {remaining} more")
        # T-3516: ONE end-of-run collected report of every worker crash this
        # session observed, on the SAME always-visible channel as
        # SUITE-RESULT -- MUST-STAY-QUIET: a clean run (empty
        # `_worker_crash_entries`) prints nothing here at all.
        if _worker_crash_entries:
            reporter.write_line(
                f"WORKER-CRASH-REPORT: {len(_worker_crash_entries)} worker crash(es)"
            )
            for entry in _worker_crash_entries:
                reporter.write_line(entry)
            # T-3516: a crash must never let the run's own exit status read
            # as clean, even if every crashed test's one capped rerun went
            # on to pass on a fresh worker -- `session.exitstatus` is read
            # by pytest's own `wrap_session` AFTER this hook returns, so
            # mutating it here is what actually changes the process's exit
            # code.
            if session.exitstatus == 0:
                session.exitstatus = 1
    else:  # pragma: no cover - defensive only, terminalreporter always registered
        print(line)
    _maybe_hard_exit_after_session_finish(session, exitstatus)


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
# frob:tests \
# tests/unit/test_conftest_parse_reset.py::TestConftestParseReset.test_reset_before_eac\
# h_test_isolates_partial_parse_state
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


# frob:ticket T-3123
# frob:ticket T-3145
@pytest.fixture(autouse=True)
def _isolate_worktree_lease_env_before_test() -> Iterator[None]:
    """Snapshot, CLEAR, and restore `FROB_WORKTREE`/`FROB_AGENT` around
    EVERY test (T-3123, extended by T-3145); `PYTEST_XDIST_AUTO_NUM_
    WORKERS` is snapshotted and restored but deliberately NOT cleared --
    see below.

    `frob.tickets._worktree_guard.apply_agent_env` (T-3094) mutates
    `os.environ` DIRECTLY (`os.environ.update(exports)`, no restore) --
    correct for its real production callers (`_verify.py`,
    `mutate_runner.py`, `perf_runner.py`, `_collect.py`,
    `_coverage_refresh.py`), each a short-lived CLI process with no
    "after" to restore to, same shape as T-1591's
    `PARSE_ARTIFACT_CACHE_ENV` stamp above. In a long-lived pytest-xdist
    worker that becomes a real cross-test leak: any test that drives
    `frob.tickets._land.land`'s post-merge evidence re-verification path
    in-process (most of `tests/test_ticket_land.py`) calls
    `apply_agent_env` on the fixture's OWN throwaway `tmp_path` worktree
    and leaves `FROB_WORKTREE` pointed at that now-torn-down directory
    for the rest of the worker's lifetime -- `enforce_worktree_lease`
    then refuses every LATER test's own mutating call against a
    DIFFERENT `tmp_path` repo with `TicketError.WorktreeLeaseViolation`
    (T-3123 measured 145-150 of 330 collected tests failing this way on
    an otherwise-unmodified main).

    T-3145: a SEPARATE root cause from the between-test leak T-3123
    closed above -- `FROB_WORKTREE`/`FROB_AGENT` set in the pytest
    WORKER's own `os.environ` from OUTSIDE the test session entirely
    (e.g. inherited from `frob ticket evidence`'s individual-reverify
    subprocess spawn, when the agent recording evidence is itself
    working inside a leased worktree -- `_run_pytest_directly`/
    `run_selected`'s spawn does not always strip these two vars from the
    child's environment, unlike the fully-audited no-`[[test.runner]]`
    fallback path). Snapshot-and-restore ALONE (the pre-T-3145 version
    of this fixture) does not touch this case at all: it captures
    whatever value is present at ITS OWN setup and restores exactly that
    value afterward, so a value already present when the very first
    test's setup runs -- this scenario -- survives untouched through
    EVERY test the fixture wraps, restore or no restore. Popping both
    keys during setup (not just capturing them) is what actually closes
    this: any test whose OWN body needs the real `enforce_worktree_
    lease` guard to fire (matching `tests/test_gates.py`'s
    `test_write_coverage_lock_refuses_under_lease_violation` opt-in
    idiom) sets one of these two itself via `monkeypatch.setenv`, from
    inside its own body, AFTER this fixture's setup already popped
    them -- `monkeypatch`'s own teardown then independently undoes that,
    so this fixture's `finally` below never fights it.

    `PYTEST_XDIST_AUTO_NUM_WORKERS` is NOT popped at setup, only
    snapshotted/restored (the T-3123 posture, unchanged): unlike the two
    lease vars, an ambient value here is not a correctness bug for any
    test -- it is playbook section 1e's own intentional fleet-aware
    xdist bound, legitimately present for the whole session, and
    clearing it here would just make `frob check`/`frob test`'s own
    in-process spawns (`apply_agent_env`, T-3094/T-3099) recompute a
    value they would have applied anyway.

    Plain `os.environ` mutation (not `monkeypatch.setenv`/`delenv`) for
    both the initial pop and the final restore, because the leak this
    closes bypasses `monkeypatch`'s own tracking entirely -- neither
    `apply_agent_env` nor an inherited-from-the-spawning-process value
    ever goes through `monkeypatch`, so `monkeypatch`'s teardown has
    nothing to undo either way. Restoring by exact prior value (present
    -> re-set, absent -> pop) handles a test that ALSO deliberately sets
    one of these three via its own `monkeypatch.setenv` (still cleaned
    up independently by `monkeypatch`'s own teardown, which runs before
    this fixture's `finally`) without this fixture fighting it."""
    keys = (FROB_WORKTREE_ENV, FROB_AGENT_ENV, PYTEST_XDIST_AUTO_NUM_WORKERS_ENV)
    # frob:waive SEC110 reason="FROB_WORKTREE/FROB_AGENT/PYTEST_XDIST_AUTO_NUM_WORKERS \
    # are dispatch-context markers (T-0574), never secrets -- same shape as the \
    # .claude/hooks/_agent_context.py waivers for the identical two vars"
    prior = {key: os.environ.get(key) for key in keys}
    for key in (FROB_WORKTREE_ENV, FROB_AGENT_ENV):
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                # frob:waive SEC110 reason="restoring a dispatch-context marker's \
                # prior value into os.environ, not writing a secret (T-0574)"
                os.environ[key] = value


# frob:ticket T-3525
_SELF_SCAN_CACHE_DIR = _REPO_ROOT / ".frob" / "self-scan-cache"
"""T-3525: on-disk persistence for `frob_self_scan_artifacts`'
`.violations`, keyed by `_repo_tree_hash()` -- makes an xdist worker
restart (T-3516's own WORKER-CRASH-REPORT machinery covers the crash
ITSELF; this covers what happens next) cheap: LOAD instead of recompute.
Lives under this repo's own `.frob/` (survives a worker's death) rather
than `tmp_path_factory`'s session temp dir (a FRESH worker process gets
its own fresh `tmp_path_factory` instance, so a tmp-rooted cache would
die with the worker that wrote it -- exactly the gap this ticket fixes)."""

_SELF_SCAN_COUNTER_ENV = "FROB_SELF_SCAN_COUNTER_FILE"
"""T-3525: test-only instrumentation -- when set, `_cached_self_scan`
appends one line to this file every time it actually RUNS `compute` (a
cache miss), never on a cache hit. Unset in every real run (CI and
local, zero overhead); the T-3525 MUST-FIRE test sets it to prove
scan-count==1 across a simulated worker restart (two separate
subprocess invocations sharing the same cache dir)."""


# frob:ticket T-3525
# frob:waive WIRE001 reason="genuinely wired -- called only from frob_self_scan_ \
# artifacts below, itself an xdist-group-pinned session fixture only consumed by \
# tests/system/test_frob_self_model.py and \
# tests/unit/strata/test_sys003_calibration.py (not a direct in-repo call site \
# WIRE001's callgraph traces into cross-package)" follow_up="T-3381"
def _repo_tree_hash(repo_root: Path) -> str:
    """A hash identifying the exact source tree `frob_self_scan_
    artifacts` would scan (T-3525) -- `HEAD`'s own commit sha plus a hash
    of `git status --porcelain`'s output, so an uncommitted local edit
    invalidates the cache too, not just a new commit. Falls back to a
    fixed sentinel (never raises) if git is unavailable or the call fails
    for any reason -- a cache-key MISS just costs one fresh scan, never a
    hard failure."""
    import hashlib
    import subprocess

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout
    except Exception:  # noqa: BLE001 -- a hash-computation failure is a cache miss
        return "no-git-fallback"
    return hashlib.sha256(f"{head}\n{status}".encode("utf-8")).hexdigest()


# frob:ticket T-3525
# frob:waive WIRE001 reason="genuinely wired -- called only from frob_self_scan_ \
# artifacts below, itself an xdist-group-pinned session fixture only consumed by \
# tests/system/test_frob_self_model.py and \
# tests/unit/strata/test_sys003_calibration.py (not a direct in-repo call site \
# WIRE001's callgraph traces into cross-package)" follow_up="T-3381"
def _cached_self_scan(cache_dir: Path, tree_hash: str, compute: "Any") -> "Any":
    """T-3525's caching primitive: load `compute`'s pickled result from
    `cache_dir/<tree_hash>.pkl` if present and readable, else call
    `compute()` ONCE, persist the result (atomic `Path.replace`, so a
    worker that dies mid-write never leaves a torn file for the next
    reader to trip over), and return it either way.

    Split out from `frob_self_scan_artifacts` itself so a test can
    exercise the caching/staleness/corruption logic directly against a
    cheap fake `compute`, without paying this repo's own real whole-tree
    scan cost per test run (T-3525's own MUST-FIRE/MUST-STAY-QUIET
    coverage: `tests/unit/test_conftest_stackdump.py::
    TestCachedSelfScan`).

    Corruption/staleness handling: any read/unpickle failure (a torn
    write from a worker that died mid-persist before this ticket's fix,
    a format change) is treated exactly like a cache miss -- falls
    through to a fresh `compute()` call, never raises."""
    import pickle

    cache_path = cache_dir / f"{tree_hash}.pkl"
    if cache_path.is_file():
        try:
            with cache_path.open("rb") as fh:
                return pickle.load(fh)
        except Exception:  # noqa: BLE001 -- a bad cache file is a cache miss
            pass
    result = compute()
    counter_path = os.environ.get(_SELF_SCAN_COUNTER_ENV)
    if counter_path:
        with open(counter_path, "a", encoding="utf-8") as fh:
            fh.write("1\n")
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(f".{os.getpid()}.tmp")
    try:
        with tmp_path.open("wb") as fh:
            pickle.dump(result, fh)
        tmp_path.replace(cache_path)
    except Exception:  # noqa: BLE001 -- persistence is best-effort only
        tmp_path.unlink(missing_ok=True)
    return result


# frob:ticket T-3495
# frob:ticket T-3525
class FrobSelfScanArtifacts:
    """Result of ONE `build_graph(_REPO_ROOT, ...)` + `sys_gate(...)` pass
    (T-3495) -- a plain in-process result carrier for test fixtures, not
    a pydantic model crossing any real boundary (it holds a `Result`
    object and a `Violation` tuple, never serialized). `.repo_root`/
    `.violations` are what every consuming test actually reads.

    T-3525: `.build_result` is `None` whenever `.violations` came from
    `_cached_self_scan`'s on-disk cache (the raw `GraphSnapshot` is not
    itself persisted -- no current consumer reads `.build_result` at
    all, see that field's own docstring below) -- also `None` on a FRESH
    scan now, for the same reason, so cache-hit and cache-miss callers
    see an identical shape rather than one that varies by chance."""

    __slots__ = ("repo_root", "build_result", "violations")

    def __init__(
        self, repo_root: Path, build_result: object, violations: tuple
    ) -> None:
        """Store one shared self-scan's repo root, raw build `Result`, and
        the `sys_gate` violations tuple every consuming test filters."""
        self.repo_root = repo_root
        self.build_result = build_result
        self.violations = violations


# frob:ticket T-3495
@pytest.fixture(scope="session")
def frob_self_scan_artifacts(
    tmp_path_factory: pytest.TempPathFactory,
) -> FrobSelfScanArtifacts:
    """ONE `build_graph(_REPO_ROOT, ...)` + `sys_gate(...)` pass over this
    repo's own real tree, computed ONCE per pytest session (per xdist
    worker process, since `tests/conftest.py::pytest_collection_
    modifyitems`'s `frob_self_scan_heavy` `xdist_group` already pins every
    consumer of this fixture onto the SAME worker -- session scope is
    therefore equivalent to "once for the whole group", T-3495's own
    fix) and shared by every test that would otherwise independently
    rebuild the identical whole-repo graph.

    T-3495: measured directly -- `tests/system/test_frob_self_model.py`'s
    `test_sys_gate_zero_violations`/`test_fragments_module_fs_read_is_
    declared_not_selfaudit001`/`test_checker_fleet_deploy_vet_have_no_
    undeclared_fs_write_selfaudit001`/`test_check_admission_exec_sites_
    are_declared_not_selfaudit001` and `tests/unit/strata/test_sys003_
    calibration.py`'s `test_sys003_zero_against_live_repo_design` each
    called `build_graph(_REPO_ROOT, tmp_path / "cache.db")` + `sys_gate`
    independently -- five identical ~30s-warm/multi-minute-cold whole-repo
    scans back to back in the SAME serialized `frob_self_scan_heavy`
    xdist group, the structural cause of the recurring CI tail stall this
    ticket fixes. Every consuming test still runs its OWN assertion over
    the SAME shared `.violations` tuple (a narrower message/rule filter,
    or the broad `== ()` bar) -- MUST-STAY-QUIET: a planted violation
    that only one narrow filter cares about still only fails that one
    test, exactly as when each test built its own graph. MUST-FIRE: a
    planted violation visible to the broad filter still fails `test_sys_
    gate_zero_violations` (or any other consumer using the same shape)
    the same way, since it is reading the real `sys_gate` output, not a
    stale or synthetic stand-in.

    A THROWAWAY cache db under `tmp_path_factory`'s own session-scoped
    temp dir (never this repo's real `.frob/cache.db`) -- same reasoning
    each test's own former `tmp_path / "cache.db"` docstring already
    gave: never race a concurrent `frob check`'s real cache file.

    T-3525: the scan is now wrapped by `_cached_self_scan`, keyed on
    `_repo_tree_hash(_REPO_ROOT)` -- an xdist worker that dies mid-GROUP
    (pytest-timeout's thread-method watchdog, this fixture's own
    dominant cost on a cold/slow runner) and gets replaced no longer
    restarts the scan from scratch: if an EARLIER worker in this same
    tree state already finished and persisted before dying on some
    LATER test, the fresh worker loads instead of recomputing. A worker
    that dies mid-COMPUTE (before persisting anything) still costs one
    fresh scan on the next worker -- this fixes the "N-times-over"
    cascade, not the one unavoidable in-flight cost the first attempt
    always pays.
    """
    from frob.gates import sys_gate
    from frob.graph import build_graph

    def _compute() -> tuple:
        cache_dir = tmp_path_factory.mktemp("frob_self_scan")
        build_result = build_graph(_REPO_ROOT, cache_dir / "cache.db")
        assert build_result.is_ok, f"graph build failed: {build_result.err}"
        return sys_gate(_REPO_ROOT, build_result.danger_ok)

    violations = _cached_self_scan(
        _SELF_SCAN_CACHE_DIR, _repo_tree_hash(_REPO_ROOT), _compute
    )
    return FrobSelfScanArtifacts(
        repo_root=_REPO_ROOT, build_result=None, violations=violations
    )


# frob:ticket T-3532
@pytest.fixture(scope="session")
def frob_self_scan_snapshot(
    tmp_path_factory: pytest.TempPathFactory,
) -> "GraphSnapshot":
    """T-3532: ONE `build_graph(_REPO_ROOT, ...)` snapshot object, shared
    by every `frob_self_scan_heavy` consumer that needs the raw graph
    (not just `frob_self_scan_artifacts`'s derived `sys_gate` violations
    tuple) -- e.g. a gate taking an explicit snapshot argument like
    `perf_gate(root, snap)`. Same "at most once per worker session"
    guarantee `frob_self_scan_artifacts` already gives (T-3495), reusing
    the SAME `frob_self_scan_heavy` xdist-group pinning
    (`pytest_collection_modifyitems`) so every consumer lands on one
    worker. Deliberately NOT threaded through the T-3525 on-disk
    violations cache: a `graph.Snapshot` object does not round-trip that
    cache cheaply the way a plain violations tuple does, so a worker that
    restarts mid-group still pays one fresh build here -- this fixture
    only removes the "N separate builds within the SAME worker session"
    cost T-3495 diagnosed, the same cost class T-3532 measured a second
    time in `tests/test_gates.py`'s `_snapshot(repo_root)` call (which
    also, incidentally, pointed at this repo's real `.frob/cache.db`
    instead of a throwaway one -- fixed here too by using
    `tmp_path_factory`, matching `frob_self_scan_artifacts`'s own
    reasoning for never touching the real cache)."""
    from frob.graph import build_graph

    cache_dir = tmp_path_factory.mktemp("frob_self_scan_snapshot")
    build_result = build_graph(_REPO_ROOT, cache_dir / "cache.db")
    assert build_result.is_ok, f"graph build failed: {build_result.err}"
    return build_result.danger_ok


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


_WIDGET_PY = '''class Widget:
    """A widget."""

    def render(self, value: int) -> str:
        """Render the widget."""
        # frob:doc docs/x.md#widget
        return str(value)
'''


_DESIGN_STRATA = """module m
node client : foreign { clearance Public; }
node api : authenticated { clearance Internal; }
node vault : trusted { clearance Secret; }
flow f_login : client -> api
boundary b_login endorse f_login : foreign -> authenticated when "jwt_verified"
"""


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    if not any(root.iterdir()):
        (root / ".gitkeep").write_text("")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "base", "--allow-empty"], cwd=root, check=True
    )


def _snapshot(root: Path):
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


# frob:ticket T-3666
def _write(root: Path, rel: str, text: str) -> Path:
    """T-3666: `newline=""` writes every `\n` in `text` verbatim, with
    NO platform translation -- the default `newline=None` text-mode
    write silently rewrites `\n` to `os.linesep` on write, which is
    `\r\n` on win32. Callers here pass literal `\n`-only strings
    expecting the file to contain EXACTLY those bytes (e.g. a dirty-
    snapshot fixture asserted against byte-for-byte by
    `tests/gates_suite/test_fix_engine.py`'s Tier-A tests) -- on win32,
    without this, `_write` silently injected a CRLF the product code
    under test never asked for, and the fixture (not the product code)
    was what introduced the mismatch. A no-op change on POSIX, where
    `os.linesep` is already `\n`."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, newline="")
    return path


def _violation(rule="R1", file="a.py", message="m", severity=Severity.WARN, line=1):
    from frob.gates import Violation

    return Violation(
        rule=rule, severity=severity, file=file, line=line, message=message
    )


# frob:ticket T-0807
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run `argv` in `cwd`, raising on a nonzero exit -- a thin `subprocess.run`
    wrapper for the real-git-repo fixtures T-0807's linked-worktree/lease
    tests need (mirrors `tests/test_tickets_leases.py::_run`)."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _rules(violations) -> list[str]:
    """The rule id of every violation, in order."""
    return [v.rule for v in violations]


def _files(violations) -> set[str]:
    """The set of files named by the violations."""
    return {v.file for v in violations}


def _first_rule(violations, rule):
    """The first violation with `rule`, or None -- assertion convenience."""
    for v in violations:
        if v.rule == rule:
            return v
    return None


def _by_rule(violations, rule) -> list:
    """Every violation carrying `rule` -- assertion convenience."""
    return [v for v in violations if v.rule == rule]


def _marker_line(root: Path, ticket_id: str) -> int:
    """The 1-indexed line number of `ticket_id`'s `<!-- ticket:... -->`
    marker in `root/tickets.md`, for building a `Hunk` span that targets
    exactly that ticket's ledger entry."""
    marker = f"<!-- ticket:{ticket_id} -->"
    lines = (root / "tickets.md").read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, start=1):
        if marker in line:
            return i
    raise AssertionError(f"marker for {ticket_id} not found in tickets.md")


# frob:ticket T-0564
def _state_line(root: Path, ticket_id: str) -> int:
    """The 1-indexed line number of `ticket_id`'s YAML `state:` field in
    `root/tickets.md` -- deliberately BELOW the marker line, for building a
    `Hunk` span that targets the state-transition line without ever
    overlapping the marker line itself (T-0564 regression coverage)."""
    marker = f"<!-- ticket:{ticket_id} -->"
    lines = (root / "tickets.md").read_text(encoding="utf-8").splitlines()
    in_block = False
    for i, line in enumerate(lines, start=1):
        if marker in line:
            in_block = True
            continue
        if in_block and line.startswith("state:"):
            return i
    raise AssertionError(f"state: line for {ticket_id} not found in tickets.md")


# frob:ticket T-0415
def _module_level_process_violation(root: Path, tag: str) -> tuple[Violation, ...]:
    """Picklable process-pool test gate (T-0415): a module-level function
    (required -- `ProcessPoolExecutor` cannot pickle a local closure) that
    returns one `Violation` whose message embeds the worker's own pid, so a
    test can prove the job actually executed in a separate process rather
    than merely running serially in-process."""
    import os

    return (
        Violation(
            rule="TESTPROC",
            severity=Severity.WARN,
            file=str(root),
            line=1,
            message=f"{tag}:{os.getpid()}",
        ),
    )


def _ticket(
    *,
    ticket_id: str = "T-0001",
    state: TicketState = TicketState.QUEUED,
    scope: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    attachments: tuple = (),
    body: str = "## Description\nx\n\n## Done report\ndone\n",
    kind: TicketKind = TicketKind.FEATURE,
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="Sample",
        state=state,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=scope,
        evidence=evidence,
        attachments=attachments,
        body=body,
    )


def _write_ticket(root: Path, ticket: Ticket) -> None:
    """Write `ticket` into `root`'s v1 monofile ledger.

    Seeds `tickets.md` first so `write_ticket` resolves to 'single' mode:
    T-1553 made a bare `tmp_path` default to v2, but this file's ledger
    assertions (`_marker_line`, COV002's closing-diff grace) are about
    `tickets.md` hunks specifically -- COV002's grace reads the ledger
    monofile diff and has no v2 equivalent yet (T-1582)."""
    ledger = root / "tickets.md"
    if not ledger.exists():
        ledger.write_text("# Tickets\n", encoding="utf-8")
    write_ticket(root, ticket).danger_ok


# frob:ticket T-1582
def _write_ticket_v2(root: Path, ticket: Ticket) -> None:
    """`_write_ticket`'s v2-mode twin: writes straight through `write_ticket`
    on a bare `tmp_path` (T-1553 default v2, no `tickets.md` seed) so the
    write resolves to `tickets/<id>/ticket.md` -- the COV002 v2-grace tests
    build their `Hunk`s against that path directly instead of a marker-line
    offset into a shared monofile."""
    write_ticket(root, ticket).danger_ok


def _v2_ticket_file_hunk(ticket_id: str) -> Hunk:
    """The `Hunk` a v2-mode diff carries for `ticket_id`'s own
    `tickets/<id>/ticket.md` -- one ticket owns the WHOLE file, so unlike
    v1's marker/state-line offsets there is no span to compute; any hunk
    on this path means this ticket's file was touched."""
    return Hunk(file=f"tickets/{ticket_id}/ticket.md", span=(1, 1))


# frob:waive DEAD001 reason="loaded dynamically via importlib.import_module by \
# doc012_gate's shared _load_parser_factory (dotted-path config value), never a direct \
# call-graph caller"
_DOC012_FAKE_CONFIG = (
    '[[docblocks.commands]]\nprog = "acme"\n'
    'parser = "tests.conftest:_doc012_fake_parser_factory"\n'
)


def _doc012_fake_parser_factory():
    """A tiny synthetic `argparse.ArgumentParser` with two top-level
    subcommands (`widget`, `gadget`) -- importable via
    `tests.conftest:_doc012_fake_parser_factory` (`tests/` is a real
    package), kept independent of frob's own live command count for the
    same reason `tests/test_docblocks_gate.py::_fake_parser_factory`
    (DOC005's own fixture) is."""
    import argparse

    parser = argparse.ArgumentParser(prog="acme")
    sub = parser.add_subparsers(dest="subcommand")
    sub.add_parser("widget", help="widget things")
    sub.add_parser("gadget", help="gadget things")
    return parser


def _complex_function_source(fn_name: str) -> str:
    """A python module with one function long enough to trip the 30-line
    default `max_function_lines` but short enough to stay under the
    calibrated 60-line threshold (T-0373), and structurally complex enough
    (>=8 branches) to pass `_py_is_complex`'s cyclomatic-proxy filter."""
    lines = [f"def {fn_name}(cfg):", "    result = {}"]
    for i in range(8):
        lines.append(f'    if cfg.get("flag_{i}"):')
        lines.append(f'        result["k{i}"] = {i}')
    for i in range(20):
        lines.append(f'    step_{i} = cfg.get("step_{i}", "default")')
    lines.append("    return result, " + ", ".join(f"step_{i}" for i in range(20)))
    return "\n".join(lines) + "\n"


def _make_fake_frob_repo_root(dest: Path) -> Path:
    """Build a `dest` directory that `_is_frob_repo_root` (T-0253) recognizes
    as frob's own checkout: `pyproject.toml` declaring `name = "frob"`, plus
    the `frob-core`/`strata-core` marker directories, plus a copy of the
    real `src/frob` tree underneath. `is_self_pattern_path`'s scan-target
    discriminator checks the exact directory passed as the scan root (no
    upward ancestor search -- see that function's docstring for why:
    ascending from a dependency located under frob's own `.venv` during
    frob vetting its OWN dependencies would otherwise wrongly classify that
    dependency's tree as "self" too), so tests exercising the discriminator
    must pass THIS directory itself as the scan root, not a subdirectory of
    it."""
    dest.mkdir(parents=True)
    repo_root = Path(__file__).resolve().parents[1]
    (dest / "pyproject.toml").write_text('[project]\nname = "frob"\n')
    (dest / "frob-core").mkdir()
    (dest / "strata-core").mkdir()
    shutil.copytree(
        repo_root / "src" / "frob",
        dest / "src" / "frob",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    return dest


def _ts_find(node, node_type: str):  # noqa: ANN001, ANN201
    """First descendant of `node` (inclusive) with `.type == node_type`, or
    `None` -- a small DFS helper `TestCapabilityScanTsAliasTablePredicates`
    uses to pluck a specific tree-sitter node out of a parsed fixture for a
    white-box call into a private resolver function."""
    if node.type == node_type:
        return node
    for child in node.children:
        found = _ts_find(child, node_type)
        if found is not None:
            return found
    return None


def _ts_find_all(node, node_type: str, out: list) -> None:  # noqa: ANN001
    """Every descendant of `node` (inclusive) with `.type == node_type`,
    appended to `out` in document order -- `_ts_find`'s multi-match
    sibling."""
    if node.type == node_type:
        out.append(node)
    for child in node.children:
        _ts_find_all(child, node_type, out)


# ---------------------------------------------------------------------------
# lockfile fixtures shared across tests.vet_suite families (T-3593 split:
# used by both lockfile-parser tests and scan-tree tests, so they live here
# rather than in any single per-family module).
# ---------------------------------------------------------------------------

UV_LOCK = """\
version = 1
requires-python = ">=3.11"

[[package]]
name = "requests"
version = "2.31.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "idna"
version = "3.6"
source = { registry = "https://pypi.org/simple" }
"""

PACKAGE_LOCK_JSON_V3 = json.dumps(
    {
        "name": "app",
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "app", "version": "1.0.0"},
            "node_modules/lodash": {"version": "4.17.21"},
            "node_modules/chalk": {"version": "5.3.0"},
        },
    }
)

PACKAGE_LOCK_JSON_V1 = json.dumps(
    {
        "name": "app",
        "lockfileVersion": 1,
        "dependencies": {
            "express": {"version": "4.18.2"},
        },
    }
)

PNPM_LOCK_YAML = """\
lockfileVersion: '6.0'

packages:
  /lodash@4.17.21:
    resolution: {integrity: sha512-xyz}
  /chalk@5.3.0:
    resolution: {integrity: sha512-abc}
"""

CARGO_LOCK = """\
version = 3

[[package]]
name = "serde"
version = "1.0.195"

[[package]]
name = "tokio"
version = "1.35.1"
"""


def _init_git_repo(root: Path) -> None:
    """A minimal real git repo for T-2009's `_land_ids_between`/`_resolve_
    actual_head` tests -- these shell out to real `git log`/`rev-parse`,
    unlike most of this module's tests which use a plain `tmp_path`."""
    import subprocess

    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)


def _git_commit(root: Path, message: str) -> str:
    """One empty, real commit with `message`; returns its full sha."""
    import subprocess

    subprocess.run(
        ["git", "-C", str(root), "commit", "--allow-empty", "-q", "-m", message],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git(repo: Path, *args: str) -> str:
    """Run git in `repo` and return stdout (test helper, T-1698)."""
    import subprocess

    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _seed_ticket(tmp_path: Path, *, state=None) -> str:
    """A minimal ticket for T-1690's attribution-filing tests. `state`
    (a `TicketState`), when given, transitions the ticket there -- `DONE`
    is reached the cheap way (via `drop_ticket`, landing on `DROPPED`,
    which is in `_ticket_is_open`'s CLOSED set alongside `DONE`) rather
    than satisfying `done`'s own evidence/Done-report requirements, which
    this test has no need to exercise."""
    from frob.tickets import Origin, TicketKind, new_ticket
    from frob.tickets._models import TicketSpec, TicketState

    spec = TicketSpec(title="seed", kind=TicketKind.BUG, origin=Origin.AGENT)
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    ticket_id = created.danger_ok.id
    if state is TicketState.DONE:
        from frob.tickets import drop_ticket

        dropped = drop_ticket(tmp_path, ticket_id, reason="seed")
        assert dropped.is_ok
    return ticket_id


def _seed_repo(tmp_path: Path) -> Path:
    """A real one-commit git repo -- `_commit_rapid_debt`'s whole contract
    is about git state, so a fake would prove nothing. A plain helper
    called explicitly, not a pytest fixture: fixture wiring is by NAME
    INJECTION, which WIRE001's reachability scan cannot see. Relocated
    to tests/conftest.py for T-3595's rapid_sweep_suite split -- callers
    now span multiple modules under tests/unit/rapid_sweep_suite/, which
    T-1558's gate fix recognizes as wired."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    # T-2997: record_rapid_debt now writes under .frob/, exactly like a
    # real checkout -- gitignore it here too, or an untracked .frob/
    # falsely reads as repo dirt in this fixture's "leaves the repo
    # clean" assertions, a gap no real checkout (which always gitignores
    # .frob/) actually has.
    (tmp_path / ".gitignore").write_text(".frob/\n", encoding="utf-8")
    _git(tmp_path, "add", "seed.txt", ".gitignore")
    _git(tmp_path, "commit", "-qm", "seed")
    return tmp_path
