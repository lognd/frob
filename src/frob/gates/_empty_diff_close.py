"""frob.gates._empty_diff_close -- TICK014 (T-3092): warn when a
FEATURE- or BUG-kind ticket closes DONE with a diff that touches nothing
outside `tickets/` (or, in ledger v1 monofile mode, `tickets.md`/
`tickets-archive.md`).

Motivating incident (T-3087, T-3092's own body): T-3064 closed `done`
with a Done report whose own narrative literally said "T-3064 is
BLOCKED, not implemented", and its land touched only ticket-ledger
bookkeeping -- no source, test, or doc file. A Done-report claim of
"not implemented" is caller-authored prose a reviewer might miss; the
actual diff shape is mechanically checkable and was not being checked.

`frob.tickets._done_transition_guard` (`_evidence.py`) deliberately
does NOT reach into `frob.gates` for its structural checks (its own
docstring: `covers_scope`/`mutation_evidence`/etc are injected booleans,
computed elsewhere, never computed in-package) -- so this check lives
here, in `frob.gates`, as an ordinary queue-wide WARN finding
(`tickets_gate`'s TICK014, alongside TICK001..TICK013) rather than a
close-time hard block.

T-3899 REFINEMENT (this module's original design read only the `###
Changed` block `compose_done_report` wrote into the ticket body at
`frob ticket done-report` time -- see `_changed_paths_from_done_report`
below). That block is a `git diff --stat <base_ref>...HEAD` snapshot
taken WHILE the ticket's branch was still separate from `base_ref`; by
the time the ticket's own land later SQUASHES its branch (feat/fix
commit(s) + a following `chore(tickets): close T-####` bookkeeping
commit, the one-logical-change-per-commit convention this project
mandates) into ONE `land_commit` on the target branch, that stored
snapshot can be stale or -- for a ticket whose `done-report` was
composed AFTER an earlier phase of a multi-step land already merged its
code -- read as empty, even though real code landed. TICK014 flagged
every such ticket: it inspected the wrong diff (a done-report-time
snapshot, effectively "the close transition"), not the ticket's actual
landed change.

FIX: when the ticket carries a `land_commit` (`frob.tickets._models.
Ticket.land_commit`, the exact sha `frob.tickets._land_squash.
_record_land_commit` writes right after `frob ticket land` produces that
ticket's single squashed commit), this module now reads THAT commit's
own `git show --stat` diff instead of the stored Changed block --
the real, mechanically-verified set of paths this ticket's actual land
touched, spanning its whole branch range (start-of-branch through the
close commit, all squashed into `land_commit` by construction) rather
than a point-in-time snapshot. The stored Changed block remains the
fallback for a ticket with no `land_commit` (never landed via `frob
ticket land` at all -- e.g. a `frob ticket close` decision record) --
see `_tick014_changed_paths`'s docstring for the exact precedence and
the three edge cases this fix was required to decide explicitly:

  1. Code landed, then reverted in a LATER, separate commit before
     close: `land_commit`'s own diff still shows the original files
     this ticket touched (a later revert is a different commit, outside
     `land_commit`'s own tree). This check verifies "did this ticket's
     land touch real files", not "does that code still exist right
     now" -- detecting a post-land revert needs a different signal
     (diffing current HEAD against the target branch), which is a
     disclosed, deliberate non-goal here, not a silently-assumed-covered
     gap.
  2. The ticket's lifetime spans another ticket's commits (concurrent
     work on the same branch before land): does not apply to
     `land_commit` at all -- `frob ticket land <id>` squashes ONLY that
     ticket's own branch commits into one commit scoped to that ticket,
     so `land_commit`'s diff can never credit a different ticket's code.
     (This is why `land_commit`, not a start-commit-to-close-commit
     range, is the right anchor: a raw commit range on a shared branch
     WOULD leak concurrent commits; a per-ticket squash commit cannot.)
  3. Closed without ever landing (no `land_commit` at all, e.g. a
     decision-record close via `frob ticket close` directly): falls
     back to the pre-existing stored-Changed-block behavior unchanged,
     so the ORIGINAL true-positive case this check exists for -- a
     ticket marked done with genuinely no code anywhere in its
     lifetime -- still fires exactly as before.

Deliberately narrow (disclosed, not silently assumed complete): only the
declared `tickets/`/`tickets.md`/`tickets-archive.md` prefixes count as
"no code" -- a close that also happens to touch a rapid-land bookkeeping
artifact outside that prefix (e.g. `rapid-debt.jsonl`, a CHANGELOG
fragment) is NOT exempted here and WOULD still fire; that is a known,
disclosed gap (the ticket's own acceptance criteria name only the
`tickets/` prefix), not a false-negative this module claims to close.

Exemptions (the ticket's own acceptance criteria, item [1]): a
`docs`-kind ticket, an `epic`-tier ticket, or a ticket with
`no_scope_declared=True` legitimately closes without a code diff and
stays quiet -- these are structural properties on `Ticket` itself, read
directly, never inferred from the diff shape."""

from __future__ import annotations

import re
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.tickets import Ticket, TicketKind, TicketQueue, TicketState, TicketTier

#: Path prefixes that count as "ticket bookkeeping, not code" for this
#: check -- both ledger backends (`tickets/T-####/*` per-ticket dir mode,
#: and the legacy `tickets.md`/`tickets-archive.md` monofile mode,
#: `frob.tickets._store._store_mode`) are exempt so this check behaves
#: identically under either backend.
_TICKET_BOOKKEEPING_PREFIXES = ("tickets/", "tickets.md", "tickets-archive.md")

#: Kinds this check applies to -- a `docs`-kind ticket closing with only
#: ledger writes is the NORMAL, expected shape (acceptance item [1]), not
#: a finding.
_APPLIES_TO_KINDS = frozenset({TicketKind.FEATURE, TicketKind.BUG})

#: `render_changed_block`'s exact empty-diff sentinel
#: (`frob.tickets._evidence.render_changed_block`) -- matched verbatim
#: rather than re-deriving "no changed lines" some other way, so this
#: check can never disagree with what the Done report itself says.
_NO_CHANGES_SENTINEL = "(no changed files detected)"

_CHANGED_HEADING_RE = re.compile(r"^###[ \t]+Changed[ \t]*$", re.MULTILINE)
_FENCE_RE = re.compile(r"```\n(.*?)\n```", re.DOTALL)

#: One `git diff --stat` file-stat line, e.g.
#: " tickets/T-2916/ticket.md | 38 +++++++++++++++-" or a rename's
#: " old/path.py => new/path.py | 4 +-" -- the path is everything before
#: the FIRST unindented ` | `; a rename keeps only the `=>` new-name half
#: (the pre-rename half is dead weight for this purpose: if the NEW path
#: is ticket-bookkeeping the file did not become code, and if the OLD
#: path was code the new path certainly still is). Deliberately excludes
#: the trailing summary line ("N file(s) changed, ..."), which has no
#: ` | ` and so never matches.
_STAT_LINE_RE = re.compile(r"^\s*(\S.*?)\s+\|\s+\S")


def _changed_paths_from_done_report(body: str) -> tuple[str, ...] | None:
    """Extract the file paths listed in `body`'s `### Changed` fenced
    block (`frob.tickets._evidence.render_changed_block`'s exact output
    shape) -- `None` if the ticket carries no such block at all (an older
    Done report predating T-0458's auto-composed Changed section, or one
    written by a caller that skipped `compose_done_report`), an EMPTY
    tuple if the block is present and reads as the no-changes sentinel.
    `None` is intentionally distinct from `()`: this module treats "we
    cannot tell" as silence (see `empty_code_diff_violations`), never as
    a false-positive empty diff."""
    heading = _CHANGED_HEADING_RE.search(body)
    if heading is None:
        return None
    rest = body[heading.end() :].lstrip("\n")
    # T-0458's `render_changed_block` renders the empty-diff case as the
    # bare sentinel with NO fence at all (only the non-empty case fences)
    # -- checked before requiring a fence so this branch is not silently
    # mistaken for "no Changed block found".
    if rest.startswith(_NO_CHANGES_SENTINEL):
        return ()
    fence = _FENCE_RE.search(rest)
    if fence is None:
        return None
    block = fence.group(1)
    paths: list[str] = []
    for line in block.splitlines():
        match = _STAT_LINE_RE.match(line)
        if match is None:
            continue
        raw = match.group(1).strip()
        # Rename: "old/path => new/path" (git's --stat rename shorthand)
        # -- keep only the new-name half, see this function's docstring.
        if " => " in raw:
            raw = raw.rsplit(" => ", 1)[1].strip()
        paths.append(raw)
    return tuple(paths)


def _is_ticket_bookkeeping(path: str) -> bool:
    """`True` if `path` is entirely ticket-ledger bookkeeping (the
    `tickets/`/`tickets.md`/`tickets-archive.md` prefixes this module
    exempts, module docstring) -- `False` for everything else, including
    paths this check has no specific opinion on (an unrecognized
    bookkeeping artifact is conservatively treated as "code", per this
    module's disclosed narrowing)."""
    return path.startswith(_TICKET_BOOKKEEPING_PREFIXES)


def _changed_paths_from_land_commit(root: Path, sha: str) -> tuple[str, ...] | None:
    """`git show --stat <sha>`'s changed paths (T-3899) -- the REAL,
    mechanically-verified diff this ticket's land squashed onto the
    target branch, spanning its whole branch range by construction
    (`frob ticket land` squashes every commit from the ticket's start
    through its close into this one commit). `None` if `sha` does not
    resolve in this clone (a shallow clone, a pruned/rewritten history,
    or a corrupt `land_commit` value) -- treated as "cannot tell" by the
    caller, falling back to the stored done-report Changed block, never
    silently read as an empty diff."""
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "show", "--stat", "--format=", sha])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    paths: list[str] = []
    for line in spawned.danger_ok.stdout.splitlines():
        match = _STAT_LINE_RE.match(line)
        if match is None:
            continue
        raw = match.group(1).strip()
        if " => " in raw:
            raw = raw.rsplit(" => ", 1)[1].strip()
        paths.append(raw)
    return tuple(paths)


def _tick014_changed_paths(root: Path, t: Ticket) -> tuple[str, ...] | None:
    """The paths TICK014 judges `t`'s close by (T-3899): `t.land_commit`'s
    own `git show --stat` diff when a land_commit is recorded (the fix --
    see this module's docstring for the three decided edge cases), else
    the pre-existing stored done-report `### Changed` block
    (`_changed_paths_from_done_report`) for a ticket that never landed
    via `frob ticket land` at all. `None` means "cannot tell" either way
    (no parsable Changed block AND no resolvable land_commit) -- the
    caller treats that as silence, never a false-positive empty diff."""
    if t.land_commit:
        from_land = _changed_paths_from_land_commit(root, t.land_commit)
        if from_land is not None:
            return from_land
    return _changed_paths_from_done_report(t.body)


# frob:doc \
# docs/modules/tickets-data-storage.md#tick014----empty-code-diff-on-close-t-3092
# frob:waive AFFECT001 reason="T-3899: docs/modules/tickets-data-storage.md is leased \
# by another in-progress ticket (frob ticket scope refused --add on it); doc update \
# filed as T-draft-79a4ea1d instead of skipped silently"
# frob:enforces CHK-GATE-TICK014
# frob:ticket T-3092
# frob:ticket T-3283
# frob:ticket T-3899
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_bug_warns
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_feature_warns
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_docs_kind_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_epic_tier_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_no_scope_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_real_diff_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_no_block_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_open_never_fires
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014LandCommit.test_land_commit_with_real_code_quiet  # noqa: E501
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014LandCommit.test_land_commit_bookkeeping_only_warns  # noqa: E501
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014LandCommit.test_land_commit_overrides_stale_empty_changed_block  # noqa: E501
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014LandCommit.test_unresolvable_land_commit_falls_back_to_changed_block  # noqa: E501
def empty_code_diff_violations(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK014 (WARN, T-3092/T-3899): one violation per DONE ticket whose
    `kind` is `feature` or `bug` (`_APPLIES_TO_KINDS`), that is NOT
    exempted (`tier == epic`, `no_scope_declared`, or -- structurally,
    since it is filtered by `_APPLIES_TO_KINDS` -- `kind == docs`), and
    whose judged changed-paths (`_tick014_changed_paths`: `land_commit`'s
    real diff when recorded, else the stored done-report `### Changed`
    block) list no path outside ticket-bookkeeping
    (`_is_ticket_bookkeeping`).

    Deliberately silent (never a finding) when `_tick014_changed_paths`
    returns `None` -- neither a resolvable `land_commit` nor a parsable
    Changed block exists, so this module has no evidence to judge by at
    all. That is a disclosed coverage gap (an older ledger row predating
    T-0458's auto-composed section, or a `land_commit` this clone cannot
    resolve), never a live "empty diff" claim made without support.

    A non-DONE ticket (queued/in-progress/planned/dropped/blocked) never
    fires: `dropped` is not a completion at all (no code was ever
    expected), and every other state has not closed yet."""
    violations: list[Violation] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state is not TicketState.DONE:
            continue
        if t.kind not in _APPLIES_TO_KINDS:
            continue
        if t.tier is TicketTier.EPIC:
            continue
        if t.no_scope_declared:
            continue
        paths = _tick014_changed_paths(root, t)
        if paths is None:
            continue
        if paths and not all(_is_ticket_bookkeeping(p) for p in paths):
            continue
        violations.append(
            Violation(
                rule="TICK014",
                severity=Severity.WARN,
                file="tickets.md",
                line=0,
                message=(
                    f"TICK014: {t.id} ({t.kind.value}) closed done with a "
                    f"diff touching only ticket bookkeeping "
                    f"(tickets/tickets.md/tickets-archive.md) -- no code, "
                    f"test, or doc change landed anywhere in its lifetime "
                    f"(checked via its land_commit's own diff when "
                    f"recorded, T-3899); if this IS a legitimate no-code "
                    f"close (a decision record, a dropped-in-practice "
                    f"item, etc), declare it retroactively with `frob "
                    f"ticket scope {t.id} --declare-no-scope --reason "
                    f"'...'` (this ticket has already closed, so "
                    f"'--declare-no-scope' is applied after the fact, not "
                    f"before), or re-file with kind=docs/tier=epic if "
                    f"that is a better fit; otherwise this is likely a "
                    f"ticket that was marked done without its described "
                    f"work actually landing (T-3064's own incident)"
                ),
            )
        )
    return tuple(violations)


__all__ = ["empty_code_diff_violations"]
