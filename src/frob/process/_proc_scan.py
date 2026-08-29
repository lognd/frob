"""Process-table (`/proc`) scanning: orphaned-forkserver detection and
`frob check` liveness counting (T-3152, T-2443, T-2473, T-3072).

Split out of `frob.process._reap` (T-3396, LARGE001) -- that module's own
docstring documents the SIGTERM-reaping/`PR_SET_PDEATHSIG` fix this
supports (`reap_orphaned_forkservers` is the DEFENSIVE half of that
fix's two-part design, item 2). This module holds none of that fix's
mechanics itself: everything here is read-only `/proc` parsing and
classification (age, ancestry, cmdline matching) that `_reap.py` and
`scripts/fleet_status.py` both consume. POSIX-only by construction --
every public entry point below degrades to `None`/a no-op on
`sys.platform == "win32"` (no `/proc` there), matching this repo's
PLATFORM001 doctrine of declaring the platform boundary explicitly
rather than degrading silently.
"""

from __future__ import annotations

import os
import re
import signal
import sys
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)


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
