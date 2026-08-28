"""SIGTERM-safe reaping of leaked `multiprocessing` children (T-2443,
docs/modules/process.md#forkserver-reaping-t-2443), plus (T-2849) the
`PR_SET_PDEATHSIG`-based root-cause fix that stops the leak from happening
at all on the dominant SIGKILL path -- see `arm_parent_death_signal` and
`_arm_forkserver_helper_pdeathsig_if_requested` below for that half.

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

import ctypes
import multiprocessing
import os
import re
import signal
import sys
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


# frob:ticket T-2849
#: `linux/prctl.h`'s `PR_SET_PDEATHSIG` option number -- stable ABI, not
#: exposed by the stdlib `os`/`signal` modules, so it is called directly
#: via `ctypes` against libc's `prctl(2)` (the same approach every other
#: language's "die with parent" helper uses; there is no portable stdlib
#: wrapper for this option).
_PR_SET_PDEATHSIG = 1

# frob:doc docs/modules/process.md#forkserver-reaping-t-2443
# frob:ticket T-2849
#: Env var `_open_process_pool` (`frob.gates`) stamps to `"1"` in the
#: PARENT process's environment, BEFORE constructing its `multiprocessing.
#: forkserver` pool, so the freshly-exec'd forkserver HELPER process (which
#: inherits the parent's environment at exec time, same mechanism
#: `_WORKER_STDOUT_LOG_LEVEL_ENV`/`_INHERITED_LOCK_KEYS_ENV` already rely
#: on) can tell it is running as that helper and should arm itself -- see
#: `_arm_forkserver_helper_pdeathsig_if_requested`. A normal `frob` CLI
#: invocation (or test import of this module) never sets this, so the
#: check below is a no-op there.
FORKSERVER_ARM_PDEATHSIG_ENV = "FROB_FORKSERVER_ARM_PDEATHSIG"


# frob:doc docs/modules/process.md#forkserver-reaping-t-2443
# frob:ticket T-2849
# frob:ticket T-2944
# frob:tests tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_arms_successfully_on_linux  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_self_kills_on_missed_reparent_race  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_returns_false_off_linux  # noqa: E501
def arm_parent_death_signal(sig: int | None = None) -> bool:
    """T-2936: `sig` defaults to `None`, resolved to `signal.SIGKILL`
    ONLY after the `sys.platform != "linux"` check below passes -- a
    default argument is evaluated once, at MODULE LOAD, when the `def`
    statement itself runs; `sig: int = signal.SIGKILL` crashed the
    IMPORT of this whole module on Windows (no `signal.SIGKILL` there
    at all) with an `AttributeError`, before a single line of this
    function's own body -- including its own platform guard -- ever ran.
    Every downstream import of `frob.process` (and everything that
    imports IT) failed with it; `frob --help` itself crashed. Measured
    for real via T-2917's windows-latest CI job (54s to failure, at
    `uv run frob natives build`'s own import of this module).

    Arm `PR_SET_PDEATHSIG(sig)` (T-2849) on the CALLING process via
    `ctypes`' libc `prctl(2)`: the kernel delivers `sig` to this process
    the instant its DIRECT OS parent terminates, by ANY means including
    `SIGKILL` -- this is what makes the mechanism uncatchable-parent-death
    -proof where a `finally`/`atexit` handler is not (T-2443's own
    documented gap: a `SIGTERM`-killed parent still runs Python cleanup,
    a `SIGKILL`-killed one never does). Returns `False` (never raises) on
    any non-Linux platform or a `prctl` call failure -- callers degrade to
    "not armed", the same best-effort posture every other `/proc`-reading
    helper in this module already has.

    Closes the race between "read my current parent" and "the arm call
    actually takes effect": if `os.getppid()` differs before vs.
    immediately after the `prctl` call, the original parent already
    exited in that window and the kernel may have had no live parent left
    to attribute the future signal to, so this self-delivers `sig`
    immediately rather than risk running on, unmonitored, exactly like
    the leak this closes.

    T-2880: that before/after comparison only detects a parent death that
    happens DURING this call -- it is blind to a parent that already died
    BEFORE this function was ever entered (the real gap: fork() returns
    in the child, then the real parent dies, then the child gets around
    to calling this function -- by the time `parent_before` is read, the
    kernel has already reparented the caller to init, so both reads agree
    and no diff is ever observed). On Linux, a process's live parent
    reparents to pid 1 (init) the instant it exits with no subreaper in
    the chain (this codebase installs none -- see `docs/modules/process.
    md#forkserver-reaping-t-2443`), and neither the forkserver helper's
    real parent (the `frob check` launcher) nor a worker's real parent
    (the helper) is ever legitimately pid 1 itself, so `getppid() == 1`
    at this point is unambiguous evidence of exactly that already-missed
    race, not a false positive on a normal parent. So: self-deliver `sig`
    whenever the CURRENT parent (whether just-changed or already-1 when
    first read) is pid 1, not only when the before/after reads disagree.
    This was the actual leak T-2849's own fix left open (measured live:
    T-2849's fix landed and orphans kept appearing at the pre-fix rate,
    T-2880's own failure log) -- an already-orphaned process this
    function is called on never had a chance to arm against a parent
    that could still die, and the old check could never see that because
    it only compared two reads of the SAME (already-wrong) answer.

    T-2849's own two use sites: (1) `frob.gates._open_process_pool`'s
    forkserver-helper preload hook below arms this on the HELPER, whose
    real OS parent is the `frob check` launcher (multiprocessing `exec`s
    the helper directly, confirmed via T-2849's own failure-log
    measurement); (2) the pool's worker initializer arms this on each
    WORKER, whose real OS parent is that same helper (workers are raw
    `fork()`ed from it, never `exec`ed). Chaining the two closes the full
    launcher-death propagation path across the intermediate helper this
    ticket's failure log identified as the trap in a naive one-hop fix:
    launcher dies -> helper (direct child) is signalled -> helper dies ->
    every worker (direct child of the HELPER, not the launcher) is
    signalled in turn."""
    if sys.platform != "linux":
        # T-2944: log HERE, in this guard's own body, not only at the
        # call site -- `_arm_forkserver_helper_pdeathsig_if_requested`
        # already warns on a `False` return, but PLATFORM001's static
        # scan cannot see across call sites, and a future caller with no
        # such lucky log would ship this exact silent-degrade shape
        # completely undetected.
        _log.warning(
            "process: arm_parent_death_signal: PR_SET_PDEATHSIG has no "
            "equivalent on %s -- forkserver orphan-reaping via parent-death "
            "signal is disabled on this platform (T-2944)",
            sys.platform,
        )
        return False
    if sig is None:
        sig = signal.SIGKILL
    try:
        libc = ctypes.CDLL(None, use_errno=True)
    except OSError:
        _log.debug("process: arm_parent_death_signal: could not load libc")
        return False
    parent_before = os.getppid()
    try:
        rc = libc.prctl(_PR_SET_PDEATHSIG, int(sig), 0, 0, 0)  # frob:callee-raises
    except (OSError, AttributeError) as exc:
        _log.debug("process: arm_parent_death_signal: prctl call failed: %s", exc)
        return False
    if rc != 0:
        _log.debug("process: arm_parent_death_signal: prctl returned rc=%d", rc)
        return False
    parent_after = os.getppid()
    if parent_after != parent_before:
        # The direct parent already exited/reparented between the getppid()
        # above and the prctl() call landing -- the kernel may have had no
        # parent left to deliver `sig` to when it dies, so self-deliver now
        # rather than risk running on as a fresh orphan.
        _log.warning(
            "process: arm_parent_death_signal: parent changed pid=%d during arm "
            "(was %d, now %d), self-signalling %d",
            os.getpid(),
            parent_before,
            parent_after,
            sig,
        )
        os.kill(os.getpid(), sig)
    elif parent_after == 1:
        # T-2880: already reparented to init BEFORE this function was even
        # entered (parent_before == parent_after == 1) -- the before/after
        # diff above can never catch this, since both reads already agree
        # on the wrong answer. Neither a forkserver helper's real parent
        # (the launcher) nor a worker's real parent (the helper) is ever
        # legitimately pid 1, so this is unambiguous: the real parent is
        # already gone and PR_SET_PDEATHSIG(sig) was just armed against a
        # parent (init) that will not die, i.e. it will never fire. Self-
        # deliver now instead of leaking as an unreapable orphan.
        _log.warning(
            "process: arm_parent_death_signal: pid=%d already reparented to "
            "init (parent-before-entry race) -- pdeathsig against init would "
            "never fire, self-signalling %d",
            os.getpid(),
            sig,
        )
        os.kill(os.getpid(), sig)
    return True


# frob:doc docs/modules/process.md#forkserver-reaping-t-2443
# frob:ticket T-2849
# frob:tests tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested.test_noop_without_env_var  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested.test_arms_when_env_var_set  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested.test_success_logs_nothing_at_all  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested.test_failure_still_warns  # noqa: E501
# frob:waive COV007 reason="docs/modules/process.md's Forkserver reaping (T-2443) \
# section documents several symbols under one section, not just a public entry point \
# -- the many-symbols-one-section convention this repo already accepted for vet.md \
# (T-2810 declined to touch it), not a T-2810-shaped duplicate"
def _arm_forkserver_helper_pdeathsig_if_requested() -> None:
    """Module-import-time hook (T-2849): `frob.gates._FORKSERVER_PRELOAD`
    names this module, so `multiprocessing.forkserver` imports it exactly
    ONCE inside the freshly-started forkserver HELPER process, before that
    helper forks any worker. When `FORKSERVER_ARM_PDEATHSIG_ENV` is set
    (stamped by `frob.gates._open_process_pool` into the environment the
    helper inherits at `exec` time -- see that env var's own docstring),
    arm `PR_SET_PDEATHSIG(SIGKILL)` on THIS process, i.e. the helper
    itself, via `arm_parent_death_signal`. The helper's real OS parent is
    the `frob check` launcher, not the launcher's own parent shell -- so
    this is the half of T-2849's fix that makes the helper die the instant
    the launcher does, by any means. A plain `import frob.process._reap`
    from the main CLI process or a test module never has the env var set,
    so this check is a no-op there; it only ever fires inside the
    forkserver helper subprocess.

    Deliberately silent on SUCCESS (matches `arm_parent_death_signal`'s
    own convention of returning `True` with no log call) -- this hook
    runs at HELPER PRELOAD time, before `frob.gates._run_process_gate`'s
    per-job `_WORKER_STDOUT_LOG_LEVEL_ENV` clamp (T-0806) has ever had a
    chance to run for this process, so a DEBUG-level log emitted here
    would reach `frob check --json`'s stdout unfiltered on every single
    run (this repo's own `[handlers.stdout]` default is `level = "DEBUG"`)
    -- reproduced directly while validating this ticket's own fix
    (`process: forkserver helper pid=... armed ...` leaking into a real
    `frob check --json` capture) before removing it. The failure branch
    stays a `_log.warning`, which is safe: `[handlers.stderr]` is the
    WARNING-and-above sink and `[handlers.stdout]`'s own `below_warning`
    filter explicitly excludes it, so a genuine arm failure still
    surfaces on stderr without contaminating JSON stdout."""
    # frob:waive SEC110 reason="boolean forkserver-arm marker, not a secret"
    if os.environ.get(FORKSERVER_ARM_PDEATHSIG_ENV) == "1":
        if not arm_parent_death_signal():
            _log.warning(
                "process: forkserver helper pid=%d could not arm "
                "PR_SET_PDEATHSIG -- launcher-death leak NOT closed for this run "
                "(non-Linux platform or prctl failure)",
                os.getpid(),
            )


_arm_forkserver_helper_pdeathsig_if_requested()


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


# frob:ticket T-3152
def _stat_fields_after_comm(stat_text: str) -> list[str] | None:
    """`/proc/<pid>/stat`'s own fields AFTER the `") "` that closes the
    `(comm)` field (a process name can itself contain spaces/parens, which
    is why every reader here splits on the LAST `")"` rather than counting
    space-separated tokens from the start) -- `fields[1]` is ppid,
    `fields[19]` is starttime (field 22 overall). Mirrors `scripts/
    fleet_status.py::_stat_fields_after_comm` exactly (T-3152: same field
    layout, same split idiom, deliberately NOT imported across the
    boundary -- that script carries its own standalone copy under its own
    "no `frob` import" contract, `_is_live_check_cmdline`'s own docstring
    covers the same posture for T-3072/T-3093). Returns `None` if
    `stat_text` has no `")"` at all (unparseable/truncated read)."""
    close_paren = stat_text.rfind(")")
    if close_paren == -1:
        return None
    return stat_text[close_paren + 2 :].split()


# frob:ticket T-3072
# frob:ticket T-3152
def _read_ppid_from_stat(pid: int, proc: Path) -> int | None:
    """`<proc>/<pid>/stat`'s own ppid field, or `None` on any read/parse
    failure (already exited, permission denied, malformed entry) -- T-3072
    split this out of `_is_orphaned_forkserver` (DUP001) so `_all_process_
    ppids`'s multi-hop ancestry substrate can reuse the exact same
    parsing, never a second copy of the "locate fields after the LAST
    `)`" idiom `man proc` documents. T-3152: now shares its field split
    with `_process_start_age_s` via `_stat_fields_after_comm`, rather than
    inlining its own copy of that split."""
    try:
        stat_text = (proc / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    fields = _stat_fields_after_comm(stat_text)
    # Fields after ")": [state, ppid, pgrp, ...] -- state (field 3 overall)
    # is fields[0] here, ppid (field 4 overall) is fields[1].
    if fields is None or len(fields) < 2:
        return None
    try:
        return int(fields[1])
    except ValueError:
        return None


# frob:ticket T-2443
# frob:ticket T-3152
def _process_start_age_s(
    pid: int, proc: Path, uptime_s: float | None, clk_tck: int
) -> float | None:
    """Age (seconds) of `pid`, derived from `/proc/<pid>/stat`'s own
    `starttime` field (clock ticks since boot -- `man proc`'s canonical,
    kernel-documented process-start timestamp, field 22 overall /
    `fields[19]` after `_stat_fields_after_comm`'s split) combined with
    `/proc/uptime` -- `None` if `uptime_s`/`clk_tck` are unavailable, the
    file is unreadable (already exited, permission denied, non-Linux
    `/proc`), or the field does not parse.

    T-3152: this used to derive age from the `<proc>/<pid>` DIRECTORY's
    own mtime instead (the directory is created at process start and,
    empirically, never touched again) -- a second, independent
    approximation of the same quantity `scripts/fleet_status.py::
    _forkserver_age_s` already computed via `stat`'s `starttime` field,
    the exact class of duplication T-3072/T-3093/T-3139 already found
    three other instances of in this file pair. `starttime` is the more
    precise and more clearly-specified of the two: it is the field every
    standard tool (`ps -o etimes`, `/proc/uptime`-relative age
    calculations) already treats as the process's start time, at
    `1/clk_tck` resolution (typically 10ms); an inode's mtime is a
    filesystem side effect of procfs entry creation, not a documented
    kernel contract for this purpose, and is not guaranteed identical to
    process start time in every kernel/container scenario even though
    the two agree in practice on a normal Linux host. Unified on
    `starttime` here (matching `_forkserver_age_s`'s own algorithm
    exactly, field-for-field) rather than the reverse, since `starttime`
    is the more precise source and `fleet_status.py`'s own "no `frob`
    import" contract means the two copies stay textually independent
    (see `_stat_fields_after_comm`'s own docstring) -- verified to agree
    on identical synthetic input by `tests/unit/test_process_reap.py::
    TestProcessStartAgeMatchesFleetStatus`."""
    if uptime_s is None or not clk_tck:
        return None
    try:
        stat_text = (proc / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    fields = _stat_fields_after_comm(stat_text)
    if fields is None or len(fields) < 20:
        return None
    try:
        starttime_ticks = int(fields[19])
    except ValueError:
        return None
    try:
        return uptime_s - (starttime_ticks / clk_tck)
    except ZeroDivisionError:
        return None


# frob:ticket T-2443
# frob:tests tests/unit/test_process_reap.py::TestIsOrphanedForkserver.test_matches_forkserver_reparented_to_init  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestIsOrphanedForkserver.test_forkserver_with_live_parent_is_not_orphaned  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestIsOrphanedForkserver.test_non_forkserver_process_is_never_matched  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestIsOrphanedForkserver.test_missing_entry_is_false_not_raised  # noqa: E501
def _is_orphaned_forkserver(pid: int, proc: Path) -> bool:
    """`True` when `<proc>/<pid>/cmdline` matches `_FORKSERVER_CMDLINE_RE`
    AND `<proc>/<pid>/stat`'s own ppid field is `1` (reparented to init --
    the exact signature the live-fleet measurement used: 100% of the 94
    leaked forkservers had no live ancestor, i.e. their creating process
    was dead and init had adopted them). Any read failure (already exited,
    permission denied, malformed `/proc` entry) reads as `False` -- never
    guesses an orphan from partial data.

    T-3072: this is the ONE-HOP check -- accurate for a forkserver whose
    own real parent died, but blind to a forkserver reparented to ANOTHER
    already-orphaned forkserver (that intermediate forkserver is itself
    alive, so a one-hop test on the pid below it reads "live parent" and
    misses the leak). `reap_orphaned_forkservers` below no longer calls
    this alone -- see `_forkserver_root_is_live_check` for the multi-hop
    walk that closes that gap. Kept as its own tested unit unchanged
    (still correct for the common single-hop case, and `_forkserver_
    cmdline_matches` reuses its cmdline half) rather than removed."""
    if not _forkserver_cmdline_matches(pid, proc):
        return False
    return _read_ppid_from_stat(pid, proc) == 1


# frob:ticket T-3072
def _forkserver_cmdline_matches(pid: int, proc: Path) -> bool:
    """`True` when `<proc>/<pid>/cmdline` matches `_FORKSERVER_CMDLINE_RE`
    -- the cmdline half of `_is_orphaned_forkserver`, split out (T-3072)
    so `_all_forkserver_pids` (the multi-hop reaper's own enumeration)
    does not re-implement the same read+match. Any read failure reads as
    `False`, matching `_is_orphaned_forkserver`'s own posture."""
    try:
        cmdline = (proc / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ")
    except OSError:
        return False
    return bool(
        _FORKSERVER_CMDLINE_RE.search(cmdline.decode("utf-8", errors="replace"))
    )


# frob:ticket T-3072
#: `frob check`'s own argv shape, as separate NUL-separated `/proc/<pid>/
#: cmdline` tokens: a live check process's cmdline always carries a token
#: that IS (not merely contains) the literal `frob` -- either the
#: executable's own basename (`.../bin/frob check ...`) or the module
#: name after `-m` (`python -m frob check ...`, this fleet's own dominant
#: invocation shape under `uv run`) -- plus a separate `check` token
#: somewhere after it. T-3072's own live-fleet evidence: `scripts/fleet_
#: status.py`'s equivalent classifier (`_FROB_CHECK_TOKEN_RE = re.compile
#: (rb"(?:^|/)frob\x00")`) does NOT match this shape -- `^` only anchors
#: the WHOLE cmdline blob's start, not each NUL-delimited token, so a
#: `frob` token that is neither the very first token nor preceded by a
#: literal `/` (exactly the `-m frob` case: the token before it is `-m`,
#: not a path) never matches, and two live `python -m frob check ...`
#: launchers were measured falsely reported ORPHANED as a direct result
#: (T-3072's Done report; T-3093 fixes that regex in `scripts/fleet_
#: status.py` itself). This module's own classifier below compares whole
#: TOKENS after splitting on `\x00`, never a regex over the raw joined
#: bytes, so it has no equivalent anchor bug by construction.
_LIVE_CHECK_EXE_TOKEN = b"frob"
_LIVE_CHECK_SUBCOMMAND_TOKEN = b"check"


# frob:ticket T-3072
def _is_live_check_process(pid: int, proc: Path) -> bool:
    """`True` when `<proc>/<pid>/cmdline` is a live `frob check` process:
    some NUL-separated argv token equals `frob` (or ends `/frob`, the
    executable-path form) AND some token equals `check`, tested by
    comparing whole tokens, never a substring/regex over the raw joined
    cmdline (`_LIVE_CHECK_EXE_TOKEN`'s own docstring: the false-negative
    this closes). Any read failure reads as `False` (not a live check),
    matching every other best-effort `/proc` reader in this module."""
    try:
        raw = (proc / str(pid) / "cmdline").read_bytes()
    except OSError:
        return False
    tokens = raw.split(b"\x00")
    has_exe = any(
        token == _LIVE_CHECK_EXE_TOKEN or token.endswith(b"/" + _LIVE_CHECK_EXE_TOKEN)
        for token in tokens
    )
    return has_exe and _LIVE_CHECK_SUBCOMMAND_TOKEN in tokens


# frob:ticket T-3072
def _all_process_ppids(proc: Path) -> dict[int, int]:
    """`{pid: ppid}` for every live process under `proc`, read via
    `_read_ppid_from_stat` (T-3072) -- the ancestry substrate `_forkserver_
    root_is_live_check`'s multi-hop walk needs. Mirrors `scripts/fleet_
    status.py`'s own `_all_process_ppids` (T-2818); this module cannot
    import that script (the dependency direction only ever runs the other
    way -- a script may import the installed `frob` package, not the
    reverse), so this is the canonical, corrected copy T-3093 is expected
    to make `scripts/fleet_status.py` consume instead of carrying its own
    (see this module's own top-of-file note and T-3072's Done report). A
    single unreadable/malformed `<pid>/stat` degrades that ONE entry
    (omitted, reads as "not currently alive" to a caller walking through
    it) -- never fails the whole scan."""
    ppids: dict[int, int] = {}
    try:
        entries = list(proc.iterdir())
    except OSError:
        return ppids
    for entry in entries:
        if not entry.name.isdigit():
            continue
        ppid = _read_ppid_from_stat(int(entry.name), proc)
        if ppid is None:
            continue
        ppids[int(entry.name)] = ppid
    return ppids


#: Max ancestry hops `_forkserver_root_is_live_check` walks before
#: concluding the chain does not reach a live check -- mirrors `scripts/
#: fleet_status.py`'s own `_FORKSERVER_ANCESTRY_MAX_HOPS` (T-2818):
#: defensive bound against a malformed/cyclic ppid snapshot, never
#: expected to bind for a real forkserver chain.
_FORKSERVER_ANCESTRY_MAX_HOPS = 64


# frob:ticket T-3072
# frob:tests tests/unit/test_process_reap.py::TestForkserverRootIsLiveCheck.test_direct_child_of_live_check_is_not_orphaned  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestForkserverRootIsLiveCheck.test_orphaned_forkserver_of_forkserver_is_orphaned  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestForkserverRootIsLiveCheck.test_deep_chain_under_a_live_check_is_not_orphaned  # noqa: E501
def _forkserver_root_is_live_check(
    pid: int, ppid_map: dict[int, int], live_check_pids: set[int]
) -> bool:
    """Walk `pid`'s ancestry through `ppid_map`, `True` the instant ANY
    ancestor (at any depth) is a live `frob check` pid (T-3072, matching
    `scripts/fleet_status.py`'s own T-2818 algorithm exactly -- see this
    module's `_all_process_ppids` docstring for why this is a fresh copy,
    not an import). Closes the one-hop `_is_orphaned_forkserver` gap: a
    forkserver reparented to ANOTHER, already-orphaned forkserver has a
    live immediate parent (that forkserver itself), so a one-hop test
    misses it -- this walks past any number of alive-but-doomed
    intermediate forkservers until it EITHER finds a genuine live check
    (not orphaned) or the chain terminates (reaches pid 1, an ancestor no
    longer in `ppid_map`, a cycle, or `_FORKSERVER_ANCESTRY_MAX_HOPS`) --
    all of which are `False`, i.e. orphaned, the safe direction."""
    seen = {pid}
    current = pid
    for _ in range(_FORKSERVER_ANCESTRY_MAX_HOPS):
        parent = ppid_map.get(current)
        if parent is None or parent == current or parent in seen:
            return False
        if parent in live_check_pids:
            return True
        if parent == 1:
            return False
        seen.add(parent)
        current = parent
    return False


# frob:doc docs/modules/process.md#forkserver-reaping-t-2443
# frob:ticket T-2443
# frob:ticket T-3072
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_terminates_old_orphaned_forkservers  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_leaves_young_orphaned_forkservers_alone  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_leaves_non_forkserver_processes_alone  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_missing_proc_returns_empty  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_forkserver_of_orphaned_forkserver_is_reaped  # noqa: E501
# frob:tests tests/unit/test_process_reap.py::TestReapOrphanedForkservers.test_forkserver_under_a_live_check_is_never_reaped  # noqa: E501
def reap_orphaned_forkservers(
    age_floor_s: float = DEFAULT_ORPHAN_AGE_FLOOR_S,
    proc: Path = Path("/proc"),
) -> list[int]:
    """Startup-reaper half of T-2443's fix (this module's own docstring,
    part 2): SIGTERM every `multiprocessing.forkserver` helper under `proc`
    that is (a) orphaned -- ancestry never reaches a live `frob check`
    process, `_forkserver_root_is_live_check` -- and (b) at least
    `age_floor_s` old (`_process_start_age_s`) -- best-effort and
    defensive, meant to be called once at `frob check` startup so a
    machine that already accumulated leaked forkservers (from before
    `install_sigterm_reaper` shipped, or from a run that died some other
    way this fix does not cover) keeps getting cleaned up going forward.

    T-3072: upgraded from a one-hop `_is_orphaned_forkserver` (ppid == 1)
    check to the multi-hop ancestry walk -- the one-hop test misses a
    forkserver reparented to ANOTHER, already-orphaned forkserver (that
    intermediate forkserver is itself alive, so a one-hop test on the pid
    below it reads "live parent"). MUST-STAY-QUIET is the property that
    matters most here (T-3072's own house rule): a forkserver several
    hops below a genuinely running `frob check` -- including the fleet's
    dominant `python -m frob check ...` invocation shape, which T-3072
    found `scripts/fleet_status.py`'s own equivalent classifier fails to
    recognize -- must never be reaped, at any depth, under a live fleet
    where such chains always exist.

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
    try:
        entries = list(proc.iterdir())
    except OSError:
        return []
    forkserver_pids = [
        int(entry.name)
        for entry in entries
        if entry.name.isdigit() and _forkserver_cmdline_matches(int(entry.name), proc)
    ]
    if not forkserver_pids:
        return []
    ppid_map = _all_process_ppids(proc)
    live_check_pids = {pid for pid in ppid_map if _is_live_check_process(pid, proc)}
    return _reap_orphaned_pids(
        forkserver_pids, ppid_map, live_check_pids, age_floor_s, proc
    )


# frob:ticket T-3152
# frob:ticket T-3191
def _read_uptime_and_clk_tck(proc: Path) -> tuple[float | None, int]:
    """`(/proc/uptime's first field, os.sysconf("SC_CLK_TCK"))` -- read
    ONCE per scan (mirrors `scripts/fleet_status.py`'s own `_forkserver_
    snapshot` posture: both `uptime_s`/`clk_tck` are host-wide constants
    for the duration of one scan, not per-pid values, so re-reading them
    inside `_process_start_age_s`'s own per-pid loop would be wasted
    syscalls for no precision gain). `uptime_s` is `None` (never a
    fabricated value) if `/proc/uptime` is missing/unparseable (non-Linux
    `/proc`); `clk_tck` falls back to the near-universal Linux default of
    100 if `os.sysconf` itself fails, matching `_forkserver_age_s`'s own
    fallback.

    T-3191: `os.sysconf` is POSIX-only -- typeshed's `os.pyi` declares it
    under `if sys.platform != "win32":`, so a Windows-target `ty check`
    reports `unresolved-attribute` on a bare, unconditional call. Callers
    already never reach this path on Windows (`_forkserver_orphans`/
    `_process_start_age_s` both refuse before it via their own
    `sys.platform == "win32"` guard), but that caller-side guard is
    invisible to `ty`, which checks each function's body independently of
    who calls it. The `sys.platform != "win32"` check INSIDE this
    function is what lets `ty` narrow per `--python-platform` target the
    same way typeshed's own stub does: on a win32 target the `sysconf`
    branch is unreachable and never checked at all; on every other
    target it is checked exactly as before. This needs no `ty: ignore`
    in either direction -- the matched-opposite-error shape a static
    suppression cannot satisfy (see T-3191) never arises here."""
    try:
        uptime_s = float((proc / "uptime").read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        uptime_s = None
    clk_tck = 100
    if sys.platform != "win32":
        try:
            clk_tck = os.sysconf("SC_CLK_TCK")
        except (ValueError, OSError):
            clk_tck = 100
    return uptime_s, clk_tck


# frob:ticket T-3072
# frob:ticket T-3152
def _reap_orphaned_pids(
    forkserver_pids: list[int],
    ppid_map: dict[int, int],
    live_check_pids: set[int],
    age_floor_s: float,
    proc: Path,
) -> list[int]:
    """ARCH001 split of `reap_orphaned_forkservers` (T-3072): the actual
    per-pid orphan-check/age-check/SIGTERM loop, given an already-built
    `ppid_map`/`live_check_pids` snapshot (`reap_orphaned_forkservers`'s
    own docstring covers the full contract; this is purely the
    mechanical second half). T-3152: `uptime_s`/`clk_tck` (read once via
    `_read_uptime_and_clk_tck`) replace the old per-pid `now_s = time.
    time()` -- `_process_start_age_s` now derives age from `stat`'s
    `starttime` field, not `<proc>/<pid>`'s own mtime."""
    uptime_s, clk_tck = _read_uptime_and_clk_tck(proc)
    reaped: list[int] = []
    for pid in forkserver_pids:
        if _forkserver_root_is_live_check(pid, ppid_map, live_check_pids):
            continue
        age_s = _process_start_age_s(pid, proc, uptime_s, clk_tck)
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
            "forkserver pid=%d (age=%.0fs, no live frob check anywhere in "
            "its ancestry)",
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
# frob:waive COV007 reason="docs/modules/process.md's Concurrent-check advisory \
# (T-2473) section documents several symbols under one section, not just a public \
# entry point -- the many-symbols-one-section convention this repo already accepted \
# for vet.md (T-2810 declined to touch it), not a T-2810-shaped duplicate"
#: T-3072: `_is_frob_check_process` used to carry its OWN
#: `_FROB_TOKEN_RE = re.compile(rb"(?:^|/)frob\x00")` here -- the exact
#: same anchor bug T-3072 found and fixed in `scripts/fleet_status.py`'s
#: equivalent classifier (`^` only anchors the WHOLE cmdline blob's
#: start, not each NUL-delimited token, so a `frob` token that is neither
#: the very first token nor preceded by a literal `/` -- exactly `python
#: -m frob check ...`'s shape -- never matched). A THIRD copy of the same
#: broken pattern, in this same file, undercounting `count_running_
#: checks` for the fleet's own dominant `-m frob` invocation shape.
#: Replaced with `_is_live_check_process` (T-3072's whole-token
#: classifier, defined above `_forkserver_root_is_live_check`) rather
#: than patching the regex a third time -- DUP001: one classifier, one
#: home.


# frob:ticket T-2473
# frob:ticket T-3072
def _is_frob_check_process(pid: int, proc: Path, self_pid: int) -> bool:
    """`True` when `<proc>/<pid>/cmdline` names a live `frob check`
    invocation, excluding `self_pid` (a process never counts itself as
    "another" concurrent check, T-2473's own must-not-stall acceptance:
    a single check on an idle machine must read 0 others running, not
    1). Delegates the cmdline classification itself to `_is_live_check_
    process` (T-3072) -- see this module's note just above for why this
    no longer carries its own regex."""
    if pid == self_pid:
        return False
    return _is_live_check_process(pid, proc)


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
