"""frob.tickets._unlanded -- finished-but-unlanded branch work detector
(T-1934, T-1948).

MEASURED LEAK (T-1934, 2026-08-09): an agent can finish a ticket, commit
everything cleanly in its worktree, and die before ever invoking `frob
ticket land`. Because the tree is clean, `frob worktree sweep`'s dirtiness
heuristic marks the worktree removable -- the BETTER an agent behaved
(committed instead of leaving junk), the MORE likely its finished work is
swept, since sweep never consults branch content vs. main at all. This is
the third of three crash windows this repo's ledger machinery covers:

  1. crash DURING `frob ticket land`     -> `frob.tickets._journal`'s
     intent marker, surfaced by `reconcile`'s `orphaned_land_intents`.
  2. crash AFTER commit, BEFORE land     -> THIS MODULE.
  3. crash BEFORE commit (dirty tree)    -> `frob worktree sweep`'s
     existing `kept:dirty` verdict.

Pure git plumbing, no checkout, no test runs (the ticket's own working
prototype): scan every local branch's `tickets/T-####/` tree for a
`done-report.md` file, or a `ticket.md` whose OWN `state:` field reads
`done`/`dropped`, then resolve that ticket id's state on `main` --
INCLUDING the archive (`tickets/archive/T-####/ticket.md`), never by path
existence alone. A first attempt that keyed on "does this path exist on
main" produced 186 false positives, because a done ticket is ARCHIVED on
main, not left in place (see `tests/unit/test_unlanded_branch_work.py`'s
own regression test for this exact shape). A ticket whose CURRENT
cross-worktree lease `frob.tickets._leases.lease_staleness_reason` judges
still live (a real agent working it right now, elsewhere) is never
reported -- reused directly, not re-derived, per this repo's own
"one staleness predicate" precedent (T-1806).

Report-only, by design (T-1934's REQUIRED section): nothing here lands,
requeues, or removes anything. `frob.tickets._reconcile.reconcile` surfaces
the result as a THIRD anomaly class alongside its existing two (T-0476)
plus the T-0456 orphaned-land-intent class, rather than a fourth standalone
CLI verb -- one place a coordinator already runs to ask "what is
inconsistent?" (a specific correction on this ticket, once the obvious
`frob ticket reconcile`/journal overlap was pointed out mid-dispatch:
sweep/reconcile already own worktree<->lease drift; this module owns
BRANCH-CONTENT-vs-main drift, a dimension neither previously read at all).
`frob.tickets._leases.sweep_worktrees` also consults this module directly
(a `kept:unlanded` verdict, ranked ABOVE the dirty-tree gate) so a clean,
unlanded worktree is never swept just because it behaved.

T-1948 DETECTOR GAP (measured against a real specimen, 2026-08-10): the
two signals above both key on a "finished" marker -- a `done-report.md`
file, or `ticket.md`'s own `state:` reading `done`/`dropped`. Neither
exists for `frob:ticket`-ANCHORED code whose own `ticket.md` was simply
never updated at all (real specimen: `t1552-ledger-v2`'s T-1691 carried
525 committed lines opening with a `frob:ticket T-1691` directive
comment, while its `ticket.md` sat at `state: queued` the whole time --
invisible to both existing signals since neither a done-report nor a
`state: done/dropped` was ever written). A THIRD signal,
`"directive-anchored"` (`_directive_anchor_signals_on_branch`), closes
this: scan the branch's OWN changed, non-`tickets/**` files for a
`frob:ticket T-####` directive comment, then read that id's OWN
`ticket.md` state ON THE SAME BRANCH -- if it disagrees with "real work
is in flight" (anything other than `in-progress`, including missing
entirely or still `queued`), the anchored code is invisible proof of
work the ledger itself never recorded. Deliberately narrower than
T-1934's own two signals: it only reads COMMITTED branch content (never
the working tree) -- an uncommitted directive-anchored file is `frob
worktree sweep`'s existing `kept:dirty` gate's job, not this module's,
per T-1948's own explicit scope note.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import KeysView

from pydantic import BaseModel

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._leases import _LeaseRecord, lease_staleness_reason, read_all_leases

_log = get_logger(__name__)

# `tickets/T-<id>/ticket.md` or `tickets/T-<id>/done-report.md`, v2 ledger
# layout (design/ledger-v2.md section 1) -- deliberately excludes
# `tickets/archive/**`, which is a resolved-and-done ticket's home on a
# HEALTHY branch, never a signal of unlanded work on that branch itself.
_TICKET_PATH_RE = re.compile(
    r"^tickets/(T-[0-9A-Za-z][0-9A-Za-z-]*)/(ticket\.md|done-report\.md)$"
)
_STATE_RE = re.compile(r"(?m)^state:\s*(\S+)\s*$")

# The two ledger states `frob.tickets._models.TicketState` treats as
# terminal (`DONE`, `DROPPED`) -- a bare string set rather than importing
# the enum, since every value here comes from a regex match against raw
# YAML frontmatter text (a branch/main blob), never a validated `Ticket`.
_TERMINAL_STATES = frozenset({"done", "dropped"})

# frob:ticket T-1948
# A `frob:ticket T-####` directive comment anywhere in a blob's text --
# language-agnostic (no comment-marker prefix required), matching the
# same bare `T-[0-9A-Za-z][0-9A-Za-z-]*` id shape `_TICKET_PATH_RE` uses.
# Deliberately permissive rather than anchored to a specific comment
# syntax: this module never parses source, only greps blob text, and the
# directive DSL itself is shared verbatim across every language this repo
# supports (docs/modules/graph.md#comment-dsl).
_TICKET_DIRECTIVE_RE = re.compile(r"frob:ticket\s+(T-[0-9A-Za-z][0-9A-Za-z-]*)")

# The one branch-local state T-1948's disagreement check treats as "real
# work is genuinely in flight, nothing to report" -- anything else
# (`queued`, `planned`, missing entirely) alongside a directive-anchored
# file is the gap this signal exists to surface.
_ACTIVE_STATE = "in-progress"


class _UnlandedWork(BaseModel):
    """One ticket that reads finished on a branch (`signal`) but is NOT
    terminal on `main` (T-1934) -- `state_on_main` is `None` if `main` has
    no record of the ticket at all (active or archived), which is reported,
    not treated as "nothing to see": an id `main` cannot resolve is exactly
    as unsafe to silently drop as one main knows about and has not
    finished."""

    model_config = {}

    ticket_id: str
    branch: str
    signal: str
    state_on_main: str | None


def _local_branch_names(root: Path) -> tuple[str, ...]:
    """Every local branch under `root` except `main` (T-1934's own
    prototype) -- `()` on any git failure, the same best-effort posture
    every other git-derived read in this package degrades to."""
    spawned = run_argv(("git", "-C", str(root), "branch", "--format=%(refname:short)"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("tickets: unlanded-work scan: git branch failed under %s", root)
        return ()
    return tuple(
        name
        for line in spawned.danger_ok.stdout.splitlines()
        if (name := line.strip()) and name != "main"
    )


def _blob_text(root: Path, ref: str, path: str) -> str | None:
    """`git show <ref>:<path>`'s stdout, or `None` if the blob does not
    exist at `ref` (or the spawn itself fails) -- the no-checkout read
    every lookup in this module goes through."""
    spawned = run_argv(("git", "-C", str(root), "show", f"{ref}:{path}"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout


def _state_from_ticket_md(text: str) -> str | None:
    """The `state:` value from a v2 `ticket.md` blob's YAML frontmatter, or
    `None` if the line is absent/unparseable -- a narrow regex, not a full
    YAML load, since this module never needs anything else out of the
    frontmatter and a malformed OTHER field on a branch (mid-edit, a stale
    schema) must never block reading just this one line."""
    match = _STATE_RE.search(text)
    return match.group(1) if match else None


def _ticket_state_on_main(root: Path, ticket_id: str) -> str | None:
    """`ticket_id`'s `state:` on `main`, checking the ACTIVE path first and
    the ARCHIVE path second (T-1934's core fix over the first, path-only
    prototype: a done ticket is archived to `tickets/archive/<id>/
    ticket.md` on main, not left at `tickets/<id>/ticket.md` -- checking
    active existence alone produced 186 false positives, every one of them
    an archived-done ticket misread as "not on main at all"). `None` if
    neither path resolves on `main`."""
    for path in (
        f"tickets/{ticket_id}/ticket.md",
        f"tickets/archive/{ticket_id}/ticket.md",
    ):
        text = _blob_text(root, "main", path)
        if text is not None:
            return _state_from_ticket_md(text)
    return None


# frob:ticket T-1955
def _branch_own_changed_files(root: Path, branch: str) -> frozenset[str]:
    """The set of paths `branch` has COMMITTED changes to since it diverged
    from `main`, via `git diff --name-only main...<branch>` (three-dot: the
    merge-base diff -- T-1955's fix, mirroring `frob.tickets._land.
    _branch_changed_files`'s identical two-dot/three-dot lesson from
    T-1922). `_finished_signals_on_branch` used a bare `git ls-tree
    <branch> -- tickets`, which lists everything REACHABLE from the
    branch tip -- including every ticket ever finished on `main` before the
    branch was cut, since that whole tree is an ancestor of the branch.
    That produced 216 false positives (T-1955): a branch cut from main
    MINUTES ago inherited main's entire finished-ticket history as
    "signals it carries". Intersecting against this three-dot diff instead
    means only paths the branch's OWN commits touched can ever count.
    Returns an empty set (never an error) on any git failure -- the same
    best-effort posture as every other read in this module; a caller that
    cannot resolve its own diff reports nothing rather than guessing."""
    spawned = run_argv(
        ("git", "-C", str(root), "diff", "--name-only", f"main...{branch}")
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning(
            "tickets: unlanded-work scan: git diff main...%s failed under %s",
            branch,
            root,
        )
        return frozenset()
    return frozenset(
        line.strip() for line in spawned.danger_ok.stdout.splitlines() if line.strip()
    )


# frob:ticket T-1955
def _finished_signals_on_branch(root: Path, branch: str) -> dict[str, str]:
    """`ticket_id -> signal` for every ticket `branch` carries that LOOKS
    finished, by either of T-1934's REQUIRED-A shapes: `"done-report"` (a
    `tickets/T-####/done-report.md` blob exists on the branch -- the
    stronger, cheaper-to-check signal, since a `done-report.md`'s mere
    presence never happens for an in-progress ticket) or
    `"local-state-done"` (no `done-report.md`, but the branch's OWN
    `ticket.md` reads `state: done`/`state: dropped` -- covers a done
    ticket whose done-report a hand-crafted or scripted commit omitted).
    T-1955: both shapes are additionally gated on `_branch_own_changed_
    files` -- a `git ls-tree` alone lists every ticket path REACHABLE from
    the branch tip, which includes everything already finished on `main`
    before the branch was cut. Only a path the branch's OWN commits
    touched (the three-dot `main...branch` diff) can produce a signal, so
    a freshly-cut branch that has not touched `tickets/` at all reports
    nothing, no matter how large main's finished-ticket history is. A
    single `git ls-tree` still lists every candidate path in one spawn;
    only ids that need the second signal get an extra `git show` for their
    `ticket.md` content.

    T-1948 adds a THIRD shape, `"directive-anchored"`
    (`_directive_anchor_signals_on_branch`), merged in last and only for
    ids neither shape above already claimed: a `frob:ticket T-####`
    directive comment anchors a non-`tickets/**` file among `branch`'s own
    changes, but that id's OWN `ticket.md` never even reads `in-progress`
    on this branch -- code exists that neither existing signal can see."""
    own_changed = _branch_own_changed_files(root, branch)
    signals = _done_report_and_local_state_signals(root, branch, own_changed)
    for ticket_id, signal in _directive_anchor_signals_on_branch(
        root, branch, own_changed, exclude=signals.keys()
    ).items():
        signals[ticket_id] = signal
    return signals


# frob:ticket T-1955
def _done_report_and_local_state_signals(
    root: Path, branch: str, own_changed: frozenset[str]
) -> dict[str, str]:
    """`_finished_signals_on_branch`'s original two-shape scan (`"done-
    report"`/`"local-state-done"`), split out to keep that function under
    the ARCH001 line threshold once T-1948 added a third shape on top --
    one `git ls-tree` for every candidate `tickets/**` path, then a
    `git show` only for ids that need the second signal's `ticket.md`
    content."""
    spawned = run_argv(
        (
            "git",
            "-C",
            str(root),
            "ls-tree",
            "-r",
            "--name-only",
            branch,
            "--",
            "tickets",
        )
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return {}
    done_report_ids: set[str] = set()
    ticket_md_ids: set[str] = set()
    for line in spawned.danger_ok.stdout.splitlines():
        path = line.strip()
        if path not in own_changed:
            continue
        match = _TICKET_PATH_RE.match(path)
        if match is None:
            continue
        ticket_id, kind = match.group(1), match.group(2)
        if kind == "done-report.md":
            done_report_ids.add(ticket_id)
        else:
            ticket_md_ids.add(ticket_id)
    signals: dict[str, str] = dict.fromkeys(done_report_ids, "done-report")
    for ticket_id in ticket_md_ids - done_report_ids:
        text = _blob_text(root, branch, f"tickets/{ticket_id}/ticket.md")
        if text is None:
            continue
        if _state_from_ticket_md(text) in _TERMINAL_STATES:
            signals[ticket_id] = "local-state-done"
    return signals


# frob:ticket T-1948
def _directive_anchored_ticket_ids(
    root: Path, branch: str, own_changed: frozenset[str]
) -> frozenset[str]:
    """Every ticket id a `frob:ticket T-####` directive comment anchors
    inside `branch`'s OWN non-`tickets/**` changed files (T-1948) -- one
    `git show` per candidate file, same no-checkout posture as every
    other blob read in this module. `tickets/**` paths are excluded (a
    ticket's own ledger files legitimately cite their own id and every
    other id they reference; that is not a "code exists for this ticket"
    signal, `_finished_signals_on_branch`'s existing two already own that
    surface)."""
    ids: set[str] = set()
    for path in own_changed:
        if path.startswith("tickets/"):
            continue
        text = _blob_text(root, branch, path)
        if text is None:
            continue
        ids.update(_TICKET_DIRECTIVE_RE.findall(text))
    return frozenset(ids)


# frob:ticket T-1948
def _directive_anchor_signals_on_branch(
    root: Path,
    branch: str,
    own_changed: frozenset[str],
    *,
    exclude: KeysView[str],
) -> dict[str, str]:
    """`ticket_id -> "directive-anchored"` for every id T-1948's third
    signal catches: a `frob:ticket T-####`-anchored file exists among
    `branch`'s own changes, but that id's OWN `ticket.md` state ON THIS
    BRANCH is not `_ACTIVE_STATE` (missing, `queued`, `planned`, ... --
    real work the ledger never recorded as in flight, `_finished_
    signals_on_branch`'s docstring/T-1691 specimen). `exclude` skips any
    id `_finished_signals_on_branch` already flagged via a stronger
    signal (`done-report`/`local-state-done` take priority; this is the
    weakest, "code exists but the ledger disagrees" signal, not a second
    vote on an id already known finished)."""
    signals: dict[str, str] = {}
    for ticket_id in _directive_anchored_ticket_ids(root, branch, own_changed):
        if ticket_id in exclude:
            continue
        text = _blob_text(root, branch, f"tickets/{ticket_id}/ticket.md")
        state = _state_from_ticket_md(text) if text is not None else None
        if state != _ACTIVE_STATE:
            signals[ticket_id] = "directive-anchored"
    return signals


def _is_ticket_lease_live(
    root: Path, ticket_id: str, leases: tuple[_LeaseRecord, ...]
) -> bool:
    """`True` iff a CURRENT lease for `ticket_id` exists and `lease_
    staleness_reason` judges it still live (T-1934 acceptance 3) -- reuses
    T-1876's single staleness predicate rather than inventing a second
    liveness notion, per this repo's own T-1806 "one predicate" precedent.
    A ticket with no lease at all, or only a stale one, is NOT excluded --
    only a genuinely live holder silences this detector."""
    for record in leases:
        if record.ticket_id == ticket_id:
            return lease_staleness_reason(root, record) is None
    return False


def _unlanded_findings_for_branch(
    root: Path, branch: str, leases: tuple[_LeaseRecord, ...] | None = None
) -> tuple[_UnlandedWork, ...]:
    """`_UnlandedWork` for every ticket `branch` carries a finished signal
    for (`_finished_signals_on_branch`) whose state on `main` is NOT
    terminal (`_ticket_state_on_main` not in `_TERMINAL_STATES`, including
    `None` -- unresolvable is reported, not assumed safe) and whose lease
    is not currently live (`_is_ticket_lease_live`). `leases` is
    injectable so a caller already holding `read_all_leases(root)` (a
    sweep pass iterating many candidate worktrees) never re-reads it once
    per branch."""
    if leases is None:
        leases = read_all_leases(root)
    findings: list[_UnlandedWork] = []
    for ticket_id, signal in sorted(_finished_signals_on_branch(root, branch).items()):
        if _is_ticket_lease_live(root, ticket_id, leases):
            continue
        state_on_main = _ticket_state_on_main(root, ticket_id)
        if state_on_main in _TERMINAL_STATES:
            continue
        findings.append(
            _UnlandedWork(
                ticket_id=ticket_id,
                branch=branch,
                signal=signal,
                state_on_main=state_on_main,
            )
        )
    return tuple(findings)


def _unlanded_branch_work(root: Path) -> tuple[_UnlandedWork, ...]:
    """Every `_UnlandedWork` finding across EVERY local branch under `root`
    except `main` itself (T-1934 acceptance 1/2/3) -- the read-only,
    report-only entry point `frob.tickets._reconcile.reconcile` surfaces as
    its third anomaly class and `frob ticket doable` summarizes as an "N
    branch(es) carry unlanded ticket work" line (T-1934 REQUIRED-C).
    NEVER lands, requeues, or removes anything -- REQUIRED-DO-NOT of
    T-1934's own brief: unattended landing of a dead agent's branch is how
    unreviewed work would reach `main`, so this stops at reporting.

    Cheap: a `git branch` spawn plus one `git ls-tree` per branch, and one
    `git show` only for ids that need the second signal or a main-side
    state resolution -- no checkout, no test run, matching the ticket's own
    working prototype exactly."""
    leases = read_all_leases(root)
    findings: list[_UnlandedWork] = []
    for branch in _local_branch_names(root):
        findings.extend(_unlanded_findings_for_branch(root, branch, leases))
    return tuple(findings)
