# frob:ticket T-1684
# frob:waive LARGE001 reason="T-2829 (T-1651-grade review): one detached pipeline \
# (baseline read/write/CAS-lock -> land-id enumeration since the last sweep -> \
# unscoped check -> attribution/quarantine partitioning -> quarantine-raise for a red \
# batch -> commit the debt line), same orchestrator shape T-1651 already accepted for \
# check_runner.py/sys_runner.py -- every helper here (baseline I/O, attribution, \
# quarantine filtering) exists only to serve this one sweep's stages, in the order \
# those stages run, not a bundle of unrelated concerns. The file is large because the \
# pipeline genuinely has many stages (this module's own docstring walks through 5+ of \
# them to justify why a synchronous land no longer needs to), not because unrelated \
# features were bundled in. A line-count cut through a linear pipeline would separate \
# a stage from its own upstream/downstream data (e.g. the baseline CAS-lock helpers \
# from the attribution step that reads what they wrote), the same 'strictly worse than \
# the warning' shape T-1651 established."
"""T-1684: the `rapid`-profile replacement for `_land_cmd`'s synchronous
post-land unscoped error sweep -- a DETACHED sweep that files a ticket
instead of blocking the land.

`standard`'s post-land sweep (T-1456) is synchronous and reverts an
already-made land commit when it finds new unscoped errors. That is the
right bargain when a land is rare and expensive to unwind, but it costs a
full unscoped `frob check` (measured at 2-8 minutes on this repo) on the
critical path of every single land, plus a second full check for the
T-1463 pre-land baseline. A land that takes five minutes is its own
correctness risk: the queue stops draining, and work batches up into
giant unreviewable lands.

Under `rapid` the same verification still happens -- just not while the
developer waits, and without ever rewriting published history:

- **Rolling baseline, one check instead of two.** `standard` measures a
  pre-land baseline (check #1) and a post-land set (check #2) and diffs
  them. Here the previous deferred sweep's recorded absolute error set IS
  the baseline (`.frob/rapid-sweep-baseline.json`), so a sweep costs
  exactly one check and the land itself costs zero. The first sweep in a
  repo has no stored baseline: it records one and reports nothing, the
  same "unmeasurable baseline is not zero" posture `_land_cmd`'s sweeps
  already take rather than pretending every pre-existing error is new.
- **Files, never reverts.** The land commit is already published (and,
  under rapid, other agents are landing against it concurrently) -- a
  `git reset --hard` of another agent's base is strictly worse than a
  filed bug. New `(rule_id, file)` pairs become one `bug` ticket naming
  every pair and the commit that introduced them.
- **The window is recorded, not silent.** Every deferred sweep appends a
  `rapid-debt.jsonl` line at spawn time, so "this commit landed
  unverified" is a machine-readable fact from the instant it is true --
  even if the child is killed before it ever reports.

The baseline is rewritten to the freshly measured set on EVERY sweep,
including a red one. Errors that have already been filed as a ticket must
not be re-filed by the next land; the filed ticket is the record from
then on.

T-1935: the baseline/attribution/quarantine machinery below all operate
on `(rule_id, file)` IDENTITIES (via `_land_cmd._unscoped_error_
findings`, which itself dedupes on `(rule, file)` -- see `frob.app.
ticket_runner._verify._parse_error_findings_from_json`'s own docstring),
never on raw per-finding counts. This is deliberate for attribution and
quarantine (both reason about "which files/rules went red", not
individual diagnostics) and stays that way here (widening the identity
itself would need changes inside `_land_cmd.py`/`_verify.py`'s shared
parsers, both under another agent's live lease at the time of this fix,
T-1720/T-1929). What changes here instead: a filed regression ticket's
own "N new identit(ies)" count can be smaller than the true number of
distinct findings when several findings share one `(rule, file)` pair --
confirmed live, T-1923's sweep reported 6 identities for a commit whose
real unscoped `frob check` found 19 distinct findings (18 COV003 across 5
files collapsed to 5 identities, plus 1 F401) -- so `_file_regression_
ticket` (a) labels its own headline count "(rule, file) identit(ies)",
never "error(s)", and (b) pays for ONE extra, independent `frob check
--json` spawn (`_true_finding_count_for_identities`) ONLY on this rare
red-batch path (a clean sweep never reaches it, so the common-case "one
check per land" design goal above is unaffected) to report the TRUE
per-finding count alongside the identity count, rather than let the
identity count alone be misread as a completeness claim."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.process._lock import (
    lock_backend_available,
    portable_flock_acquire,
    portable_flock_release,
)
from frob.process._pid_liveness import pid_alive

# T-2595/T-2918/T-3506: `_baseline_lock` used to degrade to a logged
# NO-OP for the whole runtime of a process without `fcntl` (i.e. every
# Windows process, unconditionally, not just under rare contention) --
# T-2918 replaced that with a genuine `msvcrt.locking`-based lock on
# Windows. T-3506 moved that dual-path acquire/release itself to
# `frob.process._lock`'s shared `portable_flock_acquire`/`portable_
# flock_release`/`lock_backend_available` (see `_baseline_lock`'s
# docstring) rather than re-deriving its own `fcntl`/`msvcrt` pair.

if TYPE_CHECKING:
    # frob:ticket T-2312
    # `_dispose_to_existing_duplicate_or_none`'s own annotations only --
    # `from __future__ import annotations` above makes every annotation a
    # lazy string at runtime (its own local imports still cover the
    # function body), but `ty` resolves annotations statically and needs
    # these names in scope to typecheck the signature.
    from frob.tickets import TicketSpec
    from frob.tickets._models import TicketError

_log = get_logger(__name__)

#: Rolling absolute error set from the last deferred sweep. Under
#: `.frob/` (local, disposable, per-checkout) on purpose: it is a
#: measurement cache, not a record -- the RECORD is `rapid-debt.jsonl`
#: plus the filed tickets, both tracked. Losing this file costs one
#: skipped comparison, never a lost obligation.
_BASELINE_REL = Path(".frob") / "rapid-sweep-baseline.json"

#: T-2595: advisory lock guarding ONLY the tiny read-decide-write of
#: `_BASELINE_REL` below, never the multi-minute `frob check` a sweep runs
#: to produce `fresh` -- matching `_land.py`'s `land.lock` posture (same
#: `.frob/` directory, same flock mechanism) but scoped far more tightly,
#: since serializing sweeps themselves would defeat T-1684's whole point
#: of keeping them off the land critical path.
_BASELINE_LOCK_REL = Path(".frob") / "rapid-sweep-baseline.lock"

#: T-2595: how long `_baseline_lock` waits for a concurrent sweep's own
#: lock hold before giving up and degrading to an unlocked write (see its
#: docstring) -- generous relative to the sub-millisecond critical section
#: it actually protects, but still bounded so a crashed holder (whose
#: flock the kernel already released) or a genuinely stuck one cannot wedge
#: every other sweep on this shared root forever.
_BASELINE_LOCK_TIMEOUT_S = 30.0

#: Detached-child stdout/stderr, one file per swept ticket, so a sweep
#: that dies (OOM, reboot) leaves its partial output behind to read.
_LOG_DIR_REL = Path(".frob") / "rapid-sweep"

# frob:ticket T-4414
#: T-4414: the rate-limit/batch window's persisted state machine --
#: "idle" (no window open, no worker running) -> "window_open" (a
#: detached worker is alive and SLEEPING until the window closes,
#: collecting `pending_lands`) -> "sweep_running" (that SAME worker is
#: now actually running the unscoped `frob check` for the batch it
#: collected) -> back to "idle" (or straight back to "window_open" if
#: more lands joined while it ran, without a NEW worker process ever
#: being spawned -- see `_sweep_async`). Under `.frob/` like the
#: baseline/lock files above: local, disposable, per-checkout state, not
#: a durable record (the durable record of "this land is unswept yet" is
#: still `rapid-debt.jsonl`, unaffected by this ticket).
_WINDOW_STATE_REL = Path(".frob") / "rapid-sweep-window.json"

#: T-4414: advisory lock guarding ONLY the tiny read-decide-write of
#: `_WINDOW_STATE_REL` -- a dedicated lock file, deliberately never
#: `_BASELINE_LOCK_REL` (a land's registration and a sweep's baseline
#: write are independent critical sections) or `land.lock` (same
#: reasoning as `_baseline_lock_path`'s own docstring).
_WINDOW_LOCK_REL = Path(".frob") / "rapid-sweep-window.lock"

#: T-4414: how long `_window_lock` waits for a concurrent land's own
#: registration before giving up and degrading to an unlocked read-
#: decide-write (see `_advisory_file_lock`). The critical section here is
#: even smaller than the baseline lock's (no git subprocess, just a JSON
#: read/write), so this mirrors `_BASELINE_LOCK_TIMEOUT_S` rather than
#: inventing a different number.
_WINDOW_LOCK_TIMEOUT_S = 30.0

#: T-4414: the batching window's default length (seconds) when neither
#: `frob.toml` nor `pyproject.toml`'s `[tool.frob]` table overrides it
#: (see `_sweep_window_seconds`) -- long enough that a burst of lands a
#: few tens of seconds apart (the common multi-agent-wave shape this
#: ticket exists for) collapses onto one sweep, short enough that a
#: single isolated land is not kept "unverified" for an unreasonable
#: time before its sweep actually runs.
_DEFAULT_SWEEP_WINDOW_SECONDS = 120.0

#: T-1983: `_file_regression_ticket`'s title prefix, reused here to
#: recognize a sweep-filed ticket for `_close_resolved_sweep_tickets`'s
#: staleness check -- a title match plus `_REGRESSION_IDENTITY_HEADING`
#: parsing recovers the exact identity set the sweep itself recorded,
#: rather than re-deriving a second, possibly-drifting notion of "which
#: findings this ticket is about".
_REGRESSION_TITLE_PREFIX = "post-land sweep regression from "

#: T-1983: the exact heading `_file_regression_ticket` writes immediately
#: before its `"- {rule}  {file}"` lines -- the anchor
#: `_parse_sweep_ticket_identities` scans from, so parsing only ever
#: reads the identity list itself, never the attribution section below it
#: (which reuses the same "- rule  file  -> ..." shape but is not the
#: ticket's own obligation).
_REGRESSION_IDENTITY_HEADING = "New (rule, file) identit(ies) filed here:"

#: T-1935: the FALLBACK check budget (seconds)
#: `_true_finding_count_for_identities`/`_identities_still_reproducing`
#: pass to their own independent `frob check --budget --json` re-measure
#: when `budget=None` (both functions' default) and `root` has no (or too
#: little) recorded `.frob/check-budget-timing.json` data yet -- see
#: `_matching_error_diagnostics`. T-2715: this used to be a hardcoded
#: literal duplicate of `_land_cmd._POST_LAND_SWEEP_BUDGET_S`, kept in
#: sync by hand (the original comment here even said so) -- exactly the
#: drift class T-2715 found had already happened (this constant still
#: read 300 while `_land_cmd`'s had moved to 480). Both now default to
#: the SAME live-derived ceiling instead of two hand-synced numbers.
_TRUE_COUNT_BUDGET_S = 300

#: T-2106: the check budget (seconds) `revalidate_dispatchable_sweep_
#: tickets` passes to ITS OWN re-measure, deliberately much SMALLER than
#: `_TRUE_COUNT_BUDGET_S`. MEASURED (T-2106's own filing, coordinator
#: telemetry): a `frob ticket doable` invocation with sweep-filed
#: candidates present spawns this exact re-measure with the deferred-
#: sweep-sized budget (300) and it routinely runs the full 300s+ --
#: `_TRUE_COUNT_BUDGET_S`'s value and the measured 301.2s doable-time
#: cost line up almost exactly, meaning this call was in practice ALWAYS
#: paying close to the full budget, not a bounded fast path. A DEFERRED
#: sweep (this module's other caller, `_land_cmd.py`, off any
#: interactive path) can reasonably afford 300s; a coordinator or agent
#: waiting on `frob ticket doable` at the terminal cannot -- unmeasurable
#: is handled safely already (never treats a timeout as "resolved",
#: drops nothing), so trading a lower budget for bounded latency loses
#: nothing but revalidation confidence on the rare timeout case.
_DOABLE_REVALIDATION_BUDGET_S = 20

#: T-2089: `revalidate_dispatchable_sweep_tickets`'s doable-time
#: revalidation cache. MEASURED (T-2089's own filing): the uncached spawn
#: this function pays on every `frob ticket doable` call while any
#: sweep-filed candidate exists took 207.5s for 21 candidates / 265
#: identities -- comparable to the land lock's own ~210s ceiling, on a
#: QUERY verb run routinely, often several times in a row against a tree
#: that has not moved. Content-keyed on tree state (`_tree_state_key`)
#: plus the exact identity set re-checked (never a superset match), so a
#: real source or ticket change always invalidates it -- see
#: `_tree_state_key`'s own docstring for why a cache-unavailable signal
#: degrades to the old uncached behavior, never to a false HIT. Under
#: `.frob/` -- a measurement cache, not a record, same posture as
#: `_BASELINE_REL` above.
_REVALIDATION_CACHE_REL = Path(".frob") / "doable-revalidation-cache.json"

#: T-2089: defense-in-depth TTL bound layered on top of the content key
#: above. The content key alone should already be sound (any real source
#: or ticket-queue change moves HEAD or dirties the tree), but a TTL caps
#: how long one cache entry can be trusted if the tree-state signal ever
#: turns out to miss something the underlying check result actually
#: depends on (e.g. an external env/tool-version change) -- a stale clean
#: verdict must never be reachable purely by the tree happening to sit
#: still for a long session.
_REVALIDATION_CACHE_TTL_S = 300.0


# frob:doc \
# docs/modules/tickets-verify-sweep.md#deferred-post-land-sweep-rapid-only-t-1684
# frob:ticket T-1684
class RapidSweepError(ErrorSet):
    """Fallible outcomes of the deferred-sweep spawn and run."""

    SpawnRefused = "the detached sweep child could not be spawned"
    Unmeasurable = "the unscoped check produced no parsable error set"


def _baseline_path(root: Path) -> Path:
    """`.frob/rapid-sweep-baseline.json` for a checkout rooted at `root`."""
    return root / _BASELINE_REL


# frob:ticket T-2036
def _normalize_identity_file(root: Path, file: str) -> str:
    """T-2036: collapse an identity's `file` component to
    repo-relative POSIX form, so an absolute-path finding and a
    repo-relative finding for the SAME file are never treated as two
    different `(rule, file)` identities by the plain tuple-equality
    comparison `vanished`/`reproducing`/`identities <= vanished` all
    rely on.

    MEASURED root cause (T-2022, 2026-08-10): a ticket filed with an
    ABSOLUTE-path identity (`/home/.../tests/x.py`) was later compared
    against a fresh measurement reporting the SAME file REPO-RELATIVE
    (`tests/x.py`) -- the two strings never matched, the identity read
    as "vanished", and the ticket was auto-dropped while its finding was
    still live. Different callers of `frob check` in this repo's history
    have not agreed on which form a diagnostic's own `file` field takes,
    so normalizing at every point `_rapid_sweep.py` constructs or reads
    an identity (not just one) is what actually closes the gap -- the
    module's own "no false drops" invariant only holds if both sides of
    every comparison went through the SAME normalization.

    Falls back to the ORIGINAL string, unchanged, when `file` cannot be
    resolved relative to `root` at all (already relative, or absolute
    but outside `root` entirely) -- this can never make two genuinely
    different files collide, since an unresolvable absolute path is
    left exactly as unique as it already was."""
    path = Path(file)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# frob:ticket T-4607
def _is_git_metadata_path(file: str) -> bool:
    """`True` when `file` (already `_normalize_identity_file`-relative)
    names something under this checkout's own `.git/` directory --
    lease files (`.git/frob-leases/T-####.json`), lock files, and every
    other bit of git-internal bookkeeping is process state, never
    repository content a land can regress. Measured incident (T-4607):
    the deferred post-land sweep's own unscoped `frob check` reads
    `.git/frob-leases/*.json` for another ticket's OWN in-progress
    worktree lease and reports a TICK010 against it; the file's
    `mtime`/contents change on every concurrent lease renewal, so the
    NEXT sweep sees it as a brand-new, unattributable finding every
    single time -- a permanent, self-inflicted quarantine raise no land
    ever actually caused. Checked structurally on the path's own leading
    component, never on the emitting rule id, since any future rule
    reading `.git/**` would hit the exact same false-regression shape."""
    return file == ".git" or file.startswith(".git/")


# frob:ticket T-2313
# frob:ticket T-4607
def _normalize_identities(
    root: Path, identities: frozenset[tuple[str, str]]
) -> frozenset[tuple[str, str]]:
    """T-2036/T-2313/T-4607: apply `_normalize_identity_file` across a
    whole `(rule, file)` identity set -- the single call every producer/
    consumer of an identity set in this module should route through.

    T-2313: also drops any genuinely identity-less pair (rule AND file
    BOTH empty) here, before it can enter a baseline diff or be rendered
    into a filed ticket body -- observed verbatim in T-2297
    ("-   ", both fields blank). Such a pair carries no key any
    downstream auto-filer/attribution/dedup/dispose path can act on (a
    plausible route to an unclearable quarantine entry, T-2207's own
    precedent for a genuinely identity-less record), and its presence
    signals an upstream diagnostic with missing `code`/`file` data (see
    `_parse_error_findings_from_json` in `_verify.py`), never a real,
    actionable finding. Logged when it happens, never silently dropped.
    A pair with only ONE field empty (a real rule with no file, or vice
    versa) is left alone -- that is still a genuine, if partial,
    identity, not the T-2313 shape.

    T-4607: a pair whose normalized `file` is git-internal
    (`_is_git_metadata_path`, e.g. `.git/frob-leases/T-1234.json`) is
    ALSO dropped here, at the same choke point and for the same reason
    as the identity-less case above: it is not repository content this
    module's baseline/attribution/quarantine machinery can meaningfully
    reason about, and left in, it re-files and re-raises quarantine on
    every single sweep (see the helper's own docstring for the measured
    incident). A `tickets/` (or any other real repo path) finding is
    untouched -- this checks the literal `.git/` path prefix, never a
    rule id, so it can never suppress a genuine regression."""
    normalized: set[tuple[str, str]] = set()
    dropped = 0
    git_metadata_dropped = 0
    for rule, file in identities:
        if not rule and not file:
            dropped += 1
            continue
        normalized_file = _normalize_identity_file(root, file)
        if _is_git_metadata_path(normalized_file):
            git_metadata_dropped += 1
            continue
        normalized.add((rule, normalized_file))
    if dropped:
        _log.warning(
            "rapid sweep: T-2313: dropped %d genuinely identity-less "
            "(rule, file) pair(s) -- both fields empty, cannot be keyed, "
            "attributed, deduped, or disposed; likely an upstream "
            "diagnostic missing its code/file data",
            dropped,
        )
    if git_metadata_dropped:
        _log.info(
            "rapid sweep: T-4607: dropped %d (rule, file) pair(s) whose "
            "file is git-internal (under .git/, e.g. a frob-lease file) "
            "-- process state, never repository content a land can "
            "regress",
            git_metadata_dropped,
        )
    return frozenset(normalized)


def _read_baseline(root: Path) -> frozenset[tuple[str, str]] | None:
    """The last recorded `(rule_id, file)` error set (file components
    normalized repo-relative, T-2036 -- an older baseline
    written before this fix may still carry an absolute path on disk,
    normalized again here on read), or `None` when there is no usable
    baseline yet (absent or corrupt file).

    `None` is deliberately NOT an empty set: comparing a fresh scan
    against an assumed-clean baseline would report every pre-existing
    error in the repo as newly introduced by this land, which is exactly
    the false alarm that makes an automated filer get ignored."""
    path = _baseline_path(root)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return _normalize_identities(
            root, frozenset((str(rule), str(file)) for rule, file in raw["findings"])
        )
    except Exception as exc:  # noqa: BLE001 -- json/shape, any corruption
        _log.warning(
            "rapid sweep: baseline %s unreadable (%s) -- treating as NO "
            "baseline (unmeasured, not zero); this sweep records a fresh "
            "one and compares nothing",
            path,
            exc,
        )
        return None


# frob:ticket T-2009
def _read_baseline_commit(root: Path) -> str | None:
    """T-2009: the commit the last recorded baseline was ACTUALLY
    measured at, as opposed to the `commit_sha` a land passed to
    `spawn_deferred_post_land_sweep`, which only names the land that
    SPAWNED the sweep -- not necessarily the tree state the detached
    sweep actually measured once it finally ran (other agents' lands can
    and do land in between, since the sweep is deliberately off the land
    critical path, T-1684). `None` under the same conditions `_read_
    baseline` returns `None` for (absent/corrupt -- deliberately not "no
    commits happened", the same "unmeasured is not zero" posture)."""
    path = _baseline_path(root)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return str(raw["commit"])
    except Exception:  # noqa: BLE001 -- same posture as _read_baseline
        return None


#: T-2009: matches a `frob ticket land`-authored commit subject, e.g.
#: "fix(tickets): land T-1977 <title...>" -- see `_land_ids_between`.
_LAND_COMMIT_ID_RE = re.compile(r"\bland (T-\d+)\b")


# frob:ticket T-2009
def _land_ids_between(root: Path, since_commit: str, until_commit: str) -> list[str]:
    """T-2009: every distinct `T-####` id named in a `land T-####` commit
    subject reachable in `since_commit..until_commit` (oldest first).

    This is the mechanical fix for misattribution: `run_deferred_post_
    land_sweep`'s `fresh` measurement reflects whatever `root`'s tree
    looks like at the moment the DETACHED sweep child actually runs, not
    the moment it was spawned -- an arbitrary number of OTHER agents'
    lands can land in between (the sweep is deliberately off the land
    critical path, T-1684). Blaming `new_findings` solely on the land
    that happened to spawn this particular sweep process is only correct
    when exactly one land occurred in that window; this function answers
    "how many, and which" so the caller can tell the two cases apart
    instead of guessing. Returns `[]` on any git failure (a non-repo
    `tmp_path` in tests, or a detached-worktree edge case) so callers
    degrade to the pre-T-2009 single-attribution behavior rather than
    raise -- an unmeasurable range must never crash a sweep that has
    already found real findings to file."""
    from frob.gitio import run_argv

    result = run_argv(
        [
            "git",
            "-C",
            str(root),
            "log",
            "--reverse",
            "--format=%s",
            f"{since_commit}..{until_commit}",
        ]
    )
    if result.is_err or result.danger_ok.returncode != 0:
        return []
    ids: list[str] = []
    for line in result.danger_ok.stdout.splitlines():
        match = _LAND_COMMIT_ID_RE.search(line)
        if match and match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


# frob:ticket T-2009
def _resolve_actual_head(root: Path, fallback: str) -> str:
    """T-2009: the actual git HEAD of `root` at the moment this sweep's
    `frob check` finished running, or `fallback` (the land's own
    `commit_sha`, i.e. the pre-T-2009 assumption) when `root` is not a
    git worktree or the resolve fails. Recording THIS as the baseline's
    `commit` (instead of blindly trusting `commit_sha`) is what lets
    `_land_ids_between` compute an honest window on the NEXT sweep --
    never worse than the old behavior, since a resolve failure falls
    straight back to it."""
    from frob.gitio import run_argv

    result = run_argv(["git", "-C", str(root), "rev-parse", "HEAD"])
    if result.is_err or result.danger_ok.returncode != 0:
        return fallback
    head = result.danger_ok.stdout.strip()
    return head or fallback


# frob:ticket T-2571
def _files_deleted_between(root: Path, since: str | None, until: str) -> frozenset[str]:
    """T-2571: repo-relative POSIX paths git considers PURELY DELETED
    (never a rename target, `--diff-filter=D`) between `since` and
    `until` -- the ground-truth half of the T-2571 phantom-path fix.

    MEASURED root cause (T-2571's own triage, four sweep-filed tickets
    T-2381/T-2474/T-2525/T-2560): `TICK003`/`TICK004` fired against
    `tickets.md` in three separate sweeps AFTER the same ledger-v2 land
    had already DELETED `tickets.md` from the tree -- whatever check
    produces that identity is reading stale state, not the tree this
    sweep is actually measuring. A `(rule, file)` pair naming a file git
    itself confirms is gone can never be a real regression this land
    introduced, independent of whatever bug lives in the check that
    produced it.

    Returns the empty set (never raises, matches this module's git-
    degrades-gracefully posture -- `_land_ids_between`/`_resolve_actual_
    head`) when `since` is `None`/equal to `until` (no window to diff) or
    the `git diff` itself fails (non-repo `tmp_path`, detached edge
    case) -- an unmeasurable deletion set must never be treated as "no
    deletions happened" being SPECIAL-CASED into a phantom-filtering
    bug of its own; it degrades to the pre-T-2571 behavior (nothing
    filtered) exactly like every other git-backed helper here."""
    if not since or since == until:
        return frozenset()
    from frob.gitio import run_argv

    result = run_argv(
        [
            "git",
            "-C",
            str(root),
            "diff",
            "--name-status",
            "--diff-filter=D",
            f"{since}..{until}",
        ]
    )
    if result.is_err or result.danger_ok.returncode != 0:
        return frozenset()
    deleted: set[str] = set()
    for line in result.danger_ok.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].startswith("D"):
            deleted.add(parts[1])
    return frozenset(deleted)


# frob:ticket T-2571
def _filter_phantom_deleted_findings(
    final_id: str,
    fresh: frozenset[tuple[str, str]],
    deleted_files: frozenset[str],
) -> frozenset[tuple[str, str]]:
    """T-2571: drop every `(rule, file)` pair in `fresh` whose `file` is
    in `deleted_files` -- acceptance criterion 1's "not produced at all"
    branch, applied BEFORE `fresh` can enter a baseline write or a
    `new_findings` diff. A no-op (returns `fresh` unchanged, by identity)
    when `deleted_files` is empty, so this never allocates a new
    frozenset on the overwhelmingly common clean-window case.

    Logged at WARNING, never silent, naming every excluded identity --
    the silent-zero doctrine (T-2391) applies here just as much as to a
    real finding: a phantom finding excluded without a trace is exactly
    as undiagnosable later as a real one dropped without a trace."""
    if not deleted_files:
        return fresh
    phantom = frozenset((rule, file) for rule, file in fresh if file in deleted_files)
    if not phantom:
        return fresh
    _log.warning(
        "rapid sweep: %s: excluding %d phantom-path (rule, file) "
        "identit(ies) whose file was DELETED in the measured window -- "
        "never a real regression this land introduced, regardless of "
        "what produced the finding: %s",
        final_id,
        len(phantom),
        sorted(phantom),
    )
    return fresh - phantom


# frob:ticket T-2571
def _baseline_write_survived(root: Path, written_commit: str) -> bool:
    """T-2571: `True` iff the baseline file on disk RIGHT NOW still
    records `written_commit` as its `commit` -- i.e. no OTHER process
    (a concurrent land's own detached sweep, writing to the SAME shared
    `root` this module always operates on, T-1684's own design) clobbered
    this sweep's write with a different one in the tiny window between
    this sweep's own `_write_baseline` call and this check.

    Acceptance criterion 0's decisive check: a rolling baseline that does
    NOT survive to the next sweep's read is the concrete, measurable
    shape "an identity recurs across 3+ unrelated sweeps" would produce
    -- the next sweep reads back whatever the LAST writer left, which may
    already have discarded identities THIS sweep just recorded. `False`
    here does not undo anything (the write already happened and this
    function cannot un-race it) -- it exists so the caller can log the
    race explicitly instead of silently trusting a write that may already
    be gone, per acceptance criterion 0's own "or the log states
    explicitly why" clause."""
    return _read_baseline_commit(root) == written_commit


# tests/unit/rapid_sweep_suite/test_baseline.py::TestRollingBaseline.test_write_then_read_round_trips  # noqa: E501
def _write_baseline(
    root: Path, findings: frozenset[tuple[str, str]], commit: str
) -> None:
    """Record `findings` as the baseline the NEXT deferred sweep diffs
    against. Written on every sweep, red or green -- see this module's
    docstring on why an already-filed error must not be re-filed.

    Unlocked, unconditional overwrite -- callers that must survive a
    concurrent sweep racing on the same shared root (T-2595) want
    `_write_baseline_cas` instead, which wraps this same write in a lock
    plus an ancestry check. Kept as the low-level primitive both that
    function and every pre-T-2595 test still exercise directly."""
    path = _baseline_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "commit": commit,
        "findings": sorted([rule, file] for rule, file in findings),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _log.info(
        "rapid sweep: recorded rolling baseline of %d error(s) at %s",
        len(findings),
        commit[:12],
    )


def _baseline_lock_path(root: Path) -> Path:
    """`.frob/rapid-sweep-baseline.lock` for a checkout rooted at `root`
    (T-2595) -- a dedicated lock file, never the unrelated `land.lock`
    (`_land.py`'s `_LAND_LOCK_REL`): a sweep must never contend with, or
    be blocked by, an actual `frob ticket land` in flight."""
    return root / _BASELINE_LOCK_REL


# frob:ticket T-2918
# frob:doc \
# docs/modules/tickets-verify-sweep.md#baseline-lock-posixwindows-backends-loud-refusal-otherwise-t-2595t-2918  # noqa: E501
class BaselineLockUnavailable(RuntimeError):
    """T-2918: raised by `_baseline_lock` when NEITHER `fcntl` (POSIX) nor
    `msvcrt` (Windows) is importable on this interpreter -- there is no
    known advisory-lock primitive to use at all. This is a loud refusal,
    never a silent no-op: proceeding unlocked here would let two
    concurrent sweeps race the read-decide-write of the rolling baseline
    for the lock's ENTIRE unbounded lifetime (not the rare, brief window
    `_baseline_lock`'s timeout-exceeded branch accepts under real
    contention), which is exactly the silent-corruption shape T-2918 was
    filed to close. If this ever fires in practice it means a THIRD
    platform family with neither primitive is now in scope -- add a real
    backend for it here rather than reaching for a wider except."""


# frob:ticket T-2595
# frob:ticket T-2918
@contextmanager
def _baseline_lock(
    root: Path, *, timeout: float = _BASELINE_LOCK_TIMEOUT_S
) -> Iterator[None]:
    """T-2595/T-2918: exclusive, cross-process lock around ONLY the tiny
    read-decide-write of the rolling baseline -- never around the
    multi-minute `frob check` that produces the findings being written.
    Same mechanism as `_land.py`'s `_land_lock` (a dedicated lock file
    under `.frob/`), deliberately NOT the same lock file -- serializing
    sweeps against an in-flight `land()` would defeat T-1684's entire
    point of keeping them off the land critical path.

    Two real backends, tried in this order:

    - POSIX (`fcntl.flock`): the original T-2595 implementation.
    - Windows (`msvcrt.locking`): T-2918's addition. `msvcrt.locking`
      locks a byte RANGE of an open file rather than the whole
      descriptor, so the lock file is seeded with one byte on first use
      and every lock/unlock call always targets exactly that byte at
      offset 0 (seeking back to it after each `locking()` call, since
      `locking()` also advances the file position). `LK_NBLCK` (non-
      blocking) mirrors `fcntl`'s `LOCK_NB` so the same poll-with-timeout
      loop below drives both backends identically; `PermissionError` is
      what `msvcrt.locking` raises for "already locked", `OSError`'s
      Windows-specific subclass, so the shared `except OSError` catches
      it the same way it catches `fcntl.flock`'s `OSError`.

    If NEITHER primitive is importable, this RAISES `BaselineLockUnavailable`
    instead of proceeding unlocked (T-2918) -- see that exception's own
    docstring for why an unconditional platform-wide no-op is a different,
    worse risk than the bounded contention-timeout degrade below.

    A blocking-with-retry poll (not `_land_lock`'s poll-with-holder-
    logging dance) is enough here: the critical section is a few
    milliseconds of file I/O plus one `git merge-base --is-ancestor`
    call, so contention is rare and brief, and unlike a land there is no
    interactive human waiting on the other end to name. Still
    timeout-bounded (`timeout`, default `_BASELINE_LOCK_TIMEOUT_S`)
    rather than an unbounded wait, in case a holder is genuinely wedged
    -- on timeout, this degrades to proceeding WITHOUT the lock (logged
    at WARNING) rather than raising and losing this sweep's findings
    entirely; the CAS ancestry check the caller performs under (or
    without) the lock is the actual correctness guarantee, this lock
    only narrows the race window against an ORDINARY concurrent sweep
    that is ALREADY holding it, so degrading to unlocked on a stuck lock
    is a reduced guarantee, never a silent corruption -- unlike the
    platform-wide no-op T-2918 removed, this branch only fires when a
    real lock exists and is contended, not merely absent."""
    with _advisory_file_lock(
        _baseline_lock_path(root), timeout=timeout, label="_baseline_lock"
    ):
        yield


# frob:ticket T-4414
@contextmanager
def _advisory_file_lock(path: Path, *, timeout: float, label: str) -> Iterator[None]:
    """T-4414: the exact acquire/seed/release body `_baseline_lock` used
    to carry inline, extracted so `_window_lock` (this ticket's own
    batching-window lock, guarding `.frob/rapid-sweep-window.json`
    instead of the baseline file) reuses the SAME cross-process primitive
    rather than a second hand-copied `fcntl`/`msvcrt` dance -- one lock
    implementation, two lock files. `label` names the caller in the
    timeout-degrade log line only; behavior (create-and-seed a 1-byte
    lock file, `portable_flock_acquire`/`_release`, degrade to
    proceeding WITHOUT the lock -- logged -- on timeout rather than
    raising) is unchanged from `_baseline_lock`'s pre-T-4414 body."""
    if not lock_backend_available():  # pragma: no cover -- via monkeypatch
        raise BaselineLockUnavailable(
            f"rapid sweep: {label}: neither fcntl (POSIX) nor "
            f"msvcrt (Windows) is available on this platform -- refusing "
            f"to proceed unlocked against {path}, since an unconditional "
            f"platform-wide no-op would race concurrent writers for "
            f"this lock's entire lifetime, not just under rare, brief "
            f"contention (T-2918)"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    # `os.O_BINARY` only exists on Windows; `getattr` keeps this portable
    # (a no-op on POSIX) rather than branching on the backend to decide.
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | getattr(os, "O_BINARY", 0), 0o644)
    if os.fstat(fd).st_size < 1:
        os.write(fd, b"\0")
        os.fsync(fd)
    # frob:ticket T-3506
    acquired = portable_flock_acquire(fd, exclusive=True, timeout=timeout)
    if not acquired:
        _log.warning(
            "rapid sweep: %s: %s still held after "
            "%.0fs -- proceeding WITHOUT the lock (the CAS "
            "ancestry check is the correctness backstop, this "
            "is a reduced guarantee, not corruption)",
            label,
            path,
            timeout,
        )
    try:
        yield
    finally:
        if acquired:
            # frob:ticket T-3506
            portable_flock_release(fd)
        os.close(fd)


# frob:ticket T-2595
def _is_ancestor(root: Path, older: str, newer: str) -> bool | None:
    """`True` iff `older` is an ancestor of (or equal to) `newer` in
    `root`'s git history, `False` if git resolved the question and it is
    not, `None` when the question could not be resolved at all (a
    non-repo `tmp_path`, an unknown/GC'd commit, or any other git
    failure) -- mirrors this module's existing `_land_ids_between`/
    `_resolve_actual_head` posture of a third `None`/unmeasurable state
    that is never conflated with a definite `False` (T-2391's silent-zero
    doctrine: "could not tell" and "checked, and no" are different
    facts). `_write_baseline_cas` treats `None` as "cannot prove safety",
    which means it does NOT skip the write -- see that function's
    docstring for why degrading to the pre-T-2595 unconditional-write
    behavior is correct there specifically."""
    if older == newer:
        return True
    from frob.gitio import run_argv

    result = run_argv(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", older, newer]
    )
    if result.is_err:
        return None
    returncode = result.danger_ok.returncode
    if returncode == 0:
        return True
    if returncode == 1:
        return False
    return None


# frob:ticket T-2595
def _write_baseline_cas(
    root: Path, findings: frozenset[tuple[str, str]], commit: str
) -> bool:
    """T-2595: the race fix. Under `_baseline_lock`, re-reads whatever
    commit is CURRENTLY on disk (not the `prev_baseline_commit` the
    caller read minutes ago, before its multi-minute `frob check` ran --
    that snapshot is exactly what makes the unlocked write in `_write_
    baseline` racy: sweep B reads it stale, then unconditionally
    overwrites whatever sweep A wrote in the meantime) and only performs
    the write when it cannot possibly discard newer information than it
    is contributing:

    - no prior baseline on disk at all -> write (nothing to lose).
    - the on-disk commit is an ANCESTOR of (or equal to) `commit` -> this
      sweep's view is at least as fresh -> write.
    - the on-disk commit is NOT an ancestor of `commit` (concurrent sweep
      B here would be about to overwrite concurrent sweep A's fresher
      write with B's own stale one) -> SKIP, log loudly, and return
      `False` so the caller can report the skip rather than pretend it
      wrote.
    - ancestry could not be resolved at all (`_is_ancestor` returned
      `None` -- non-repo, GC'd commit, git failure) -> write anyway,
      matching this module's "an unmeasurable condition never blocks a
      sweep that already has real findings to record" posture used
      throughout (`_files_deleted_between`, `_land_ids_between`); refusing
      to ever persist a baseline again on a transient git hiccup would be
      strictly worse than the rare unnecessary overwrite this case
      accepts.

    Returns `True` iff the write actually happened."""
    with _baseline_lock(root):
        on_disk_commit = _read_baseline_commit(root)
        if on_disk_commit is not None:
            ancestry = _is_ancestor(root, on_disk_commit, commit)
            if ancestry is False:
                _log.warning(
                    "rapid sweep: baseline write at %s SKIPPED -- the "
                    "baseline currently on disk (commit %s) is not an "
                    "ancestor of this write's commit, meaning it was "
                    "written by a concurrent sweep with a FRESHER view; "
                    "overwriting it here would discard real findings "
                    "that sweep just recorded (T-2595, the "
                    "read-modify-write race T-2571's _baseline_write_"
                    "survived could only detect, not prevent)",
                    commit[:12],
                    on_disk_commit[:12],
                )
                return False
        _write_baseline(root, findings, commit)
        return True


#: T-2671: filename prefix for `_persist_commit_step_failure`'s retained
#: diagnostic log -- lives alongside a detached sweep's own stdout/stderr
#: files in `_LOG_DIR_REL` so both survive the same way for the same
#: reason (a foreground `frob ticket land` invocation's own terminal
#: output is retained NOWHERE by default; `frob.logging` installs no file
#: handler).
_RAPID_DEBT_FAILURE_LOG_PREFIX = "rapid-debt-commit-failure"


# tests/unit/rapid_sweep_suite/test_commit.py::TestPersistCommitStepFailure.test_writes_proc_result_diagnostics  # noqa: E501
# tests/unit/rapid_sweep_suite/test_commit.py::TestPersistCommitStepFailure.test_writes_spawn_error_diagnostics  # noqa: E501
# tests/unit/rapid_sweep_suite/test_commit.py::TestPersistCommitStepFailure.test_swallows_its_own_write_failure  # noqa: E501
# frob:ticket T-2671
def _persist_commit_step_failure(
    root: Path,
    ticket_id: str,
    step: str,
    outcome: Result[Any, Any],
) -> Path | None:
    """T-2671: persist ONE `_commit_rapid_debt` git step's full outcome
    (argv/returncode/stdout/stderr, or the spawn-level `GitError` when the
    process never even ran) to a retained file under `_LOG_DIR_REL`, so a
    DirtyMain recurrence names its own cause instead of requiring
    reconstruction from commit timestamps.

    MEASURED gap this closes: T-2669 fixed one confirmed cause of the
    rapid-debt DirtyMain failure, but a SECOND, intermittent recurrence
    happened the same day in a tree that already contained T-2669's fix
    (proven via `git show <land>:_rapid_sweep.py | grep -c
    _land_internal_git_env` returning 2) -- and it could not be diagnosed
    further because the land invocation's own stderr was never retained
    anywhere; only the SILENT detached post-land sweep log survived.
    `_commit_rapid_debt`'s prior failure handling logged only a one-line
    module-logger summary ("could not commit ... commit it by hand")
    with no git output at all -- the exact information a future
    diagnosis needs is the thing that was being thrown away.

    Best-effort and NEVER raises: a failure writing this diagnostic file
    must not itself become a second, unrelated commit failure. Returns
    the written path, or `None` if the write failed (logged separately in
    that case)."""
    log_dir = root / _LOG_DIR_REL
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = log_dir / f"{_RAPID_DEBT_FAILURE_LOG_PREFIX}-{ticket_id}-{ts}.log"
    if outcome.is_err:
        payload: dict[str, object] = {
            "ticket_id": ticket_id,
            "step": step,
            "timestamp_utc": ts,
            "outcome": "spawn_failed",
            "git_error": str(outcome.danger_err),
        }
    else:
        proc = outcome.danger_ok
        payload = {
            "ticket_id": ticket_id,
            "step": step,
            "timestamp_utc": ts,
            "outcome": "nonzero_returncode",
            "argv": list(getattr(proc, "argv", ())),
            "returncode": getattr(proc, "returncode", None),
            "stdout": getattr(proc, "stdout", ""),
            "stderr": getattr(proc, "stderr", ""),
        }
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        _log.error(
            "rapid sweep: %s could not write rapid-debt commit-failure "
            "diagnostic log for step %s in %s: %s -- the underlying "
            "failure is still logged above, just not retained to disk",
            ticket_id,
            step,
            log_dir,
            exc,
        )
        return None
    return path


# tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_leaves_the_repo_clean  # noqa: E501
# tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_stages_only_the_debt_file  # noqa: E501
# tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_a_non_repo_never_raises  # noqa: E501
# tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_survives_the_scaffolded_root_write_guard  # noqa: E501
# tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_guard_still_refuses_a_genuinely_foreign_file  # noqa: E501
# tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_commit_failure_persists_a_diagnostic_log  # noqa: E501
# frob:ticket T-1698
# frob:ticket T-2669
# frob:ticket T-2671
def _commit_rapid_debt(root: Path, ticket_id: str) -> None:
    """Commit the `rapid-debt.jsonl` line this land just appended, so the
    land leaves `root` CLEAN.

    `rapid-debt.jsonl` is tracked on purpose (it must survive a clone and
    a `frob clean`, and be reviewable in a diff), and this record is
    written AFTER the land commit is sealed because it names that commit
    -- so it cannot ride along in it, and amending is forbidden here. It
    therefore gets its own tiny follow-up commit. Without this, every
    rapid land left the shared root checkout dirty and the NEXT land from
    ANY agent refused with `DirtyMain`: one uncommitted line deadlocked a
    whole three-agent wave (T-1698).

    Stages `rapid-debt.jsonl` and NOTHING else. A blanket `git add -A` on
    a root checkout that concurrent lands are racing against would sweep
    up whatever another agent had in flight -- the opposite of the
    isolation this file exists to record.

    Best-effort: a failure here must never fail a land that has already
    succeeded, but it is logged at ERROR, because the resulting dirty root
    is invisible in the `DirtyMain` error every other agent then hits.

    T-2669: the `commit` spawn below is wrapped in `_land_internal_git_
    env()` (T-0828), same as every other land-internal commit in `_land_
    git_ops.py`. Without it, this commit is indistinguishable from an
    ordinary non-ledger write to the shared root checkout, and the T-2071
    scaffolded `pre-commit` hook refuses exactly that (a non-ledger file
    staged directly in the primary checkout while linked worktrees exist)
    unless `FROB_LAND_INTERNAL=1` is set -- measured directly as the cause
    of 70 hand-committed `rapid-debt.jsonl` DirtyMain recoveries in one
    day (T-2669's own measurement) before this fix."""
    from frob.gitio import run_argv
    from frob.tickets._land_git_ops import _land_internal_git_env

    rel = "rapid-debt.jsonl"
    status = run_argv(["git", "-C", str(root), "status", "--porcelain", "--", rel])
    if status.is_err or status.danger_ok.returncode != 0:
        log_path = _persist_commit_step_failure(root, ticket_id, "status", status)
        _log.error(
            "rapid sweep: %s could not read %s status in %s -- if it is "
            "dirty, every subsequent land in this repo will refuse with "
            "DirtyMain (diagnostic: %s)",
            ticket_id,
            rel,
            root,
            log_path,
        )
        return
    if not status.danger_ok.stdout.strip():
        return  # nothing appended (e.g. the write failed and logged already)

    staged = run_argv(["git", "-C", str(root), "add", "--", rel])
    if staged.is_err or staged.danger_ok.returncode != 0:
        log_path = _persist_commit_step_failure(root, ticket_id, "add", staged)
        _log.error(
            "rapid sweep: %s could not stage %s in %s (diagnostic: %s)",
            ticket_id,
            rel,
            root,
            log_path,
        )
        return
    with _land_internal_git_env():
        committed = run_argv(
            [
                "git",
                "-C",
                str(root),
                "commit",
                "-m",
                f"chore(rapid): record {ticket_id}'s deferred post-land sweep",
                "--",
                rel,
            ]
        )
    if committed.is_err or committed.danger_ok.returncode != 0:
        # T-2671: this is the exact step whose failure the DirtyMain
        # recurrence traced to -- persist the full git outcome (a hook
        # refusal, a lock-contention message, or something else entirely)
        # so the NEXT occurrence names its own cause instead of requiring
        # commit-timestamp archaeology.
        log_path = _persist_commit_step_failure(root, ticket_id, "commit", committed)
        _log.error(
            "rapid sweep: %s could not commit %s in %s -- root is now DIRTY "
            "and the next land from any agent will refuse with DirtyMain; "
            "commit it by hand (diagnostic: %s)",
            ticket_id,
            rel,
            root,
            log_path,
        )
        return
    _log.info("rapid sweep: %s committed the deferred-sweep debt line", ticket_id)


# frob:ticket T-4414
def _window_state_path(root: Path) -> Path:
    """`.frob/rapid-sweep-window.json` for a checkout rooted at `root`."""
    return root / _WINDOW_STATE_REL


# frob:ticket T-4414
def _window_lock_path(root: Path) -> Path:
    """`.frob/rapid-sweep-window.lock` for a checkout rooted at `root`."""
    return root / _WINDOW_LOCK_REL


# frob:ticket T-4414
@contextmanager
def _window_lock(
    root: Path, *, timeout: float = _WINDOW_LOCK_TIMEOUT_S
) -> Iterator[None]:
    """T-4414: exclusive lock around the read-decide-write of the
    batching-window state (`_WINDOW_STATE_REL`) -- every land registers
    itself under this lock before deciding whether it opened a new
    window, joined an existing one, or was deferred to the next, so two
    lands landing at the same instant never both conclude "I am the one
    that opens the window" and spawn two workers."""
    with _advisory_file_lock(
        _window_lock_path(root), timeout=timeout, label="_window_lock"
    ):
        yield


# frob:ticket T-4414
def _toml_number(path: Path, keys: tuple[str, ...]) -> float | int | None:
    """Read a dotted-key numeric value out of a TOML file at `path`,
    tolerating a missing file, a missing table/key anywhere along
    `keys`, or an unparsable file -- every case returns `None` ("no
    override found here"), never raises. Mirrors `check_runner.py`'s
    `_apply_frob_toml_defaults` frob.toml-read posture (T-1038): a
    malformed or absent config file degrades to the caller's own
    default, it never crashes a detached sweep worker."""
    if not path.exists():
        return None
    import tomllib

    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("rapid sweep: %s unreadable for window config: %s", path, exc)
        return None
    node: Any = data
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return node
    return None


# frob:ticket T-4414
def _sweep_window_seconds(root: Path) -> float:
    """T-4414: the configured batching-window length (seconds), read
    directly from config rather than threaded through `AppConfig`/
    argparse (this module's DETACHED `sweep-async` child has no
    `argparse.Namespace` of its own to receive a CLI flag through --
    same reasoning as `_apply_frob_toml_defaults`'s own frob.toml-only
    fields in `check_runner.py`). Checked in order, first match wins:
    `frob.toml`'s `[sweep] window_seconds`, then `frob.toml`'s top-level
    `rapid_sweep_window_seconds`, then `pyproject.toml`'s `[tool.frob]
    rapid_sweep_window_seconds` -- falling back to `_DEFAULT_SWEEP_
    WINDOW_SECONDS` when none of the three is set."""
    value = _toml_number(root / "frob.toml", ("sweep", "window_seconds"))
    if value is None:
        value = _toml_number(root / "frob.toml", ("rapid_sweep_window_seconds",))
    if value is None:
        value = _toml_number(
            root / "pyproject.toml", ("tool", "frob", "rapid_sweep_window_seconds")
        )
    if value is None:
        return _DEFAULT_SWEEP_WINDOW_SECONDS
    return float(value)


# frob:ticket T-4414
def _default_window_state() -> dict[str, Any]:
    """The `idle`, empty-batch shape `_read_window_state` returns when
    `_WINDOW_STATE_REL` is absent or unreadable -- a fresh checkout, or a
    corrupt state file, must degrade to "no window open, nothing
    pending", never raise (this is read by both an interactive land and
    a detached worker with nobody watching its exit code)."""
    return {
        "phase": "idle",
        "window_opened_at": None,
        "worker_pid": None,
        "pending_lands": [],
    }


# frob:ticket T-4414
def _read_window_state(root: Path) -> dict[str, Any]:
    """The persisted batching-window state, or `_default_window_state()`
    when `_WINDOW_STATE_REL` is absent or unreadable -- callers must
    hold `_window_lock` around any read that will be followed by a
    write, this function itself takes no lock (the lock's critical
    section spans read-decide-write together, not this call alone)."""
    path = _window_state_path(root)
    if not path.exists():
        return _default_window_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 -- json/shape, any corruption
        _log.warning(
            "rapid sweep: window state %s unreadable (%s) -- treating as "
            "idle with nothing pending",
            path,
            exc,
        )
        return _default_window_state()
    state = _default_window_state()
    state.update(
        {k: raw[k] for k in ("phase", "window_opened_at", "worker_pid") if k in raw}
    )
    if isinstance(raw.get("pending_lands"), list):
        state["pending_lands"] = raw["pending_lands"]
    return state


# frob:ticket T-4414
def _write_window_state(root: Path, state: dict[str, Any]) -> None:
    """Persist `state` to `_WINDOW_STATE_REL`. Callers hold `_window_lock`
    around the read-decide-write this is the tail of; this function
    itself only writes -- it does not lock."""
    path = _window_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


# frob:ticket T-4414
def _worker_is_alive(state: dict[str, Any]) -> bool:
    """Whether `state["worker_pid"]` names a currently-running detached
    worker -- `False` for a `None` pid (no worker was ever recorded, or
    it already finished and cleared itself) as well as for a pid that
    named a worker which has since crashed (the reap case every caller
    of this function must treat identically to "no worker is running")."""
    pid = state.get("worker_pid")
    return isinstance(pid, int) and pid_alive(pid)


# frob:ticket T-4414
def _decide_land_registration(
    state: dict[str, Any],
    land: dict[str, Any],
    *,
    now: float,
) -> tuple[str, dict[str, Any]]:
    """T-4414's pure decision core (acceptance criteria 1 and 3): given
    the CURRENT persisted `state` and one `land`'s identity dict
    (`ticket_id`/`final_id`/`commit_sha`/`target_branch`), returns
    `(action, new_state)` where `action` is one of:

    - `"open"`: no worker is alive (idle, or a dead `worker_pid` reaped
      here) -- `new_state` opens a fresh window with `land` as its sole
      pending entry; the caller must spawn a new detached worker and
      record its pid.
    - `"join"`: a worker is alive and `state["phase"]` is `"window_open"`
      -- `land` is appended to the SAME window's `pending_lands`; no new
      worker is spawned. Deliberately joins even when the window's own
      deadline has technically elapsed (a live worker still sleeping is
      the authority on when it actually wakes, not a second clock racing
      it) -- the alternative would risk opening a second window on top
      of one whose worker has not yet noticed its own deadline passed.
    - `"defer"`: a worker is alive and `state["phase"]` is
      `"sweep_running"` -- `land` is appended to the SAME `pending_lands`
      list (it becomes the batch the worker picks up for its NEXT window
      once its current run finishes, per `_sweep_async`); no new worker
      is spawned. Never a second concurrent sweep (criterion 3).

    Never mutates `state`/`land` in place -- always returns a fresh dict,
    so a caller that decides not to persist a rejected write (a pinned
    write elsewhere in this module, or a future caller) never has to
    worry about a partially-applied decision leaking through the input
    it was handed."""
    new_state = dict(state)
    pending = list(state.get("pending_lands", []))
    if _worker_is_alive(state) and state.get("phase") in (
        "window_open",
        "sweep_running",
    ):
        action = "join" if state["phase"] == "window_open" else "defer"
        pending.append(land)
        new_state["pending_lands"] = pending
        return action, new_state
    # Idle, or `worker_pid` named a now-dead process (reaped here): open a
    # fresh window with `land` as its sole pending entry. `worker_pid` is
    # left for the caller to fill in once the new worker is actually
    # spawned (this function never spawns processes itself).
    new_state["phase"] = "window_open"
    new_state["window_opened_at"] = now
    new_state["worker_pid"] = None
    new_state["pending_lands"] = [land]
    return "open", new_state


# frob:ticket T-2030
def _detached_sweep_env(root: Path, target_branch: str | None = None) -> dict[str, str]:
    """T-2030: the `env=` this module's detached `sweep-async` child MUST
    be spawned with -- never the bare inherited `os.environ`.

    MEASURED root cause: `_resolve_ticket_root` (`ticket_runner/
    __init__.py`) resolves a `frob ticket <verb>` invocation's root by
    checking `FROB_ROOT` in the environment BEFORE falling back to `cwd`
    -- and `subprocess.Popen` here used to pass no `env=` at all, so the
    detached child silently inherited whatever `FROB_ROOT` happened to be
    set in the LANDING process's own shell. When that ambient value named
    a DIFFERENT worktree than the `cwd=root` this call already resolved
    correctly (T-1003's own precedent: pin explicitly, never trust
    ambient state), the child's root resolution was silently hijacked --
    `cwd` was right, `FROB_ROOT` overrode it anyway, and the sweep wrote
    ticket-file content into whatever worktree that stale value named.
    This is the single upstream mechanism T-2030 measured across all
    three symptoms (root residue, cross-worktree writes, and the
    double-appended drop block): every one of them is a write that
    landed in the wrong tree because the child's OWN root resolution,
    not `cwd`, decided where to write.

    Pins `FROB_ROOT` to `root` explicitly (winning outright over any
    ambient value, matching `_frob_root_env`'s own precedence) and strips
    `FROB_WORKTREE`/`FROB_AGENT` (T-0574's worktree-lease env, section
    5b's identical precedent for `tests/system/**`'s subprocess helper --
    a detached sweep against the resolved land root is not "a dispatched
    worktree agent" and must not inherit whichever worktree the LANDING
    process happened to be leased to).

    T-4105: `target_branch` (default `None`) is `cfg.ticket_land_branch`
    from the land that is deferring this sweep -- when given, set as
    `FROB_LAND_TARGET_BRANCH` in the child's env so `_spawn_true_count_
    check` (running inside the DETACHED `sweep-async` process this env
    feeds, a separate OS process this function's own argv-building
    caller cannot pass a CLI flag to without a new `sweep-async` parser
    flag, which is `_cli_parsers/` code and out of this ticket's scope)
    can forward it on as `--base` to its own nested `frob check` spawn.
    An explicit env var is the deliberate exception to 'thread as an
    argument, not an env var' here: the alternative is a same-file-only
    variable that never crosses this specific process boundary. Unset
    (`None`) omits the var entirely -- an ordinary main-line land's
    detached sweep is byte-identical to pre-T-4105 behavior."""
    env = dict(os.environ)
    env["FROB_ROOT"] = str(root)
    env.pop("FROB_WORKTREE", None)
    env.pop("FROB_AGENT", None)
    if target_branch is not None:
        env["FROB_LAND_TARGET_BRANCH"] = target_branch
    else:
        env.pop("FROB_LAND_TARGET_BRANCH", None)
    return env


# frob:ticket T-2450
# frob:doc \
# docs/modules/tickets-verify-sweep.md#public-seam-for-cross-node-callers-t-2450
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDetachedSweepEnvPublicSeam.test_delegates_to_the_private_implementation  # noqa: E501
def detached_sweep_env(root: Path) -> dict[str, str]:
    """T-2450: public seam for `_detached_sweep_env`, for callers OUTSIDE
    `app.ticket_runner`'s own node (`frob.verify._drain`, which spawns
    the SAME detached `sweep-async` child machinery this module owns) --
    filed from T-2407's SYS003 burn-down, which flagged `frob.verify`
    reaching across the node boundary to call a private, underscore-
    prefixed helper directly as debt in its own right, independent of
    whether the coupling itself is architecturally sound (it is: T-2407
    already declared the verify -> cli flow legitimate). Every in-module
    caller keeps using `_detached_sweep_env` directly, unchanged -- this
    wrapper exists ONLY for the cross-node case, so a future reader
    grepping for this module's own private helpers is not misled into
    thinking `_detached_sweep_env` itself became public."""
    return _detached_sweep_env(root)


# frob:doc \
# docs/modules/tickets-verify-sweep.md#deferred-post-land-sweep-rapid-only-t-1684
# frob:ticket T-1684
def spawn_deferred_post_land_sweep(
    root: Path,
    ticket_id: str,
    final_id: str,
    commit_sha: str,
    target_branch: str | None = None,
) -> Result[int, RapidSweepError]:
    """Fire the unscoped post-land sweep for `final_id` into a DETACHED
    child and return its pid immediately -- the whole point of the rapid
    land path. Records the deferral to `rapid-debt.jsonl` BEFORE the
    spawn, so the "this commit is unverified" fact survives a child that
    never starts or is killed mid-sweep.

    Never raises and never blocks: a refused spawn is `Err(SpawnRefused)`
    and the caller logs it and proceeds. The land commit is already
    durable at this point; nothing here can or should undo it.

    T-4105: `target_branch` (default `None`) is `cfg.ticket_land_branch`
    from the deferring land -- forwarded to `_detached_sweep_env` (see its
    own T-4105 paragraph) so the detached child can recover it as
    `FROB_LAND_TARGET_BRANCH` and pass it on as `--base` to its own nested
    `frob check` spawn.

    T-4414: this is now the BATCHING/rate-limit seam (owner design
    decision 2026-09-11, T-4410's epic). It never unconditionally spawns
    a new detached child any more -- under `_window_lock`, it registers
    `(ticket_id, final_id, commit_sha, target_branch)` against the
    persisted window state (`_decide_land_registration`) and only spawns
    when that decision is `"open"` (no worker currently alive for this
    root). A `"join"`/`"defer"` decision returns `Ok(-1)` -- a
    deliberately non-real pid sentinel meaning "no new process; this
    land's coverage rides an existing worker's batch" -- since every
    existing caller of this function (`_land_cmd.py`) already ignores
    the returned pid entirely, this is not a signature-breaking change
    for either caller in this repo, only for a future one that starts
    reading it."""
    from frob.process import exec_enabled
    from frob.tickets._evidence import record_rapid_debt

    record_rapid_debt(root, ticket_id, "post-land-unscoped-sweep-deferred")
    _commit_rapid_debt(root, ticket_id)

    if not exec_enabled():
        _log.warning(
            "rapid sweep: %s exec is disabled -- the deferred unscoped "
            "sweep for %s was NOT spawned; that commit stays unverified "
            "(recorded in rapid-debt.jsonl), run `frob check` by hand",
            final_id,
            commit_sha[:12],
        )
        return Err(RapidSweepError.SpawnRefused)

    land = {
        "ticket_id": ticket_id,
        "final_id": final_id,
        "commit_sha": commit_sha,
        "target_branch": target_branch,
    }
    with _window_lock(root):
        state = _read_window_state(root)
        action, new_state = _decide_land_registration(state, land, now=time.time())
        if action != "open":
            _write_window_state(root, new_state)
            description = (
                "joined the pending window"
                if action == "join"
                else "deferred to the next window (a sweep is running now)"
            )
            _log.info(
                "rapid sweep: %s window: land %s -- batch now %d land(s), "
                "worker pid=%s, no new sweep process spawned",
                final_id,
                description,
                len(new_state["pending_lands"]),
                new_state.get("worker_pid"),
            )
            return Ok(-1)
        # "open": no worker is alive for this root -- spawn one and
        # record its pid in the SAME state write that opened the window,
        # so no other land can also conclude "open" before this pid is
        # visible.
        spawned = _spawn_sweep_worker(root, final_id, commit_sha, target_branch)
        if spawned.is_err:
            # T-4414: a failed spawn must not leave the window state
            # claiming a worker is alive that never started -- revert to
            # idle-with-nothing-pending's PREDECESSOR shape by simply not
            # persisting `new_state` at all; the land is still recorded
            # in `rapid-debt.jsonl` above, so it stays visibly unswept
            # rather than silently believed covered by a phantom worker.
            _log.error(
                "rapid sweep: %s window: opening a new window's worker "
                "spawn failed -- window state left unchanged (idle); "
                "commit %s stays unverified (recorded in rapid-debt.jsonl)",
                final_id,
                commit_sha[:12],
            )
            return spawned
        new_state["worker_pid"] = spawned.danger_ok
        _write_window_state(root, new_state)
        window_seconds = _sweep_window_seconds(root)
        _log.info(
            "rapid sweep: %s window OPENED (worker pid=%d, closes in "
            "%.0fs) -- 1 land pending so far; any land that lands before "
            "then joins this same sweep instead of spawning its own",
            final_id,
            spawned.danger_ok,
            window_seconds,
        )
        return spawned


# frob:ticket T-4414
def _spawn_sweep_worker(
    root: Path,
    final_id: str,
    commit_sha: str,
    target_branch: str | None,
) -> Result[int, RapidSweepError]:
    """T-4414: the exact detached-`Popen` body `spawn_deferred_post_land_
    sweep` used to run unconditionally per land -- extracted unchanged so
    it can be called from exactly ONE branch of that function's window
    decision (`"open"`) instead of on every call. `final_id`/`commit_sha`
    only seed the FIRST window's `sweep-async` argv and log filename; the
    worker itself (`_sweep_async`) reads the actual batch (which may grow
    past this one land before the window closes) from the persisted
    window state, not from these argv values."""
    log_dir = root / _LOG_DIR_REL
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{final_id}-{commit_sha[:12]}.log"
    argv = [
        sys.executable,
        "-m",
        "frob",
        "ticket",
        "sweep-async",
        final_id,
        "--commit",
        commit_sha,
    ]
    try:
        with log_path.open("w", encoding="utf-8") as handle:
            proc = subprocess.Popen(  # noqa: S603
                argv,
                cwd=root,
                env=_detached_sweep_env(root, target_branch=target_branch),
                stdout=handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
    except OSError as exc:
        _log.error(
            "rapid sweep: %s deferred sweep spawn failed: %s -- commit %s "
            "stays unverified (recorded in rapid-debt.jsonl)",
            final_id,
            exc,
            commit_sha[:12],
        )
        return Err(RapidSweepError.SpawnRefused)

    _log.info(
        "rapid sweep: %s post-land unscoped sweep DEFERRED to detached "
        "pid=%d (log: %s) -- land is not waiting on it; new errors become "
        "a filed bug ticket, never a revert of the published commit",
        final_id,
        proc.pid,
        log_path,
    )
    return Ok(proc.pid)


#: T-2261: minimum HEAD-commit age before an idle worktree is swept
#: automatically. Matches the measured precedent in T-2261's own body
#: (`frob worktree sweep --dry-run --min-age 4`); a lower floor risks
#: sweeping a worktree between two active bursts of the same agent, a
#: higher one lets sprawl accumulate for longer between lands.
_AUTO_SWEEP_MIN_AGE_HOURS = 4.0


# frob:doc \
# docs/modules/tickets-verify-sweep.md#automatic-stale-worktree-reclamation-t-2261
# frob:ticket T-2261
def sweep_stale_worktrees_after_land(root: Path) -> None:
    """T-2261: reclaim stale agent worktrees automatically, hooked into
    the SAME detached, off-critical-path child `spawn_deferred_post_land_
    sweep` already spawns per land (`_sweep_async`, below) -- never inside
    the land itself (T-1684 deliberately moved post-land work off that
    critical path; adding a filesystem sweep back onto it would
    re-lengthen exactly what that work shortened). Measured before this
    ticket: 107 worktrees / 67GB accumulated because the only existing
    caller of `sweep_worktrees` was `frob worktree sweep`, a command an
    operator has to remember to run (`src/frob/app/ticket_runner/
    _land_cmd.py` printed 'run `frob worktree sweep` later to clean it
    up' and nothing ever acted on it).

    Calls `sweep_worktrees` with `dry_run=False`, `force=False` (T-1739's
    override is NEVER used by this automatic path -- a scheduled sweep
    must not bypass the liveness gate), and `min_age_hours=
    _AUTO_SWEEP_MIN_AGE_HOURS`, reusing its own five keep verdicts
    (`kept:live`/`kept:dirty`/`kept:unlanded`/`kept:lease`/`kept:age`)
    unmodified -- this function REUSES `sweep_worktrees`'s decisions, it
    does not reimplement or narrow them. Every verdict is logged (removed
    or kept, with its reason) so a later operator can reconstruct what
    happened; a fully-failed sweep (`sweep_worktrees` itself returning
    `Err`, e.g. `root` is not a git repository) is logged and swallowed --
    this runs in a detached child nobody is waiting on, and must never
    raise back into `_sweep_async`."""
    from frob.tickets._worktree_sweep import sweep_worktrees

    result = sweep_worktrees(
        root, min_age_hours=_AUTO_SWEEP_MIN_AGE_HOURS, dry_run=False, force=False
    )
    if result.is_err:
        _log.warning(
            "rapid sweep: automatic worktree sweep failed: %s",
            result.danger_err.value,
        )
        return
    verdicts = result.danger_ok
    removed = [v for v in verdicts if v.verdict == "removed"]
    for verdict in verdicts:
        _log.info(
            "rapid sweep: worktree %s -> %s%s",
            verdict.path,
            verdict.verdict,
            f" ({verdict.detail})" if verdict.detail else "",
        )
    _log.info(
        "rapid sweep: automatic worktree sweep removed %d of %d worktree(s)",
        len(removed),
        len(verdicts),
    )


# frob:doc docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690
# frob:ticket T-1690
# frob:waive COV007 reason="docs/modules/tickets-verify-sweep.md's Symbolic \
# attribution (T-1690) section individually frob:describes this symbol by its own \
# qualified path -- a deliberate per-symbol anchor, not a duplicate"
def _attribute_new_findings(
    root: Path, pairs: Sequence[tuple[str, str] | tuple[str, str, int]]
):  # noqa: ANN201 -- dict[tuple[str, str], Attribution], deferred-import type
    """T-1690 tier-2: attribute each `(rule, file)` (or, when a caller has
    a line number, `(rule, file, line)`) pair in `pairs` to the single
    durable `VerifyQueueEntry` (if any) whose `touched_symbols`
    graph-reaches it, using the CURRENT verify queue as the batch (the set
    of lands recorded since the last watermark advance -- exactly the
    commits this red sweep could have been caused by). Returns `{}`
    (attribution unavailable for every pair, never a partial mapping) when
    the queue cannot be read or the reference graph cannot be built --
    `_file_regression_ticket` treats an empty mapping as "no attribution
    information", not "everything unattributed", falling back to filing
    the whole set exactly as it did before this ticket."""
    from frob.verify import attribute_batch, queue_status

    queue = queue_status(root)
    if queue.is_err:
        _log.warning(
            "rapid sweep: attribution: verify queue unreadable (%s) -- "
            "filing without attribution",
            queue.danger_err,
        )
        return {}
    batch = queue.danger_ok
    if not batch:
        _log.info(
            "rapid sweep: attribution: verify queue is empty -- filing "
            "without attribution"
        )
        return {}
    attributed = attribute_batch(root, pairs, batch)
    if attributed.is_err:
        _log.warning(
            "rapid sweep: attribution: reference graph unavailable (%s) -- "
            "filing without attribution",
            attributed.danger_err,
        )
        return {}
    return {(a.rule_id, a.file): a for a in attributed.danger_ok}


# frob:doc docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690
# frob:ticket T-1690
# tests/unit/rapid_sweep_suite/test_commit.py::TestTicketIsOpen.test_done_ticket_is_not_open  # noqa: E501
# tests/unit/rapid_sweep_suite/test_commit.py::TestTicketIsOpen.test_missing_ticket_is_not_open  # noqa: E501
# frob:waive COV007 reason="docs/modules/tickets-verify-sweep.md's Symbolic \
# attribution (T-1690) section individually frob:describes this symbol by its own \
# qualified path -- a deliberate per-symbol anchor, not a duplicate"
def _ticket_is_open(root: Path, ticket_id: str) -> bool:
    """`True` when `ticket_id` still exists and is NOT `done`/`dropped` --
    the "owning ticket still open" half of T-1690's filing rule. A ticket
    that cannot be loaded at all (queue read failure, id not found)
    counts as NOT open: attribution should never suppress a real
    regression's own ticket because the owning ticket became
    unreadable."""
    from frob.tickets import load_queue
    from frob.tickets._models import TicketState

    queue = load_queue(root)
    if queue.is_err:
        return False
    ticket = queue.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        return False
    return ticket.state not in (TicketState.DONE, TicketState.DROPPED)


# frob:doc docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690
# frob:ticket T-1690
# frob:ticket T-1791
# tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_unattributed_is_filed  # noqa: E501
# frob:waive COV007 reason="docs/modules/tickets-verify-sweep.md's Symbolic \
# attribution (T-1690) section documents several symbols under one section, not just a \
# public entry point -- the many-symbols- one-section convention this repo already \
# accepted for vet.md (T-2810 declined to touch it), not a T-2810-shaped duplicate"
def _partition_findings_by_attribution(
    root: Path,
    final_id: str,
    pairs: list[tuple[str, str]],
    attributions: dict,  # noqa: ANN401 -- dict[tuple[str, str], Attribution], deferred-import type
) -> tuple[list[tuple[str, str]], list[str]]:
    """T-1690: split `pairs` into `(unfiled_pairs, attribution_lines)`
    (ARCH001 split of `_file_regression_ticket`, which was previously one
    122-line function). `unfiled_pairs` is every pair that still needs its
    own regression ticket -- unattributed, or attributed to a
    closed/dropped ticket's commit; a pair attributed to a STILL-OPEN
    ticket is left out of it entirely (logged instead, at INFO, once per
    owning ticket) since it already has a home. `attribution_lines` is the
    human-readable audit trail for EVERY pair with attribution
    information (including the already-open ones, so a caller that wants
    the full picture -- not just what got filed -- still has it), in the
    same order `pairs` was given.

    `attributions` is computed ONCE by the caller (`_file_regression_
    ticket`, via `_attribute_new_findings`) and passed in here rather than
    recomputed -- T-1791 needs that same mapping a second time (to raise
    quarantine over the whole red batch), and a second `attribute_batch`
    call would mean a second reference-graph build for no new
    information."""
    unfiled_pairs: list[tuple[str, str]] = []
    attribution_lines: list[str] = []
    already_open: dict[str, int] = {}
    for rule, file in pairs:
        attr = attributions.get((rule, file))
        if attr is None:
            unfiled_pairs.append((rule, file))
            continue
        if attr.status == "attributed" and _ticket_is_open(root, attr.ticket_id):
            already_open[attr.ticket_id] = already_open.get(attr.ticket_id, 0) + 1
            attribution_lines.append(
                f"- {rule}  {file}  -> attributed to {attr.ticket_id} "
                f"(commit {attr.commit_sha[:12]}, already open -- not "
                f"re-filed) via {' -> '.join(attr.reachability_path)}"
            )
            continue
        unfiled_pairs.append((rule, file))
        if attr.status == "attributed":
            attribution_lines.append(
                f"- {rule}  {file}  -> attributed to {attr.ticket_id} "
                f"(commit {attr.commit_sha[:12]}, already closed/dropped -- "
                f"filed below) via {' -> '.join(attr.reachability_path)}"
            )
        else:
            attribution_lines.append(
                f"- {rule}  {file}  -> UNATTRIBUTED ({attr.reason}); "
                f"candidate commits: {list(attr.candidate_commits)}"
            )

    if already_open:
        _log.info(
            "rapid sweep: %s: %d finding(s) already attributed to still-"
            "open ticket(s) %s -- not re-filed",
            final_id,
            sum(already_open.values()),
            sorted(already_open),
        )
    return unfiled_pairs, attribution_lines


#: T-1847: rule ids whose shape is consistent with cold-worktree
#: native-extension noise (a `ty check`/import-resolution failure that
#: fires on a fresh worktree before `frob natives build`/`make core` has
#: run) rather than a genuine regression. Deliberately narrow -- widening
#: this set silently swallows real findings, so only the one rule id the
#: T-1697 incident actually observed is listed; add another only against a
#: second confirmed incident, never speculatively.
_NATIVE_EXTENSION_ADJACENT_RULE_IDS = frozenset({"unresolved-import"})


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
# frob:ticket T-1847
# frob:waive COV007 reason="docs/modules/tickets-verify-sweep.md's Quarantine circuit \
# breaker (T-1693) section individually frob:describes this symbol by its own \
# qualified path -- a deliberate per-symbol anchor, not a duplicate"
def _warm_tree_clears_unattributed_native_noise(root: Path, rule: str, attr) -> bool:  # noqa: ANN001 -- Attribution | None, deferred-import type
    """T-1847: `True` when `(rule, attr)` matches the cold-worktree
    native-extension-noise shape (UNATTRIBUTED, rule in
    `_NATIVE_EXTENSION_ADJACENT_RULE_IDS`) AND a re-check RIGHT NOW shows
    every declared native imports cleanly. That combination means the
    finding's own likely cause -- a native extension not yet built when
    the sweep's check ran -- no longer holds: the tree has since warmed
    (another sweep/build finished, or this is simply a slightly later
    point in the same cold-worktree window), so treating this one finding
    as durable regression signal would just be re-reporting environment
    staleness. `attr` is the `Attribution | None` for the pair; only a
    genuinely UNATTRIBUTED pair (no attribution info, or `attr.status !=
    "attributed"`) is eligible -- an attributed finding already has a real
    commit behind it and this warm re-check is never allowed to override
    that.

    If any declared native is STILL unimportable right now, this returns
    `False` -- that is not transient noise, it is a still-broken
    environment, and the raise proceeds exactly as before this ticket."""
    if rule not in _NATIVE_EXTENSION_ADJACENT_RULE_IDS:
        return False
    if attr is not None and attr.status == "attributed":
        return False
    from frob.strata._native_staleness import unimportable_natives

    broken = unimportable_natives(root)
    if broken:
        _log.debug(
            "rapid sweep: quarantine warm-tree re-check: %s still broken "
            "(%s) -- treating %r as real, not cold-worktree noise",
            rule,
            [s.name for s in broken],
            rule,
        )
        return False
    return True


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
# frob:ticket T-1847
# frob:ticket T-2604
# frob:waive COV007 reason="docs/modules/tickets-verify-sweep.md's Quarantine circuit \
# breaker (T-1693) section documents several symbols under one section, not just a \
# public entry point -- the many-symbols- one-section convention this repo already \
# accepted for vet.md (T-2810 declined to touch it), not a T-2810-shaped duplicate"
# frob:ticket T-4607
def _log_directory_shaped_pairs_dropped(
    final_id: str, directory_shaped_pairs: list[tuple[str, str]]
) -> None:
    """`_filter_pairs_for_quarantine_raise`'s own ARCH001 split: logs why
    `directory_shaped_pairs` (T-4607) was dropped from the quarantine
    raise, when non-empty -- a directory-shaped identity (e.g. DOC012's
    own `file="docs/commands/"`) never appears as a changed FILE in any
    commit's diff, so file-based attribution can never resolve it and it
    would re-trip the quarantine circuit breaker on every sweep that
    still has any doc drift at all. A no-op on an empty list. Still filed
    as a regression ticket by the caller's own caller (real doc drift,
    not suppressed) -- this only keeps it off the dispose queue."""
    if not directory_shaped_pairs:
        return
    _log.info(
        "rapid sweep: %s: %d directory-shaped (rule, file) pair(s) "
        "(e.g. DOC012's docs/commands/) dropped from the quarantine "
        "raise -- a directory never matches a commit's changed-file "
        "set, so attribution can never resolve it and it would "
        "re-raise quarantine on every sweep (still filed as a "
        "regression ticket, just not sent to the dispose queue)",
        final_id,
        len(directory_shaped_pairs),
    )


def _filter_pairs_for_quarantine_raise(
    root: Path,
    final_id: str,
    pairs: list[tuple[str, str]],
    attributions: dict,  # noqa: ANN401 -- dict[tuple[str, str], Attribution], deferred-import type
) -> list[tuple[str, str]]:
    """`_raise_quarantine_for_red_batch`'s own ARCH001 split -- narrow
    `pairs` down to what should actually reach the quarantine dispose
    queue, applying two independent filters and logging what each one
    drops.

    T-1847: a pair matching the cold-worktree native-extension-noise
    shape (UNATTRIBUTED, `unresolved-import`) whose warm re-check now
    shows every native importing cleanly is dropped -- it is still filed
    as a regression ticket by the caller's own caller, this only changes
    what reaches the quarantine dispose queue.

    T-2604: a pair attributed to a ticket that is STILL OPEN
    (`_ticket_is_open`, the exact predicate the filing path's own
    `_partition_findings_by_attribution` already uses for the identical
    question) is also dropped -- such a finding already has a home and
    someone actively working it, so tripping the quarantine circuit
    breaker (T-1693: turns off deferred landing repo-wide) a second time
    over the same identity only pays the whole fleet's synchronous-land
    cost for no new information. This does NOT affect filing at all --
    `_partition_findings_by_attribution` already skipped re-filing it
    upstream. A pair attributed to a CLOSED/DROPPED ticket, or with no
    attribution at all, is left untouched by this filter and still
    reaches the raise -- both are real, unowned-or-reopened regression
    signal, exactly what quarantine exists to catch."""
    open_ticket_pairs = [
        (rule, file)
        for rule, file in pairs
        if (attr := attributions.get((rule, file))) is not None
        and attr.status == "attributed"
        and _ticket_is_open(root, attr.ticket_id)
    ]
    # frob:ticket T-4607
    directory_shaped_pairs = [
        (rule, file)
        for rule, file in pairs
        if (rule, file) not in open_ticket_pairs and file.endswith("/")
    ]
    quarantine_pairs = [
        (rule, file)
        for rule, file in pairs
        if (rule, file) not in open_ticket_pairs
        and (rule, file) not in directory_shaped_pairs
        and not _warm_tree_clears_unattributed_native_noise(
            root, rule, attributions.get((rule, file))
        )
    ]
    _log_directory_shaped_pairs_dropped(final_id, directory_shaped_pairs)
    if open_ticket_pairs:
        _log.info(
            "rapid sweep: %s: %d finding(s) already attributed to still-"
            "open ticket(s) dropped from the quarantine raise (still "
            "filed as a regression ticket -- see "
            "_partition_findings_by_attribution)",
            final_id,
            len(open_ticket_pairs),
        )
    dropped = (
        len(pairs)
        - len(quarantine_pairs)
        - len(open_ticket_pairs)
        - len(directory_shaped_pairs)
    )
    if dropped:
        _log.info(
            "rapid sweep: %s: warm-tree re-check cleared %d cold-worktree "
            "native-extension finding(s) from the quarantine raise (still "
            "filed as a regression ticket, just not sent to the dispose "
            "queue)",
            final_id,
            dropped,
        )
    return quarantine_pairs


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
# frob:ticket T-1791
# frob:ticket T-1847
# frob:ticket T-2604
# frob:waive COV007 reason="docs/modules/tickets-verify-sweep.md's Quarantine circuit \
# breaker (T-1693) section individually frob:describes this symbol by its own \
# qualified path -- a deliberate per-symbol anchor, not a duplicate"
def _raise_quarantine_for_red_batch(
    root: Path,
    final_id: str,
    pairs: list[tuple[str, str]],
    attributions: dict,  # noqa: ANN401 -- dict[tuple[str, str], Attribution], deferred-import type
) -> None:
    """T-1791: the batch-verification driver's missing half -- `frob.
    verify._quarantine.raise_quarantine` existed (T-1693) and the land
    path already enforces it (T-1693's own `_land_cmd._quarantine_
    override_ceilings`), but nothing ever CALLED it. `_file_regression_
    ticket` is the shared "a red batch verification came back" seam both
    T-1684's per-land sweep and T-1688's coalescing worker call through,
    so wiring the raise here covers both drivers from one call site.

    `batch_commit_shas` comes from the CURRENT verify queue (`frob.
    verify.queue_status`) -- the exact set of lands this red result could
    have been caused by, same batch `_attribute_new_findings` itself
    reads. An empty or unreadable queue means there is nothing to name as
    the raising batch (a red result with no queued lands to blame is not
    this ticket's scope to invent an answer for) -- logged and skipped,
    never a raise with a fabricated batch. A `raise_quarantine` failure
    (`QuarantineError.EmptyFindings`, structurally unreachable here since
    `pairs` is always non-empty by the caller's own contract, or a write
    failure) is logged at ERROR and swallowed: the regression ticket
    filing this function's caller does next must never be blocked by the
    quarantine flag failing to persist -- the filed ticket is still the
    primary, durable record of what went wrong.

    T-1847/T-2604: before naming the batch, every pair is narrowed by
    `_filter_pairs_for_quarantine_raise` (this function's own ARCH001
    split) -- see that function's docstring for the two independent
    filters it applies (cold-worktree native noise, and a still-open
    owning ticket). If narrowing leaves nothing, the raise is skipped
    altogether and logged at INFO, same "nothing to name" shape as the
    empty-queue branch below."""
    from frob.verify import queue_status
    from frob.verify._quarantine import raise_quarantine

    queue = queue_status(root)
    if queue.is_err or not queue.danger_ok:
        _log.warning(
            "rapid sweep: %s: red batch at %s but the verify queue is "
            "empty/unreadable -- no batch to name, quarantine NOT raised",
            final_id,
            pairs,
        )
        return

    quarantine_pairs = _filter_pairs_for_quarantine_raise(
        root, final_id, pairs, attributions
    )
    if not quarantine_pairs:
        _log.info(
            "rapid sweep: %s: every finding in this red batch cleared as "
            "cold-worktree native-extension noise or still-open-ticket "
            "attribution -- quarantine NOT raised",
            final_id,
        )
        return

    batch_commit_shas = tuple(e.commit_sha for e in queue.danger_ok)
    findings = _quarantined_findings_from_attributions(quarantine_pairs, attributions)
    raised = raise_quarantine(
        root, batch_commit_shas=batch_commit_shas, findings=findings
    )
    if raised.is_err:
        _log.error(
            "rapid sweep: %s: raise_quarantine failed (%s) for batch %s -- "
            "the regression ticket this red result files is still the "
            "durable record; quarantine flag may be stale until the next "
            "red batch retries the raise",
            final_id,
            raised.danger_err,
            batch_commit_shas,
        )


# frob:ticket T-1791
def _quarantined_findings_from_attributions(
    pairs: list[tuple[str, str]],
    attributions: dict,  # noqa: ANN401 -- dict[tuple[str, str], Attribution], deferred-import type
) -> tuple:  # noqa: ANN401 -- tuple[QuarantinedFinding, ...], deferred-import type
    """Build one `QuarantinedFinding` per `pairs` entry from `attributions`
    (`_raise_quarantine_for_red_batch`'s own ARCH001 split) -- `commit_sha`/
    `ticket_id` are set only for a pair whose `Attribution.status ==
    "attributed"`; an unattributed or unmapped pair gets `None` for both
    (never a guess), matching `QuarantinedFinding`'s own "both `None` for
    an unattributed finding" contract."""
    from frob.verify._quarantine import QuarantinedFinding

    findings = []
    for rule, file in pairs:
        attr = attributions.get((rule, file))
        attributed = attr is not None and attr.status == "attributed"
        findings.append(
            QuarantinedFinding(
                rule_id=rule,
                file=file,
                line=attr.line if attr is not None else None,
                commit_sha=attr.commit_sha if attributed else None,
                ticket_id=attr.ticket_id if attributed else None,
            )
        )
    return tuple(findings)


# frob:ticket T-1935
def _spawn_true_count_check(root: Path, budget: int):  # noqa: ANN201 -- Result[CompletedProcess, ...] | None sentinel via caller, deferred import
    """T-1935: spawn the independent `frob check --budget --json`
    `_true_finding_count_for_identities` needs (ARCH001 split of that
    function). Returns the spawned `subprocess.CompletedProcess` on
    success, or `None` on any of the three unmeasurable outcomes (timeout,
    spawn refused, decode failure) -- each already logged here at WARNING
    with the specific reason, so the caller only has to check for `None`
    and degrade.

    T-4105: this runs inside the DETACHED `sweep-async` process (see
    `_detached_sweep_env`'s own T-4105 paragraph for why this is the one
    site in this ticket that reads a base via `os.environ` rather than an
    explicit argument -- crossing an actual OS-process boundary this
    module cannot add a new `sweep-async` CLI flag for without touching
    `_cli_parsers/`, out of scope). `FROB_LAND_TARGET_BRANCH`, set by
    `_detached_sweep_env` only when the deferring land had an explicit
    target branch, is forwarded here as `--base`; unset (the ordinary
    main-line-land case) omits `--base` entirely, unchanged from
    pre-T-4105 behavior."""
    import os as _os
    import subprocess as _subprocess

    from frob.app.ticket_runner._verify import _python_for_tree
    from frob.process._guard import guarded_subprocess_run

    _argv = [
        _python_for_tree(root),
        "-m",
        "frob",
        "check",
        "--budget",
        str(budget),
        "--json",
    ]
    _target_branch = _os.environ.get("FROB_LAND_TARGET_BRANCH")
    if _target_branch:
        _argv += ["--base", _target_branch]
    try:
        guarded = guarded_subprocess_run(
            _argv,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=budget + 60,
            check=False,
        )
    except _subprocess.TimeoutExpired:
        _log.warning(
            "rapid sweep: T-1935 true-finding-count re-measure timed out "
            "after %ds -- reporting the identity count alone",
            budget + 60,
        )
        return None
    if guarded.is_err:
        _log.warning(
            "rapid sweep: T-1935 true-finding-count re-measure spawn "
            "refused (%s) -- reporting the identity count alone",
            guarded.danger_err,
        )
        return None
    return guarded.danger_ok


# frob:ticket T-1935
# frob:ticket T-2006
def _matching_error_diagnostics(
    root: Path, pairs: frozenset[tuple[str, str]], budget: int | None
) -> list[dict] | None:
    """T-2006 (ARCH001 split, extracted from the pre-T-2006 body of
    `_true_finding_count_for_identities`): the shared low-level fetch
    both that function (T-1935, raw per-finding count) and
    `_identities_still_reproducing` (T-2006, which IDENTITIES are still
    live) build on -- ONE independent `frob check --budget --json` spawn
    (`_spawn_true_count_check`) and parse, never two. Returns every
    `severity == "error"` diagnostic dict whose `(code, file)` is in
    `pairs`, or `None` on any unmeasurable outcome -- never an empty list
    standing in for "could not measure". T-2715: `budget=None` derives the
    ceiling from `root`'s own measured stage timing, falling back to
    `_TRUE_COUNT_BUDGET_S` (see `_derive_post_land_sweep_budget_s`)."""
    from frob.app._check_chunking import _derive_post_land_sweep_budget_s
    from frob.app.ticket_runner._verify import (
        _incomplete_tool_results,
        _parse_check_json,
    )

    if budget is None:
        budget = _derive_post_land_sweep_budget_s(root, default=_TRUE_COUNT_BUDGET_S)

    proc = _spawn_true_count_check(root, budget)
    if proc is None:
        return None
    data = _parse_check_json(proc.stdout)
    if data is None:
        _log.warning(
            "rapid sweep: true-finding re-measure produced unparsable "
            "output -- treating as unmeasurable"
        )
        return None
    results = data.get("results")
    if not isinstance(results, list):
        return None
    # T-2521: same structural completeness check `_verify.py::_parse_
    # error_findings_from_json` applies to the deferred-sweep path --
    # a FAILED tool result with no error diagnostic (a crashed/malformed
    # ruff-check, e.g.) must never read as "measured, found nothing" on
    # THIS scoped doable-time path either; both call sites share the one
    # detector rather than each re-deriving it.
    incomplete = _incomplete_tool_results(results)
    if incomplete:
        _log.warning(
            "rapid sweep: true-finding re-measure had %d tool result(s) "
            "(%s) that exited nonzero with no error diagnostic -- "
            "treating as unmeasurable (T-2521)",
            len(incomplete),
            ", ".join(incomplete),
        )
        return None
    matched: list[dict] = []
    for r in results:
        if not isinstance(r, dict):
            continue
        for d in r.get("diagnostics", ()):
            if not isinstance(d, dict) or d.get("severity") != "error":
                continue
            if (d.get("code") or "", d.get("file") or "") in pairs:
                matched.append(d)
    return matched


# frob:ticket T-1935
def _true_finding_count_for_identities(
    root: Path, pairs: frozenset[tuple[str, str]], budget: int | None = None
) -> int | None:
    """T-1935: the TRUE per-finding count restricted to `pairs` -- as
    opposed to `len(pairs)`, which is only ever a count of DISTINCT
    `(rule, file)` IDENTITIES, never a raw finding count (this module's
    docstring). WITHOUT deduping by identity -- so several findings
    sharing one `(rule, file)` pair are each counted, unlike `_land_cmd.
    _unscoped_error_findings`'s own identity set.

    Returns `None` (never a wrong number) when unmeasurable (see
    `_matching_error_diagnostics`). The caller degrades gracefully to
    reporting the identity count alone when this returns `None`.

    Deliberately a SECOND check spawn, paid only by
    `_file_regression_ticket`'s red-batch path (a clean sweep never calls
    this) -- see the module docstring for why that does not reopen T-
    1684's "one check per land" cost concern."""
    matched = _matching_error_diagnostics(root, pairs, budget)
    if matched is None:
        return None
    return len(matched)


# frob:ticket T-2006
def _identities_still_reproducing(
    root: Path, pairs: frozenset[tuple[str, str]], budget: int | None = None
) -> frozenset[tuple[str, str]] | None:
    """T-2006: which of `pairs` (rule, file) identities STILL reproduce
    right now, restricted to exactly `pairs` (never a full unscoped
    sweep) -- what `revalidate_dispatchable_sweep_tickets` needs to
    decide which candidate sweep-filed tickets are resolved vs. still
    live. `None` on the same unmeasurable conditions `_matching_error_
    diagnostics` returns `None` for -- an unmeasurable re-check must
    never be read as "resolved"."""
    matched = _matching_error_diagnostics(root, pairs, budget)
    if matched is None:
        return None
    return frozenset((d.get("code") or "", d.get("file") or "") for d in matched)


# frob:ticket T-2089
def _tree_state_key(root: Path) -> str | None:
    """T-2089: a cheap signature of `root`'s current tree state -- the
    committed HEAD sha plus a hash of `git status --porcelain`'s output
    (which changes the instant ANY file starts/stops differing from HEAD,
    without this function itself hashing any file's content) -- so two
    `revalidate_dispatchable_sweep_tickets` calls against the exact SAME
    tree state can be told apart from two calls where the tree genuinely
    moved in between, cheaply (two git spawns, not a full check).

    `None` when either git call fails -- not a git repo (a test's
    `tmp_path`), or a spawn failure. Callers must treat `None` as "cache
    unavailable this call", never as a cache HIT: a git failure can only
    ever fall back to the pre-T-2089 uncached behavior, never produce a
    stale or wrong verdict."""
    import hashlib

    from frob.gitio import run_argv

    head = run_argv(["git", "-C", str(root), "rev-parse", "HEAD"])
    if head.is_err or head.danger_ok.returncode != 0:
        return None
    status = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if status.is_err or status.danger_ok.returncode != 0:
        return None
    status_digest = hashlib.sha256(status.danger_ok.stdout.encode("utf-8")).hexdigest()
    return f"{head.danger_ok.stdout.strip()}:{status_digest}"


# frob:ticket T-2165
def _identity_scoped_state_key(root: Path, pairs: frozenset[tuple[str, str]]) -> str:
    """T-2165: `_tree_state_key`'s replacement for
    `_reproducing_identities_cached`'s cache key -- narrowed from "has
    the WHOLE tree's HEAD+status changed at all" to "has anything
    relevant to THESE SPECIFIC (rule, file) `pairs` changed", per this
    ticket's own body.

    `_tree_state_key` (committed HEAD sha + a `git status --porcelain`
    digest) was CORRECTLY WIRED but too narrow to ever hit under
    concurrent-land load: HEAD advances on essentially every land in a
    busy multi-agent session, so two `revalidate_dispatchable_sweep_
    tickets` calls a minute apart against a tree that is IDENTICAL from
    THIS candidate set's own point of view (no file any of `pairs`
    names has changed) still got different keys and the cache could
    never hit (T-2106's own Done report measured this live: a doable-
    time re-verification reported UNMEASURABLE rather than served from
    cache, on a tree that had almost certainly not moved relative to the
    candidate files).

    Reads the CURRENT on-disk content of every distinct file named in
    `pairs` directly (never `git show`/blob lookups) and hashes it --
    this is deliberately content-based, not git-state-based, so it is
    correct whether the file's current content is committed or still
    sitting uncommitted in the working tree: an agent's own uncommitted
    fix to one of the revalidated files changes that file's content,
    which changes this key, which correctly invalidates the cache for
    exactly that candidate set (the "must not mask a genuine fix"
    requirement this ticket's own body calls out, the same class of
    care T-1436's gate-cache staleness bug paid for elsewhere). A file
    that no longer exists (deleted, or renamed away) hashes to a stable
    sentinel string rather than raising -- "this file is now absent" is
    itself a real, cache-relevant state change, and must produce a
    DIFFERENT key from when the file existed, not crash the caller.

    Never `None`: unlike `_tree_state_key` (which can fail if `root` is
    not a git repository at all, or a git spawn errors), this function
    does no git spawn and reads plain files -- an unreadable individual
    file degrades to its own sentinel entry, never a total failure, so
    every call produces a real, usable key. Cost is O(number of DISTINCT
    files named in `pairs`), always small in practice: `pairs` is a
    doable-time candidate identity set, not a full-repo sweep."""
    import hashlib

    _ABSENT_SENTINEL = "<absent-or-unreadable>"
    files = sorted({file for _, file in pairs})
    parts: list[str] = []
    for file in files:
        try:
            content = (root / file).read_bytes()
        except OSError:
            parts.append(f"{file}:{_ABSENT_SENTINEL}")
            continue
        parts.append(f"{file}:{hashlib.sha256(content).hexdigest()}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _revalidation_cache_path(root: Path) -> Path:
    """`.frob/doable-revalidation-cache.json` for a checkout rooted at
    `root` -- T-2089's doable-time revalidation cache file."""
    return root / _REVALIDATION_CACHE_REL


# frob:ticket T-2089
class _UnmeasurableCacheSentinel:
    """T-5135 (H2): a dedicated, uniquely-typed sentinel (rather than a
    bare string or `object()`) so `ty`/mypy can narrow `_read_
    revalidation_cache`'s return type by `isinstance`/identity check --
    returned when the cached entry records a PRIOR re-check that was
    itself unmeasurable (timed out), distinct from `None` (no usable
    cache, caller must re-measure) so `_reproducing_identities_cached`
    can recognize "we already tried and could not measure this" and skip
    the doomed re-spawn entirely, while still never treating
    "unmeasurable" as "resolved" (T-1983's rule): the caller still
    returns `None` (nothing dropped), it just does so with 0 spawns
    instead of re-paying the 20s budget every call."""


#: The one process-lifetime instance of `_UnmeasurableCacheSentinel` --
#: compared by identity (`is`), never constructed a second time.
_UNMEASURABLE_CACHE_SENTINEL = _UnmeasurableCacheSentinel()


def _read_revalidation_cache(
    root: Path, tree_key: str, pairs: frozenset[tuple[str, str]]
) -> tuple[frozenset[tuple[str, str]], float] | _UnmeasurableCacheSentinel | None:
    """T-2089: the last cached `(reproducing, age_seconds)` for exactly
    `(tree_key, pairs)`, `_UNMEASURABLE_CACHE_SENTINEL` (T-5135, H2) when
    the last re-check at this exact tree state/identity set was itself
    UNMEASURABLE (timed out) and that negative outcome is still within
    `_REVALIDATION_CACHE_TTL_S`, or `None` when there is no USABLE cache
    entry -- absent, corrupt, a different tree state, a different identity
    set (no superset/subset matching, exact only -- a caller re-checking a
    different candidate set always re-measures), or older than
    `_REVALIDATION_CACHE_TTL_S`. Every one of those is "cache miss, spawn
    for real", never a wrong or stale reuse."""
    path = _revalidation_cache_path(root)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("tree_key") != tree_key:
            return None
        cached_pairs = frozenset((str(r), str(f)) for r, f in raw.get("pairs", []))
        if cached_pairs != pairs:
            return None
        age_s = time.time() - float(raw["timestamp"])
        if age_s < 0 or age_s > _REVALIDATION_CACHE_TTL_S:
            return None
        if raw.get("unmeasurable", False):
            return _UNMEASURABLE_CACHE_SENTINEL
        reproducing = frozenset((str(r), str(f)) for r, f in raw.get("reproducing", []))
        return reproducing, age_s
    except Exception as exc:  # noqa: BLE001 -- json/shape, any corruption
        _log.warning(
            "rapid sweep: T-2089: revalidation cache %s unreadable (%s) -- "
            "treating as no cache, this call re-measures for real",
            path,
            exc,
        )
        return None


# frob:ticket T-2089
def _write_revalidation_cache(
    root: Path,
    tree_key: str,
    pairs: frozenset[tuple[str, str]],
    reproducing: frozenset[tuple[str, str]] | None,
) -> None:
    """T-2089: record `reproducing` (the outcome of a real, just-completed
    re-measure of `pairs` at `tree_key`) so the NEXT `revalidate_
    dispatchable_sweep_tickets` call against the same unchanged tree state
    and identity set can reuse it instead of spawning a second full check.
    T-5135 (H2): `reproducing=None` records the NEGATIVE outcome -- the
    re-check was itself UNMEASURABLE (timed out) -- with `unmeasurable:
    true`, so the next call recognizes "already tried, could not measure"
    via `_UNMEASURABLE_CACHE_SENTINEL` and skips the doomed re-spawn
    instead of repeating an unbounded-cost re-check that buys nothing;
    this still never treats unmeasurable as resolved, it only memoizes the
    NON-result under the same TTL as a successful measurement. Best-effort:
    a write failure is logged and swallowed -- a caller that just paid for
    a real measurement (or a real timeout) must never have ITS result
    blocked by a cache-write problem."""
    path = _revalidation_cache_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tree_key": tree_key,
        "pairs": sorted([rule, file] for rule, file in pairs),
        "reproducing": sorted([rule, file] for rule, file in reproducing)
        if reproducing is not None
        else [],
        "unmeasurable": reproducing is None,
        "timestamp": time.time(),
    }
    try:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except OSError as exc:
        _log.warning(
            "rapid sweep: T-2089: could not write revalidation cache %s (%s) "
            "-- the NEXT doable call will simply re-measure for real",
            path,
            exc,
        )


# frob:ticket T-2077
def _regression_count_line(
    unfiled_pairs: Sequence[tuple[str, str]], true_count: int | None
) -> str:
    """T-2058 (ARCH001 split of `_file_regression_ticket`): the T-1935
    identity-vs-finding-count caveat line for a filed regression ticket's
    body -- names the distinct-identity count always, and the
    independently re-measured true finding count only when that
    re-measurement itself succeeded (`None` means unmeasurable this run,
    never "zero")."""
    if true_count is None:
        return (
            "T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, "
            "not a raw finding count -- every finding sharing a (rule, "
            "file) pair collapses into ONE identity here (deliberately, "
            'so attribution and quarantine reason about "which files '
            'went red", not individual diagnostics). The true per-'
            "finding count could not be independently re-measured this "
            "run (spawn refused/timeout/unparsable) -- re-run `frob "
            "check` unscoped against the file(s) below for the exact "
            "count before treating this identity count as a "
            "completeness claim."
        )
    return (
        f"T-1935: this is a count of DISTINCT (rule, file) IDENTITIES "
        f"({len(unfiled_pairs)}), not a raw finding count -- every "
        "finding sharing a (rule, file) pair collapses into ONE "
        "identity here (deliberately, so attribution and quarantine "
        'reason about "which files went red", not individual '
        f"diagnostics). An independent re-measurement found "
        f"{true_count} actual finding(s) across those "
        f"{len(unfiled_pairs)} identit(ies)."
    )


# frob:ticket T-2077
def _build_regression_body(
    *,
    attribution_label: str,
    commit_sha: str,
    pairs: Sequence[tuple[str, str]],
    unfiled_pairs: Sequence[tuple[str, str]],
    count_line: str,
    attributed_ids: Sequence[str] | None,
    attribution_lines: Sequence[str],
) -> str:
    """T-2058 (ARCH001 split of `_file_regression_ticket`): assemble the
    filed regression ticket's full body -- the T-1684 preamble, the
    T-1935 count caveat, every `(rule, file)` identity, the T-2009
    multi-land disclosure (only when more than one land landed in the
    measured window), the T-1690 attribution audit trail (only when one
    was computable), and the standing rapid-profile closing note.
    Behavior-identical to the body this replaces -- only the assembly is
    now named and testable on its own."""
    body_lines = [
        f"The deferred post-land unscoped sweep (T-1684) for {attribution_label} "
        f"at commit {commit_sha} found {len(pairs)} new (rule, file) "
        "identit(ies) that were not present in the previous sweep's "
        "baseline.",
        "",
        count_line,
        "",
        _REGRESSION_IDENTITY_HEADING,
        "",
        *(f"- {rule}  {file}" for rule, file in unfiled_pairs),
    ]
    if attributed_ids and len(attributed_ids) > 1:
        body_lines += [
            "",
            f"T-2009: {len(attributed_ids)} lands ({', '.join(attributed_ids)}) "
            "landed between the previous sweep's baseline and the commit "
            "THIS sweep actually measured (the sweep is deliberately "
            "detached, off the land critical path -- T-1684 -- so other "
            "agents' lands can land in the window before it runs). Which "
            "specific land introduced which finding below could not be "
            "determined without re-measuring at each intermediate commit; "
            "this ticket is filed against all of them rather than "
            f"falsely pinned on {attribution_label} alone (the one that "
            "happened to spawn this sweep process).",
        ]
    if attribution_lines:
        body_lines += [
            "",
            "Attribution (T-1690, symbolic reachability over the verify "
            "queue's touched-symbol sets):",
            "",
            *attribution_lines,
        ]
    body_lines += [
        "",
        "Under the rapid profile the sweep runs detached and files this "
        "ticket rather than reverting an already-published commit. Fix the "
        "errors, or -- if they are pre-existing residue the rolling "
        "baseline simply had not recorded yet -- close this ticket with "
        "that finding stated explicitly.",
    ]
    return "\n".join(body_lines)


# frob:doc docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690
# frob:ticket T-1690
# frob:ticket T-1791
# frob:ticket T-2077
# frob:ticket T-1952
# tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_unattributed_is_filed  # noqa: E501
# frob:ticket T-2312
# frob:ticket T-3051
# tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_unrelated_duplicate_finding_in_a_different_file_still_refuses  # noqa: E501
# frob:waive COV007 reason="docs/modules/tickets-verify-sweep.md's Symbolic \
# attribution (T-1690) section documents several symbols under one section, not just a \
# public entry point -- the many-symbols- one-section convention this repo already \
# accepted for vet.md (T-2810 declined to touch it), not a T-2810-shaped duplicate"
def _dispose_to_existing_duplicate_or_none(
    root: Path,
    spec: TicketSpec,
    final_id: str,
    unfiled_pairs: list[tuple[str, str]],
    error: TicketError,
) -> str | None:
    """T-2312 (ARCH001 split of `_file_regression_ticket`): its own
    `new_ticket(...)` failure branch. A `DuplicateTicket` refusal means an
    EXISTING ticket already covers this exact title+scope -- correctly
    refusing to file a second one must not also abandon disposal, so this
    resolves that existing ticket (`_find_exact_duplicate`) and disposes
    `unfiled_pairs` to it, exactly as if this call had just filed it,
    returning its id.

    T-3051 (H4): a `DuplicateFinding` refusal is the SAME shape under a
    different identity check (T-2760's `(rule, file)` overlap instead of
    title+scope) -- it fires precisely when an open ticket already
    DECLARES the finding this sweep just re-measured, which is the
    expected, encouraged steady state for a fix ticket that names its own
    findings via `--finding`. Before this branch existed, that refusal
    dropped disposal entirely: `_file_regression_ticket` returned `None`,
    the watermark stayed pinned (T-2324's unfiled branch), and quarantine
    had no ticket to resolve against (T-2744) -- the fixing ticket's own
    land was then blocked by the very finding it fixes (the measured
    2026-08-26 T-2977 incident). This mirrors the DuplicateTicket branch
    exactly: resolve the declaring ticket via `_find_finding_duplicate`
    and dispose to it.

    Every OTHER failure -- including either duplicate kind whose match
    cannot be re-resolved (a TOCTOU race between the refusal and this
    lookup; never expected in practice) -- is logged at ERROR and returns
    `None`, unchanged from the pre-T-2312 behavior: an unfiled regression
    with NO known owner at all is the one outcome quarantine must keep
    blocking on, and this must never widen to cover a filing failure that
    is not actually a duplicate of either kind."""
    from frob.tickets._models import TicketError
    from frob.tickets._new_renumber import (
        _find_exact_duplicate,
        _find_finding_duplicate,
    )

    if error is TicketError.DuplicateTicket:
        existing = _find_exact_duplicate(root, spec)
        if existing is not None:
            _log.info(
                "rapid sweep: %s: %s already covers this exact title "
                "and scope -- disposing %d finding(s) to it instead "
                "of filing a duplicate",
                final_id,
                existing.id,
                len(unfiled_pairs),
            )
            _auto_dispose_filed_findings(root, unfiled_pairs, existing.id)
            return existing.id
    elif error is TicketError.DuplicateFinding:
        existing = _find_finding_duplicate(root, spec)
        if existing is not None:
            _log.info(
                "rapid sweep: %s: %s already declares this finding -- "
                "disposing %d finding(s) to it instead of filing a "
                "duplicate (T-3051)",
                final_id,
                existing.id,
                len(unfiled_pairs),
            )
            _auto_dispose_filed_findings(root, unfiled_pairs, existing.id)
            return existing.id
    _log.error(
        "rapid sweep: %s introduced %d new error(s) but the regression "
        "ticket could NOT be filed (%s) -- pairs: %s",
        final_id,
        len(unfiled_pairs),
        error,
        unfiled_pairs,
    )
    return None


# frob:ticket T-2352
def _relativize_regression_scope_file(root: Path, file: str) -> str:
    """T-2352: normalize one regression finding's `.file` to a
    repo-relative path before it becomes a filed ticket's `scope:` entry
    -- the producer-side fix for T-2308's real incident (an ABSOLUTE path
    written into a live ticket's scope crashed `frob ticket new`
    fleet-wide, T-2342's reader-side half). Same posture as T-2314's
    `_relativize_perf_violation_file` (`frob.gates.__init__`): normalize
    once, at THIS producer's own return boundary, rather than teaching
    every consumer of `scope:` to accept both an absolute and a relative
    shape. A no-op for a `file` that is already relative. A `file` that is
    absolute but does NOT resolve under `root` at all is kept as-is (never
    silently coerced into a wrong-but-plausible relative path) and logged
    at WARNING naming the anomalous path, since that shape should not
    occur and deserves a diagnosable trace if it ever does."""
    if not Path(file).is_absolute():
        return file
    try:
        rel = Path(file).relative_to(root)
    except ValueError:
        # T-4244: `%r` (repr) DOUBLES every backslash in a Windows path,
        # so a caller checking `file in message` (a plain substring test
        # against the raw, un-repr'd path) never matches there even
        # though the same path is logged -- verified: '%r' % 'C:\\foo'
        # yields doubled backslashes, '%s' % same string round-trips
        # exactly. `%s` logs the path as-is on every platform.
        _log.warning(
            "rapid sweep: regression finding file %s is absolute but does "
            "not resolve under root %s -- keeping as-is rather than "
            "guessing a relative path",
            file,
            str(root),
        )
        return file
    # NOTE (T-4244): NOT switched to `.as_posix()` here -- T-2352's own
    # tests (test_absolute_under_root_is_relativized,
    # test_filed_ticket_scope_is_relative_end_to_end) pin `str(Path(...))`
    # (native separator) as this function's contract for the resolves-
    # under-root case, measured still passing on real Windows. Only the
    # WARNING-branch %r formatting above was the actual defect.
    return str(rel)


# frob:ticket T-2672
def _single_land_attribution_label(
    final_id: str,
    commit_sha: str,
    unfiled_pairs: Sequence[tuple[str, str]],
    attributions: dict,  # noqa: ANN401 -- dict[tuple[str, str], Attribution], deferred-import type
) -> str:
    """T-2672: `_file_regression_ticket`'s single-land-window label (the
    `attributed_ids`-empty case -- see T-2009's own multi-land handling
    right above this call site, which is unaffected). Names `final_id` as
    the cause ONLY when at least one `unfiled_pairs` entry's own symbolic
    attribution (T-1690, already computed by the caller) actually reached
    `commit_sha` -- never merely because `final_id` happened to be the
    one land that spawned this detached sweep. That distinction is
    exactly what six real sweep-filed tickets got wrong (T-2672's own
    measurement): the per-finding attribution correctly reported every
    one of them UNATTRIBUTED, but the filed ticket's title still read
    "post-land sweep regression from <that land>" -- a causal claim the
    evidence directly contradicted. When nothing implicates `final_id`,
    the label discloses that honestly instead of silently asserting a
    cause; the full per-pair reasoning is already in `attribution_lines`
    (the body), this only fixes the TITLE/first-body-line framing that
    quotes this label verbatim."""
    implicated = any(
        (attr := attributions.get(pair)) is not None
        and attr.status == "attributed"
        and attr.commit_sha == commit_sha
        for pair in unfiled_pairs
    )
    if implicated:
        return final_id
    # Deliberately does NOT read "... from <final_id>" -- a reader who
    # greps a filed ticket's title for a ticket id must not be pointed at
    # a land the evidence just said did not reach these findings. The
    # sweep that happened to notice this is still named, but never as
    # "the cause".
    return f"an unattributed source (sweep spawned by {final_id})"


# frob:ticket T-3222
# tests/unit/rapid_sweep_suite/test_attribution.py::TestReverifyUnfiledPairsAtFileTime.test_still_live_pair_is_kept  # noqa: E501
# tests/unit/rapid_sweep_suite/test_attribution.py::TestReverifyUnfiledPairsAtFileTime.test_vanished_pair_is_dropped_and_recorded_as_debt  # noqa: E501
# tests/unit/rapid_sweep_suite/test_attribution.py::TestReverifyUnfiledPairsAtFileTime.test_unmeasurable_files_everything_as_before  # noqa: E501
def _reverify_unfiled_pairs_at_file_time(
    root: Path, final_id: str, unfiled_pairs: Sequence[tuple[str, str]]
) -> tuple[list[tuple[str, str]], int | None]:
    """T-3222: the file-time liveness gate `_file_regression_ticket`
    skipped for its whole life -- it already paid for exactly this
    independent `frob check --json` re-measure (`_true_finding_count_
    for_identities`, T-1935), but only ever used the result for a
    cosmetic "N finding(s)" title label, never to decide whether a
    now-dead identity should still be filed. MEASURED (T-3222, two
    independent samples across three prior triage series): 27 of 30
    sweep-filed identities no longer reproduced by read time; the
    starkest confirmation was that several already-filed tickets
    (T-3188, T-3210, T-3215) carried this SAME re-measure's own "0
    finding(s)" result in their own body and were filed anyway.

    Reuses `_matching_error_diagnostics` directly (the shared low-level
    fetch both `_true_finding_count_for_identities` and
    `_identities_still_reproducing` already build on) so this is still
    exactly ONE independent check spawn -- the same one the pre-fix code
    paid for, not a second one.

    Returns `(live_pairs, true_count)`. `true_count` is `None` on an
    unmeasurable re-check (timeout, spawn refused, unparsable output) --
    per this module's long-standing posture, "unmeasurable" is never
    read as "resolved", so `live_pairs` degrades to `unfiled_pairs`
    unchanged (the pre-T-3222 behavior: file everything, no liveness
    claim made). Every pair NOT in `live_pairs` is recorded as rapid
    debt (`record_rapid_debt`) rather than silently dropped -- a finding
    that vanished between measurement and file time may still be real
    intermittently, and this keeps it in the cheap, machine-readable
    record T-1681 already maintains instead of costing a future agent a
    full ticket triage cycle for something that no longer reproduces."""
    from frob.tickets._evidence import record_rapid_debt

    matched = _matching_error_diagnostics(root, frozenset(unfiled_pairs), None)
    if matched is None:
        _log.warning(
            "rapid sweep: %s: file-time re-verify unmeasurable -- filing "
            "all %d new identit(ies) unchanged (T-3222: unmeasurable is "
            "never read as resolved)",
            final_id,
            len(unfiled_pairs),
        )
        return list(unfiled_pairs), None
    true_count = len(matched)
    reproducing = frozenset((d.get("code") or "", d.get("file") or "") for d in matched)
    live_pairs = [pair for pair in unfiled_pairs if pair in reproducing]
    vanished_pairs = [pair for pair in unfiled_pairs if pair not in reproducing]
    for rule, file in vanished_pairs:
        record_rapid_debt(
            root, final_id, f"sweep-finding-vanished-before-file:{rule}:{file}"
        )
    if vanished_pairs:
        _log.warning(
            "rapid sweep: %s: %d of %d new identit(ies) no longer "
            "reproduced at file time (T-3222) -- recorded as rapid debt, "
            "NOT filed as a ticket: %s",
            final_id,
            len(vanished_pairs),
            len(unfiled_pairs),
            ", ".join(f"{r} {f}" for r, f in vanished_pairs),
        )
    return live_pairs, true_count


# frob:ticket T-2744
# tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_commit_failure_skips_auto_dispose_and_returns_none  # noqa: E501
def _file_regression_ticket(
    root: Path,
    final_id: str,
    commit_sha: str,
    new_findings: frozenset[tuple[str, str]],
    *,
    attributed_ids: Sequence[str] | None = None,
) -> str | None:
    """File one `bug` ticket naming every newly-introduced `(rule_id,
    file)` pair NOT already owned by a still-open ticket, and return its
    id (`None` if the ledger write failed -- logged at ERROR, since an
    unfiled regression is the one outcome that makes deferred sweeping
    unsound; also `None` when every finding attributes to an
    already-open ticket, since that finding already has a home and
    re-filing it would just be noise).

    T-2009: `attributed_ids`, when given (non-empty), OVERRIDES `final_id`
    in the filed ticket's own TITLE and first body line only -- every
    other use of `final_id` in this function (attribution/quarantine
    logging) is unchanged. This exists because `final_id` names the land
    that happened to SPAWN this detached sweep, which is not necessarily
    the same as "the land(s) that actually introduced `new_findings`"
    when more than one land occurred between the last baseline and the
    tree this sweep measured (`_land_ids_between`, computed by the
    caller). `None`/empty falls back to `[final_id]`, i.e. the pre-T-2009
    behavior, unchanged.

    T-1690: each pair is first run through `_partition_findings_by_
    attribution` (tier-2 symbolic reachability over the durable verify
    queue, via `_attribute_new_findings`). A pair that attributes to
    EXACTLY ONE batch commit whose ticket is still open is logged and left
    off this ticket entirely -- it is already tracked. Every other pair
    (attributed to a closed/dropped ticket's commit, or UNATTRIBUTED --
    zero or more than one reaching commit) is filed here, with the full
    attribution audit trail (commit, symbol, reachability path, or the
    reason it could not be attributed) in the body, so a reader never has
    to re-derive what this ticket already computed. Attribution
    unavailability (empty mapping from `_attribute_new_findings`)
    degrades to the pre-T-1690 behavior: every pair filed, no attribution
    lines -- "cannot attribute" must never suppress a real regression's
    own ticket.

    T-1791: EVERY call here is, by definition, a red batch verification
    (the caller only reaches this function when `new_findings` is
    non-empty) -- so this also raises `frob.verify._quarantine.
    raise_quarantine` over the whole batch, using the SAME attributions
    this function already computed for the ticket body, before deciding
    whether a fresh regression ticket is needed. Quarantine is raised
    even when every pair already has an open ticket (the `not
    unfiled_pairs` early return below): the circuit breaker's job is
    "did the tree go red", not "did filing produce a NEW ticket" -- those
    are different questions, and conflating them would let a red batch
    whose findings all happen to already be tracked slip past the
    breaker with deferred landing still enabled."""
    from frob.tickets import TicketSpec, new_ticket
    from frob.tickets._models import Origin, Priority, TicketKind

    pairs = sorted(new_findings)
    attributions = _attribute_new_findings(root, pairs)
    unfiled_pairs, attribution_lines = _partition_findings_by_attribution(
        root, final_id, pairs, attributions
    )
    _raise_quarantine_for_red_batch(root, final_id, pairs, attributions)

    if not unfiled_pairs:
        _log.info(
            "rapid sweep: %s: every new finding attributed to an already-"
            "open ticket -- no regression ticket filed",
            final_id,
        )
        return None

    # T-3222: re-verify at FILE time -- MEASURED (T-3222, two independent
    # samples): 27 of 30 sweep-filed identities no longer reproduced by
    # the time an agent read the filed ticket, and several of those
    # (T-3188, T-3210, T-3215) already carried this exact re-measure's
    # OWN "0 finding(s)" result in their title/body and were filed
    # anyway -- the re-measure existed but was never used as a filing
    # gate, only as a cosmetic count. `_true_finding_count_for_identities`
    # below is replaced with the shared lower-level fetch so the same
    # single spawn answers both "how many findings" and "which identities
    # are still live", instead of the pre-fix shape (which already paid
    # for exactly this spawn and then discarded the liveness half of its
    # answer).
    unfiled_pairs, true_count = _reverify_unfiled_pairs_at_file_time(
        root, final_id, unfiled_pairs
    )
    if not unfiled_pairs:
        _log.info(
            "rapid sweep: %s: every new finding vanished between "
            "measurement and file time (T-3222) -- no regression ticket "
            "filed",
            final_id,
        )
        return None

    # T-2672: `attributed_ids` (T-2009) already handles the multi-land
    # window honestly -- it names every land that occurred, never just
    # `final_id`. The single-land window (`attributed_ids` empty/None)
    # used to default straight to `final_id` as the filed ticket's named
    # cause with NO check against what `_attribute_new_findings` actually
    # found -- six real sweep-filed tickets were measured naming a land
    # that touched none of the flagged files, because every one of them
    # was this exact single-land-but-unattributed shape: the per-finding
    # symbolic attribution above already correctly computed UNATTRIBUTED
    # (recorded in `attribution_lines`/the body), but the TITLE and first
    # body line still asserted causation regardless. `_causally_
    # implicates_final_id` asks the one question this label actually
    # needs answered: did the evidence this function already computed
    # implicate `final_id`'s own commit for at least one of the pairs
    # being filed here? If not, the label discloses "unattributed"
    # instead of quietly asserting a cause the evidence contradicts.
    attribution_label = (
        ", ".join(attributed_ids)
        if attributed_ids
        else _single_land_attribution_label(
            final_id, commit_sha, unfiled_pairs, attributions
        )
    )

    rules = sorted({rule for rule, _ in unfiled_pairs})
    count_line = _regression_count_line(unfiled_pairs, true_count)
    body = _build_regression_body(
        attribution_label=attribution_label,
        commit_sha=commit_sha,
        pairs=pairs,
        unfiled_pairs=unfiled_pairs,
        count_line=count_line,
        attributed_ids=attributed_ids,
        attribution_lines=attribution_lines,
    )
    title_count = (
        f"{len(unfiled_pairs)} new (rule, file) identit(ies)"
        if true_count is None
        else f"{len(unfiled_pairs)} new (rule, file) identit(ies), "
        f"{true_count} finding(s)"
    )
    spec = TicketSpec(
        title=(
            f"{_REGRESSION_TITLE_PREFIX}{attribution_label}: {title_count} "
            f"({', '.join(rules[:4])})"
        ),
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        priority=Priority.HIGH,
        scope=tuple(
            sorted(
                {
                    _relativize_regression_scope_file(root, file)
                    for _, file in unfiled_pairs
                }
            )
        ),
        # frob:ticket T-2760
        # populate the structured finding identity directly from the same
        # `unfiled_pairs` this function already computed -- the T-2760
        # incident this closes was two tickets filing for the SAME
        # (rule, file) with titles sharing no words at all, and one of
        # them was exactly this auto-filing path; a hand-written ticket
        # filed for the same pair afterward is now caught by `_refuse_
        # finding_duplicate` at filing time, and a start-time race is
        # caught by `_warn_if_finding_duplicate_at_start`, without either
        # check ever having to parse this function's generated prose.
        findings=tuple(unfiled_pairs),
        body=body,
    )
    # T-1758: new_ticket now auto-commits internally by default -- opt
    # out here (no_commit=True) so _commit_regression_ticket's own commit
    # below still lands, carrying the more informative message naming
    # BOTH the regression ticket id and the land it regressed from,
    # rather than new_ticket's own generic "file T-####" commit.
    # T-1891: warn_if_dirty=False too -- _commit_regression_ticket below
    # always attempts its own commit for the same pathspecs (retried on
    # a transient land-in-progress conflict, T-1841), so a dirty ledger
    # HERE is never the final, left-behind state a --no-commit warning
    # would correctly describe.
    #
    # T-3245: `new_ticket`'s own duplicate refusal (`_refuse_exact_
    # duplicate`/`_refuse_finding_duplicate`, in `_validate_new_ticket_
    # spec`) reads the ledger with a plain `load_all`, BEFORE the
    # allocate-and-write step takes `allocator_lock`/`ledger_lock` --
    # two detached sweep processes filing for the SAME (rule, file) can
    # each run that duplicate check while neither has written yet (both
    # see "no duplicate"), then each proceed to allocate-and-write in
    # turn, producing two byte-identical tickets (the T-3236/T-3237,
    # T-3158/T-3159, T-3022/T-3023 incidents this closes). The guard
    # itself (`_dispose_to_existing_duplicate_or_none`, below) is
    # correct; it just never got a chance to see the sibling's write.
    # Taking BOTH locks here, around the duplicate check AND the write,
    # closes that gap: they are the same cross-process, thread-reentrant
    # `flock`s `new_ticket` re-acquires internally (`_flock_path`), so a
    # second racing process now blocks until the first's write is
    # already on disk -- its own `new_ticket` call then sees the sibling
    # via a fresh `load_all` and correctly disposes to it instead of
    # filing a duplicate, exactly as if the two calls had never
    # overlapped at all.
    from frob.tickets import ledger_lock
    from frob.tickets._store import allocator_lock

    with allocator_lock(root), ledger_lock(root):
        created = new_ticket(root, spec, no_commit=True, warn_if_dirty=False)
        if created.is_err:
            return _dispose_to_existing_duplicate_or_none(
                root, spec, final_id, unfiled_pairs, created.danger_err
            )
    regression_id = created.danger_ok.id
    committed = _commit_regression_ticket(root, regression_id, attribution_label)
    if not committed:
        # T-2744: the T-2736 incident -- `regression_id` was allocated and
        # would otherwise be cited as the clearing reason below, but its
        # ledger write never landed (retries exhausted, the uncommitted
        # dir was discarded per `_discard_uncommitted_regression_ticket`).
        # Disposing/clearing against an id that does not exist on `root`
        # is exactly the phantom-home bug this ticket fixes -- skip it
        # here (defense in depth on top of `clear_quarantine`'s own
        # `UnresolvableFiledTicket` refusal, which would also catch this)
        # and leave quarantine raised so the findings stay tracked.
        _log.error(
            "rapid sweep: %s: regression ticket could not be committed -- "
            "skipping auto-dispose/clear against it; quarantine stays "
            "raised for %d finding(s) until a human refiles and disposes "
            "them",
            regression_id,
            len(unfiled_pairs),
        )
        return None
    _auto_dispose_filed_findings(root, unfiled_pairs, regression_id)
    return regression_id


# frob:ticket T-2450
# frob:doc \
# docs/modules/tickets-verify-sweep.md#public-seam-for-cross-node-callers-t-2450
# tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicketPublicSeam.test_delegates_to_the_private_implementation  # noqa: E501
def file_regression_ticket(
    root: Path,
    final_id: str,
    commit_sha: str,
    new_findings: frozenset[tuple[str, str]],
) -> str | None:
    """T-2450: public seam for `_file_regression_ticket`, for callers
    OUTSIDE `app.ticket_runner`'s own node (`frob.verify._worker`, which
    files a regression ticket for newly-observed error findings the same
    way a rapid-sweep does) -- see `detached_sweep_env`'s own docstring
    for the T-2407/SYS003 debt this closes; every in-module caller keeps
    using `_file_regression_ticket` directly, unchanged. Deliberately
    omits `attributed_ids` (unlike the private implementation) -- the
    ONE cross-node caller this seam exists for never supplies it, and a
    narrower public signature is easier to keep stable than one that
    exposes every internal parameter."""
    return _file_regression_ticket(root, final_id, commit_sha, new_findings)


# frob:ticket T-2208
def _auto_dispose_filed_findings(
    root: Path, unfiled_pairs: list[tuple[str, str]], regression_id: str
) -> None:
    """T-2208: dispose, with `--file-ticket` semantics, exactly the
    quarantined findings this sweep just filed `regression_id` for --
    the same operation `_file_regression_ticket`'s caller used to have
    to hand-restate via `frob verify dispose --file-ticket F=T-XXXX`
    after every single red batch (8 manual disposals in one session,
    each blocking the fleet's deferred landing until done).

    Only findings whose `(rule_id, file)` is in `unfiled_pairs` -- i.e.
    the exact set `regression_id` was just filed to cover -- are
    disposed here, each as `("filed", regression_id)`, matching
    `frob verify dispose --file-ticket`'s own disposition shape exactly
    (`_collect_dispositions` in `frob.app.verify_runner` builds the
    identical tuple). Every OTHER currently-raised finding (attributed
    to a different, already-open ticket that this call never touched)
    is left alone -- `clear_quarantine` itself then refuses the clear
    with `QuarantineError.FindingsNotDisposed` if any such finding
    remains, which is the correct outcome, not a bug to work around:
    an undisposed finding with no tracking ticket is exactly what
    quarantine exists to surface, and disposing it here just because
    THIS call happened to run would reopen the hole T-1693 closed.
    `clear_quarantine` logs its own CLEARED/refusal at WARNING/ERROR
    (`frob.verify._quarantine`'s own docstring), so a successful
    auto-dispose here is indistinguishable in the log from a manual
    `frob verify dispose --file-ticket` -- the audit trail this
    ticket's own acceptance criteria require stays unchanged."""
    from frob.verify._quarantine import clear_quarantine, load_quarantine

    loaded = load_quarantine(root)
    if loaded.is_err:
        _log.warning(
            "rapid sweep: %s: could not auto-dispose against %s -- "
            "quarantine unreadable (%s); a human must run `frob verify "
            "dispose --file-ticket` by hand",
            regression_id,
            root,
            loaded.danger_err,
        )
        return
    record = loaded.danger_ok
    if record is None or record.cleared_at is not None:
        # Nothing raised (e.g. the empty-queue/cold-noise branches of
        # `_raise_quarantine_for_red_batch` skipped the raise entirely)
        # -- nothing to dispose, this is the routine case, not an error.
        return

    covered = set(unfiled_pairs)
    dispositions = {
        (f.rule_id, f.file, f.line): ("filed", regression_id)
        for f in record.findings
        if (f.rule_id, f.file) in covered and not f.disposition
    }
    if not dispositions:
        # Every finding this ticket covers was already disposed (a race
        # with a concurrent manual dispose) or none of the raised
        # findings matched `unfiled_pairs` (e.g. all dropped as
        # cold-worktree noise before the raise) -- nothing to do.
        return

    cleared = clear_quarantine(
        root,
        dispositions=dispositions,
        reason=f"auto-filed by rapid sweep as {regression_id}",
        actor="rapid-sweep",
    )
    if cleared.is_err:
        _log.info(
            "rapid sweep: %s: auto-dispose did not clear quarantine (%s) "
            "-- %d finding(s) it covers were marked filed, but other "
            "currently-raised finding(s) remain undisposed; deferred "
            "landing stays off until a human disposes those via `frob "
            "verify dispose`",
            regression_id,
            cleared.danger_err,
            len(dispositions),
        )


#: T-1841: `_commit_regression_ticket`'s retry budget for a commit that
#: fails because a CONCURRENT `frob ticket land` holds root's exclusive
#: lock (`LeaseError.LandInProgress`) or loses a transient `git add`/
#: `git commit` race against one. The sweep runs DETACHED after every
#: rapid land, so a land from some OTHER agent still in flight is the
#: NORMAL operating condition here (T-1841's own evidence: four same-day
#: incidents, all under five concurrent agents), not an edge case worth
#: giving up on after one attempt.
_REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS = 5

#: T-1841: seconds between retry attempts. This repo's own land-lock wait
#: (`_land.py`'s `LAND_LOCK_POLL_S`) polls far faster because a live human/
#: agent is blocked on it; a detached sweep has no such urgency, so a
#: coarser interval trades a few extra seconds of sweep latency for far
#: fewer wasted attempts against a land that commonly runs for tens of
#: seconds.
_REGRESSION_TICKET_COMMIT_RETRY_DELAY_S = 3.0


def _discard_uncommitted_regression_ticket(root: Path, regression_id: str) -> None:
    """T-1841: remove `regression_id`'s just-written, never-committed
    ledger content from `root` so a fully-exhausted commit retry leaves
    root CLEAN rather than DirtyMain-blocking every concurrent land --
    the exact tradeoff this ticket's own body mandates ("a half-completed
    bookkeeping step that stalls the fleet is worse than a skipped one it
    can retry").

    v2 (sharded) stores keep one ticket entirely under its own `tickets/
    <id>/` directory (`ticket.md`, `done-report.md`, `attachments/`) that
    this call is the ONLY writer of at this point -- `no_commit=True`
    guarantees nothing has touched git's index yet, so a plain `rmtree`
    cannot destroy anyone else's work. v1 (monofile `tickets.md`) writes
    the SAME shared file every other ledger op reads/writes -- rolling
    back a still-uncommitted append there risks discarding a concurrent
    writer's own in-flight edit to that file, so this deliberately does
    NOT attempt it for v1; the existing best-effort "dirty root, logged
    loudly" posture stands for that (legacy, no longer the default)
    store shape."""
    from frob.tickets._store import _store_mode

    if _store_mode(root) != "v2":
        _log.error(
            "rapid sweep: %s: regression ticket %s could not be committed "
            "after %d attempt(s) and this is a v1 (monofile) store -- "
            "cannot safely auto-discard a shared tickets.md append, root "
            "stays DIRTY; a human must resolve tickets.md by hand",
            root,
            regression_id,
            _REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS,
        )
        return
    ticket_dir = root / "tickets" / regression_id
    shutil.rmtree(ticket_dir, ignore_errors=True)
    _log.error(
        "rapid sweep: regression ticket %s could not be committed to %s "
        "after %d attempt(s) (each spaced %.0fs apart) -- DISCARDED rather "
        "than left as untracked dirt (T-1841); this specific regression is "
        "unfiled for now and will resurface on a future sweep's diff "
        "against the rolling baseline if it is still present",
        regression_id,
        root,
        _REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS,
        _REGRESSION_TICKET_COMMIT_RETRY_DELAY_S,
    )


# frob:ticket T-2034
def _commit_or_discard_ledger_write(
    root: Path,
    ticket_id: str,
    message: str,
    *,
    max_attempts: int,
    retry_delay_s: float,
    discard: Callable[[], None],
    label: str,
) -> bool:
    """T-2034: the SHARED retry-then-discard shape every sweep
    ledger write (a fresh regression-ticket file, an auto-drop, and
    whatever the next one turns out to be) must go through: attempt
    `commit_ticket_ledger_change` up to `max_attempts` times, `retry_delay_s`
    apart, and call `discard()` exactly once -- only after every attempt is
    exhausted -- so a sweep write can never return with `root` left dirty.

    T-1841 first shipped this shape for the regression-ticket write path
    alone (`_discard_uncommitted_regression_ticket`); T-1983's newer
    auto-drop write path (`_maybe_drop_resolved_ticket`) never inherited
    it, which is exactly how a half-committed `drop_ticket()` write started
    DirtyMain-blocking every concurrent land again (measured 2026-08-10:
    6 dirty `tickets/*/ticket.md`, duplicate reason lines on T-2000/T-2008/
    T-2022 from the same un-discarded write being retried by the next
    sweep). Routing every write path through ONE retry loop means the next
    one added here inherits the guarantee for free instead of re-earning
    it per T-2034's own body.

    `discard` is injected rather than hardcoded because what "undo" means
    genuinely differs by write shape: a brand-new, never-committed
    `tickets/<id>/` directory is safe to `rmtree` outright (nothing else
    has touched git's index for it yet), while an EXISTING, already-landed
    ticket being mutated in place must instead be restored to its last
    committed content (`git checkout HEAD -- <path>`) -- `rmtree` there
    would destroy real ticket history. Only the retry/backoff/give-up
    SHAPE is shared; the two discard actions stay distinct callers below."""
    from frob.tickets._leases import commit_ticket_ledger_change

    for attempt in range(1, max_attempts + 1):
        # frob:waive PERF008 reason="deliberate retry with identical arguments, not an \
        # accidental loop-invariant call -- root's exclusive land lock held by a \
        # DIFFERENT concurrent agent is the routine case for a detached sweep \
        # (T-1841), so freshness under concurrency (does the lock still block?) is \
        # exactly the reason this must re-run every iteration rather than being \
        # hoisted or memoized"
        committed = commit_ticket_ledger_change(root, ticket_id, message)
        if committed.is_ok:
            return True
        if attempt < max_attempts:
            _log.warning(
                "rapid sweep: %s: committing ledger write for %s failed "
                "(%s) on attempt %d/%d -- retrying in %.0fs (a concurrent "
                "land holding root's lock is the routine case, T-1841)",
                label,
                ticket_id,
                committed.danger_err,
                attempt,
                max_attempts,
                retry_delay_s,
            )
            time.sleep(retry_delay_s)
    discard()
    return False


# frob:ticket T-1755
# frob:ticket T-1791
# frob:ticket T-1841
# frob:ticket T-2744
def _commit_regression_ticket(
    root: Path,
    regression_id: str,
    final_id: str,
    *,
    max_attempts: int = _REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS,
    retry_delay_s: float = _REGRESSION_TICKET_COMMIT_RETRY_DELAY_S,
) -> bool:
    """T-1755: `_file_regression_ticket`'s `new_ticket(root, spec)` call
    (the whole point of the deferred sweep) writes `tickets.md` through
    `frob.tickets._new_renumber.new_ticket` DIRECTLY -- the LIBRARY
    function, not the `frob ticket new` CLI verb -- and `new_ticket`
    itself never commits (confirmed by reading it: it takes `ledger_lock`,
    calls `write_ticket`, and returns; T-1130/T-1615's auto-commit lives
    entirely in the CLI dispatch layer, `commit_ticket_ledger_change`,
    which a programmatic caller like this one never reaches). This is the
    THIRD root-cause candidate this ticket's own body named as most
    likely, confirmed: T-1615's uniform auto-commit covers the CLI
    surface, not programmatic callers, which is a wider gap than this one
    call site -- filed as a follow-up (see this function's own Done
    report for the real id) rather than silently left for the next
    detached-write incident to rediscover.

    Calls `frob.tickets._leases.commit_ticket_ledger_change` -- the SAME
    scoped `git add <ledger pathspecs> && git commit -- <ledger
    pathspecs>` primitive `frob ticket new`/`drop`/`fail`/`start` already
    funnel through, never a bare `git commit` or `git add -A` (T-1740's
    own incident: a blanket add on a root checkout concurrent lands are
    racing against published 1416 lines of another agent's in-flight work
    under an unrelated commit message).

    T-1841: retries up to `max_attempts` times, `retry_delay_s` apart,
    before giving up -- the sweep runs DETACHED after a land, so a
    DIFFERENT concurrent land holding root's exclusive lock
    (`LeaseError.LandInProgress`) is the routine case, not a rare fluke
    worth surfacing on the very first attempt (T-1841's evidence: four
    same-day incidents, each a coordinator hand-committing a file the
    sweep gave up on after one try). If every attempt still fails, this
    now calls `_discard_uncommitted_regression_ticket` instead of leaving
    the file behind -- T-1841's own requirement: "if the commit cannot
    succeed ... the sweep must NOT leave the file behind. Either
    write-then-commit atomically or do not write."

    T-2744: this function's return value now propagates
    `_commit_or_discard_ledger_write`'s own success bool -- it USED TO
    stay `None` unconditionally (best-effort, matching
    `_commit_rapid_debt`'s identical "must never fail an already-
    succeeded sweep" posture immediately below it in this module), which
    meant `_file_regression_ticket` could not tell a genuine commit from
    an exhausted-retries discard and proceeded to cite `regression_id` as
    a `clear_quarantine` disposition either way -- exactly the T-2736
    incident (a phantom ticket id named in `cleared_reason`). The write-
    then-commit-or-discard GUARANTEE this function makes is unchanged (a
    land it degraded is still published either way; only whether ROOT
    stays clean was ever at stake there) -- only the caller's ability to
    observe which branch happened is new.

    T-2034: the retry/backoff/give-up loop itself lives in the SHARED
    `_commit_or_discard_ledger_write` (this function just supplies the
    message and the regression-ticket-specific discard action); behavior
    is unchanged, this is the same retry shape as before, just no longer
    re-derived independently of the drop path below."""
    message = (
        f"chore(tickets): file {regression_id} "
        f"(post-land sweep regression from {final_id})"
    )
    return _commit_or_discard_ledger_write(
        root,
        regression_id,
        message,
        max_attempts=max_attempts,
        retry_delay_s=retry_delay_s,
        discard=lambda: _discard_uncommitted_regression_ticket(root, regression_id),
        label=final_id,
    )


# frob:ticket T-1983
# tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_parses_a_sweep_titled_ticket_identity_set  # noqa: E501
# tests/unit/rapid_sweep_suite/test_dispose.py::TestCloseResolvedSweepTickets.test_non_sweep_ticket_returns_none  # noqa: E501
def _parse_sweep_ticket_identities(ticket) -> frozenset[tuple[str, str]] | None:  # noqa: ANN001 -- Ticket, deferred-import type
    """T-1983: recover the exact `(rule, file)` identity set
    `_file_regression_ticket` recorded in `ticket`'s body, or `None` if
    `ticket` was not filed by this sweep (its title lacks
    `_REGRESSION_TITLE_PREFIX`) or the identity list could not be found/
    was empty.

    Scans from `_REGRESSION_IDENTITY_HEADING` and stops at the first
    blank line once at least one identity has been collected -- the
    attribution section right below reuses the same `"- rule  file  ->
    ..."` shape for a DIFFERENT purpose (human-readable audit trail, not
    the ticket's own obligation), so this deliberately stops before it
    rather than also matching `" -> "` lines, which would silently widen
    the parsed set with attribution text fragments that can never appear
    in a real fresh measurement -- a wrong identity here can only ever
    make the later subset check fail closed (no drop), never wrongly
    succeed."""
    if not ticket.title.startswith(_REGRESSION_TITLE_PREFIX):
        return None
    lines = ticket.body.splitlines()
    try:
        start = lines.index(_REGRESSION_IDENTITY_HEADING) + 1
    except ValueError:
        return None
    identities: set[tuple[str, str]] = set()
    for line in lines[start:]:
        if not line.strip():
            if identities:
                break
            continue
        if not line.startswith("- ") or " -> " in line:
            break
        parts = line[2:].split("  ", 1)
        if len(parts) != 2:
            continue
        identities.add((parts[0].strip(), parts[1].strip()))
    return frozenset(identities) if identities else None


#: T-2034: retry budget for the auto-drop ledger commit, same
#: values as the regression-ticket path's own budget -- both face the
#: identical "a concurrent land holds root's lock" contention (T-1841),
#: so there is no reason to tune them independently absent evidence they
#: behave differently under load.
_TICKET_DROP_COMMIT_MAX_ATTEMPTS = _REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS
_TICKET_DROP_COMMIT_RETRY_DELAY_S = _REGRESSION_TICKET_COMMIT_RETRY_DELAY_S


# frob:ticket T-2034
# frob:waive ARCH103 reason="mirrors the sibling \
# _discard_uncommitted_regression_ticket's exact shape (store-mode check, one \
# filesystem/git undo action, one log line per branch) -- the store-mode branch and \
# the git-checkout-failure branch are both real, distinct terminal outcomes that must \
# each be logged with a DIFFERENT message (dirty-for-a-known-reason vs restored vs \
# restore-itself-failed), so splitting them apart would scatter one coherent decision \
# (what happened to this write, how do I tell the operator) across multiple functions \
# rather than separating an unrelated concern"
def _discard_uncommitted_ticket_drop(root: Path, ticket_id: str) -> None:
    """T-2034: undo `ticket_id`'s just-written, never-committed
    `drop_ticket()` mutation so an exhausted commit retry leaves `root`
    CLEAN rather than DirtyMain-blocking every concurrent land -- the same
    tradeoff T-1841 already made for the sibling regression-ticket write
    path (`_discard_uncommitted_regression_ticket`), applied here to close
    the gap that let this exact write path re-dirty root (measured
    2026-08-10: duplicate reason lines on T-2000/T-2008/T-2022 from the
    same un-discarded drop being retried by the next sweep).

    Unlike a freshly-filed regression ticket, the ticket being dropped
    here is an EXISTING, already-committed ticket -- `drop_ticket()`
    rewrote its `ticket.md` in place, it did not create a new directory.
    `rmtree` would therefore destroy real ticket history; the correct
    undo is `git checkout HEAD -- tickets/<id>/`, restoring the directory
    to its last-committed content (same content, plus whatever was there
    before the never-committed drop write -- nothing is lost)."""
    from frob.tickets._store import _store_mode

    if _store_mode(root) != "v2":
        _log.error(
            "rapid sweep: auto-drop of %s could not be committed after "
            "exhausted attempts and this is a v1 (monofile) store -- "
            "cannot safely auto-restore a shared tickets.md write, root "
            "stays DIRTY; a human must resolve tickets.md by hand",
            ticket_id,
        )
        return
    ticket_dir = root / "tickets" / ticket_id
    proc = subprocess.run(
        ["git", "checkout", "HEAD", "--", str(ticket_dir)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if proc.returncode != 0:
        _log.error(
            "rapid sweep: auto-drop of %s could not be committed and the "
            "git-checkout restore itself failed (%s) -- root may still be "
            "DIRTY, a human must resolve tickets/%s by hand",
            ticket_id,
            proc.stderr.strip(),
            ticket_id,
        )
        return
    _log.error(
        "rapid sweep: auto-drop of %s could not be committed after "
        "exhausted attempts -- RESTORED tickets/%s to its last committed "
        "state rather than left dirty (T-2034, mirrors T-1841)",
        ticket_id,
        ticket_id,
    )


# frob:ticket T-1983
# frob:ticket T-2034
# frob:ticket T-2078
def _maybe_drop_resolved_ticket(
    root: Path,
    final_id: str,
    ticket,  # noqa: ANN001 -- Ticket, deferred-import type
    vanished: frozenset[tuple[str, str]],
    measurement_note: str = "a complete measurement",
) -> str | None:
    """T-1983 (ARCH001 split of `_close_resolved_sweep_tickets`, one
    ticket's worth of the drop-if-resolved decision): `None` unless
    `ticket`'s full recorded identity set is a non-empty subset of
    `vanished`, in which case it drops `ticket` (`drop_ticket` +
    `commit_ticket_ledger_change`, mirroring `frob ticket drop`'s own CLI
    wiring) and returns its id. Best-effort: a `drop_ticket`/commit
    failure is logged and returns `None`, never raised -- one
    un-droppable stale ticket must not abort the sweep's real job
    (recording the fresh baseline) for every other ticket.

    T-2034: the commit is now attempted through the SHARED
    `_commit_or_discard_ledger_write` retry loop, and a fully-exhausted
    commit now RESTORES `ticket_id`'s file to its last-committed state
    (`_discard_uncommitted_ticket_drop`) instead of leaving the dropped-
    but-uncommitted write behind -- previously the write stayed dirty in
    root, DirtyMain-blocking every concurrent land AND making the ticket
    non-idempotent (the next sweep still saw it as QUEUED/PLANNED and
    dropped it again, appending a duplicate reason block)."""
    from frob.tickets import TicketState, drop_ticket
    from frob.tickets._reporting import _is_transition_legal

    identities = _parse_sweep_ticket_identities(ticket)
    if identities:
        # T-2036: a ticket filed before this fix may still
        # carry an absolute-path identity in its body -- normalize on
        # read so it compares correctly against `vanished` (already
        # normalized by the caller).
        identities = _normalize_identities(root, identities)
    if not identities or not identities <= vanished:
        return None
    # T-2078: `_close_resolved_sweep_tickets` already filters its own
    # candidates to QUEUED/PLANNED before calling here, but
    # `revalidate_dispatchable_sweep_tickets` (T-2006) calls this
    # function directly against `doable`'s FULL candidate set -- which
    # includes already-terminal (`done`/`dropped`) tickets whose
    # identities happen to still be recorded. Checking legality here, in
    # the shared per-ticket decision point, closes that gap for every
    # current and future caller in one place rather than duplicating the
    # state filter at each call site. Not just defense-in-depth:
    # `drop_ticket` itself now also refuses illegal transitions with
    # zero writes (T-2078), but skipping the doomed attempt here avoids
    # the InvalidTransition log noise entirely for a ticket that was
    # never droppable to begin with.
    if not _is_transition_legal(ticket.state, TicketState.DROPPED):
        return None
    reason = (
        "T-1983: auto-dropped by the deferred post-land sweep -- every "
        f"(rule, file) identity this ticket named "
        f"({', '.join(f'{r} {f}' for r, f in sorted(identities))}) is "
        f"absent from {measurement_note} at {final_id}'s deferred sweep "
        "(T-2521: this drop only fires when that measurement itself "
        "completed -- no budget deferral, no failed/silent tool stage -- "
        "never on an unmeasured or partial run), i.e. no longer "
        "reproduces. If this is wrong (a flaky/incomplete measurement), "
        "re-file with `frob check --only <gate>` evidence attached."
    )
    result = drop_ticket(root, ticket.id, reason)
    if result.is_err:
        _log.error(
            "rapid sweep: %s: could not auto-drop resolved regression ticket %s (%s)",
            final_id,
            ticket.id,
            result.danger_err,
        )
        return None
    committed = _commit_or_discard_ledger_write(
        root,
        ticket.id,
        f"chore(tickets): auto-drop {ticket.id} (resolved, T-1983)",
        max_attempts=_TICKET_DROP_COMMIT_MAX_ATTEMPTS,
        retry_delay_s=_TICKET_DROP_COMMIT_RETRY_DELAY_S,
        discard=lambda: _discard_uncommitted_ticket_drop(root, ticket.id),
        label=final_id,
    )
    if not committed:
        return None
    _log.info(
        "rapid sweep: %s: auto-dropped resolved regression ticket %s (%d "
        "identit(ies) no longer reproduce)",
        final_id,
        ticket.id,
        len(identities),
    )
    return ticket.id


# frob:ticket T-1983
def _close_resolved_sweep_tickets(
    root: Path,
    final_id: str,
    vanished: frozenset[tuple[str, str]],
    measurement_note: str = "a complete measurement",
) -> tuple[str, ...]:
    """T-1983: auto-DROP (never close -- dropping states no work happened
    and no evidence exists, matching how T-1947/T-1972 were handled by
    hand) every QUEUED/PLANNED sweep-filed regression ticket whose full
    recorded identity set is now a subset of `vanished` -- (rule, file)
    identities present in the PREVIOUS baseline but absent from THIS
    sweep's fresh unscoped measurement, i.e. no longer reproducing, per
    this exact same land's own re-measurement rather than a guess or a
    stale prior run. Per-ticket decision + drop lives in
    `_maybe_drop_resolved_ticket`; this function is just the queue scan
    + IN_PROGRESS exclusion.

    A ticket with only SOME of its identities vanished is left untouched
    entirely -- no partial drop, matching this ticket's own acceptance
    ("no false drops, since dropping a live regression is strictly worse
    than leaving a stale one"). IN_PROGRESS tickets are never touched
    here either: a ticket someone is actively working must never be
    yanked out from under them by a background sweep. Returns the
    dropped ids, for the caller's own log line."""
    if not vanished:
        return ()
    from frob.tickets import TicketState, load_queue

    queue = load_queue(root)
    if queue.is_err:
        _log.warning(
            "rapid sweep: %s: could not load the queue to check for "
            "resolved sweep tickets (%s) -- skipping the T-1983 close "
            "pass this run",
            final_id,
            queue.danger_err,
        )
        return ()

    dropped = []
    for ticket in sorted(queue.danger_ok.tickets.values(), key=lambda t: t.id):
        if ticket.state not in (TicketState.QUEUED, TicketState.PLANNED):
            continue
        result = _maybe_drop_resolved_ticket(
            root, final_id, ticket, vanished, measurement_note
        )
        if result is not None:
            dropped.append(result)
    return tuple(dropped)


# frob:ticket T-2006
# frob:ticket T-2024
# frob:doc \
# docs/modules/tickets-verify-sweep.md#doable-time-revalidation-of-sweep-filed-tickets-t-2006  # noqa: E501
# frob:ticket T-3349
def revalidate_dispatchable_sweep_tickets(
    root: Path,
    tickets: Sequence,  # noqa: ANN401 -- Sequence[Ticket], deferred-import type
) -> tuple[str, ...]:
    """T-2006: the residual gap T-1983 left open. T-1983's own auto-drop
    (`_close_resolved_sweep_tickets`, this module) works correctly, but
    its call site is INSIDE a deferred sweep, which only runs after SOME
    land -- any land, not necessarily one related to the stale ticket.
    In the window between a sweep-filed ticket's identities getting fixed
    (by another agent, or a Tier-A auto-fix) and the next unrelated
    land's sweep, the ticket sits dispatchable and unverified -- exactly
    when a coordinator reads `frob ticket doable` and dispatches it.
    Measured twice on 2026-08-10: T-2000 (already-fixed, no later sweep
    had run, dropped BY HAND) and T-1998 (misattributed AND
    mostly-already-fixed, cost a full dispatch cycle for one real line of
    work, `git show 917ba8e92 --stat`).

    Called from `frob ticket doable`'s own render path
    (`_query._doable`) with the FULL candidate ticket set, BEFORE the
    dispatchable filter runs -- deliberately NOT a full unscoped sweep
    (T-1684's whole point stays off this path) and NOT gated on `start`
    (too late -- the dispatch decision already happened by then, per
    this ticket's own body). Zero-cost when `tickets` contains no
    sweep-filed candidate at all (`_parse_sweep_ticket_identities`
    returns `None` for everything) -- the overwhelmingly common case, so
    a plain `frob ticket doable` pays nothing extra most of the time.
    When at least one candidate exists, spawns exactly ONE re-check
    (`_identities_still_reproducing`) scoped to the UNION of every
    candidate's own recorded identities (never a full sweep), and drops
    (via the same `_maybe_drop_resolved_ticket` T-1983 already built)
    any whose full identity set is now a subset of what vanished. The
    measured cost of that one re-check is always logged, matching this
    ticket's own acceptance criterion #2. An unmeasurable re-check (spawn
    refused, timeout) drops nothing -- matching T-1983's own "never treat
    unmeasurable as resolved" rule."""
    candidates: list[tuple[object, frozenset[tuple[str, str]]]] = []
    for ticket in tickets:
        identities = _parse_sweep_ticket_identities(ticket)
        if identities:
            # T-2036: normalize on read, same as the sweep path.
            candidates.append((ticket, _normalize_identities(root, identities)))
    if not candidates:
        return ()

    all_pairs: frozenset[tuple[str, str]] = frozenset().union(
        *(identities for _, identities in candidates)
    )
    reproducing = _reproducing_identities_cached(root, len(candidates), all_pairs)
    if reproducing is None:
        return ()
    vanished = all_pairs - reproducing
    # T-2521: `reproducing` already passed `_matching_error_diagnostics`'
    # own completeness gate (no failed/silent tool result) -- named here
    # so the drop reason states what was actually checked, not merely
    # asserts absence.
    measurement_note = (
        f"a direct re-check of exactly the {len(all_pairs)} named "
        "(rule, file) identit(ies) (not a full sweep) that completed "
        "with no failed/silent tool stage"
    )
    dropped: list[str] = []
    for ticket, identities in candidates:
        result = _maybe_drop_resolved_ticket(
            root, "doable", ticket, vanished, measurement_note
        )
        if result is not None:
            dropped.append(result)
    return tuple(dropped)


# frob:ticket T-2089
# frob:ticket T-2165
def _reproducing_identities_cached(
    root: Path, n_candidates: int, all_pairs: frozenset[tuple[str, str]]
) -> frozenset[tuple[str, str]] | None:
    """T-2089 (ARCH001 split of `revalidate_dispatchable_sweep_tickets`):
    which of `all_pairs` still reproduce right now, reusing a cache when
    available (logged as a HIT, `%.3fs`, 0 spawns) and falling back to a
    real `_identities_still_reproducing` spawn otherwise (logged as a
    fresh measurement, writing the cache for the NEXT call). `None` on
    an unmeasurable re-check (matching T-1983's "never treat unmeasurable
    as resolved" rule) -- the caller must never read `None` as an empty
    reproducing set. T-2106: the re-measure spawn (when the cache misses)
    is budgeted at `_DOABLE_REVALIDATION_BUDGET_S` (20s), not
    `_TRUE_COUNT_BUDGET_S` (300s) -- this call sits on an interactive
    query path (`frob ticket doable`), not the deferred sweep
    `_TRUE_COUNT_BUDGET_S` was sized for; an unmeasurable-after-20s result
    is handled exactly like any other unmeasurable outcome (drops
    nothing, never read as resolved).

    T-2165: keyed on `_identity_scoped_state_key(root, all_pairs)`, NOT
    T-2089's original `_tree_state_key(root)` -- the whole-tree key was
    correctly wired but too narrow to ever hit under concurrent-land
    load (HEAD moves on essentially every land in a busy multi-agent
    session, so a whole-tree key almost never repeats even when nothing
    relevant to THIS candidate set changed). The identity-scoped key
    only changes when a file actually named in `all_pairs` changes
    (committed OR uncommitted), so a cache HIT is now reachable across
    an unrelated land in between -- see `_identity_scoped_state_key`'s
    own docstring for the full reasoning and the "must not mask a
    genuine fix" soundness argument."""
    started = time.monotonic()
    tree_key = _identity_scoped_state_key(root, all_pairs)
    cached = _read_revalidation_cache(root, tree_key, all_pairs)
    if cached is _UNMEASURABLE_CACHE_SENTINEL:
        # T-5135 (H2): a prior re-check at this exact tree
        # state/identity set already timed out -- re-spawning the same
        # doomed 20s budget buys nothing, so reuse the cached NON-result
        # with 0 spawns instead. Still never treated as resolved: this
        # returns None, exactly like a fresh timeout would.
        _log.info(
            "rapid sweep: T-5135: doable-time re-verification of %d "
            "sweep-filed candidate ticket(s) (%d total identit(ies)) "
            "reused a cached UNMEASURABLE outcome for this exact, "
            "unchanged tree state -- 0 check spawn(s) (%.3fs)",
            n_candidates,
            len(all_pairs),
            time.monotonic() - started,
        )
        return None
    if cached is not None and not isinstance(cached, _UnmeasurableCacheSentinel):
        reproducing, cache_age_s = cached
        _log.info(
            "rapid sweep: T-2089: doable-time re-verification of %d "
            "sweep-filed candidate ticket(s) (%d total identit(ies)) "
            "reused a %.1fs-old cached result for this exact, unchanged "
            "tree state -- 0 check spawn(s) (%.3fs)",
            n_candidates,
            len(all_pairs),
            cache_age_s,
            time.monotonic() - started,
        )
        return reproducing

    # frob:ticket T-2106
    reproducing = _identities_still_reproducing(
        root, all_pairs, budget=_DOABLE_REVALIDATION_BUDGET_S
    )
    if reproducing is not None:
        reproducing = _normalize_identities(root, reproducing)
    elapsed_s = time.monotonic() - started
    if reproducing is None:
        _log.warning(
            "rapid sweep: T-2006: doable-time re-verification of %d "
            "sweep-filed candidate ticket(s) (%d total identit(ies)) was "
            "UNMEASURABLE after %.1fs -- leaving them dispatchable, "
            "never treating unmeasurable as resolved",
            n_candidates,
            len(all_pairs),
            elapsed_s,
        )
        # T-5135 (H2): memoize the negative outcome so the
        # NEXT call at this exact tree state/identity set does not
        # re-spawn the same doomed 20s re-check.
        _write_revalidation_cache(root, tree_key, all_pairs, None)
        return None
    _log.info(
        "rapid sweep: T-2006: doable-time re-verification of %d "
        "sweep-filed candidate ticket(s) (%d total identit(ies)) took "
        "%.1fs",
        n_candidates,
        len(all_pairs),
        elapsed_s,
    )
    _write_revalidation_cache(root, tree_key, all_pairs, reproducing)
    return reproducing


# frob:ticket T-2077
def _close_and_log_resolved_sweep_tickets(
    root: Path,
    final_id: str,
    baseline: frozenset[tuple[str, str]],
    fresh: frozenset[tuple[str, str]],
) -> tuple[str, ...]:
    """T-2058 (ARCH001 split of `run_deferred_post_land_sweep`): T-1983's
    close-the-loop pass -- diff `vanished` (identities the previous
    baseline had that `fresh` no longer finds) and drop every sweep-filed
    ticket now fully resolved by it, logging a summary when anything
    closed. Returns the same `_close_resolved_sweep_tickets` tuple
    unchanged; this only names and isolates the call plus its log line.

    T-2521: `fresh` reaching this point already passed `run_deferred_
    post_land_sweep`'s own completeness gates (no `--budget` deferral,
    no failed/silent tool result, via `_parse_error_findings_from_json`
    -> `_incomplete_tool_results`) -- the drop reason states that
    explicitly rather than merely asserting absence."""
    vanished = baseline - fresh
    closed = _close_resolved_sweep_tickets(
        root,
        final_id,
        vanished,
        "a full unscoped `frob check --json` run that completed with no "
        "budget deferral and no failed/silent tool stage",
    )
    if closed:
        _log.info(
            "rapid sweep: %s: closed the loop on %d resolved regression "
            "ticket(s) (T-1983): %s",
            final_id,
            len(closed),
            ", ".join(closed),
        )
    return closed


# frob:ticket T-2009
# frob:ticket T-2077
def _resolve_regression_attribution(
    root: Path,
    final_id: str,
    prev_baseline_commit: str | None,
    actual_head: str,
) -> list[str] | None:
    """T-2058 (ARCH001 split of `run_deferred_post_land_sweep`): T-2009's
    multi-land attribution decision -- `None` (trust `final_id` alone)
    unless more than one land landed between the previous sweep baseline
    and this sweep's actual measured HEAD, in which case every land id in
    that window is returned instead, logged once here."""
    if not prev_baseline_commit or prev_baseline_commit == actual_head:
        return None
    land_ids = _land_ids_between(root, prev_baseline_commit, actual_head)
    if len(land_ids) <= 1:
        return None
    _log.warning(
        "rapid sweep: %s: %d lands (%s) landed between the last "
        "sweep baseline and the tree this sweep actually "
        "measured -- attributing the regression to all of them "
        "instead of just %s (T-2009)",
        final_id,
        len(land_ids),
        ", ".join(land_ids),
        final_id,
    )
    return land_ids


# frob:doc \
# docs/modules/tickets-verify-sweep.md#deferred-post-land-sweep-rapid-only-t-1684
# frob:ticket T-2929
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_stale_baseline_refuses_to_file_and_records_debt  # noqa: E501
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_fresh_baseline_files_normally_no_new_noise  # noqa: E501
def _refuse_filing_for_stale_verification_queue(
    root: Path,
    final_id: str,
    new_findings: frozenset[tuple[str, str]],
    actual_head: str,
) -> bool:
    """T-2929 (ARCH001 split of `run_deferred_post_land_sweep`):
    `True` iff this sweep must NOT file a regression ticket for
    `new_findings` because `frob.verify.rapid_soft_warning` says the
    verification queue's own window is stale.

    Attribution's own TIER 2 (`frob.verify._attribution`) resolves "which
    land caused this" from the durable `VerifyQueueEntry` batch the
    `frob.verify` queue accumulated SINCE THE LAST WATERMARK ADVANCE --
    the exact same window `rapid_soft_warning` already measures and warns
    about (`frob verify status`). A stale watermark means that batch
    spans far more history than "the one land that just happened", so a
    doc-drift finding (DOC006 in particular, which flips as OTHER
    tickets get archived, not as code changes) can look "new" against
    the rolling baseline while being fully unrelated to `final_id` --
    measured directly this drive: 3 of 4 sweep-filed regression tickets
    (T-2868, T-2881, T-2882) were exactly this, dropped after
    independent re-measurement showed them pre-existing. Refusing to
    file here (rather than filing with a softened "unattributed source"
    title, the previous behavior) is the chosen fix: a sweep that knows
    its own attribution window is this stale should say so loudly and
    let the next, clean-baseline sweep re-evaluate, not produce a
    confidently wrong ticket. The rolling baseline write in the caller is
    UNCHANGED by this -- only the filing decision is gated -- so the next
    sweep still starts from a fresh, current comparison point."""
    from frob.verify import rapid_soft_warning

    stale_reason = rapid_soft_warning(root)
    if stale_reason is None:
        return False
    _log.error(
        "rapid sweep: %s deferred unscoped sweep found %d NEW (rule, "
        "file) identit(ies) at %s but REFUSED to file a regression "
        "ticket -- %s (a sweep whose verification-queue window is this "
        "stale cannot reliably attribute a new finding to the land that "
        "spawned it; filing here would be a confident wrong answer, not "
        "an honest one -- drain the debt with `frob verify now` and "
        "re-run this sweep by hand once it is current)",
        final_id,
        len(new_findings),
        actual_head[:12],
        stale_reason,
    )
    from frob.tickets._evidence import record_rapid_debt

    record_rapid_debt(
        root, final_id, "post-land-sweep-attribution-skipped-stale-baseline"
    )
    _commit_rapid_debt(root, final_id)
    return True


# frob:ticket T-2938
def _claim_divergence_finding_pairs(
    claims, fresh: frozenset[tuple[str, str]], ticket_scope: Sequence[str]
) -> tuple[tuple[str, str], ...]:
    """T-2938: reporting-only helper for `_check_claim_divergence_post_
    land` -- given the SAME `claims`/`fresh` pair `_reverify_gate_state_
    claim` (`frob.tickets._land_verify`, this repo's one audited
    ClaimDivergence comparator, called verbatim by the caller below) has
    ALREADY decided diverges, pick out which `(rule, file)` pairs to name
    in the filed ticket/quarantine record. Never used to DECIDE
    divergence -- only to describe one after the decision already ran --
    so this cannot become a second copy of the comparison policy the
    T-2924 investigation warned against. Mirrors `_reverify_gate_findings_
    by_identity`'s own `fresh - claims.error_findings`, scoped to `ticket_
    scope` computation exactly (same identity-set/scope-filter shape,
    duplicated here only because that function returns a bare `Result`
    with no way to hand its intermediate list back to a caller that does
    not itself refuse a land). Falls back to a single synthetic
    `("ClaimDivergence", "tickets.md")` identity when no per-finding
    identity set was captured at either done-report or sweep time (the
    count-only comparison path) -- this repo's standing "cannot name it
    precisely is never nothing to report" convention, not an empty
    result."""
    from frob.tickets._models import scope_matches

    if claims.error_findings is not None and fresh:
        scoped_new = tuple(
            sorted(
                (rule, file)
                for rule, file in (fresh - claims.error_findings)
                if scope_matches(file, ticket_scope)
            )
        )
        if scoped_new:
            return scoped_new
    return (("ClaimDivergence", "tickets.md"),)


# frob:ticket T-2938
# frob:doc docs/modules/tickets-verify-sweep.md#deferred-claim-divergence-check-t-2938
def _file_claim_divergence_ticket(
    root: Path,
    final_id: str,
    actual_head: str,
    pairs: tuple[tuple[str, str], ...],
) -> str | None:
    """T-2938: file one `bug` ticket recording that `final_id`'s own Done
    report claim (T-0754's captured gate-state claim) no longer holds
    against the post-merge tree this sweep measured at `actual_head` --
    the deferred-queue replacement for the inline `ClaimDivergence`
    refusal T-2913 removed from the rapid land critical path (see
    `_land_should_skip_inline_claims_reverify`'s own docstring for why:
    the inline `check_gates`/`check_gate_findings` spawn this comparison
    used to require was measured at 144-209s and was the single largest
    line item on a typical rapid land).

    Attribution here is exact by construction -- `final_id` IS the ticket
    whose own Done report diverged, so unlike `_file_regression_ticket`
    this needs none of T-1690's symbolic-reachability machinery to
    resolve "which land caused this." Mirrors that function's commit
    shape instead: `new_ticket(..., no_commit=True)` plus an explicit
    retry-then-discard commit (`_commit_or_discard_ledger_write`, the
    SAME shared primitive, so a claim-divergence write can never leave
    `root` dirty any more than a regression write can, T-2034/T-1841)."""
    from frob.tickets import TicketSpec, new_ticket
    from frob.tickets._models import Origin, Priority, TicketKind

    scope = tuple(
        sorted({_relativize_regression_scope_file(root, file) for _, file in pairs})
    )
    body = (
        f"Deferred post-land claim-divergence check (T-2938) found that "
        f"{final_id}'s Done report's captured gate-state claim (T-0754) "
        f"no longer holds against the tree this sweep measured at "
        f"{actual_head[:12]} -- reusing this sweep's own unscoped `frob "
        f"check` result as both the count and the per-finding identity "
        f"source, no second spawn.\n\n"
        "Diverging (rule, file) identit(ies):\n"
        + "\n".join(f"- {rule}: {file}" for rule, file in pairs)
        + "\n\nThis is a report-honesty finding, not necessarily bad "
        "content on main -- the land already published; the tree itself "
        "was already covered by this land's own pre-land check plus this "
        "sweep's unscoped post-land measurement. Determine whether the "
        "claim was a stale/incorrect capture or a real self-introduced "
        "regression, fix or refresh accordingly, then dispose the "
        "quarantine entry this ticket raised."
    )
    spec = TicketSpec(
        title=(
            f"claim divergence from {final_id}'s Done report "
            f"({len(pairs)} identit(ies))"
        ),
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        priority=Priority.HIGH,
        scope=scope,
        findings=pairs,
        body=body,
    )
    filed = new_ticket(root, spec, no_commit=True)
    if filed.is_err:
        _log.error(
            "rapid sweep: %s: failed to file the claim-divergence ticket "
            "(%s) -- quarantine will still be raised, with no filed "
            "ticket id to track disposition against",
            final_id,
            filed.danger_err,
        )
        return None
    filed_id = filed.danger_ok.id
    message = (
        f"chore(tickets): file {filed_id} (post-land claim divergence from {final_id})"
    )
    committed = _commit_or_discard_ledger_write(
        root,
        filed_id,
        message,
        max_attempts=_REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS,
        retry_delay_s=_REGRESSION_TICKET_COMMIT_RETRY_DELAY_S,
        discard=lambda: _discard_uncommitted_regression_ticket(root, filed_id),
        label="claim-divergence ticket",
    )
    if not committed:
        _log.error(
            "rapid sweep: %s: claim-divergence ticket write could not be "
            "committed (root stayed dirty through every retry) -- "
            "discarded rather than left uncommitted; quarantine will be "
            "raised with no filed ticket id",
            final_id,
        )
        return None
    return filed_id


# frob:doc docs/modules/tickets-verify-sweep.md#deferred-claim-divergence-check-t-2938
# frob:ticket T-2938
def _check_claim_divergence_post_land(
    root: Path,
    final_id: str,
    actual_head: str,
    fresh: frozenset[tuple[str, str]],
) -> None:
    """T-2938: the deferred-queue replacement for the inline
    `ClaimDivergence` re-verification T-2913 removed from the rapid land
    critical path. Runs unconditionally from `run_deferred_post_land_
    sweep` (independent of whether `fresh` contains any NEW findings --
    a stale-but-matching-reality claim and a fresh regression are
    different questions) reusing `fresh`, the exact unscoped check result
    that sweep already paid for -- no second `frob check` spawn.

    Reuses `frob.tickets._land_verify._reverify_gate_state_claim`
    VERBATIM as the comparison decision -- the same identity-based
    scope-filtered comparison, then count-only-refuse-on-increase
    fallback, the inline land path itself uses -- via two callables that
    hand back this sweep's already-measured `fresh` instead of spawning a
    second `frob check`. This is deliberate: T-2924's own investigation
    established that a cheap, `--only`-scoped reproduction of this
    comparison is UNSOUND (`--only` narrows what is compared; the T-0754
    comparator counts errors from ANY tool result) -- reusing the exact
    unscoped comparator, fed this sweep's own unscoped measurement,
    sidesteps that problem entirely rather than reintroducing a second,
    narrower copy of it here.

    Reuses `_refuse_filing_for_stale_verification_queue`'s underlying
    staleness policy (`frob.verify.rapid_soft_warning`) directly -- the
    SAME policy function, not a second one -- per T-2929's standing rule
    that a stale verification-queue window must refuse to attribute
    rather than report a confident wrong answer; a stale window here
    records the SAME `post-land-sweep-attribution-skipped-stale-baseline`
    debt reason T-2929 already established (one debt reason per policy,
    not one per caller).

    A ticket with no captured claim (a Done report written before T-0754,
    or one whose capture was itself skipped) is a no-op here, matching
    `_reverify_gate_state_claim`'s own permissive-by-default posture: an
    unmeasured claim was already disclosed loudly at done-report/land
    time, and re-disclosing "nothing to compare" on every single sweep
    thereafter would just be noise."""
    from frob.tickets import _load_one
    from frob.tickets._land_verify import _reverify_gate_state_claim
    from frob.tickets._models import parse_claims_from_done_report
    from frob.verify import rapid_soft_warning
    from frob.verify._quarantine import QuarantinedFinding, raise_quarantine

    stale_reason = rapid_soft_warning(root)
    if stale_reason is not None:
        _log.error(
            "rapid sweep: %s deferred claim-divergence check REFUSED to "
            "attribute -- %s (same T-2929 staleness policy the new-"
            "findings filing path already reuses; drain the debt with "
            "`frob verify now` and re-run this sweep by hand once it is "
            "current)",
            final_id,
            stale_reason,
        )
        from frob.tickets._evidence import record_rapid_debt

        record_rapid_debt(
            root, final_id, "post-land-sweep-attribution-skipped-stale-baseline"
        )
        _commit_rapid_debt(root, final_id)
        return

    loaded = _load_one(root, final_id)
    if loaded.is_err:
        _log.warning(
            "rapid sweep: %s not found at %s -- cannot re-verify its Done "
            "report's captured claim (already archived, or the ledger "
            "moved on)",
            final_id,
            root,
        )
        return
    ticket = loaded.danger_ok
    claims = parse_claims_from_done_report(ticket.body)
    if claims is None:
        _log.info(
            "rapid sweep: %s carries no Captured claims section -- "
            "deferred claim-divergence check has nothing to compare, "
            "skipping (matches the inline land path's own permissive-by-"
            "default posture for a ticket that never captured one)",
            final_id,
        )
        return

    outcome = _reverify_gate_state_claim(
        ticket,
        claims,
        final_id,
        check_gates=lambda: (len(fresh), None, None),
        check_gate_findings=lambda: fresh,
    )
    if outcome.is_ok:
        _log.info(
            "rapid sweep: %s deferred claim-divergence check: claim still "
            "holds (or was not re-verifiable this sweep) against %s -- no "
            "quarantine raised",
            final_id,
            actual_head[:12],
        )
        return

    pairs = _claim_divergence_finding_pairs(claims, fresh, ticket.scope)
    _log.error(
        "rapid sweep: %s deferred claim-divergence check: Done report "
        "claim DIVERGED from the tree measured at %s -- %d identit(ies) "
        "(%s)",
        final_id,
        actual_head[:12],
        len(pairs),
        sorted(pairs),
    )
    filed_id = _file_claim_divergence_ticket(root, final_id, actual_head, pairs)
    raised = raise_quarantine(
        root,
        batch_commit_shas=(actual_head,),
        findings=tuple(
            QuarantinedFinding(
                rule_id=rule,
                file=file,
                commit_sha=actual_head,
                ticket_id=filed_id if filed_id is not None else final_id,
            )
            for rule, file in pairs
        ),
    )
    if raised.is_err:
        _log.error(
            "rapid sweep: %s: raise_quarantine failed (%s) for the claim-"
            "divergence batch at %s -- the filed ticket (%s) is still the "
            "durable record; quarantine flag may be stale until the next "
            "red batch re-raises it",
            final_id,
            raised.danger_err,
            actual_head[:12],
            filed_id or "UNFILED",
        )


# frob:ticket T-4660
#: where a sweep's throwaway snapshot worktrees live -- under
#: `.frob/` (local, disposable, per-checkout, same posture as `_BASELINE_
#: REL` above), never `/tmp` directly, so they land on the SAME
#: filesystem as `root` (a same-filesystem `git worktree add` is a cheap
#: hardlink/checkout, not a cross-device copy) and are trivially found
#: and swept if a killed worker ever leaves one behind.
_SNAPSHOT_DIR_REL = Path(".frob") / "rapid-sweep-snapshots"

# frob:ticket T-4660
#: how long `_snapshot_worktree`'s own `git worktree add`/
#: `remove` calls may take -- these are plain filesystem checkouts, not
#: the multi-minute `frob check` that runs inside the result, so a
#: generous-but-bounded ceiling (rather than the check's own 1800s)
#: catches a genuinely wedged git process instead of hanging this
#: function forever.
_SNAPSHOT_WORKTREE_TIMEOUT_S = 120


# frob:ticket T-4660
@contextmanager
def _snapshot_worktree(root: Path, commit_sha: str) -> Iterator[Path | None]:
    """T-4660: check out `commit_sha` into a throwaway `git worktree`
    under `root`'s own `.frob/rapid-sweep-snapshots/`, so a full unscoped
    `frob check` can run against it INSTEAD of `root` -- see
    `_run_full_check_in_snapshot`'s docstring for why: the check
    subprocess's own `derived_state_lock` acquisition then lands on the
    SNAPSHOT's `.frob/derived.lock`, an entirely different file from
    `root`'s, so it can never be the thing a land's EXCLUSIVE acquire on
    `root`'s lock is waiting on.

    Yields `None` (never raises) when the worktree cannot be created --
    `commit_sha` does not resolve, `root` is not a git checkout at all,
    or `git` itself is unavailable -- so the caller can treat that as its
    own unmeasurable-this-round outcome. Always removes the worktree (and
    its directory) on exit, success or failure, so a killed sweep leaves
    at most one stale snapshot directory behind rather than accumulating
    one per land."""
    snapshot_dir = root / _SNAPSHOT_DIR_REL
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="sweep-", dir=snapshot_dir))
    registered = False
    try:
        added = subprocess.run(  # noqa: S603 -- fixed argv, root-relative git call
            ["git", "worktree", "add", "--detach", "--force", str(tmp), commit_sha],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=_SNAPSHOT_WORKTREE_TIMEOUT_S,
        )
        if added.returncode != 0:
            _log.error(
                "rapid sweep: T-4660 snapshot worktree add failed for %s (rc=%d): %s",
                commit_sha[:12],
                added.returncode,
                added.stderr.strip(),
            )
            yield None
            return
        registered = True
        yield tmp
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.error(
            "rapid sweep: T-4660 snapshot worktree add for %s raised %s: "
            "%s -- treating as unavailable this round",
            commit_sha[:12],
            type(exc).__name__,
            exc,
        )
        yield None
    finally:
        if registered:
            removed = subprocess.run(  # noqa: S603 -- fixed argv
                ["git", "worktree", "remove", "--force", str(tmp)],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=_SNAPSHOT_WORKTREE_TIMEOUT_S,
            )
            if removed.returncode != 0:
                _log.warning(
                    "rapid sweep: T-4660 snapshot worktree remove failed "
                    "for %s (rc=%d): %s -- removing the directory directly",
                    tmp,
                    removed.returncode,
                    removed.stderr.strip(),
                )
        shutil.rmtree(tmp, ignore_errors=True)


# frob:ticket T-4660
def _run_full_check_in_snapshot(
    root: Path, final_id: str, commit_sha: str
) -> Result[frozenset[tuple[str, str]], RapidSweepError]:
    """T-4660: the bounded-lock-window replacement call site for the
    sweep's full unscoped check -- runs it inside a throwaway
    `_snapshot_worktree` of `commit_sha` instead of directly against
    `root`, so its `derived_state_lock` SHARED hold (for the check's
    entire multi-minute run) lands on the snapshot's own lock file, never
    on `root`'s. This is the fix for the measured incident: a land's
    EXCLUSIVE acquire on `root`'s `.frob/derived.lock` no longer waits on
    a sweep's check at all, because the sweep's check never takes that
    lock in the first place -- not "bounded", genuinely absent.

    Delegates the actual spawn/parse to `_land_cmd`'s own
    `_unscoped_error_findings(effective_root, final_id, full=True)`
    UNCHANGED -- only `effective_root` differs from the pre-T-4660 call
    site (`snapshot_root` when the snapshot could be created, `root`
    itself as a degrade otherwise). This keeps the finding-identity
    format, the `FROB_ALLOW_FULL_CHECK`/1800s-ceiling/budget-deferral-
    detection semantics, and every existing caller's mock seam (tests
    that monkeypatch `_land_cmd._unscoped_error_findings` directly) as
    the ONE implementation, rather than a second hand-duplicated spawn/
    parse path here.

    Falls back to `root` itself -- the pre-T-4660 call shape -- ONLY when
    `root` is not a usable git checkout for `_snapshot_worktree` (e.g. a
    plain directory in a unit test fixture, or `commit_sha` does not
    resolve). A real land always runs inside a real git checkout, so this
    fallback is never exercised in production.

    The SECOND measured incident (a check child surviving its dead sweep
    worker) is a separate, filed follow-up (T-4686): closing it
    properly needs a new `process-control` capability declaration in
    `design/frob.strata`'s `cli` node, which is currently leased by
    another in-progress ticket (T-4112) -- see that follow-up ticket's
    body for the design and the `ScopeLeaseConflict` this ticket hit
    trying to add it here."""
    from frob.app.ticket_runner._land_cmd import _unscoped_error_findings

    with _snapshot_worktree(root, commit_sha) as snapshot_root:
        effective_root = root if snapshot_root is None else snapshot_root
        if snapshot_root is None:
            _log.warning(
                "rapid sweep: %s T-4660 snapshot worktree unavailable -- "
                "falling back to checking root directly (pre-T-4660 "
                "behavior); a real git checkout never hits this path",
                final_id,
            )
        else:
            _log.debug(
                "rapid sweep: %s T-4660 running the full check against "
                "snapshot %s -- root's own derived.lock is never touched",
                final_id,
                snapshot_root,
            )
        # T-4660: matches the exact pre-fix call shape (no `base`) --
        # `_measure_fresh_sweep_state`'s caller never threaded a target
        # branch through this seam either.
        fresh = _unscoped_error_findings(effective_root, final_id, full=True)
        if fresh is None:
            return Err(RapidSweepError.Unmeasurable)
        return Ok(fresh)


# frob:ticket T-1684
# frob:ticket T-2009
# frob:ticket T-2571
# frob:ticket T-2595
# frob:ticket T-4318
# frob:ticket T-4335
# frob:ticket T-4660
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_calls_unscoped_error_findings_with_full_true  # noqa: E501
def _measure_fresh_sweep_state(
    root: Path, final_id: str, commit_sha: str
) -> Result[
    tuple[
        frozenset[tuple[str, str]], frozenset[tuple[str, str]] | None, str | None, str
    ],
    RapidSweepError,
]:
    """T-2929 (ARCH001 split of `run_deferred_post_land_sweep`); T-4335
    (split OFF the unconditional baseline write this function used to do
    -- see `_persist_baseline` and the T-4335 note on its former write
    site below): the measure-only half of the sweep -- run the unscoped
    check and normalize/filter the fresh set, WITHOUT touching the
    persisted baseline. Returns `(fresh, prior_baseline, prev_baseline_
    commit, actual_head)`, where `prior_baseline` is `None` on a first
    sweep (no baseline existed yet -- the caller's own signal to record-
    and-file-nothing) and `Err(Unmeasurable)` when the check itself
    produced no parsable error set.

    T-4335: the caller alone decides what to persist and when, AFTER it
    knows whether `fresh`'s new identities (relative to `prior_baseline`)
    got filed as a regression ticket. This function used to CAS-write
    `fresh` unconditionally right here, before that filing decision even
    ran -- which meant a new error identity that `run_deferred_post_land_
    sweep` went on to REFUSE to file (T-2929's stale-verification-queue
    guard) was already baked into the baseline as tolerated debt, so
    every later sweep compared against a baseline that had silently
    absorbed it and reported CLEAN forever. Moving the write to the
    caller, after the filing decision, lets an unfiled new identity stay
    OUT of what gets persisted so the next sweep still sees it as new.

    T-4318: calls `_unscoped_error_findings` with `full=True`. This
    function runs ONLY inside the detached `frob ticket sweep-async`
    child (`spawn_deferred_post_land_sweep`'s `start_new_session=True`
    subprocess) -- nobody is waiting on its wall clock the way a land
    someone typed and is watching is. The prior default (`full=False`,
    a `--budget` derived by `_derive_post_land_sweep_budget_s` for an
    INLINE foreground land) bought this detached child zero latency
    benefit while costing it the entire measurement under fleet load:
    a truncated `--budget` run defers stage groups, and `_unscoped_
    error_findings`'s own (correct, unchanged) T-1703 refusal turns any
    deferral into `None` -- so a busy fleet made every deferred sweep
    UNMEASURABLE, which was in fact all five lands on 2026-09-08
    (T-4197, T-4301, T-4305, T-4306, T-4307). `full=True` was already
    built for exactly this shape of caller (see `_unscoped_error_
    findings`'s own T-3001 docstring, which names "the detached,
    `ionice`-idle watermark drain child" as one of its two intended
    users) and is already used by `frob verify now`
    (`frob.verify._worker._default_verify_fn`) -- this call site simply
    never opted in. `full=True` drops `--budget` entirely and uses
    `_FULL_CHECK_TIMEOUT_S` (1800s) as its hard ceiling instead, so this
    sweep now measures the real tree rather than a wall-clock-truncated
    guess of it."""
    _log.info(
        "rapid sweep: %s starting deferred unscoped sweep at %s",
        final_id,
        commit_sha[:12],
    )
    # T-4660: routed through the snapshot-worktree spawn (never `root`
    # itself) so this multi-minute full check's own `derived_state_lock`
    # hold can never be the thing a land's EXCLUSIVE acquire on `root`'s
    # `.frob/derived.lock` waits on -- see `_run_full_check_in_snapshot`'s
    # docstring.
    measured_fresh = _run_full_check_in_snapshot(root, final_id, commit_sha)
    if measured_fresh.is_err:
        _log.error(
            "rapid sweep: %s deferred unscoped sweep was UNMEASURABLE "
            "(refused spawn, timeout, or unparsable output) -- baseline "
            "left as-is, commit %s stays unverified",
            final_id,
            commit_sha[:12],
        )
        return Err(measured_fresh.danger_err)
    fresh = measured_fresh.danger_ok
    # T-2036: normalize BEFORE any comparison/baseline-write
    # below -- everything downstream (new_findings, vanished, the
    # persisted baseline, the recorded ticket identities) must see the
    # SAME repo-relative form the parsed/read sides already normalize to.
    fresh = _normalize_identities(root, fresh)

    # T-2009: the baseline's `commit` must record what was ACTUALLY
    # measured (this sweep's real HEAD at the moment `fresh` finished),
    # not `commit_sha` (the land that merely SPAWNED this detached
    # process) -- other agents' lands routinely land in between, since
    # taking the sweep off the land critical path (T-1684) is the whole
    # point. `prev_baseline_commit` (read BEFORE the rewrite below) is
    # what lets the NEXT sweep compute an honest land-range via
    # `_land_ids_between` instead of guessing.
    prev_baseline_commit = _read_baseline_commit(root)
    actual_head = _resolve_actual_head(root, commit_sha)

    # T-2571 acceptance criterion 1: a (rule, file) identity naming a
    # file git itself confirms was DELETED in the measured window can
    # never be a real regression -- filtered before it can enter the
    # baseline write or the new_findings diff below.
    deleted_files = _files_deleted_between(root, prev_baseline_commit, actual_head)
    fresh = _filter_phantom_deleted_findings(final_id, fresh, deleted_files)

    baseline = _read_baseline(root)
    # T-4335: the baseline write used to happen right here, unconditionally,
    # before the caller had even computed `new_findings` let alone decided
    # whether they got filed. See `_persist_baseline` -- the caller now
    # calls it once it knows exactly what should be persisted.
    return Ok((fresh, baseline, prev_baseline_commit, actual_head))


# frob:ticket T-4335
def _persist_baseline(
    root: Path,
    final_id: str,
    to_persist: frozenset[tuple[str, str]],
    actual_head: str,
) -> None:
    """T-4335 (extracted from the former unconditional write inside what
    is now `_measure_fresh_sweep_state`): CAS-write `to_persist` as the
    rolling baseline the NEXT deferred sweep diffs against, and warn if a
    concurrent sweep's fresher write is detected to have been lost.

    Callers choose `to_persist` deliberately -- it is NOT always `fresh`.
    A new identity that `run_deferred_post_land_sweep` filed a ticket for
    (or that was already establishing the first-ever baseline) belongs in
    it; a new identity that sweep explicitly REFUSED to file (T-2929's
    stale-verification-queue guard) must NOT be in it, or it is absorbed
    as tolerated debt with no ticket ever tracking it (T-4335's bug)."""
    # T-2595: was an unconditional, unlocked `_write_baseline` -- now a
    # locked compare-and-swap that refuses to overwrite a concurrent
    # sweep's FRESHER write with this sweep's stale one (see `_write_
    # baseline_cas`'s docstring for the full race this closes).
    wrote = _write_baseline_cas(root, to_persist, actual_head)
    # T-2571 acceptance criterion 0: detect (never silently trust) a
    # concurrent sweep clobbering this write before the next sweep ever
    # reads it -- root is the SHARED checkout every land's own detached
    # sweep writes to (T-1684), and concurrent lands are routine. Only
    # meaningful when this sweep actually wrote: a CAS-skipped write
    # (`wrote` is `False`) already logged its own, more precise reason
    # above and has nothing new to survive.
    if wrote and not _baseline_write_survived(root, actual_head):
        _log.warning(
            "rapid sweep: %s: the rolling baseline this sweep just wrote "
            "at %s did NOT survive -- another process (almost certainly "
            "a concurrent land's own detached sweep racing on the same "
            "shared root) overwrote it before this check could even "
            "finish; the NEXT sweep may re-report identities from THIS "
            "sweep's fresh set as new again through no fault of its own "
            "(T-2571; T-2595 closed the common case of this via CAS, but "
            "a write that itself raced past this same check's read can "
            "still in principle be observed here)",
            final_id,
            actual_head[:12],
        )


# frob:doc \
# docs/modules/tickets-verify-sweep.md#deferred-post-land-sweep-rapid-only-t-1684
# frob:ticket T-2077
# frob:ticket T-1952
# frob:ticket T-2595
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_no_new_findings_is_clean  # noqa: E501
# frob:waive AFFECT001 reason="T-2595 only replaces the baseline write's internal \
# mechanics (an unconditional unlocked write becomes a locked compare-and-swap) -- it \
# does not change this function's own documented external contract (still: one check \
# per sweep, file a ticket for new findings, record the fresh set as the next \
# baseline). docs/modules/tickets-verify-sweep.md is a shared doc other in-flight \
# tickets also touch; a prose note on the internal race-safety mechanism belongs in a \
# follow-up doc pass, not blocking this bug fix, matching T-2521's identical posture \
# on this same file just above"
# frob:ticket T-1684
# frob:ticket T-2929
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_stale_baseline_refuses_to_file_and_records_debt  # noqa: E501
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_fresh_baseline_files_normally_no_new_noise  # noqa: E501
# frob:ticket T-2938
# frob:ticket T-4335
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_stale_baseline_refusal_is_still_new_on_the_next_sweep  # noqa: E501
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_inherited_debt_is_reported_as_debt_not_clean  # noqa: E501
# tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_genuinely_zero_errors_still_says_clean  # noqa: E501
# frob:waive DRIFT001 reason="T-4335 DOES change this function's external contract (a \
# new identity is now only rolled into the rolling baseline once it is actually \
# filed/accounted for, never on a stale-verification-queue refusal) -- the fix to \
# docs/modules/tickets-verify-sweep.md#deferred-post-land-sweep-rapid-only-t-1684 is \
# real, needed work, not skippable, but filed as a separate ticket (see T-4335's Done \
# report) because this doc's own frob:describes network pulls in ~170 unrelated \
# symbols across the whole verify/land subsystem on scope closure the moment the file \
# enters a ticket's scope -- the same disproportionate-closure shape T-2521's existing \
# AFFECT001 waiver just above already accepted on this identical file for the same \
# reason (a shared doc many in-flight tickets touch)"
def run_deferred_post_land_sweep(
    root: Path, final_id: str, commit_sha: str
) -> Result[str | None, RapidSweepError]:
    """The detached child's whole job (`frob ticket sweep-async`): run one
    unscoped `frob check` over `root`, diff it against the rolling
    baseline, file a bug ticket for anything new, and record the fresh set
    as the next baseline.

    Returns the filed ticket id, or `Ok(None)` when the sweep was clean or
    had no baseline to compare against. `Err(Unmeasurable)` when the check
    itself produced no parsable error set -- the baseline is left
    untouched in that case, so an unmeasurable run degrades to "compare
    against the last set we actually trust" rather than silently adopting
    a guess as ground truth.

    T-2938: also runs `_check_claim_divergence_post_land`, unconditionally,
    against the SAME `fresh` this function already measured -- a Done
    report claim divergence is independent of whether this sweep also
    found a NEW regression finding, so it is checked regardless of the
    `baseline is None`/`not new_findings` early-outs below. Its own
    outcome (quarantine raised or not) is not reflected in this
    function's return value -- that stays exactly what it was before
    (the filed regression ticket id, if any) -- a caller that wants to
    know whether claim divergence specifically fired reads the quarantine
    record or the log.

    T-4335: WHAT GETS PERSISTED as the next baseline is now decided HERE,
    per branch, via `_persist_baseline` -- never inside the measurement
    step. A rolling baseline is the right tool for INHERITED debt (an
    identity already present in the prior baseline): tolerating it without
    re-filing is correct and unchanged. It must never be the tool for an
    identity that FIRST APPEARS in `fresh` relative to the prior baseline
    (`new_findings` below) unless that identity is actually accounted for
    -- either filed as a regression ticket just now, or (the `baseline is
    None` branch) there was no prior baseline to compare against at all,
    so recording everything found is establishing the initial baseline,
    not growing an existing one. The one case that used to slip through
    both of those (T-2929's stale-verification-queue refusal below) is
    filed nowhere, so its identities are deliberately EXCLUDED from what
    gets persisted -- the next sweep must still see them as new."""
    measured = _measure_fresh_sweep_state(root, final_id, commit_sha)
    if measured.is_err:
        return Err(measured.danger_err)
    fresh, baseline, prev_baseline_commit, actual_head = measured.danger_ok

    _check_claim_divergence_post_land(root, final_id, actual_head, fresh)

    if baseline is None:
        # T-4335: no prior baseline at all -- ESTABLISHING an initial
        # baseline, not growing one. Recording everything found here is
        # correct (the alternative is filing the entire pre-existing
        # backlog as "new" the moment a baseline is reset), and every
        # identity here is accounted for by that same act of establishing.
        _persist_baseline(root, final_id, fresh, actual_head)
        _log.warning(
            "rapid sweep: %s had no rolling baseline -- ESTABLISHED an "
            "initial baseline of %d error(s) and filed nothing; the NEXT "
            "land's sweep is the first one that can attribute a "
            "regression against it",
            final_id,
            len(fresh),
        )
        return Ok(None)

    new_findings = fresh - baseline

    # frob:ticket T-1983
    # T-1983: run the close pass regardless of whether this sweep is
    # otherwise clean or red -- a resolved regression ticket and a
    # brand-new one are independent outcomes of the same measurement.
    _close_and_log_resolved_sweep_tickets(root, final_id, baseline, fresh)

    if not new_findings:
        _persist_baseline(root, final_id, fresh, actual_head)
        if fresh:
            # T-4335: this used to say "CLEAN (%d error(s))" -- a summary
            # naming a nonzero error count must never also claim CLEAN.
            # These are pre-existing (inherited) identities the rolling
            # baseline is deliberately tolerating, not zero errors.
            _log.info(
                "rapid sweep: %s deferred unscoped sweep found 0 NEW "
                "identit(ies) vs the previous baseline -- %d pre-existing "
                "error(s) remain as TOLERATED DEBT, not clean",
                final_id,
                len(fresh),
            )
        else:
            _log.info(
                "rapid sweep: %s deferred unscoped sweep CLEAN (0 error(s))",
                final_id,
            )
        return Ok(None)

    if _refuse_filing_for_stale_verification_queue(
        root, final_id, new_findings, actual_head
    ):
        # T-4335: the refused identities are NOT filed anywhere, so they
        # must not enter the persisted baseline either -- only what was
        # already known (`fresh - new_findings`) is safe to roll forward.
        # The next sweep will recompute the SAME `new_findings` against
        # this unchanged tolerated set and get another chance to file
        # once the verification queue is current again.
        tolerated = fresh - new_findings
        _persist_baseline(root, final_id, tolerated, actual_head)
        return Ok(None)

    filed = _attribute_and_file_regression(
        root, final_id, prev_baseline_commit, actual_head, new_findings
    )
    # T-4335: only NOW, once the new identities are actually accounted for
    # (filed as a fresh regression ticket, or disposed to an existing
    # duplicate that already tracks them), is it safe to persist `fresh`
    # -- otherwise a filed-but-then-lost ticket would leave them absorbed
    # with nothing tracking them, the exact shape this ticket fixes.
    _persist_baseline(root, final_id, fresh, actual_head)
    return Ok(filed)


# frob:ticket T-2009
def _attribute_and_file_regression(
    root: Path,
    final_id: str,
    prev_baseline_commit: str | None,
    actual_head: str,
    new_findings: frozenset[tuple[str, str]],
) -> str | None:
    """T-2929 (ARCH001 split of `run_deferred_post_land_sweep`):
    the tail this function's caller reaches once `new_findings` is
    non-empty and the stale-verification-queue refusal above did not
    fire -- T-2009's multi-land attribution, `_file_regression_ticket`,
    and the final log line naming what got filed."""
    # T-2009: only trust `final_id` as the sole attribution when the
    # window between the previous baseline and this sweep's actual HEAD
    # contains exactly one land -- otherwise name every land that
    # occurred in it, so the filed ticket is never pinned on the wrong
    # (or merely coincidental) land.
    attributed_ids = _resolve_regression_attribution(
        root, final_id, prev_baseline_commit, actual_head
    )
    if attributed_ids is not None:
        filed = _file_regression_ticket(
            root, final_id, actual_head, new_findings, attributed_ids=attributed_ids
        )
    else:
        filed = _file_regression_ticket(root, final_id, actual_head, new_findings)
    _log.error(
        "rapid sweep: %s deferred unscoped sweep found %d NEW (rule, "
        "file) identit(ies) at %s -- filed as %s (the commit stands; "
        "rapid never reverts published history; T-1935: this is a "
        "distinct-identity count, not a raw per-finding count -- see "
        "the filed ticket's body for the caveat)",
        final_id,
        len(new_findings),
        actual_head[:12],
        filed or "UNFILED",
    )
    return filed


# frob:ticket T-4414
def _begin_sweep_run(root: Path, worker_pid: int) -> list[dict[str, Any]]:
    """T-4414: transition the persisted window state from `"window_open"`
    to `"sweep_running"` and return the exact batch of lands (`pending_
    lands`, oldest first) this worker is about to sweep. The state's own
    `pending_lands` is reset to `[]` in the SAME locked read-decide-write,
    so a land that registers itself WHILE this run is in progress
    accumulates into a fresh list for the NEXT window (`_decide_land_
    registration`'s `"defer"` action) instead of being silently folded
    into the batch already being measured underneath it."""
    with _window_lock(root):
        state = _read_window_state(root)
        batch = list(state.get("pending_lands", []))
        state["phase"] = "sweep_running"
        state["worker_pid"] = worker_pid
        state["pending_lands"] = []
        _write_window_state(root, state)
    return batch


# frob:ticket T-4414
def _finish_sweep_run(root: Path, worker_pid: int) -> list[dict[str, Any]] | None:
    """T-4414: called once a batch's `frob check` has finished. Under
    `_window_lock`, reads whatever accumulated in `pending_lands` WHILE
    that run was in progress: non-empty means at least one land deferred
    to "the next window" (`_decide_land_registration`'s `"defer"`
    action), so this SAME worker process becomes that next window's
    worker too -- returned (non-`None`) so `_sweep_async` loops back to
    sleeping out the next window instead of exiting, meaning NO new
    detached process is ever spawned purely to cover a batch that landed
    mid-run (acceptance criterion 3). An empty `pending_lands` resets the
    state to idle (`worker_pid=None`) and returns `None`, telling the
    caller to exit for good."""
    with _window_lock(root):
        state = _read_window_state(root)
        pending = list(state.get("pending_lands", []))
        if pending:
            state["phase"] = "window_open"
            state["window_opened_at"] = time.time()
            state["worker_pid"] = worker_pid
            _write_window_state(root, state)
            return pending
        state["phase"] = "idle"
        state["window_opened_at"] = None
        state["worker_pid"] = None
        state["pending_lands"] = []
        _write_window_state(root, state)
        return None


# frob:ticket T-1684
# frob:ticket T-4414
def _sweep_async(root: Path, cfg) -> None:  # noqa: ANN001 -- AppConfig, deferred import
    """`frob ticket sweep-async <id> --commit <sha>`: the CLI entry point
    the detached child runs. Exits 0 whether every batch it swept was
    clean, filed a regression ticket, or found no baseline -- this
    process's exit status is nobody's gate (the land(s) that spawned it
    finished minutes ago); the filed ticket(s) and the log are the
    outputs. Exits non-zero only if any batch it ran was UNMEASURABLE, so
    a human re-running this by hand can tell "verified" from "could not
    verify".

    T-4414: this is now a WINDOW WORKER, not a one-shot run -- the
    detached process this CLI verb starts IS the worker `spawn_deferred_
    post_land_sweep` recorded as `worker_pid` when it opened the window.
    It sleeps out the remainder of the current window (reading the
    deadline from the persisted state, since more lands may have joined
    -- or the window may have been opened slightly before this process
    actually got CPU time -- since `spawn_deferred_post_land_sweep`
    wrote it), runs exactly ONE batched `run_deferred_post_land_sweep`
    call for whatever landed in that window (`_begin_sweep_run`'s
    batch), then checks whether anything landed WHILE it was running
    (`_finish_sweep_run`): if so, it loops back and becomes the worker
    for THAT window too, rather than exiting and making the next land's
    `spawn_deferred_post_land_sweep` call spawn a fresh process -- the
    mechanical reason two lands separated only by this run's own
    duration still collapse onto one sweep instead of two. `final_id`/
    `commit_sha` (the CLI's own `<id>`/`--commit` argv, i.e. the FIRST
    land that opened the window) are the fallback anchor for a batch
    that somehow ends up empty (a state read racing a concurrent
    writer); an ordinary batch anchors on its OWN last (most recent)
    land instead, so the filed ticket's title/commit names the freshest
    land in it, not necessarily the one whose process happened to spawn
    the worker.

    T-2261: also runs `sweep_stale_worktrees_after_land` after EVERY
    batch, unconditionally, regardless of that batch's own gate-check
    outcome -- unchanged from pre-T-4414 (the two are independent
    concerns); a worktree-sweep failure is logged, never escalated
    here."""
    if cfg.ticket_id is None or not getattr(cfg, "ticket_sweep_commit", None):
        _log.error("frob ticket sweep-async requires <id> and --commit <sha>")
        sys.exit(1)

    worker_pid = os.getpid()
    fallback_land = {
        "ticket_id": cfg.ticket_id,
        "final_id": cfg.ticket_id,
        "commit_sha": cfg.ticket_sweep_commit,
    }
    any_unmeasurable = False
    while True:
        _sleep_out_current_window(root)
        batch = _begin_sweep_run(root, worker_pid)
        unmeasurable = _run_one_sweep_batch(root, batch, fallback_land)
        any_unmeasurable = any_unmeasurable or unmeasurable

        pending = _finish_sweep_run(root, worker_pid)
        if pending is None:
            _log.info(
                "rapid sweep: window worker pid=%d idle -- nothing pending, exiting",
                worker_pid,
            )
            break
        _log.info(
            "rapid sweep: %d land(s) joined while the previous batch's "
            "sweep was running -- continuing as the SAME worker for the "
            "next window (no new process spawned)",
            len(pending),
        )

    if any_unmeasurable:
        sys.exit(1)


# frob:ticket T-4414
def _sleep_out_current_window(root: Path) -> None:
    """T-4414 (ARCH001 split of `_sweep_async`): sleep until the
    currently-open window's deadline (`window_opened_at` from the
    persisted state, plus `_sweep_window_seconds`). A missing `window_
    opened_at` (a state read racing a concurrent writer) falls back to
    `time.time()`, i.e. no sleep -- degrading to "run now" is always
    safe here, unlike sleeping an unbounded/negative amount would be."""
    state = _read_window_state(root)
    deadline = (state.get("window_opened_at") or time.time()) + (
        _sweep_window_seconds(root)
    )
    remaining = deadline - time.time()
    if remaining > 0:
        time.sleep(remaining)


# frob:ticket T-4414
def _run_one_sweep_batch(
    root: Path, batch: list[dict[str, Any]], fallback_land: dict[str, Any]
) -> bool:
    """T-4414 (ARCH001 split of `_sweep_async`): the single-batch body a
    window worker runs once per window -- anchors on the batch's own
    LAST (most recent) land, or `fallback_land` (the CLI's own `<id>`/
    `--commit` argv, i.e. the FIRST land that opened the window) when
    `batch` is somehow empty (a state read racing a concurrent writer).
    Runs `run_deferred_post_land_sweep` plus the unconditional T-2261
    worktree sweep, unchanged from pre-T-4414 behavior for a single
    land. Returns whether this batch's check was UNMEASURABLE, so the
    caller's loop can accumulate that across every batch a worker runs
    without exiting on the first one (a later window's batch may still
    measure cleanly)."""
    final_id = batch[-1]["final_id"] if batch else fallback_land["final_id"]
    commit_sha = batch[-1]["commit_sha"] if batch else fallback_land["commit_sha"]
    _log.info(
        "rapid sweep: window CLOSED -- running ONE batched sweep for "
        "%d land(s) (%s), anchored at %s",
        len(batch),
        ", ".join(land.get("ticket_id", "?") for land in batch) or "none",
        commit_sha[:12],
    )
    # T-4414: `FROB_LAND_TARGET_BRANCH` is NOT re-derived from the batch's
    # own last land here -- it is already set in THIS process's
    # environment by `_detached_sweep_env` at the moment `_spawn_sweep_
    # worker` spawned this worker (T-4105's own mechanism, unchanged),
    # and stays set for every batch this same worker loops through.
    # Re-assigning `os.environ` per batch would only matter for a worker
    # whose later windows carry a DIFFERENT target branch than its first
    # (an edge case this function's own log line above -- not a silent
    # behavior change -- makes visible via `final_id`/`commit_sha`
    # regardless), and doing it here would be exactly the undeclared
    # `env.write` capability effect this CLI entrypoint's own strata/
    # SEC110 gates flag a bare `os.environ[...] = ...` for.
    result = run_deferred_post_land_sweep(root, final_id, commit_sha)
    sweep_stale_worktrees_after_land(root)
    return result.is_err


__all__ = [
    "RapidSweepError",
    "revalidate_dispatchable_sweep_tickets",
    "run_deferred_post_land_sweep",
    "spawn_deferred_post_land_sweep",
    "sweep_stale_worktrees_after_land",
]
