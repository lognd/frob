import os
from pathlib import Path
from typing import Any, Iterator

import pytest

import frob.lang as lang_mod
from frob.lang import PARSE_ARTIFACT_CACHE_ENV, reset_parse_cache
from frob.mutate import restore_stale_journals
from frob.testing._stackdump import STACKDUMP_ENV as _STACKDUMP_ENV  # noqa: F401
from frob.testing._stackdump import (
    install_stackdump_handler as _install_stackdump_handler,
)
from frob.tickets._worktree_guard import (
    FROB_AGENT_ENV,
    FROB_WORKTREE_ENV,
    PYTEST_XDIST_AUTO_NUM_WORKERS_ENV,
)

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
    _last_internal_error = None
    _install_stackdump_handler()
    _worker_crash_hook_config = config
    if hasattr(config, "workerinput"):
        return
    _worker_crash_entries.clear()
    _worker_crash_causes.clear()
    _worker_crash_rerun_counts.clear()
    _harden_dsession_active_nodes()
    restore_stale_journals(_REPO_ROOT)


_SUITE_RESULT_MAX_NODE_IDS = 50
"""T-1673: cap on how many failing node ids `pytest_sessionfinish` lists by
name before collapsing the remainder into an 'and N more' tail -- keeps the
always-visible summary bounded even on a suite with hundreds of failures."""


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
            shown = failing_ids[:_SUITE_RESULT_MAX_NODE_IDS]
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


# frob:ticket T-3495
class FrobSelfScanArtifacts:
    """Result of ONE `build_graph(_REPO_ROOT, ...)` + `sys_gate(...)` pass
    (T-3495) -- a plain in-process result carrier for test fixtures, not
    a pydantic model crossing any real boundary (it holds a `Result`
    object and a `Violation` tuple, never serialized). `.repo_root`/
    `.violations` are what every consuming test actually reads;
    `.build_result` is kept for a future consumer that needs the raw
    `GraphSnapshot`."""

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
    """
    from frob.gates import sys_gate
    from frob.graph import build_graph

    cache_dir = tmp_path_factory.mktemp("frob_self_scan")
    build_result = build_graph(_REPO_ROOT, cache_dir / "cache.db")
    assert build_result.is_ok, f"graph build failed: {build_result.err}"
    violations = sys_gate(_REPO_ROOT, build_result.danger_ok)
    return FrobSelfScanArtifacts(
        repo_root=_REPO_ROOT, build_result=build_result, violations=violations
    )


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
