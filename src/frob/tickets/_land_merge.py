"""`frob ticket land` -- pre-merge closeability validation + commit message.

See docs/modules/tickets.md#frob-ticket-land.

Split out of `frob.tickets._land` (T-1186, following the verbatim-move
pattern `_evidence.py`/`_reporting.py` set at T-1171), then progressively
narrowed by T-1189/T-1192/T-1194/T-1251 as each cohesive family moved to
its own module:

- T-1189 split the union-zone conflict-block resolution family out into
  `frob.tickets._land_merge_zones`.
- T-1194 split the per-ticket-id newest-wins ledger merge family out into
  `frob.tickets._land_ledger_merge`.
- T-1251 split the git-plumbing/wip-commit family (main-into-worktree merge
  staging, out-of-scope conflict auto-resolution, the wip-commit trio,
  ledger/archive splice-and-stage, the deletion-authorization pair, the
  `frob:waive`-deletion laundering guards, and the shared git primitives)
  out into `frob.tickets._land_git_ops`.

What remains here is the pre-merge closeability-validation family
(`_validate_closeable`, `_validate_acceptance_bound`,
`_validate_evidence_kind_consistency`) and the landing commit-message
helper (`_commit_message`), plus a re-export of `splice_ledger` (now
implemented in `frob.tickets._land_ledger_merge`) so
`frob.tickets.__init__`'s `from frob.tickets._land import land,
splice_ledger` public import path stays stable. Zero caller-visible
behavior change from any of these splits -- every moved function kept its
original body, docstring, and `frob:ticket`/`frob:tests` directives
verbatim throughout."""

from __future__ import annotations

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._land_git_ops import _archived_ids, _deletion_owned
from frob.tickets._land_ledger_merge import _has_done_report, splice_ledger
from frob.tickets._models import (
    CMD_EVIDENCE_ALLOWED_KINDS,
    DROP_REASON_HEADING,
    LandError,
    Ticket,
    TicketState,
    is_cmd_evidence,
    unbound_acceptance,
)

__all__ = [
    "splice_ledger",
    "_archived_ids",
    "_deletion_owned",
    "_validate_closeable",
    "_validate_acceptance_bound",
    "_validate_evidence_kind_consistency",
    "_commit_message",
]

_log = get_logger(__name__)


# frob:ticket T-1701
def _has_drop_reason(body: str) -> bool:
    """Whether `body` carries a `## Drop reason` heading with at least one
    real (non-blank) line under it -- the DROPPED-side twin of
    `_has_done_report` (T-1701). `frob.tickets._reporting.drop_ticket`
    always writes a dated bullet line here before ever transitioning to
    DROPPED (`Err(DropReasonMissing)` refuses an empty reason at write
    time), so this should never see a heading with nothing under it in
    practice -- checked anyway rather than trusting the heading's mere
    presence, matching `_has_done_report`'s own "heading alone is not
    enough" posture for the DONE side (D-03)."""
    if DROP_REASON_HEADING not in body:
        return False
    lines = body.splitlines()
    try:
        start = next(
            i for i, ln in enumerate(lines) if ln.strip() == DROP_REASON_HEADING
        )
    except StopIteration:
        return False
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.strip():
            return True
    return False


# frob:ticket T-1701
def _validate_closeable(ticket: Ticket) -> Result[None, LandError]:
    """The evidence + Done-report + acceptance-binding preconditions
    `transition(..., DONE)` will enforce anyway -- checked here FIRST,
    before any git mutation, so a landing never merges main (and commits a
    merge/finalize commit) into the worktree only to discover at close time
    that it must be unwound (the exact ordering hazard T-0176 exists to
    close, and T-0763's own closeability-preflight-before-merge fix: every
    close precondition that is knowable from the PRE-merge ticket alone --
    evidence present, Done report present, evidence-kind consistency
    (T-0215), and now unbound acceptance criteria (T-0572) -- is checked
    here, before `_land_merge_stage` ever runs `git merge`. `EvidenceScopeUnbound`
    is checked separately, by `_land_precheck`'s own
    `_validate_scope_covered_preflight` call (T-0774), not inside this
    function: it needs the injected `covers_scope` callable (`frob.gates`'s
    job, which `frob.tickets` cannot import -- docs/rework.md cycle-
    avoidance), which this function does not receive. That preflight is a
    PRE-merge simulation against the worktree's current tree, closing the
    residual fail-after-merge class this docstring used to describe as
    permanent; `_land_finalize_and_close` still re-checks `covers_scope`
    unconditionally against the actual POST-merge tree as the authoritative
    check. Also re-checks the T-0215 kind-consistency rule (`_transition_guard`'s
    DONE-path twin): a non-docs-kind ticket carrying any `cmd:` evidence
    entry -- kind hand-edited after the entry was recorded, or the entry
    hand-pasted directly into the ledger -- must never land, mirroring the
    write-time gate in `add_cmd_evidence`.

    T-1701: a ticket already `DROPPED` in the worktree ledger (`frob
    ticket drop`, not `close`) takes a SEPARATE, state-dependent path --
    a REASON is the whole artifact a drop records (`drop_ticket` already
    refuses an empty one at write time, `DropReasonMissing`), and
    evidence/a Done report/acceptance-binding are simply not applicable
    to work that was explicitly cut, not done. Requiring them anyway
    forced every dropped ticket around `frob ticket land` entirely --
    the exact defect this ticket closes (an agent bypassing worktree
    isolation to `frob ticket drop` directly against the root checkout,
    since land had no other path for a legitimate DROPPED outcome)."""
    if ticket.state == TicketState.DROPPED:
        if not _has_drop_reason(ticket.body):
            _log.error(
                "land: %s cannot land -- dropped with no recorded reason; "
                "this should be unreachable (`frob ticket drop` refuses an "
                "empty --reason at write time) -- if you see this, the "
                "ledger was likely hand-edited; run `frob ticket drop %s "
                "--reason '...'` to record one properly",
                ticket.id,
                ticket.id,
            )
            return Err(LandError.NotCloseable)
        return Ok(None)
    if not ticket.evidence or not _has_done_report(ticket.body):
        _log.error(
            "land: %s cannot land -- missing evidence or a Done report; "
            "record evidence (`frob ticket evidence %s <node-id>...`, or for "
            "a docs-kind ticket `frob ticket close %s --evidence-cmd "
            "'<command>'`) and add a '## Done report' section under %s's "
            "entry in tickets.md, then retry `frob ticket land %s`",
            ticket.id,
            ticket.id,
            ticket.id,
            ticket.id,
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    kind_check = _validate_evidence_kind_consistency(ticket)
    if kind_check.is_err:
        return kind_check
    return _validate_acceptance_bound(ticket)


def _validate_acceptance_bound(ticket: Ticket) -> Result[None, LandError]:
    """`Err(NotCloseable)`, naming the specific unbound criterion/criteria,
    if `ticket` carries any acceptance criterion with no resolving evidence
    id (T-0572's `unbound_acceptance`, mirrored here pre-merge so a landing
    never merges/finalizes only to fail this same check at close time --
    T-0763). A ticket with no acceptance criteria declared is unaffected,
    matching `unbound_acceptance`'s own T-0572 backward-compat rule."""
    unbound = unbound_acceptance(ticket)
    if unbound:
        _log.error(
            "land: %s cannot land -- unbound acceptance criterion/criteria "
            "(no evidence id resolves them): %s; bind evidence to the "
            "criterion (`frob ticket evidence %s <node-id>... "
            "--accepts <index>`, 0-based) and retry `frob ticket land %s`",
            ticket.id,
            [c.text for c in unbound],
            ticket.id,
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    return Ok(None)


# frob:waive DUP001 reason="T-1186 split-induced false positive: the DUP001 template \
# similarity heuristic matches this guard-clause shape (early-return Result validation \
# over a small enum-kind check) against several unrelated validators across the repo \
# (invariants.py, _elaborate.py, _scope.py, _evidence.py) purely on control-flow \
# resemblance -- none share this function's domain (cmd-evidence-kind-vs-ticket-kind \
# closeability); this function moved verbatim from frob.tickets._land (pre-existing, \
# unwaived there because the pre-move DUP scan never paired it against these \
# particular unrelated files) as part of T-1186's _land.py split"
def _validate_evidence_kind_consistency(ticket: Ticket) -> Result[None, LandError]:
    """`Err(NotCloseable)` if `ticket`'s kind disallows cmd: evidence but it
    carries some anyway (see `_validate_closeable`'s T-0215 doc)."""
    if ticket.kind not in CMD_EVIDENCE_ALLOWED_KINDS and any(
        is_cmd_evidence(e) for e in ticket.evidence
    ):
        _log.error(
            "land: %s cannot land -- kind=%s carries cmd: evidence, only "
            "allowed for kind in %s; fix the ticket's kind or replace the "
            "cmd: entry with real pytest --evidence node ids, then retry "
            "`frob ticket land %s`",
            ticket.id,
            ticket.kind,
            sorted(k.value for k in CMD_EVIDENCE_ALLOWED_KINDS),
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    return Ok(None)


_KIND_TO_COMMIT_TYPE = {
    "feature": "feat",
    "bug": "fix",
    "security": "fix",
    "ux": "fix",
    "docs": "docs",
    "invariant": "test",
    "incident": "fix",
}


def _commit_message(ticket: Ticket, final_id: str) -> str:
    """Conventional-commit message for the landing commit (ASCII, no
    trailing period, no Co-Authored-By -- repo convention)."""
    commit_type = _KIND_TO_COMMIT_TYPE.get(ticket.kind.value, "chore")
    subject = f"{commit_type}(tickets): land {final_id} {ticket.title}"
    return subject[:120]
