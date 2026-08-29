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
import signal
import sys
import typing
from types import FrameType
from typing import Callable

from frob.logging import get_logger

# frob:ticket T-3396
#: T-3396 split the `/proc`-scanning half of this module (orphan
#: detection, ancestry walks, `frob check` liveness counting) into
#: `frob.process._proc_scan` to clear LARGE001 (this file was 952
#: lines). Every name below is re-exported (not defined) here via the
#: explicit `as <same-name>` re-export idiom, so `frob.process._reap.
#: <name>` keeps working exactly as before for every existing caller/
#: test (`frob.gates`, `frob.__main__`, `tests/unit/test_process_reap.
#: py`'s `from frob.process._reap import ...`, `tests/unit/test_main_
#: entry.py`'s `monkeypatch.setattr("frob.process._reap.count_running_
#: checks", ...)`) -- this module's own public import path is
#: unchanged, only its internal size is. The `as <same-name>` form
#: (rather than a bare import) tells ruff's F401 this is a deliberate
#: re-export, not dead code.
from frob.process._proc_scan import (
    DEFAULT_ORPHAN_AGE_FLOOR_S as DEFAULT_ORPHAN_AGE_FLOOR_S,
)
from frob.process._proc_scan import (
    _all_process_ppids as _all_process_ppids,
)
from frob.process._proc_scan import (
    _forkserver_cmdline_matches as _forkserver_cmdline_matches,
)
from frob.process._proc_scan import (
    _forkserver_root_is_live_check as _forkserver_root_is_live_check,
)
from frob.process._proc_scan import (
    _is_frob_check_process as _is_frob_check_process,
)
from frob.process._proc_scan import (
    _is_live_check_process as _is_live_check_process,
)
from frob.process._proc_scan import (
    _is_orphaned_forkserver as _is_orphaned_forkserver,
)
from frob.process._proc_scan import (
    _process_start_age_s as _process_start_age_s,
)
from frob.process._proc_scan import (
    _read_ppid_from_stat as _read_ppid_from_stat,
)
from frob.process._proc_scan import (
    _read_uptime_and_clk_tck as _read_uptime_and_clk_tck,
)
from frob.process._proc_scan import (
    _reap_orphaned_pids as _reap_orphaned_pids,
)
from frob.process._proc_scan import (
    _stat_fields_after_comm as _stat_fields_after_comm,
)
from frob.process._proc_scan import (
    count_running_checks as count_running_checks,
)
from frob.process._proc_scan import (
    reap_orphaned_forkservers as reap_orphaned_forkservers,
)

# frob:ticket T-3396
#: Re-exported facade names -- T-3396 split the `/proc`-scanning half of
#: this module (orphan detection, ancestry walks, `frob check` liveness
#: counting) into `frob.process._proc_scan` to clear LARGE001 (this file
#: was 952 lines). Every symbol above is imported here, not just defined
#: there, so `frob.process._reap.<name>` keeps working exactly as before
#: for every existing caller/test (`frob.gates`, `frob.__main__`,
#: `tests/unit/test_process_reap.py`'s `from frob.process._reap import
#: ...`, `tests/unit/test_main_entry.py`'s `monkeypatch.setattr("frob.
#: process._reap.count_running_checks", ...)`) -- this module's own
#: public import path is unchanged, only its internal size is.

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


