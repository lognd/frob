# frob:waive SCOPE001 reason="T-1402: this file needed only a mechanical, necessary \
# rename of a stale frob:waive EXHAUST001 comment to EXHAUST003 (the EXHAUST001 \
# precision fix, declared scope src/frob/gates/_exhaustive_handling.py) or (this file, \
# _tickets_gate.py, _waive.py) is the actual TICK011 fix itself -- frob ticket scope \
# --add refuses it: T-1279 (TEST005 burn-down) holds a concurrent in-progress lease on \
# src/frob/gates/** for the whole package, so this ticket cannot formally register the \
# file in its own declared scope until T-1279 closes or narrows; see this ticket's \
# Done report for the full disclosure (reviewed 2026-08-03, drain-to-zero WAIVE004 \
# sweep: left in place -- SCOPE001 is a scope/lease-dependent rule \
# (frob.gates._waive.SCOPED_RUN_FLAKY_RULE_IDS), not a stale finding a full unscoped \
# run can prove dead the way WIRE001/REF002/etc can"
"""frob.gates._tickets_gate -- TICK00x ledger-hygiene/invariant family (T-1140).

Split out of `frob.gates.__init__` (T-1115/T-1140 residue, one-family-per-
land discipline) so the parent module can drop below the large-file
threshold without changing any public behavior. `tickets_gate` is
re-exported from `frob.gates` unchanged -- it is the only name this family
is externally imported by (verified by a repo-wide grep before the move);
every `_tickN_*` helper stays private to this module.
"""

# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_tickets_gate.py's exclusivity-vocabulary hits are source-level \
# design-rationale prose (docstrings and comments describing already-implemented \
# internal behavior, verifiable by reading the code they annotate) rather than a \
# separate cross-module contract needing its own tracked invariant; disposed as a \
# calibration batch, not claim-by-claim -- module prose split verbatim from the \
# pre-T-1140 gates/__init__.py monolith"
from __future__ import annotations

import difflib
import os
import re
import tomllib
from datetime import date
from pathlib import Path

from typani.result import Result

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.tickets import Ticket, TicketQueue, TicketState, closed_ticket_ids
from frob.tickets._models import Priority, TicketError
from frob.tickets._provisional import is_draft_id
from frob.tickets._store import _dir_glob as _tickets_dir_glob
from frob.tickets._store import _parse_ledger as _tickets_parse_ledger
from frob.tickets._store import _store_mode as _tickets_store_mode
from frob.tickets._store import ledger_path as _tickets_ledger_path
from frob.tickets._store import load_all as _tickets_load_all
from frob.tickets._store import load_archive as _tickets_load_archive

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# TICK001 / TICK002: ticket-id collision invariant (T-0162, decision record
# in docs/modules/tickets.md#decision-record-t-0162)
# ---------------------------------------------------------------------------


# frob:ticket T-0162
# frob:ticket T-0929
# frob:tests tests/test_tickets_collision.py::TestRealLedgerIntegrity.test_no_duplicate_ids_within_or_across_ledgers  # noqa: E501
# frob:enforces CHK-GATE-TICK001
def _tick001_duplicate_ids(
    active: Result[dict[str, Ticket], TicketError],
    archived: Result[dict[str, Ticket], TicketError],
) -> tuple[Violation, ...]:
    """TICK001: an id present in BOTH the active and archive ledgers.

    Defense in depth, not the primary mechanism: `_load_merged` (frob.tickets)
    already hard-Errs `run_gates` itself (GateError.QueueUnavailable) the
    moment ledger loading sees this, which is louder than any Violation --
    the whole `frob check` run refuses to produce a report at all. This rule
    exists so that stays true even if a future change makes ledger loading
    more permissive; see the decision record for why duplicate-id detection
    is split this way instead of only living in one place.

    T-0929 (docs/audits/check-performance.md row 10, `tickets` gate,
    2.09s): `active`/`archived` are now loaded ONCE by `tickets_gate` and
    shared with `_tick003_stale_archive`/`_tick006_phantom_filing`, rather
    than each of the three re-reading and re-parsing the full
    `tickets.md`/`tickets-archive.md` ledger text independently -- the
    same "same expensive input recomputed N times with no shared cache"
    shape the audit's meta-gap finding (E) describes, at the level of
    `tickets_gate`'s own three sibling rules instead of cross-stage.
    """
    if active.is_err or archived.is_err:
        return ()
    overlap = sorted(set(active.danger_ok) & set(archived.danger_ok))
    return tuple(
        Violation(
            rule="TICK001",
            severity=Severity.ERROR,
            file="tickets.md",
            line=0,
            message=(
                f"TICK001: {tid} exists in both tickets.md and "
                f"tickets-archive.md -- resolve the collision (frob ticket "
                f"renumber one of them) before the ledger can be trusted"
            ),
        )
        for tid in overlap
    )


# frob:ticket T-0162
# frob:enforces CHK-GATE-TICK002
def _tick002_draft_on_default(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK002: a T-draft-* provisional id still present while `root` is on
    the default branch -- the finalize step (T-0162's provisional-id
    mechanism; `frob ticket land`/T-0176 will call `finalize_draft`
    automatically) was skipped, failed, or never run. A draft id reaching
    the default branch means the collision-proofing this whole mechanism
    exists for silently did not happen, so this rule is unwaivable
    (`_UNWAIVABLE_RULES`) for the same reason TEST008 is.

    Calls back through `frob.gates.on_default_branch` (lazy, call-time)
    rather than this module's own import so that tests patching
    `frob.gates.on_default_branch` (the pre-split monkeypatch target)
    keep working unchanged."""
    from frob.gates import on_default_branch

    if not on_default_branch(root):
        return ()
    return tuple(
        Violation(
            rule="TICK002",
            severity=Severity.ERROR,
            file="tickets.md",
            line=0,
            message=(
                f"TICK002: draft id {tid} survived onto the default branch -- "
                f"finalize it: `frob ticket renumber {tid} T-####` (or the "
                f"land step, once T-0176 lands)"
            ),
        )
        for tid in sorted(queue.tickets)
        if is_draft_id(tid)
    )


# frob:ticket T-0409
_TICK003_DEFAULT_WARN = 20
_TICK003_DEFAULT_ERROR = 60


def _tick003_thresholds(root: Path) -> tuple[int, int]:
    """`(warn_at, error_at)` un-archived-closed-ticket count thresholds
    (T-0409) from `frob.toml`'s `[tickets]` table (`stale_archive_warn`/
    `stale_archive_error`), defaulting to
    `(_TICK003_DEFAULT_WARN, _TICK003_DEFAULT_ERROR)`. A missing/malformed
    `frob.toml` degrades to the defaults rather than blocking the gate --
    ledger hygiene is a hint, not something a config-loading hiccup should
    take down."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return _TICK003_DEFAULT_WARN, _TICK003_DEFAULT_ERROR
    try:
        with toml_path.open("rb") as fh:
            table = tomllib.load(fh).get("tickets", {})
        return (
            int(table.get("stale_archive_warn", _TICK003_DEFAULT_WARN)),
            int(table.get("stale_archive_error", _TICK003_DEFAULT_ERROR)),
        )
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        _log.warning(
            "tick003: frob.toml unreadable/malformed (%s), using defaults", exc
        )
        return _TICK003_DEFAULT_WARN, _TICK003_DEFAULT_ERROR


# frob:enforces CHK-GATE-TICK003
def _tick003_violation(count: int, severity: Severity, threshold: int) -> Violation:
    """One TICK003 `Violation` at `severity`, naming `count` and the
    `threshold` it crossed, always pointing at `frob ticket archive` as the
    fix (T-0409)."""
    return Violation(
        rule="TICK003",
        severity=severity,
        file="tickets.md",
        line=0,
        message=(
            f"TICK003: {count} closed ticket(s) sitting un-archived in "
            f"tickets.md (threshold {threshold}) -- run `frob ticket "
            f"archive` (in a quiet window, no in-flight worktrees) to clear it"
        ),
    )


# frob:ticket T-0929
# frob:tests tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive.test_above_default_error_threshold_errors  # noqa: E501
def _tick003_stale_archive(
    root: Path, active: Result[dict[str, Ticket], TicketError]
) -> tuple[Violation, ...]:
    """TICK003 (T-0409): WARN (escalating to ERROR past a hard cap) when
    the ACTIVE ledger (never the archive -- an already-archived closed
    ticket is not a hygiene problem) holds more than a configurable
    threshold of closed (done/dropped) tickets un-archived.

    Resurrection-safe by construction: this gate only ever COUNTS and
    recommends `frob ticket archive`; it never archives anything itself, so
    it can never interact with the land/splice path's archive-resurrection
    guards (`_drop_resurrected_ids`, `splice_ledger`, docs/modules/
    tickets.md#frob-ticket-land) -- those guard a WRITE this gate never
    performs. `frob ticket archive` itself should still only be run in a
    quiet window (no active worktrees), per the same known hazard; this
    gate's message says so but cannot enforce it.

    T-0929: `active` is now the SAME `load_all` result `tickets_gate`
    already loaded once for `_tick001_duplicate_ids`, not a second
    independent re-parse of `tickets.md` (docs/audits/check-performance.md
    row 10).
    """
    if active.is_err:
        return ()
    count = len(closed_ticket_ids(TicketQueue(tickets=active.danger_ok)))
    warn_at, error_at = _tick003_thresholds(root)
    if count > error_at:
        return (_tick003_violation(count, Severity.ERROR, error_at),)
    if count > warn_at:
        return (_tick003_violation(count, Severity.WARN, warn_at),)
    return ()


# frob:ticket T-0411
_TICK004_DEFAULT_ROT_DAYS = {
    Priority.CRITICAL: 3,
    Priority.HIGH: 7,
    Priority.MEDIUM: 30,
    Priority.LOW: 90,
}


# frob:ticket T-0411
def _tick004_rot_thresholds(root: Path) -> dict[Priority, int]:
    """Per-priority rot-day thresholds (T-0411) from `frob.toml`'s
    `[tickets]` table (`rot_days_critical`/`rot_days_high`/
    `rot_days_medium`/`rot_days_low`), defaulting to
    `_TICK004_DEFAULT_ROT_DAYS`. Same fail-open-to-defaults shape as
    `_tick003_thresholds` -- a missing/malformed `frob.toml` degrades to
    the defaults rather than blocking the gate."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return dict(_TICK004_DEFAULT_ROT_DAYS)
    try:
        with toml_path.open("rb") as fh:
            table = tomllib.load(fh).get("tickets", {})
        return {
            priority: int(table.get(f"rot_days_{priority.value}", default))
            for priority, default in _TICK004_DEFAULT_ROT_DAYS.items()
        }
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        _log.warning(
            "tick004: frob.toml unreadable/malformed (%s), using defaults", exc
        )
        return dict(_TICK004_DEFAULT_ROT_DAYS)


# frob:ticket T-0411
# frob:enforces CHK-GATE-TICK004
def _tick004_queue_rot(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK004 (T-0411): WARN (escalating to ERROR at 2x threshold) per
    queued/planned ticket whose priority-specific rot-day threshold has
    been crossed since `created` -- the queue-health signal T-0411's
    Description asks for: "we forgot we have a stack of things and only
    end up popping off the top half" becomes a visible gate finding
    instead of a silent, age-only queue. Only QUEUED/PLANNED tickets are
    considered (an in-progress/blocked ticket is not rotting, it is being
    worked or is explicitly waiting on a blocker)."""
    thresholds = _tick004_rot_thresholds(root)
    today = date.today()
    violations: list[Violation] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state not in (TicketState.QUEUED, TicketState.PLANNED):
            continue
        age_days = (today - t.created).days
        threshold = thresholds[t.priority]
        if age_days <= threshold:
            continue
        severity = Severity.ERROR if age_days > threshold * 2 else Severity.WARN
        violations.append(
            Violation(
                rule="TICK004",
                severity=severity,
                file="tickets.md",
                line=0,
                message=(
                    f"TICK004: {t.id} ({t.priority.value} priority) has sat "
                    f"{t.state.value} for {age_days}d (threshold {threshold}d) "
                    f"-- it is rotting; work it, re-prioritize it "
                    f"(`frob ticket priority {t.id} <level>`), or drop it"
                ),
            )
        )
    return tuple(violations)


#: Terminal `TicketState`s -- once a ticket reaches one of these, moving it
#: back to any other state is a regression, never a legitimate forward
#: transition (T-0537).
_TERMINAL_STATES = (TicketState.DONE, TicketState.DROPPED)


def _tick005_head_second_parent(root: Path) -> str | None:
    """`HEAD^2`'s resolved sha if `root`'s current commit is a real two-
    parent merge commit, else `None` -- TICK005 only runs in a genuine
    post-merge context (a fast-forward or an ordinary single-parent commit
    has no "first parent before this merge" to diff against, and would
    otherwise false-positive on any ordinary ticket-state edit)."""
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "rev-parse", "HEAD^2"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout.strip()


def _tick005_ledger_at_ref(root: Path, ref: str) -> dict[str, Ticket] | None:
    """`tickets.md`'s parsed ticket-id -> `Ticket` map as of git ref `ref`,
    or `None` if the ref/path does not resolve or the content fails to
    parse -- either degrades TICK005 to a no-op rather than a false
    positive or a crash."""
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "show", f"{ref}:tickets.md"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    parsed = _tickets_parse_ledger(spawned.danger_ok.stdout)
    if parsed.is_err:
        return None
    return parsed.danger_ok


# frob:ticket T-0537
# frob:enforces CHK-GATE-TICK005
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1056: leaked Unknown traces to \
# _tick005_head_second_parent/_tick005_ledger_at_ref's own gitio.run_argv calls, which \
# already return a typani Result (no exception path) that the resolver cannot \
# statically see through; every locally fallible step here degrades via an explicit \
# None/() check, not a bare propagation"
def _tick005_merge_state_regression(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """TICK005 (T-0537): after a genuine two-parent merge commit, ERROR on
    any ticket that was DONE/DROPPED (terminal) in the merge's FIRST
    parent's `tickets.md` but is neither DONE nor DROPPED in the current
    (post-merge) ledger, nor archived. `_land`'s own ticket-scoped splice
    (`_splice_only_ticket`, T-0479) and `splice_ledger`'s state-rank
    tiebreak (`_newer`, terminal ranks highest) already make this
    structurally impossible for anything that goes THROUGH those code
    paths -- this gate exists for the incident class that bypasses both: a
    `tickets.md` merge conflict resolved BY HAND (the merge driver not
    registered, or a conflict shape it declined), which can silently keep
    stale non-terminal states for tickets main had already closed (the
    real incident: 7 tickets -- T-0454/T-0498/T-0500/T-0514/T-0520/T-0526/
    T-0527 -- resurrected this way). Runs regardless of mechanism, since it
    inspects only the git history/ledger content, never how the merge
    commit was produced."""
    second_parent = _tick005_head_second_parent(root)
    if second_parent is None:
        return ()
    parent_ledger = _tick005_ledger_at_ref(root, "HEAD^1")
    if parent_ledger is None:
        return ()

    archived_ids = frozenset()
    try:
        from frob.tickets._land_merge import _archived_ids

        archived_ids = _archived_ids(root)
    except ImportError:  # pragma: no cover -- frob.tickets._land_merge always ships
        _log.warning("tick005: could not import _archived_ids, treating as empty")

    violations: list[Violation] = []
    for ticket_id, parent_ticket in sorted(parent_ledger.items()):
        if parent_ticket.state not in _TERMINAL_STATES:
            continue
        if ticket_id in archived_ids:
            continue
        current = queue.tickets.get(ticket_id)
        if current is None:
            continue
        if current.state in _TERMINAL_STATES:
            continue
        violations.append(
            Violation(
                rule="TICK005",
                severity=Severity.ERROR,
                file="tickets.md",
                line=0,
                message=(
                    f"TICK005: {ticket_id} was {parent_ticket.state.value} "
                    f"in this merge's first parent but is "
                    f"{current.state.value} now -- a terminal ticket "
                    f"regressed to a non-terminal state, the T-0537 hand-"
                    f"resolved-conflict resurrection incident; restore it "
                    f"to {parent_ticket.state.value} (`git show "
                    f"HEAD^1:tickets.md`) unless this state change is a "
                    f"deliberate, reasoned reopen"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-0726
#: Matches a `## Done report` (or `### Done report`, `## Round 1 Done
#: report`, `## Done report (batch 8)`, etc.) heading -- any markdown
#: heading line whose text contains "done report", case-insensitive. Used
#: to find where a ticket body's Done-report content starts, since a Done
#: report always follows a Description/Plan section that must NOT be
#: scanned (see `_tick006_done_report_text`'s docstring for why).
_DONE_REPORT_HEADING_RE = re.compile(r"^#{1,6}[^\n]*done report", re.I | re.M)

#: A ticket-id lexeme: a real `T-####` id or a provisional `T-draft-<8 hex>`
#: id (mirrors `frob.tickets._store._TICKET_ID_RE`). Matches inside a
#: literal placeholder like `T-####` never fire (`#` is not `\d`), and a
#: templated `T-draft-XXXXXXXX` placeholder never fires either (`X` is not
#: `[0-9a-f]`) -- both are common in narrative prose that is not a filing
#: claim at all.
_TICK006_ID_RE = re.compile(r"T-(?:\d{4}|draft-[0-9a-f]{8})")

#: A "filed" occurrence preceded within this many characters by a negation
#: word (not/never/no/n't) is an explicit negation ("not filed", "no
#: ticket filed", "never filed") per T-0726's Description, and is skipped
#: rather than treated as an affirmative filing claim.
_TICK006_NEGATION_RE = re.compile(r"\b(?:not|never|no|n't)\b", re.I)
_TICK006_NEGATION_WINDOW = 40

#: How far past a "filed" occurrence to look for the id(s) it claims to
#: have filed -- generous enough to span a wrapped markdown line/sentence
#: (real Done reports wrap `Filed: T-draft-... (description...)` across
#: 2-3 lines) without bleeding into an unrelated later paragraph.
_TICK006_CLAIM_WINDOW = 300


# frob:ticket T-0726
def _tick006_done_report_text(body: str) -> str:
    """The substring of a ticket `body` starting at its first "Done
    report" heading, or `""` if none exists (a ticket with no Done report
    yet has nothing to scan). Restricting to this substring -- rather than
    the whole body -- is deliberate: a ticket's Description/Plan often
    narrates OTHER tickets' ids in ordinary prose ("T-0570 landed the...",
    "NOTE: T-0177's Done report references this as T-draft-...") and none
    of that is a filing claim about THIS ticket's own work, so scanning it
    would be a false-positive generator. A Done report's own "Filed: ..."
    line is the one place a ticket asserts something about a NEW id it
    is responsible for."""
    match = _DONE_REPORT_HEADING_RE.search(body)
    if match is None:
        return ""
    return body[match.start() :]


# frob:ticket T-0726
def _tick006_phantom_ids(done_report_text: str) -> tuple[str, ...]:
    """Every ticket id affirmatively claimed as filed somewhere in
    `done_report_text` -- i.e. following an unnegated occurrence of the
    word "filed" within `_TICK006_CLAIM_WINDOW` characters -- in first-seen
    order, deduplicated. Recognizes the filing-claim grammar actually used
    in this repo's ledger: `Filed: T-0104`, `Filed: none`, `filed as
    **T-0137**`, `filed as a follow-up`, `Filed T-draft-4e98abb1 (mints a
    real T-#### id at land)`, `Filed a new standing ticket (drafted
    off-main as T-draft-05d8f716...)`. Explicit negations ("not filed",
    "no ticket filed", "never filed") are skipped per T-0726's Description
    -- see `_TICK006_NEGATION_RE`."""
    seen: dict[str, None] = {}
    for occurrence in re.finditer(r"\bfiled\b", done_report_text, re.I):
        start = occurrence.start()
        pre = done_report_text[max(0, start - _TICK006_NEGATION_WINDOW) : start]
        if _TICK006_NEGATION_RE.search(pre):
            continue
        window = done_report_text[start : start + _TICK006_CLAIM_WINDOW]
        for tid in _TICK006_ID_RE.findall(window):
            seen.setdefault(tid, None)
    return tuple(seen)


# frob:ticket T-0929
# frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_phantom_filed_colon_fires  # noqa: E501
# frob:enforces CHK-GATE-TICK006
def _tick006_phantom_filing(
    queue: TicketQueue, archived: Result[dict[str, Ticket], TicketError]
) -> tuple[Violation, ...]:
    """TICK006 (T-0726): ERROR on a Done report's affirmative filing claim
    (`Filed: ...`, `filed as ...`, a bare `T-draft-<hex>`/`T-#### id`
    following "filed") whose referenced id resolves to NO block in either
    `tickets.md` or `tickets-archive.md` -- a phantom filing trail, the
    T-0707 (invented filed-then-absorbed trail) and T-0615 (invented
    T-draft id, never actually filed) incidents this rule exists to catch
    mechanically instead of relying on reviewer diligence alone. A
    `T-draft-<hex>` id that WAS real at write time but did not survive
    land (the T-0577 draft-loss bug) also fires here -- that is a genuine,
    disclosed historical phantom by this rule's own definition (the id
    resolves to nothing, right now, in the ledger a reader actually has),
    and is expected to be waived per-instance with an honest reason
    (docs/modules/gates.md#tick006-t-0726) rather than treated as a false
    positive to suppress structurally.

    T-0929: `archived` is the SAME `load_archive` result `tickets_gate`
    already loaded once for `_tick001_duplicate_ids`, not a second
    independent re-parse of `tickets-archive.md` (docs/audits/
    check-performance.md row 10)."""
    known_ids = set(queue.tickets) | (
        set(archived.danger_ok) if archived.is_ok else set()
    )
    violations: list[Violation] = []
    for ticket in sorted(queue.tickets.values(), key=lambda t: t.id):
        done_report_text = _tick006_done_report_text(ticket.body)
        if not done_report_text:
            continue
        for tid in _tick006_phantom_ids(done_report_text):
            if tid in known_ids:
                continue
            violations.append(
                Violation(
                    rule="TICK006",
                    severity=Severity.ERROR,
                    file="tickets.md",
                    line=0,
                    message=(
                        f"TICK006: {ticket.id}'s Done report claims {tid} "
                        f"was filed, but {tid} resolves to no block in "
                        f"tickets.md or tickets-archive.md -- a phantom "
                        f"filing trail (the T-0707/T-0615 incident class); "
                        f"file the real ticket, correct the Done report to "
                        f"name the real id, or waive with an honest reason "
                        f"if this is a disclosed historical draft-loss case"
                    ),
                )
            )
    return tuple(violations)


#: T-1129: disclosure phrases a Done report uses to admit deferred/cut
#: work -- deliberately CONSERVATIVE multi-word phrases (not a bare
#: "deferred"/"cut" trigger) so a WARN-tier first turn-on does not drown
#: in false positives against this ledger's existing prose. Five real
#: incidents this drive shaped the list: T-1085 ("deliberately left for a
#: follow-up pass"), T-0321's close (the serve RPC gap "not yet ticketed
#: as its own item"), T-1140, T-1150 (see tickets-archive.md for their
#: exact wording; the phrases below cover the shape all five share).
_TICK011_DISCLOSURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bleft (?:for|as) a follow-?up\b", re.I),
    re.compile(r"\bnot yet ticketed\b", re.I),
    re.compile(r"\bnot ticketed\b", re.I),
    re.compile(r"\bdeferred (?:to|as|for) a follow-?up\b", re.I),
    re.compile(r"\b(?:residue|residual)\b", re.I),
    re.compile(r"\bscope cut\b", re.I),
    re.compile(r"\bcut (?:from|for) (?:this|the) (?:pass|scope|ticket)\b", re.I),
)

#: An explicit "no ticket needed" disposition (T-1129's own acceptance
#: criterion's escape hatch) found near a disclosure phrase suppresses
#: TICK011 for that occurrence -- a Done report that already reasoned
#: about the gap and decided it needs no tracking is not the T-1085/
#: T-0321 incident class this rule targets.
_TICK011_NO_TICKET_NEEDED_RE = re.compile(
    r"no (?:follow-?up )?ticket (?:is )?needed|no-ticket-needed", re.I
)

#: How far before/after a disclosure phrase to look for either a citing
#: `T-####`/`T-draft-<hex>` id or an explicit no-ticket-needed reason --
#: generous enough to span the same bullet/paragraph (a wrapped markdown
#: sentence) without bleeding into an unrelated later paragraph, mirroring
#: TICK006's own `_TICK006_CLAIM_WINDOW` precedent.
_TICK011_VICINITY = 300

#: T-1402: how many ids below the ledger's own highest known `T-####` count
#: as the ACTIVE WINDOW a Done report's disclosed cut can still be
#: honestly followed up on. A 2026-08-01 measurement (T-1402) found 50
#: unwaived TICK011 findings, every one against a HISTORICAL Done report,
#: 14 of them citing tickets below T-0500 -- nobody can now reconstruct
#: what a years-old ticket's "scope cut" prose referred to, so those 50
#: can never be honestly driven to zero by doing the work, only waived en
#: masse (exactly the dishonest zero this rule exists to prevent). TICK011
#: stays at full strength for any report inside this window -- where a
#: disclosed cut can still be turned into a real follow-up ticket -- and
#: is silent by default outside it (`_tick011_ticket_in_active_window`).
#: 500 is deliberately generous (not a tight recency cutoff): it is sized
#: to comfortably outlast a single active development drive so a report
#: written a few hundred tickets ago -- still plausibly reconstructable --
#: is not silenced just because the ledger kept moving underneath it.
_TICK011_ACTIVE_WINDOW = 500

#: T-1402: the escape hatch for someone deliberately auditing the
#: historical ledger tail this rule is otherwise silent on by default
#: (the "gated behind an explicit opt-in flag" half of this ticket's own
#: acceptance) -- set to any non-empty value to scan every ticket
#: regardless of `_TICK011_ACTIVE_WINDOW`, matching this repo's existing
#: `FROB_AGENT`/`FROB_ALLOW_FULL_CHECK`-style env-var opt-in convention
#: (`frob.gates.__init__`'s own `_agent_mode`).
_TICK011_INCLUDE_HISTORY_ENV = "FROB_TICK011_INCLUDE_HISTORY"

#: T-1402: a ticket id's trailing numeric component (`"T-0500"` -> `500`),
#: or `None` for a provisional `T-draft-<hex>` id (drafts are never old --
#: they have not landed yet, so the active-window question does not apply;
#: callers treat `None` as "always active").
_TICK_NUM_RE = re.compile(r"^T-(\d{4})$")


def _tick011_ticket_num(ticket_id: str) -> int | None:
    """The numeric component of a real `T-####` id (T-1402), or `None` for
    anything else (a `T-draft-<hex>` id, or a malformed id that should
    never reach here) -- the recency proxy `_tick011_active_window_floor`/
    `_tick011_in_active_window` key off of."""
    m = _TICK_NUM_RE.match(ticket_id)
    return int(m.group(1)) if m else None


def _tick011_active_window_floor(known_ids: set[str]) -> int:
    """The lowest ticket number (T-1402) still inside TICK011's active
    window: `_TICK011_ACTIVE_WINDOW` below the highest real `T-####` id in
    `known_ids` (0 if none parse, so an empty/all-draft ledger never
    excludes anything). Self-adjusting rather than a fixed historical
    cutoff -- the window slides forward with the ledger's own growth,
    matching this ticket's own "active window" framing rather than a
    fixed date/id line that would itself go stale."""
    nums = [n for n in (_tick011_ticket_num(tid) for tid in known_ids) if n is not None]
    if not nums:
        return 0
    return max(0, max(nums) - _TICK011_ACTIVE_WINDOW)


def _tick011_in_active_window(ticket_id: str, floor: int) -> bool:
    """True when `ticket_id` is inside TICK011's active window (T-1402):
    a provisional `T-draft-<hex>` id (never old) or a real `T-####` id
    whose number is at or above `floor`. False means the ticket is
    HISTORICAL -- TICK011 stays silent on it by default (see
    `_TICK011_ACTIVE_WINDOW`'s docstring), unless
    `_TICK011_INCLUDE_HISTORY_ENV` is set."""
    num = _tick011_ticket_num(ticket_id)
    return num is None or num >= floor


#: Calibrating this rule against the LIVE repo ledger (T-1129's own
#: obligation: "frob's own ledger findings fixed or dispositioned in the
#: same land") found bare "residue"/"residual" is a term of art in this
#: codebase's own engineering vocabulary meaning "remaining FINDING
#: count" ("7 residual", "WARN residue", "REG010 residue", "gate:WAIVE
#: residue", "5-error residue" -- all real T-1111 Done-report text), never
#: disclosed leftover SCOPE. The shared shape: the word immediately
#: before "residue"/"residual" is a technical token (a bare number, an
#: ALL-CAPS/rule-id-shaped word, or a `namespace:RULE`-shaped identifier)
#: rather than ordinary prose. Excluding on that token shape (not a fixed
#: digit-lookback) is what actually clears the real false positives found.
# frob:waive PII012 reason="'token' here means a lexical word/substring from a Done \
# report's own prose (a whitespace-delimited chunk this rule checks the shape of), not \
# a credential/auth token -- a name-signature false positive, same class as \
# frob.gates._docptr's own existing PII012 waiver for its unrelated lexical-token \
# vocabulary"
_TICK011_TECHNICAL_TOKEN_RE = re.compile(r"[A-Z]{2,}|:|\d")


# frob:waive PII012 reason="'token' here means a lexical word/substring from a Done \
# report's own prose, not a credential/auth token -- see _TICK011_TECHNICAL_TOKEN_RE's \
# own waiver for the same false-positive class"
def _tick011_preceded_by_technical_token(text: str, start: int) -> bool:
    """Whether the whitespace-delimited word immediately before `text[
    start:]` looks like a technical token (a digit, a `namespace:NAME`
    colon, or 2+ consecutive uppercase letters) rather than ordinary
    prose -- see `_TICK011_TECHNICAL_TOKEN_RE`'s comment for the real
    false positives this excludes."""
    before = text[:start].rstrip()
    word = before.rsplit(maxsplit=1)[-1] if before else ""
    return bool(_TICK011_TECHNICAL_TOKEN_RE.search(word))


# frob:ticket T-1129
def _tick011_disclosure_hits(text: str) -> tuple[re.Match[str], ...]:
    """Every `_TICK011_DISCLOSURE_PATTERNS` match in `text`, in document
    order, EXCLUDING a bare "residue"/"residual" hit immediately preceded
    by a technical token (`_tick011_preceded_by_technical_token`) -- this
    codebase's own "remaining finding count" idiom, not a disclosure of
    leftover scope -- the candidate disclosure occurrences
    `_tick011_disclosed_cuts_without_ticket` checks for a nearby
    citation."""
    hits = []
    for pattern in _TICK011_DISCLOSURE_PATTERNS:
        for m in pattern.finditer(text):
            if m.group(0).lower() in (
                "residue",
                "residual",
            ) and _tick011_preceded_by_technical_token(text, m.start()):
                continue
            hits.append(m)
    return tuple(sorted(hits, key=lambda m: m.start()))


# frob:ticket T-1129
# frob:ticket T-1402
# frob:tests tests/test_gates.py::TestTick011DisclosedCutWithoutTicket.test_disclosed_follow_up_with_no_citation_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestTick011DisclosedCutWithoutTicket.test_recent_ticket_outside_old_window_still_fires_exactly_as_today  # noqa: E501
# frob:tests tests/test_gates.py::TestTick011DisclosedCutWithoutTicket.test_historical_ticket_outside_active_window_is_silent_by_default  # noqa: E501
# frob:tests tests/test_gates.py::TestTick011DisclosedCutWithoutTicket.test_include_history_env_opt_in_restores_the_historical_finding  # noqa: E501
# frob:enforces CHK-GATE-TICK011
def _tick011_disclosed_cuts_without_ticket(
    queue: TicketQueue, archived: Result[dict[str, Ticket], TicketError]
) -> tuple[Violation, ...]:
    """TICK011 (T-1129, active-window-narrowed T-1402): WARN when a Done
    report's prose discloses deferred/cut work
    (`_TICK011_DISCLOSURE_PATTERNS`: "left for a follow-up", "not yet
    ticketed", "deferred to a follow-up", "residue"/"residual", a scope
    cut) with no `T-####`/`T-draft-<hex>` id resolving to a real ledger
    block, and no explicit no-ticket-needed reason, within
    `_TICK011_VICINITY` characters.

    Five incidents this drive motivated this (T-1085, T-0321's close,
    T-1140, T-1150 -- see this module's `_TICK011_DISCLOSURE_PATTERNS`
    comment): a coordinator hand-screening every Done report for
    unticketed disclosures does not scale, and the gap silently stalls
    real follow-up work exactly the way TICK006 already stops a phantom
    FILING claim from silently standing. One finding per ticket (the
    first uncited disclosure occurrence) rather than one per phrase hit --
    conservative on noise for a WARN-tier first turn-on, matching this
    rule's own `_TICK011_DISCLOSURE_PATTERNS` calibration posture.

    T-1402: this check is full strength (unchanged from the paragraph
    above) inside `_TICK011_ACTIVE_WINDOW` -- the window a disclosed cut
    can still be honestly turned into a real follow-up ticket. A ticket
    outside that window (or every ticket, if `_tick011_ticket_num` cannot
    parse anything to anchor a window on) is skipped by default: a
    2026-08-01 measurement found 50 unwaived findings, all against
    historical reports nobody can now reconstruct context for -- a
    dishonest-only-waivable-en-masse zero, not this rule's job to produce.
    Set `_TICK011_INCLUDE_HISTORY_ENV` non-empty to scan the full ledger
    anyway (deliberate history audits)."""
    known_ids = set(queue.tickets) | (
        set(archived.danger_ok) if archived.is_ok else set()
    )
    include_history = _tick011_include_history_opt_in()
    active_floor = 0 if include_history else _tick011_active_window_floor(known_ids)
    violations: list[Violation] = []
    for ticket in sorted(queue.tickets.values(), key=lambda t: t.id):
        if not include_history and not _tick011_in_active_window(
            ticket.id, active_floor
        ):
            continue
        found = _tick011_first_uncited_disclosure(ticket, known_ids)
        if found is not None:
            violations.append(found)
    return tuple(violations)


def _tick011_include_history_opt_in() -> bool:
    """True when `_TICK011_INCLUDE_HISTORY_ENV` is set to a non-empty value
    (T-1402) -- the deliberate-history-audit escape hatch that disables the
    active-window filter entirely (see `_TICK011_ACTIVE_WINDOW`'s
    docstring)."""
    # frob:waive SEC110 reason="T-1402: FROB_TICK011_INCLUDE_HISTORY is a boolean \
    # opt-in flag (same shape as the existing FROB_AGENT/FROB_WORKTREE precedent in \
    # frob.tickets._leases) that toggles whether this rule scans the historical ledger \
    # tail -- it carries no secret/confidential value"
    return bool(os.environ.get(_TICK011_INCLUDE_HISTORY_ENV))


def _tick011_first_uncited_disclosure(
    ticket: Ticket, known_ids: set[str]
) -> Violation | None:
    """The first uncited disclosure occurrence in `ticket`'s Done report
    (T-1402, split out of `_tick011_disclosed_cuts_without_ticket` to stay
    under `ARCH001`'s function-length threshold), or `None` if its Done
    report has no such occurrence -- one finding per ticket, matching that
    function's own docstring."""
    done_report_text = _tick006_done_report_text(ticket.body)
    if not done_report_text:
        return None
    for match in _tick011_disclosure_hits(done_report_text):
        lo = max(0, match.start() - _TICK011_VICINITY)
        hi = min(len(done_report_text), match.end() + _TICK011_VICINITY)
        vicinity = done_report_text[lo:hi]
        if _TICK011_NO_TICKET_NEEDED_RE.search(vicinity):
            continue
        if any(tid in known_ids for tid in _TICK006_ID_RE.findall(vicinity)):
            continue
        return Violation(
            rule="TICK011",
            severity=Severity.WARN,
            file="tickets.md",
            line=0,
            message=(
                f"TICK011: {ticket.id}'s Done report discloses "
                f'deferred/cut work ("{match.group(0)}") with no '
                f"ticket id cited nearby and no explicit "
                f"no-ticket-needed reason -- file the follow-up "
                f"ticket and cite it, or say so explicitly if none "
                f"is needed"
            ),
        )
    return None


# frob:ticket T-0820
# frob:enforces CHK-GATE-TICK007
# frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_stale_critical_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_fresh_critical_is_silent  # noqa: E501
# frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_medium_priority_never_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_blocked_ticket_is_silent  # noqa: E501
# frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_real_repo_scan_runs_end_to_end_without_crashing  # noqa: E501
def _tick007_undispatched_stale(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """TICK007 (T-0820): WARN per dispatchable (unblocked, unleased)
    CRITICAL/HIGH ticket that has sat past its `undispatched_stale`
    threshold (T-0752's `frob.tickets.undispatched_stale`/
    `dispatch_stale_hours` -- reused verbatim here, per T-0820's Description:
    the staleness judgment lives in exactly one place, this gate only
    surfaces it). T-0752 already renders this alarm in `frob ticket
    doable`'s human-facing listing; this is the same signal's `frob check`
    half, so it is caught mechanically rather than only when someone
    happens to run `doable` and read the UNDISPATCHED marker."""
    from frob.tickets import doable, has_live_lease, undispatched_stale

    tickets = doable(queue, root)
    dispatchable = [t for t in tickets if not has_live_lease(t, root)]
    alarms = undispatched_stale(dispatchable, root)
    violations: list[Violation] = []
    for t, elapsed, threshold in alarms:
        violations.append(
            Violation(
                rule="TICK007",
                severity=Severity.WARN,
                file="tickets.md",
                line=0,
                message=(
                    f"TICK007: {t.id} ({t.priority.value} priority) has sat "
                    f"dispatchable and unleased for {elapsed:.0f}h "
                    f"(threshold {threshold:.0f}h) -- it is undispatched-"
                    f"stale; dispatch it or re-prioritize it "
                    f"(`frob ticket priority {t.id} <level>`)"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-0842
# frob:enforces CHK-GATE-TICK008
# frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_fires_on_unknown_field  # noqa: E501
# frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_fuzzy_hint_on_near_miss_typo  # noqa: E501
# frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_silent_on_clean_ledger  # noqa: E501
# frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_real_repo_ledger_is_tick008_clean  # noqa: E501
# frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_waivable  # noqa: E501
def _tick008_unknown_ledger_fields(queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK008 (T-0842): WARN on every ticket in the CHECKED ledger that
    carries unknown/extra frontmatter field(s) -- the mechanical follow-up
    T-0838's reviewer mandated. T-0838 made `Ticket` `extra="allow"` so a
    ledger written by a NEWER binary (a field this model does not know
    about yet) loads instead of hard-failing `MalformedFrontmatter`; the
    disclosed cost is that a TYPOED known field (`priorty: low`) is
    indistinguishable from that at load time -- it silently becomes an
    extra, the schema default is used instead, and the only signal is a
    WARNING log line (`_warn_unknown_extras`) no gate reads. This makes
    that drift visible mechanically on `main`, where the ledger must be
    canonical, without re-tightening `extra="allow"` back to `"forbid"`
    (that would re-brick forward-compat loading, the exact thing T-0838
    fixed).

    WARN, NOT ERROR -- this is a corrected decision, not the original one.
    An initial ERROR pass was REJECTED in adversarial review of T-0842
    itself, and the failure mode is worth stating explicitly so a future
    "promote to ERROR" attempt re-derives the same constraint instead of
    re-discovering it the hard way: `frob ticket land`'s claim
    re-verification (`_reverify_done_report_claims_post_merge`) spawns
    `frob check --ticket <id>` via `sys.executable` from the ROOT
    checkout's venv (playbook section 2's stale-binary hazard -- the ROOT
    binary's `src` tree, not the landing worktree's). While a schema-
    extending ticket is ITSELF being landed, the root binary's `Ticket`
    model does not yet know the new field it is landing -- a populated new
    field on that very ticket's own block gets captured as
    `__pydantic_extra__` by the root's OLD model. `tickets_gate` never
    scopes TICK008 to only the active ticket (it scans the whole merged
    queue, correctly, since a stale field anywhere is real drift) -- so an
    ERROR here fires over the full merged ledger at exactly the moment the
    schema-owning ticket lands, `real_errors` diverges from the worktree-
    captured claim, and land refuses via `ClaimDivergence`. A
    `frob:waive TICK008` cannot route around this either: the same stale
    root binary evaluating the gate is the one evaluating the waiver, so
    the schema gap that causes the false ERROR equally prevents the waiver
    from being understood as covering it. In short: "the schema catches up"
    -- the condition the original docstring claimed made ERROR safe -- IS
    the land event itself, which is exactly the window ERROR breaks. WARN
    avoids this because `frob check`'s pass/fail gating (and land's
    real-errors/claim-divergence comparison) keys off ERROR-severity
    counts, not warnings; a WARN still renders as a live, mechanical `frob
    check` finding (the T-0838 review's actual demand -- visibility, not
    a hard gate), matching the TICK004/TICK006/TICK007 precedent of
    leaving open-ended-judgment/schema-transition cases as WARN rather
    than ERROR. Fuzzy-matches each unknown key against the model's own
    known field names via `difflib.get_close_matches` so a typo like
    `priorty` names its likely intended field (`priority`) directly in the
    message instead of leaving the fix to guesswork. Waivable (not added
    to `_UNWAIVABLE_RULES`) per the TICK004/TICK006/TICK007 precedent: a
    genuinely temporary, disclosed exception stays available the same way."""
    known_fields = sorted(Ticket.model_fields)
    violations: list[Violation] = []
    for ticket in queue.tickets.values():
        violations.extend(_tick008_violations_for_ticket(ticket, known_fields))
    return tuple(violations)


# frob:ticket T-0976
def _tick008_violations_for_ticket(
    ticket: Ticket, known_fields: list[str]
) -> list[Violation]:
    """One ticket's TICK008 findings: one WARN per unknown pydantic-extra
    ledger field it carries, fuzzy-matched (`difflib.get_close_matches`)
    against `known_fields` so a typo like `priorty` names its likely
    intended field directly -- the per-ticket half of `_tick008_unknown_
    ledger_fields`."""
    extras = ticket.__pydantic_extra__
    if not extras:
        return []
    violations: list[Violation] = []
    for extra_field in sorted(extras):
        hint = ""
        close = difflib.get_close_matches(extra_field, known_fields, n=1)
        if close:
            hint = f" -- did you mean '{close[0]}'?"
        violations.append(
            Violation(
                rule="TICK008",
                severity=Severity.WARN,
                file="tickets.md",
                line=0,
                message=(
                    f"TICK008: {ticket.id} carries unknown ledger "
                    f"field '{extra_field}'{hint} (value lost to the "
                    f"schema default until the field name is fixed or "
                    f"the schema-owning feature lands)"
                ),
            )
        )
    return violations


# frob:ticket T-0714
# frob:ticket T-1645
# frob:enforces CHK-GATE-TICK009
def _tick009_scope_breadth_nudges(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """TICK009 (T-0714): one WARN per over-broad-scope nudge
    `frob.tickets.large_glob_warnings` finds across every planned/
    in-progress ticket -- the same detail `frob ticket doable` used to
    print, unconditionally, as a `WARNING:` line PER nudge on EVERY queue
    query (observed flooding a 5-lease session-start listing). `doable`
    now only shows a single count line
    (`frob.app.ticket_runner._render_scope_breadth_summary`); this gate is
    where the per-ticket remediation detail lives instead, reported once
    per `frob check` run rather than once per `doable` invocation. Purely
    a relocation -- `large_glob_warnings` itself (T-0453) is unchanged.

    T-1645: a `QUEUED` ticket no longer fires at all. Its declared scope
    is a PREDICTION of what work will eventually touch, made before
    anyone has opened the code -- demanding file-level precision at that
    point produces one of two bad outcomes, both observed on this repo's
    own ledger (48 tickets, ~204 findings, 40 filed in a single incident-
    response session where the honest scope for most really was a
    package glob): either the author invents a narrow list that turns
    out wrong (the implementer scope-adds anyway, so the declaration was
    noise), or the honest broad scope carries a permanent warning nobody
    ever acts on because there is nothing yet TO narrow it to. By `frob
    ticket start` (which also surfaces this same nudge directly, see
    `frob.app.ticket_runner._lifecycle._warn_scope_breadth_on_start`) the
    ticket is `PLANNED`/`IN_PROGRESS`, the author has the code open, and
    a broad scope has started actually costing other tickets (T-1639) --
    that is the point this nudge is worth making, not before."""
    from frob.tickets import TicketState, large_glob_warnings, scope_breadth_context

    breadth = scope_breadth_context(root)
    violations: list[Violation] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state not in (TicketState.IN_PROGRESS, TicketState.PLANNED):
            continue
        # frob:ticket T-1484
        # WAVE14-B: an acknowledged-broad ticket (`frob ticket scope-ack`)
        # is exempt entirely -- TICK009 previously had no waive channel at
        # all for a genuinely broad epic/umbrella scope, so every ledger
        # scan re-nudged the same already-decided tickets forever.
        if t.scope_breadth_ack:
            continue
        for warning in large_glob_warnings(t, root, breadth=breadth):
            violations.append(
                Violation(
                    rule="TICK009",
                    severity=Severity.WARN,
                    file="tickets.md",
                    line=0,
                    message=f"TICK009: {warning}",
                )
            )
    return tuple(violations)


# frob:ticket T-0714
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1056: leaked Unknown traces to leases_dir's own \
# Result-returning fallibility, already checked via .is_err below; no bare raise path \
# is reachable from this function's locally-visible calls"
# frob:waive EXHAUST002 reason="T-1056: json.JSONDecodeError is a ValueError subclass \
# already covered by this function's own except (OSError, ValueError); the resolver \
# does not perform subclass reasoning against the caught tuple"
# frob:enforces CHK-GATE-TICK010
def _tick010_stale_lease_report(root: Path) -> tuple[Violation, ...]:
    """TICK010 (T-0714): one WARN per cross-worktree lease file
    (`.git/frob-leases/*.json`, T-0473) whose recorded `worktree` path no
    longer exists on disk -- named by its lease-file path and ticket id,
    with the remedy spelled out (`frob.tickets._leases`'s own
    opportunistic prune already unlinks these the next time a `doable`/
    `start` call reads the leases directory; this gate exists to surface
    them ONCE with a location and remedy for a human/auditor, not to
    re-implement the prune). Silent when the leases directory does not
    exist or every lease's worktree is present -- this is a read-only scan
    (`Path.exists()`, not the internal TOCTOU-hardened liveness probe
    `frob.tickets._leases._probe_worktree_liveness` uses for its own
    unlink decision) so it never mutates the leases directory itself."""
    import json

    from frob.tickets._leases import leases_dir

    resolved = leases_dir(root)
    if resolved.is_err:
        return ()
    leases_root = resolved.danger_ok
    if not leases_root.is_dir():
        return ()

    violations: list[Violation] = []
    for path in sorted(leases_root.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        worktree = raw.get("worktree")
        ticket_id = raw.get("ticket_id", "?")
        if not worktree or Path(worktree).exists():
            continue
        violations.append(
            Violation(
                rule="TICK010",
                severity=Severity.WARN,
                file=str(path),
                line=0,
                message=(
                    f"TICK010: {ticket_id} lease {path} references worktree "
                    f"{worktree!r}, which no longer exists -- remove the "
                    f"lease file (it will also be opportunistically "
                    f"pruned the next time `frob ticket doable`/`start` "
                    f"reads the leases directory)"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-1259
# T-1259: the sunset date this repo has recorded for ledger v1 (monofile
# tickets.md/tickets-archive.md) in docs/modules/tickets.md's ledger-v2
# migration section -- LEDGERV1001 stays a WARNING before this date and
# escalates to a hard ERROR after it, mirroring DEPR004's own
# escalation-after-expiry shape (`_deprecated_is_expired`) one level up
# at the whole-ledger-backend granularity instead of a single symbol.
# Moving this date is a docs+code pair: update the recorded note in
# docs/modules/tickets.md in the SAME change as this constant so the two
# never silently disagree.
_LEDGERV1_SUNSET = "2027-02-02"


# frob:doc docs/modules/tickets.md#migration-to-v2-t-1259-docsdesignledger-v2md-section-7  # noqa: E501
# frob:doc docs/modules/tickets.md#storage-internals
# frob:waive COV007 reason="docs/modules/tickets.md's Storage internals section \
# individually frob:describes this private helper by name (T-0529) -- a deliberate \
# architecture doc, not accidental drift onto a private helper, same precedent as \
# _store_mode/_split_done_report/_migrate_one_v2 above"
# frob:tests tests/test_tickets_migration.py::TestLedgerV1DeprecationGate.test_monofile_mode_warns_before_sunset  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestLedgerV1DeprecationGate.test_monofile_mode_errors_past_sunset  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestLedgerV1DeprecationGate.test_v2_mode_repo_is_silent  # noqa: E501
# frob:enforces CHK-GATE-LEDGERV1001
def _ledgerv1001_violations(root: Path) -> tuple[Violation, ...]:
    """LEDGERV1001 (ledger v2 design section 7, deliverable 3): a repo
    that actually HAS legacy content (a real `tickets.md` or dir-mode
    `tickets/*.md` files on disk -- not merely `_store_mode`'s fresh-repo
    DEFAULT, which a from-scratch `tmp_path` test fixture with zero
    tickets would otherwise also match) gets one finding naming `frob
    ticket migrate --to v2` as the recorded path off the deprecated
    backend -- a WARNING while today's date has not yet passed
    `_LEDGERV1_SUNSET`, escalating to a hard ERROR once it has, mirroring
    the DEPR00x family's own "warn in-window, error past expiry" shape
    (`_deprecated_is_expired`/`_depr004_violations`) so an unmigrated repo
    does not silently carry the deprecated backend forever. Silent for a
    v2-mode repo, and silent for a repo with no ledger content of EITHER
    shape at all (nothing yet to migrate) -- there is nothing left (or
    nothing yet) to warn about in either case."""
    mode = _tickets_store_mode(root)
    if mode == "v2":
        return ()
    has_legacy_content = _tickets_ledger_path(root).exists() or bool(
        _tickets_dir_glob(root)
    )
    if not has_legacy_content:
        return ()
    from datetime import date

    expired = date.today().isoformat() > _LEDGERV1_SUNSET
    severity = Severity.ERROR if expired else Severity.WARN
    verb = "past its recorded sunset" if expired else "still within its recorded window"
    _log.debug(
        "LEDGERV1001: monofile-mode repo, %s (sunset=%s)", verb, _LEDGERV1_SUNSET
    )
    return (
        Violation(
            rule="LEDGERV1001",
            severity=severity,
            file="tickets.md",
            line=0,
            message=(
                f"LEDGERV1001: this repo is still ledger v1 (monofile "
                f"tickets.md/tickets-archive.md), {verb} "
                f"(sunset={_LEDGERV1_SUNSET}); run `frob ticket migrate "
                f"--to v2` to move to the file-per-ticket backend "
                f"(docs/design/ledger-v2.md)"
            ),
        ),
    )


# frob:doc docs/modules/tickets.md#decision-record-t-0162
def tickets_gate(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK001/TICK002/TICK003/TICK004/TICK005/TICK006/TICK007/TICK008/
    TICK009/TICK010/TICK011: the T-0162 ticket-id collision invariant
    gate, plus the T-0409 ledger-hygiene check, the T-0411 priority-rot
    check, the T-0537 post-merge terminal-state-regression lint, the
    T-0726 phantom-filing-claim check, the T-0820/T-0752 undispatched-
    stale-CRITICAL/HIGH alarm, the T-0842 unknown-ledger-field check, the
    T-0714 scope-breadth-nudge/stale-lease reports (relocated out of
    `frob ticket doable`'s own per-invocation diagnostics), and the
    T-1129 disclosed-cut-without-ticket check.

    T-0929 (docs/audits/check-performance.md row 10, `tickets` gate): the
    full `tickets.md`/`tickets-archive.md` ledger text is now loaded ONCE
    here and shared by `_tick001_duplicate_ids`/`_tick003_stale_archive`/
    `_tick006_phantom_filing`, instead of each of those three rules
    independently re-reading and re-parsing the same ledger files (a
    same-shape duplicate as the cross-stage redundant-parse class the
    audit's meta-gap finding (E) describes, one level down inside a
    single gate)."""
    # T-0714: TICK010 reads the leases directory directly (a plain
    # `Path.exists()` scan, not the internal liveness probe) and must run
    # BEFORE any call that touches `frob.tickets.read_all_leases` (TICK007
    # below, via `doable`/`has_live_lease`) -- that call opportunistically
    # UNLINKS a lease file the moment it confirms the worktree is gone, so
    # a report computed after it would find the very files it should be
    # reporting already removed out from under it.
    stale_leases = _tick010_stale_lease_report(root)
    active = _tickets_load_all(root)
    archived = _tickets_load_archive(root)
    return (
        _tick001_duplicate_ids(active, archived)
        + _tick002_draft_on_default(root, queue)
        + _tick003_stale_archive(root, active)
        + _tick004_queue_rot(root, queue)
        + _tick005_merge_state_regression(root, queue)
        + _tick006_phantom_filing(queue, archived)
        + _tick011_disclosed_cuts_without_ticket(queue, archived)
        + _tick007_undispatched_stale(root, queue)
        + _tick008_unknown_ledger_fields(queue)
        + _tick009_scope_breadth_nudges(root, queue)
        + stale_leases
        + _ledgerv1001_violations(root)
    )
