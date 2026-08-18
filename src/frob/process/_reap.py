"""SIGTERM-safe reaping of leaked `multiprocessing` children (T-2443,
docs/modules/process.md#forkserver-reaping-t-2443).

MEASURED DEFECT this closes: `frob check`'s gate-running `ProcessPoolExecutor`
(`frob.gates._open_process_pool`, `forkserver` start method) tears itself down
correctly on every NORMAL return/exception path -- `frob.gates._run_combined_
jobs` already wraps it in `try/finally: ppool.shutdown(wait=True)`. What that
`finally` block can never cover is the process being killed outright: this
fleet routinely wraps `frob check` in `timeout 540 ...`, and Python's DEFAULT
SIGTERM disposition terminates the interpreter immediately, with no exception
raised and no `finally` block run. The worker processes `ProcessPoolExecutor`
spawned survive that termination (nothing ever signals them), and because
each worker holds its own duplicate of the forkserver helper's "alive" pipe
write-end (`multiprocessing.forkserver.ForkServer.connect_to_new_process`
explicitly hands `self._forkserver_alive_fd` to every child it creates, so
the helper's own EOF-triggered shutdown only fires once EVERY holder of that
fd -- the parent AND every worker it ever spawned -- has exited), an orphaned
worker keeps the forkserver helper alive too. Live-fleet measurement (T-2443's
own ticket body): 94 forkserver processes reparented to `/init`, 100% with no
live ancestor, holding 17.3GB of swap, accumulated purely from repeated
`timeout`-killed `frob check` runs.

The fix has two parts, matching the ticket's two must-pass controls:

1. `install_sigterm_reaper` (called once, at CLI startup) installs a SIGTERM
   handler that reaps every `multiprocessing.active_children()` this
   interpreter still tracks -- which covers a `ProcessPoolExecutor`'s workers
   regardless of which module constructed the pool (`concurrent.futures.
   process` registers every worker `Process` the same way
   `multiprocessing.Process.start()` always does) -- BEFORE the process
   exits. Reaping the workers closes their `alive` pipe duplicates; the
   handler then lets the process exit normally, closing the parent's own
   duplicate too, so the forkserver helper observes EOF and self-terminates
   exactly as it would on an unkilled, normal exit. This deliberately does
   NOT touch `frob.gates`' pool construction/shutdown at all (T-2430 held a
   live cross-worktree lease on that file for the duration of this ticket,
   and the fix does not need it): `active_children()` is process-wide stdlib
   state, not something the pool owner has to register anywhere.
2. `reap_orphaned_forkservers` (best-effort, called once at `frob check`
   startup) is the DEFENSIVE half: a process-table sweep for forkserver
   helpers already reparented to init (no live ancestor, i.e. exactly the
   pattern the live-fleet measurement found) and older than a threshold,
   terminated proactively. This does not depend on (1) -- it exists because
   the leak was invisible to any operator until the machine actually started
   swapping, and a machine that already has leaked forkservers from BEFORE
   this fix shipped needs something that cleans them up going forward too.

Neither function touches `ProcessPoolExecutor` construction, sizing, or the
`forkserver`/`spawn` start-method choice -- the must-still-pass control
(gates keep running in parallel with identical findings) holds by
construction: nothing here changes how or how many workers a healthy run
starts, only what happens to them if the run is killed.
"""

from __future__ import annotations

import multiprocessing
import os
import re
import signal
import sys
import time
import typing
from pathlib import Path
from types import FrameType
from typing import Callable

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:ticket T-2443
#: How long to wait for a lingering `multiprocessing` child to exit
#: gracefully after `terminate()` before escalating to `kill()` -- mirrors
#: `frob.serve._socketd._CHILD_REAP_GRACE_S`'s own value/reasoning exactly
#: (short and bounded so reaping never itself becomes the thing that stalls
#: a signal-driven exit).
_CHILD_REAP_GRACE_S = 1.0

# frob:ticket T-2443
#: Module-level guard so `install_sigterm_reaper` is idempotent -- `frob`'s
#: CLI entry point may construct/call it more than once in one interpreter
#: (tests build a fresh parser/dispatch per case), and `signal.signal` is a
#: global process-wide registration: installing twice would just mean the
#: second call's handler silently replaces the first with an identical one,
#: which is harmless but worth avoiding the redundant work for.
_sigterm_reaper_installed = False

# frob:ticket T-2443
#: A signal handler's own shape (`signal.signal`'s return type) -- either a
#: real callable, or one of the two sentinel ints/`signal.Handlers` members
#: (`SIG_DFL`/`SIG_IGN`) `signal.signal` can hand back when no Python-level
#: callable was previously installed.
_SignalHandler = (
    Callable[[int, FrameType | None], object] | int | signal.Handlers | None
)

# frob:ticket T-2443
#: The previous SIGTERM handler, captured by `install_sigterm_reaper` so the
#: reaper can chain to it (or the platform default) after reaping -- never
#: silently swallows whatever behavior was registered before this module
#: ran (e.g. a test harness's own SIGTERM handling).
_prior_sigterm_handler: _SignalHandler = None


# frob:doc docs/modules/process.md#forkserver-reaping-t-2443
# frob:ticket T-2443
# frob:tests tests/unit/test_process_reap.py::TestReapActiveChildren.test_terminates_and_joins_active_children  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapActiveChildren.test_escalates_to_kill_if_terminate_does_not_stick  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapActiveChildren.test_no_children_is_a_silent_noop  # noqa: E501
def reap_active_multiprocessing_children(
    grace_s: float = _CHILD_REAP_GRACE_S,
) -> list[int]:
    """Terminate (then, if needed, kill) every `multiprocessing.active_
    children()` process this interpreter still tracks, returning the pids
    reaped. Generalizes `frob.serve._socketd._reap_multiprocessing_children`
    (T-1378's own daemon-shutdown precedent) into a shared primitive both
    that caller and `install_sigterm_reaper` below use, rather than each
    reimplementing the same terminate-then-escalate loop (NO DUPLICATION).
    A no-op (returns `[]`) when nothing is tracked -- never raises."""
    children = multiprocessing.active_children()
    if not children:
        return []
    pids = [c.pid for c in children if c.pid is not None]
    _log.warning(
        "process: reaping %d lingering multiprocessing child(ren): %s",
        len(children),
        pids,
    )
    for child in children:
        child.terminate()
    for child in children:
        child.join(timeout=grace_s)
        if child.is_alive():
            _log.warning(
                "process: child pid=%s survived terminate(), killing", child.pid
            )
            child.kill()
            child.join(timeout=grace_s)
    return pids


# frob:ticket T-2443
# frob:waive WIRE001 follow_up="T-2451" reason="genuinely wired -- passed as the \
# handler argument to signal.signal(sigterm, _sigterm_handler) in install_sigterm_ \
# reaper immediately below, then invoked by the interpreter's own signal dispatch \
# machinery on a real SIGTERM, never called directly by name from Python code -- the \
# same class of gap as this repo's other WIRE001 waivers for a callback stored as a \
# value/passed as a constructor kwarg rather than called directly \
# (frob.app.ticket_runner._land_cmd's _FILE_LOCAL_ERROR_CHECKERS precedent); the \
# callgraph cannot trace a name passed into a stdlib registration call as a caller"
def _sigterm_handler(signum: int, frame: FrameType | None) -> None:
    """The SIGTERM handler `install_sigterm_reaper` registers: reap every
    live `multiprocessing` child (closing its duplicate of the forkserver
    helper's `alive` pipe write-end -- see this module's docstring for why
    that is what lets the helper self-terminate), then chain to whatever
    handler was previously installed (a prior `signal.signal(SIGTERM, ...)`
    call, if any) or the platform default otherwise -- this function never
    itself decides how the process should die, only what must happen FIRST,
    so callers observe the same exit code/behavior they would have without
    this module installed, just with the leak closed."""
    _log.warning("process: SIGTERM received -- reaping multiprocessing children")
    reap_active_multiprocessing_children()
    global _prior_sigterm_handler
    handler = _prior_sigterm_handler
    if handler not in (None, signal.SIG_DFL, signal.SIG_IGN):
        # `handler` is `_SignalHandler` (Callable[[int, FrameType | None],
        # object] | int | signal.Handlers | None); the two sentinel members
        # and None are excluded above, so every value reachable here IS the
        # callable branch -- the type checker cannot narrow a Union-of-a-
        # Callable-and-sentinel-ints through an equality exclusion the way
        # it can narrow via isinstance, so this is cast rather than proven,
        # matching how signal.signal's own typeshed stub treats this exact
        # union.
        typing.cast("Callable[[int, FrameType | None], object]", handler)(signum, frame)
        return
    # frob:waive EXHAUST002 reason="restoring the DEFAULT disposition and re-raising \
    # is the only way to terminate a process from inside a signal handler that mirrors \
    # the pre-existing (un-installed) SIGTERM behavior exactly -- signal.signal itself \
    # cannot raise here (SIGTERM is always a valid, settable signal), and \
    # os.kill/getpid cannot raise for a signal this process is permitted to send to \
    # itself"
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    os.kill(os.getpid(), signal.SIGTERM)


# frob:doc docs/modules/process.md#forkserver-reaping-t-2443
# frob:ticket T-2443
# frob:tests tests/unit/test_process_reap.py::TestInstallSigtermReaper.test_installs_handler_once  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestInstallSigtermReaper.test_second_call_is_a_noop  # noqa: E501
def install_sigterm_reaper() -> None:
    """Install `_sigterm_handler` as this process's SIGTERM handler
    (idempotent -- a second call is a no-op, `_sigterm_reaper_installed`).
    Meant to be called once, early, from `frob`'s CLI entry point
    (`frob.__main__.main`) -- see this module's own docstring for the
    exact leak this closes and why a process-wide, pool-construction-
    agnostic handler is the right shape for it. Only installs on platforms
    where `signal.SIGTERM` exists and this is the main thread (`signal.
    signal` raises `ValueError` from any other thread) -- both are true for
    every real CLI invocation; a caller from a non-main thread (some test
    harnesses) is silently skipped rather than crashing the import."""
    global _sigterm_reaper_installed, _prior_sigterm_handler
    if _sigterm_reaper_installed:
        return
    sigterm = getattr(signal, "SIGTERM", None)
    if sigterm is None:
        return
    try:
        _prior_sigterm_handler = signal.signal(sigterm, _sigterm_handler)
    except ValueError:
        # Not the main thread -- signal.signal cannot install here. Skip
        # quietly rather than raise: a CLI entry point is always the main
        # thread in practice, this only guards a test-harness edge case.
        _log.debug("process: install_sigterm_reaper: not the main thread, skipping")
        return
    _sigterm_reaper_installed = True


# frob:ticket T-2443
#: `cmdline` substring identifying a `multiprocessing.forkserver` helper
#: process (the exact command `multiprocessing.forkserver.ForkServer.
#: ensure_running` execs, stdlib-verified: `'from multiprocessing.forkserver
#: import main; main(...)'` passed via `-c`). Matching this text is the
#: portable way to identify the helper -- it does not depend on this
#: repo's own layout or package name (T-2384 portability doctrine), only on
#: CPython's own stdlib module path, which is the same on every host this
#: runs on.
_FORKSERVER_CMDLINE_RE = re.compile(r"multiprocessing\.forkserver")

# frob:doc docs/modules/process.md#forkserver-reaping-t-2443
# frob:ticket T-2443
#: Default minimum age (seconds) before `reap_orphaned_forkservers` will
#: touch a reparented-to-init forkserver -- deliberately generous (well
#: past any single `frob check` invocation's own wall time) so this never
#: races a forkserver helper that is still legitimately in use by a
#: currently-running, not-yet-orphaned `frob check`.
DEFAULT_ORPHAN_AGE_FLOOR_S = 300.0


# frob:ticket T-2443
def _process_start_age_s(pid: int, proc: Path, now_s: float) -> float | None:
    """Best-effort age (seconds) of `pid`, approximated from `<proc>/<pid>`'s
    own mtime (the directory is created at process start and never touched
    again) -- `None` if unreadable (already exited, permission denied, or a
    non-Linux `/proc`). A heuristic, not exact accounting: precise enough to
    apply `DEFAULT_ORPHAN_AGE_FLOOR_S`'s multi-minute floor, which is all
    this reaper needs."""
    try:
        return max(now_s - (proc / str(pid)).stat().st_mtime, 0.0)
    except OSError:
        return None


# frob:ticket T-2443
def _is_orphaned_forkserver(pid: int, proc: Path) -> bool:
    """`True` when `<proc>/<pid>/cmdline` matches `_FORKSERVER_CMDLINE_RE`
    AND `<proc>/<pid>/stat`'s own ppid field is `1` (reparented to init --
    the exact signature the live-fleet measurement used: 100% of the 94
    leaked forkservers had no live ancestor, i.e. their creating process
    was dead and init had adopted them). Any read failure (already exited,
    permission denied, malformed `/proc` entry) reads as `False` -- never
    guesses an orphan from partial data."""
    try:
        cmdline = (proc / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ")
    except OSError:
        return False
    if not _FORKSERVER_CMDLINE_RE.search(cmdline.decode("utf-8", errors="replace")):
        return False
    try:
        stat_text = (proc / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError:
        return False
    # stat's 2nd field (comm) is parenthesized and may itself contain
    # spaces/parens, so the state/ppid fields that follow it must be
    # located by the LAST ')' rather than a naive split -- this mirrors
    # the standard /proc/<pid>/stat parsing idiom (matches man proc's own
    # documented caveat).
    close_paren = stat_text.rfind(")")
    if close_paren == -1:
        return False
    # Fields after ")": [state, ppid, pgrp, ...] -- state (field 3 overall)
    # is fields[0] here, ppid (field 4 overall) is fields[1].
    fields = stat_text[close_paren + 2 :].split()
    if len(fields) < 2:
        return False
    try:
        ppid = int(fields[1])
    except ValueError:
        return False
    return ppid == 1


# frob:doc docs/modules/process.md#forkserver-reaping-t-2443
# frob:ticket T-2443
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_terminates_old_orphaned_forkservers  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_leaves_young_orphaned_forkservers_alone  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_leaves_non_forkserver_processes_alone  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_missing_proc_returns_empty  # noqa: E501
def reap_orphaned_forkservers(
    age_floor_s: float = DEFAULT_ORPHAN_AGE_FLOOR_S,
    proc: Path = Path("/proc"),
) -> list[int]:
    """Startup-reaper half of T-2443's fix (this module's own docstring,
    part 2): SIGTERM every `multiprocessing.forkserver` helper under `proc`
    that is (a) reparented to init (`_is_orphaned_forkserver`) and (b) at
    least `age_floor_s` old (`_process_start_age_s`) -- best-effort and
    defensive, meant to be called once at `frob check` startup so a
    machine that already accumulated leaked forkservers (from before
    `install_sigterm_reaper` shipped, or from a run that died some other
    way this fix does not cover) keeps getting cleaned up going forward.
    Returns the pids signaled. Never raises: an unreadable `/proc` (non-
    Linux host, sandboxed container) or a pid that exits mid-scan both
    degrade to "nothing found here", matching every other best-effort
    `/proc`-scanning helper in this codebase (`scripts/fleet_status.py`'s
    own `_scan_for_live_worktree_process` precedent)."""
    if sys.platform == "win32" or not proc.is_dir():
        # Windows has no `/proc` and no `forkserver` start method
        # (`multiprocessing.get_all_start_methods()` never includes it
        # there) -- a structural no-op, not a degraded scan, matching
        # `frob.gates._process_pool_start_method`'s own `spawn`-fallback
        # posture for exactly this platform.
        return []
    now_s = time.time()
    reaped: list[int] = []
    try:
        entries = list(proc.iterdir())
    except OSError:
        return []
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if not _is_orphaned_forkserver(pid, proc):
            continue
        age_s = _process_start_age_s(pid, proc, now_s)
        if age_s is None or age_s < age_floor_s:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as exc:
            _log.debug(
                "process: reap_orphaned_forkservers: could not signal pid=%d: %s",
                pid,
                exc,
            )
            continue
        _log.warning(
            "process: reap_orphaned_forkservers: SIGTERM'd orphaned "
            "forkserver pid=%d (age=%.0fs, reparented to init)",
            pid,
            age_s,
        )
        reaped.append(pid)
    return reaped


# frob:doc docs/modules/process.md#concurrent-check-advisory-t-2473
# frob:ticket T-2473
#: `cmdline` shape identifying a live `frob check` invocation -- matches
#: the two argv tokens `frob`/`check` appearing as SEPARATE tokens (never
#: a substring match, which would also fire on `frob ticket check-repro`
#: or a path containing the word "check"). `frob`/`check` are matched
#: independently rather than as one fixed substring because the CLI entry
#: point varies by invocation shape (`frob check ...`, `uv run frob check
#: ...`, `.venv/bin/frob check ...`) but the token pair is constant across
#: all of them. Compiled against RAW cmdline bytes (NUL-separated argv,
#: kept as-is rather than replaced with spaces) so token-boundary matching
#: is exact.
_FROB_TOKEN_RE = re.compile(rb"(?:^|/)frob\x00")
_CHECK_TOKEN_RE = re.compile(rb"\x00check\x00|\x00check$")


# frob:ticket T-2473
def _is_frob_check_process(pid: int, proc: Path, self_pid: int) -> bool:
    """`True` when `<proc>/<pid>/cmdline` names a live `frob check`
    invocation, excluding `self_pid` (a process never counts itself as
    "another" concurrent check, T-2473's own must-not-stall acceptance:
    a single check on an idle machine must read 0 others running, not
    1). Any read failure (already exited, permission denied) reads as
    `False` -- never guesses from partial data, matching `_is_orphaned_
    forkserver`'s own posture."""
    if pid == self_pid:
        return False
    try:
        raw = (proc / str(pid) / "cmdline").read_bytes()
    except OSError:
        return False
    if not raw.endswith(b"\x00"):
        raw += b"\x00"
    return bool(_FROB_TOKEN_RE.search(raw)) and bool(_CHECK_TOKEN_RE.search(raw))


# frob:doc docs/modules/process.md#concurrent-check-advisory-t-2473
# frob:ticket T-2473
# frob:tests tests/unit/test_process_reap.py::TestCountRunningChecks.test_counts_other_check_processes  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestCountRunningChecks.test_excludes_self  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestCountRunningChecks.test_ignores_non_check_processes  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestCountRunningChecks.test_missing_proc_returns_none  # noqa: E501
def count_running_checks(
    proc: Path = Path("/proc"), self_pid: int | None = None
) -> int | None:
    """How many OTHER live `frob check` processes are running on this host
    right now (T-2473) -- read-only, no lock, no enforcement: this is the
    ADVISORY half of T-2473's fix (the coordinator's chosen direction over
    an enforced concurrency limit, which risks turning a busy fleet into a
    queue of stalled agents if the limit is chosen badly). Counts, never
    blocks or defers anything itself -- a caller (`frob check`'s own
    startup log line, `scripts/fleet_status.py`'s LAND status block) is
    free to act on the number, but this function's own contract is
    read-and-report only, so it can never be the thing that adds latency
    or a new failure mode to a single check on an idle machine (T-2473's
    own must-not-stall acceptance).

    `self_pid` defaults to `os.getpid()` -- overridable for tests.
    Returns `None` (unknown, never "0 others running") if `/proc` is
    missing/unreadable, mirroring `orphaned_forkserver_count`'s own
    best-effort-degrades-to-None contract exactly."""
    if sys.platform == "win32" or not proc.is_dir():
        return None
    if self_pid is None:
        self_pid = os.getpid()
    try:
        entries = list(proc.iterdir())
    except OSError:
        return None
    count = 0
    for entry in entries:
        if not entry.name.isdigit():
            continue
        if _is_frob_check_process(int(entry.name), proc, self_pid):
            count += 1
    return count
