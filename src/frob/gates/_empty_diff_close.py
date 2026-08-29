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
close-time hard block. It reads the SAME data `compose_done_report`
already wrote (the `### Changed` fenced `git diff --stat` block,
`frob.tickets._evidence.render_changed_block`) back out of the ticket's
own body -- no separate diff computation, no new git call, and no risk
of disagreeing with what the Done report itself already recorded.

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

from frob.gates._models import Severity, Violation
from frob.tickets import TicketKind, TicketQueue, TicketState, TicketTier

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


# frob:doc \
# docs/modules/tickets-data-storage.md#tick014----empty-code-diff-on-close-t-3092
# frob:enforces CHK-GATE-TICK014
# frob:ticket T-3092
# frob:ticket T-3283
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_bug_warns
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_feature_warns
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_docs_kind_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_epic_tier_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_no_scope_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_real_diff_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_no_block_quiet
# frob:tests tests/test_gates_empty_diff_close.py::TestTick014.test_open_never_fires
def empty_code_diff_violations(queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK014 (WARN, T-3092): one violation per DONE ticket whose `kind`
    is `feature` or `bug` (`_APPLIES_TO_KINDS`), that is NOT exempted
    (`tier == epic`, `no_scope_declared`, or -- structurally, since it is
    filtered by `_APPLIES_TO_KINDS` -- `kind == docs`), and whose own
    Done report `### Changed` block lists no path outside ticket-
    bookkeeping (`_is_ticket_bookkeeping`).

    Deliberately silent (never a finding) when the Done report carries no
    parsable `### Changed` block at all (`_changed_paths_from_done_report`
    returns `None`) -- an older ledger row predating T-0458's auto-
    composed section is a coverage gap this check discloses rather than
    guesses at, not a live "empty diff" claim this module can actually
    support with evidence.

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
        paths = _changed_paths_from_done_report(t.body)
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
                    f"test, or doc change; if this is a legitimate no-code "
                    f"close (a decision record, a dropped-in-practice "
                    f"item, etc), declare it explicitly with `frob ticket "
                    f"scope {t.id} --declare-no-scope --reason '...'` "
                    f"before closing, or set kind=docs/tier=epic if that "
                    f"is a better fit; otherwise this is likely a ticket "
                    f"that was marked done without its described work "
                    f"actually landing (T-3064's own incident)"
                ),
            )
        )
    return tuple(violations)


__all__ = ["empty_code_diff_violations"]
