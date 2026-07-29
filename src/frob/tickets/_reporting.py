"""frob.tickets._reporting -- the done-report/review/drop/attach family
(T-1171, T-1152/T-1108/T-1103 residue): freeform-label mutation
(`mutate_labels`), the mission-briefing composer (`brief_ticket`), the
Done-report write path (`compose_done_report`, `_capture_done_report_
claims`, `set_done_report`), failure-memory (`record_failure`), the
structured review channel (`_resolve_review_commit`, `record_review`,
`has_approved_review_for_commit`), first-class drop (`drop_ticket`), and
image/file attachments (`attach` and its `_attachment_bytes`/`_next_
attachment_path`/`_record_attachment` helpers) -- split out of
`frob.tickets.__init__` following T-1103's per-family extraction pattern
(verbatim moves, directives intact, public surface re-exported via
explicit imports, zero caller-visible behavior change).

Kept together because every one of these functions appends caller-
authored narrative or structured evidence onto an EXISTING ticket's body
or metadata after it was filed -- the "record what happened to this
ticket, in its own words" concern, as opposed to the state-machine
transition guard chain (`_evidence.py`) or the scope/schema mutations
(`_scope.py`/`_setters.py`) that already have their own homes.

`_load_one` and `_load_ticket_and_queue` intentionally STAY in
`frob.tickets.__init__` (both are shared by `add_acceptance`, still
there, and are depended on externally as bare package attributes via the
`from frob.tickets import _load_one` late-import indirection several
other split modules -- `_evidence.py`, `_land.py`,
`app/ticket_runner/_lifecycle.py` -- already use) -- this module late-
imports both from the package at call time rather than at load time, the
same load-order-safe indirection `_evidence.py`/`_setters.py`/`_scope.py`
use for the same two helpers, since `__init__` imports THIS module before
either exists yet at its own module scope.
"""
# frob:waive ARCH102 reason="the naming/usage clustering heuristic groups these 16 \
# exports into several clusters by surface-level name prefix and direct call edges \
# (mutate_labels/brief_ticket standalone, the done-report compose/capture/set trio, \
# record_failure/record_review/_resolve_review_commit/has_approved_review_for_commit, \
# drop_ticket, and the attach/_attachment_bytes/_next_attachment_path/_record_ \
# attachment quartet); the module docstring above already names the real cohesion -- \
# every one of these functions records caller-authored narrative or structured \
# evidence onto an EXISTING ticket after filing, not by call-graph adjacency alone; \
# same T-1103/T-1152 precedent as frob.tickets.__init__'s own ARCH102 waiver for the \
# identical reason (one deliberately centralized concern, not several bolted together)"
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/tickets/_reporting.py's exclusivity-vocabulary hits are source-level \
# design-rationale prose (docstrings describing already-implemented internal behavior, \
# verifiable by reading the code they annotate) rather than a separate cross-module \
# contract needing its own tracked invariant; disposed as a calibration batch, not \
# claim-by-claim -- module prose carried verbatim from frob.tickets.__init__ (T-1171 \
# split, same INV006-on-split-modules precedent as 0abc4e3a/T-1151 and T-1152's own \
# _evidence.py split)"

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._evidence import (
    base_ref_resolvable,
    compute_changed_lines,
    render_changed_block,
    render_evidence_block,
    transition,
)
from frob.tickets._models import (
    DONE_REPORT_HEADING,
    DROP_REASON_HEADING,
    FAILURE_LOG_HEADING,
    Attachment,
    AttachmentSource,
    DoneReportClaims,
    FailureEntry,
    ReviewEntry,
    ReviewVerdict,
    Ticket,
    TicketError,
    TicketState,
    is_cmd_evidence,
    render_claims_block,
    replace_done_report_section,
)
from frob.tickets._models import _split_scope_entries as _normalize_scope_entries
from frob.tickets._store import (
    atomic_write,
    attachments_dir,
    ledger_lock,
    slugify,
    tickets_dir,
    write_ticket,
)
from frob.tickets._worktree_guard import enforce_worktree_lease
from frob.tickets.clipboard import ClipboardError, clipboard_image

_log = get_logger(__name__)

AttachError = TicketError | ClipboardError

_MAX_WARN_BYTES = 1024 * 1024

# frob:ticket T-0579
# `frob ticket drop` writes its dated reason line under this heading instead
# of the hand-edited freeform prose the pre-T-0579 workflow used.
#
# T-0848: these are `frob.tickets._models`'s own `FAILURE_LOG_HEADING` /
# `DROP_REASON_HEADING` re-exported under this module's private naming
# convention, not a second hand-typed copy -- `_models._done_report_
# section_end`'s structural-sentinel set must never drift out of sync with
# the headings this module actually writes.
_FAILURE_LOG_HEADING = FAILURE_LOG_HEADING
_DROP_REASON_HEADING = DROP_REASON_HEADING


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_organization.py::TestMutateLabels.test_add_and_remove_labels  # noqa: E501
def mutate_labels(
    root: Path,
    ticket_id: str,
    *,
    add: Sequence[str] = (),
    remove: Sequence[str] = (),
) -> Result[Ticket, TicketError]:
    """Add/remove freeform `labels` on `ticket_id` (T-0454) -- orthogonal to
    `scope`'s lease-aware `mutate_scope`: a label is a plain organizational
    tag, never a filesystem glob, so it carries no lease-conflict check and
    no audit trail the way a scope mutation does. `add`/`remove` may be
    combined in one call; each is comma-split the same way `scope`/`labels`
    entries always are (`_split_scope_entries`, T-0241's normalization
    reused here). A no-op call (nothing to add or remove) is an error --
    same "don't call this for nothing" discipline `mutate_scope` enforces."""
    from frob.tickets import _load_ticket_and_queue

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    add_labels = _normalize_scope_entries(tuple(add))
    remove_labels = _normalize_scope_entries(tuple(remove))
    if not add_labels and not remove_labels:
        return Err(TicketError.LabelChangeEmpty)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        new_labels = tuple(lbl for lbl in ticket.labels if lbl not in remove_labels)
        for label in add_labels:
            if label not in new_labels:
                new_labels += (label,)
        updated = ticket.model_copy(update={"labels": new_labels})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s labels changed (+%d/-%d), now %s",
        ticket_id,
        len(add_labels),
        len(remove_labels),
        list(updated.labels),
    )
    return Ok(updated)


# frob:ticket T-0568
# frob:doc docs/modules/tickets.md#frob-ticket-brief-t-0568
# frob:tests tests/test_tickets_brief.py::TestBriefTicket.test_composes_full_briefing
def brief_ticket(root: Path, ticket_id: str) -> Result[str, TicketError]:
    """`frob ticket brief <id>` (T-0568): compose the complete agent
    mission briefing text (`frob.tickets._brief.compose_brief`) for
    `ticket_id` -- replacing the ~400 words of hand-typed dispatch
    boilerplate a coordinator otherwise repeats per ticket. `Err(NotFound)`
    if `ticket_id` does not resolve."""
    from frob.tickets import _load_one, leased_by, load_queue
    from frob.tickets._brief import compose_brief

    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    queue_result = load_queue(root)
    holders: tuple[tuple[str, str], ...] = ()
    if queue_result.is_ok:
        holders = leased_by(queue_result.danger_ok, ticket, root)

    return Ok(compose_brief(root, ticket, holders))


_LEADING_DONE_REPORT_HEADING_RE = re.compile(
    r"\A(?:[ \t]*\n)*[ \t]*#{1,6}[ \t]+done report[ \t]*\n?", re.IGNORECASE
)


# frob:ticket T-0826
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_strips_duplicate_leading_heading_from_why  # noqa: E501
def _strip_leading_done_report_heading(why: str) -> str:
    """Strip a leading '## Done report' (any `#` level, any case, optional
    leading blank lines) heading line from `why` (T-0826): `compose_done_
    report` always prepends its own canonical `DONE_REPORT_HEADING`, so a
    caller-supplied `why` (typically `--why-file` content an agent already
    wrote with its own heading) that starts with one too would otherwise
    render TWO headings back to back -- a recurring cosmetic ledger-noise
    finding reviewers kept re-flagging. Only a LEADING heading is
    stripped -- one appearing later in the narrative body is left alone,
    since it is not a duplicate of the one this function's caller is about
    to prepend."""
    return _LEADING_DONE_REPORT_HEADING_RE.sub("", why, count=1)


# frob:ticket T-0458
# frob:ticket T-0826
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_composes_all_three_sections  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_strips_duplicate_leading_heading_from_why  # noqa: E501
def compose_done_report(
    why: str,
    changed_lines: Sequence[str],
    evidence: Sequence[str],
    claims: DoneReportClaims | None = None,
) -> str:
    """Compose a full '## Done report' section: the caller's narrative
    `why` plus AUTO-FILLED Changed (`render_changed_block`), Evidence
    (`render_evidence_block`), and (T-0754, when `claims` is given) Captured
    claims (`render_claims_block`) sections -- the mechanical parts are
    always generated, never hand-typed, so they can never drift from what
    frob, git, and a real test/gate run actually observed. `claims=None`
    (the default) omits the Captured claims section entirely, matching
    every caller before T-0754.

    T-0826: if `why` itself already begins with a '## Done report' heading
    (case-insensitive, possibly preceded by blank lines -- e.g. an agent's
    `--why-file` content that already carries its own heading, a recurring
    cosmetic ledger noise reviewers kept flagging), that leading heading
    line is stripped BEFORE composing so the rendered block always has
    exactly one heading, never two."""
    why_text = _strip_leading_done_report_heading(why).strip() or (
        "(no narrative supplied)"
    )
    changed_block = render_changed_block(changed_lines)
    evidence_block = render_evidence_block(evidence)
    claims_section = f"\n\n{render_claims_block(claims)}" if claims is not None else ""
    return (
        f"{DONE_REPORT_HEADING}\n\n"
        f"{why_text}\n\n"
        f"### Changed\n{changed_block}\n\n"
        f"### Evidence\n{evidence_block}{claims_section}\n"
    )


# frob:ticket T-0976
# frob:waive DUP001 reason="T-1171 split-induced false positive: the DUP001 template \
# similarity heuristic matches this function's shape against \
# frob.vet._capability._ts_single_substitution_identifier (a TypeScript \
# single-substitution AST helper) purely on control-flow/hole-arity resemblance -- the \
# two functions share no domain, no data type, and no call relationship (Done-report \
# claims capture vs TS grammar parsing); this function moved verbatim from \
# frob.tickets.__init__ (pre-existing, unwaived there because the pre-move DUP scan \
# never paired it against this particular vet-module sibling) and carries no new logic"
def _capture_done_report_claims(
    ticket_id: str,
    ticket: Ticket,
    run_tests: Callable[[Sequence[str]], int] | None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None,
) -> "DoneReportClaims | None":
    """`set_done_report`'s T-0754/T-0832/T-0846 Captured-claims computation,
    split from its load-compose-write body: `None` unless BOTH `run_tests`
    and `check_gates` were supplied, else a `DoneReportClaims` with gate
    counts recorded as unmeasured (`None`, never a `-1` sentinel, T-0832)
    when `check_gates()` itself returns `None`."""
    if run_tests is None or check_gates is None:
        return None
    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    gate_result = check_gates()
    if gate_result is None:
        # T-0832: never embed a -1 sentinel -- record the gate half of the
        # claim as explicitly unmeasured instead.
        _log.warning(
            "ticket %s: fresh `frob check --ticket %s` produced no "
            "parsable gate-summary -- recording the Captured "
            "claims gate-state as unmeasured (the test-count claim "
            "is unaffected)",
            ticket_id,
            ticket_id,
        )
        gate_errors = gate_warnings = gate_waived = None
    else:
        gate_errors, gate_warnings, gate_waived = gate_result
    error_findings = check_gate_findings() if check_gate_findings is not None else None
    return DoneReportClaims(
        test_count=run_tests(non_cmd),
        evidence_count=len(non_cmd),
        gate_errors=gate_errors,
        gate_warnings=gate_warnings,
        gate_waived=gate_waived,
        error_findings=error_findings,
    )


# frob:ticket T-0458
# frob:ticket T-0754
# frob:ticket T-0832
# frob:ticket T-0846
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_composes_and_writes_atomically  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_caller_never_touches_markdown  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims.test_claims_captured_from_real_callables  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_two_unmeasured_gate_claims_never_vacuously_match kind="integration"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity kind="integration"  # noqa: E501
def set_done_report(
    root: Path,
    ticket_id: str,
    *,
    why: str,
    base_ref: str = "main",
    run_tests: Callable[[Sequence[str]], int] | None = None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None = None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None = None,
) -> Result[Ticket, TicketError]:
    """THE single write path for a ticket's Done report (T-0458): compose
    `why` (the caller's narrative -- the ONLY thing the caller supplies)
    with auto-filled Changed (`compute_changed_lines` vs `base_ref`) and
    Evidence (`render_evidence_block`, from the ticket's own recorded
    evidence) sections, then splice the result into `body`'s '## Done
    report' section via `replace_done_report_section` -- the caller never
    parses or edits markdown directly, and never re-derives block
    boundaries by hand (the exact failure mode -- a dropped marker, a
    mis-listed Changed/Evidence block, an Edit landing mid-section -- that
    repeatedly corrupted `tickets.md` when done by hand).

    T-0754: when BOTH `run_tests` and `check_gates` are supplied, this also
    CAPTURES (never lets the caller type) a `### Captured claims` section:
    `run_tests(non_cmd_evidence_ids)` actually runs the ticket's own
    recorded non-cmd evidence and returns the real passing count, and
    `check_gates()` runs a fresh `frob check --ticket` and returns its
    `(errors, warnings, waived)` COUNTS -- deliberately not that run's
    free-text summary line, whose per-gate timing blob is nondeterministic
    even against an unchanged tree (T-0754 review round 2's FATAL fix) --
    both rendered via `render_claims_block` into the same Done report
    `set_done_report` already writes, and later re-verified against the
    post-merge tree by `frob.tickets._land`'s
    `_reverify_done_report_claims_post_merge` (T-0754's land-side half).
    Either or both omitted (the default, `None`) skips the Captured claims
    section entirely -- unchanged behavior for every caller before T-0754,
    since computing either needs `frob.testing`/`frob.gates`/subprocess
    access `frob.tickets` deliberately does not have (docs/rework.md
    cycle-avoidance); the `frob ticket done-report` CLI supplies both by
    default (see `ticket_runner.py`'s `_done_report`).

    T-0832: `check_gates()` returning `None` means the fresh `frob check
    --ticket` it ran produced no parsable gate-summary (no lease, a crash,
    unparsable output) -- this is recorded as an UNMEASURED gate-state
    claim (`DoneReportClaims.gate_errors=None`, etc.), logged as a
    warning, and rendered via the explicit `unmeasured` marker
    (`render_claims_block`), never as a `-1` sentinel. A `-1` sentinel
    written here previously could later compare equal to another `-1`
    land observed post-merge, passing a re-verification that had actually
    measured nothing on either side (the T-0830 incident). The test-count
    half of the claim is unaffected -- `run_tests` always returns a real
    measured count whenever it runs at all.

    T-0846: `check_gate_findings()` (opt-in, additional to `check_gates`)
    returns a `frozenset[(rule_id, file)]` of the SAME fresh check's error
    findings -- captured alongside the plain count so `land`'s
    re-verification can compare identities (rule id + file) rather than a
    scope-wide total. A count-only comparison let a land whose own diff
    introduced N new errors sail through whenever an unrelated fix on the
    same branch removed more than N (a self-introduced regression
    laundered by a net-better total) -- the gap the count-only T-0846 `>`
    fix left open. `check_gate_findings=None` (the default) records no
    identity set (`DoneReportClaims.error_findings=None`), matching every
    caller before this addition; `_reverify_done_report_claims_post_merge`
    falls back to the count-only comparison whenever either side of the
    claim lacks an identity set.

    T-0887: `base_ref` is validated (`base_ref_resolvable`) BEFORE any
    other work -- an unresolvable ref (in a real git checkout) returns
    `Err(TicketError.BaseRefUnresolvable)` immediately rather than being
    discovered minutes later via a silently-empty diff or a downstream
    `frob check` spawn. T-0887 also moves the (potentially slow, up to
    two 600s `frob check --ticket` subprocess spawns via `check_gates`/
    `check_gate_findings`) claims capture OUTSIDE the `ledger_lock` --
    those are read-only and do not need the single-writer lock at all;
    holding the lock across them used to serialize every OTHER concurrent
    ticket mutation on this ledger behind up to ~20 minutes of subprocess
    spawns (the observed "hangs under concurrent tickets.md lock
    contention" symptom class). Only the final load-compose-write is now
    held under `ledger_lock` end to end, so a concurrent `set_done_
    report`/`add_evidence`/`new_ticket` call on the same ledger still can
    never interleave with THAT part (T-0458 single-writer invariant) --
    the narrow tradeoff is that `ticket.evidence` used to compute the
    non-cmd id list fed to `run_tests`/claims is read once, before the
    lock, and could in principle be stale if evidence changes
    concurrently between that read and the final write; the Evidence
    section itself is always rendered from the freshly-reloaded ticket
    inside the lock, so the written report's Evidence block can never be
    stale, only (rarely) the Captured claims' `evidence_count`."""
    from frob.tickets import _load_one

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)

    resolvable = base_ref_resolvable(root, base_ref)
    if resolvable is False:
        _log.error(
            "ticket %s: done-report --base-ref %r does not resolve to a "
            "commit in this clone -- fetch it or pass a base ref that "
            "exists",
            ticket_id,
            base_ref,
        )
        return Err(TicketError.BaseRefUnresolvable)

    preloaded = _load_one(root, ticket_id)
    if preloaded.is_err:
        return Err(preloaded.danger_err)
    changed_lines = compute_changed_lines(root, base_ref)
    claims = _capture_done_report_claims(
        ticket_id, preloaded.danger_ok, run_tests, check_gates, check_gate_findings
    )

    with ledger_lock(root):
        loaded = _load_one(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket = loaded.danger_ok
        report = compose_done_report(why, changed_lines, ticket.evidence, claims)
        updated = ticket.model_copy(
            update={"body": replace_done_report_section(ticket.body, report)}
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s Done report set (%d evidence id(s), %d changed line(s)%s)",
        ticket_id,
        len(ticket.evidence),
        len(changed_lines),
        f", claims={claims.test_count}/{claims.evidence_count} tests"
        if claims is not None
        else "",
    )
    return Ok(updated)


# frob:doc docs/modules/tickets.md#public-api
def record_failure(
    root: Path, ticket_id: str, entry: FailureEntry
) -> Result[Ticket, TicketError]:
    """Append entry to the '## Failure log' body section, creating it if absent."""
    from frob.tickets import _load_one

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    line = f"- {entry.date.isoformat()} attempt {entry.attempt}: {entry.summary}"
    new_body = _append_to_section(ticket.body, _FAILURE_LOG_HEADING, line)
    updated = ticket.model_copy(update={"body": new_body})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info("tickets: %s recorded failure attempt %d", ticket_id, entry.attempt)
    return Ok(updated)


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#public-api
# frob:waive COV007 reason="docs/modules/tickets.md#public-api individually names \
# _resolve_review_commit by name (T-0529 precedent: a deliberate architecture-doc \
# callout of the never-store-abbreviated-SHA security behavior, not accidental drift \
# onto a private helper)"
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_unresolvable_commit_rejected  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_short_sha_normalized_to_full_sha  # noqa: E501
def _resolve_review_commit(root: Path, commit: str) -> Result[str, TicketError]:
    """Resolve `commit` (a short SHA, ref name, `HEAD`, ...) to its full
    40-char SHA via `git rev-parse` under `root` (T-0571 review round 2):
    `record_review` must NEVER store a caller-supplied commit verbatim --
    `has_approved_review_for_commit` does a plain string-equality
    comparison against a full `rev-parse HEAD` sha, so an abbreviated
    value (e.g. copied from `git log --oneline`) would silently never
    match and make `close --strict` permanently unsatisfiable for that
    review. `Err(ReviewCommitUnresolvable)` on any git failure (unknown
    ref, not a git repo, ...) -- an unresolvable input is never stored
    raw."""
    from frob.gitio import run_argv

    resolved = run_argv(["git", "-C", str(root), "rev-parse", commit])
    if (
        resolved.is_err
        or resolved.danger_ok.returncode != 0
        or not resolved.danger_ok.stdout.strip()
    ):
        _log.warning(
            "tickets: review --commit %r did not resolve under %s", commit, root
        )
        return Err(TicketError.ReviewCommitUnresolvable)
    return Ok(resolved.danger_ok.stdout.strip())


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#structured-review-channel-t-0571
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_appends_approve_entry  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_blank_findings_rejected  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_multiple_reviews_append_only  # noqa: E501
def record_review(
    root: Path,
    ticket_id: str,
    *,
    verdict: ReviewVerdict,
    reviewer: str,
    findings: str,
    commit: str,
) -> Result[Ticket, TicketError]:
    """Append a structured `ReviewEntry` to `ticket_id`'s append-only
    `reviews` list (T-0571) -- the first-class evidence channel for
    adversarial review, replacing a verdict pasted only into dispatch
    chat. `Err(ReviewFindingsMissing)` if `findings` is blank: a review
    record with no findings text is indistinguishable from one nobody
    actually read. `commit` is normalized to its full SHA via
    `_resolve_review_commit` before storage (T-0571 review round 2):
    `Err(ReviewCommitUnresolvable)` if it does not resolve, rather than
    storing an abbreviated/unnormalized value that could never satisfy
    `close --strict`'s exact-match comparison later. Never validates
    `verdict` against the ticket's own state beyond schema -- `close
    --strict` is what decides whether a given review record actually
    satisfies the gate."""
    from frob.tickets import _load_one

    if not findings.strip():
        return Err(TicketError.ReviewFindingsMissing)
    resolved_commit = _resolve_review_commit(root, commit)
    if resolved_commit.is_err:
        return Err(resolved_commit.danger_err)
    commit = resolved_commit.danger_ok
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    entry = ReviewEntry(
        verdict=verdict,
        reviewer=reviewer,
        findings=findings.strip(),
        commit=commit,
        at=date.today(),
    )
    updated = ticket.model_copy(update={"reviews": ticket.reviews + (entry,)})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info(
        "tickets: %s recorded review verdict=%s reviewer=%s commit=%s",
        ticket_id,
        verdict.value,
        reviewer,
        commit,
    )
    return Ok(updated)


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_review.py::TestHasApprovedReviewForCommit.test_true_only_for_matching_approve  # noqa: E501
def has_approved_review_for_commit(ticket: Ticket, commit: str) -> bool:
    """Whether `ticket` carries at least one `verdict: approve` review
    record naming exactly `commit` (T-0571) -- the predicate `close
    --strict` gates on. A ticket with zero review records, or reviews that
    only name earlier commits (the code moved since the last review), both
    return `False`: a stale approval is not an approval of the CURRENT
    final commit."""
    return any(
        r.verdict == ReviewVerdict.APPROVE and r.commit == commit
        for r in ticket.reviews
    )


# frob:ticket T-0579
# frob:doc docs/modules/tickets.md#public-api
def drop_ticket(
    root: Path, ticket_id: str, reason: str, *, absorbed_by: str | None = None
) -> Result[Ticket, TicketError]:
    """First-class `frob ticket drop` (T-0579): append a dated reason line
    under '## Drop reason' (creating the section if absent, same pattern as
    `record_failure`'s '## Failure log'), then transition to DROPPED through
    the normal state machine so a held worktree lease is released the same
    way any other terminal transition releases one
    (`_sync_cross_worktree_lease`) -- this replaces the pre-T-0579 workflow
    of hand-editing `state: dropped` directly, which left leases dangling
    and never recorded why. `Err(DropReasonMissing)` if `reason` is blank:
    a drop with no reason is indistinguishable from a silent discard later.
    `absorbed_by` (a ticket id) is appended parenthetically to the line when
    given, but is NOT validated against the queue -- it is a cross-reference
    note, not a `blocked_by`-style edge."""
    from frob.tickets import _load_one

    if not reason.strip():
        return Err(TicketError.DropReasonMissing)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    line = f"- {date.today().isoformat()}: {reason.strip()}"
    if absorbed_by:
        line += f" (absorbed by {absorbed_by})"
    new_body = _append_to_section(ticket.body, _DROP_REASON_HEADING, line)
    updated = ticket.model_copy(update={"body": new_body})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)

    transitioned = transition(root, ticket_id, TicketState.DROPPED)
    if transitioned.is_err:
        _log.error(
            "tickets: %s drop reason recorded but transition failed: %s",
            ticket_id,
            transitioned.danger_err,
        )
        return Err(transitioned.danger_err)
    _log.info("tickets: %s dropped: %s", ticket_id, reason.strip())
    return transitioned


def _append_to_section(body: str, heading: str, line: str) -> str:
    """Append `line` under `heading` in body; create the section at the end if gone."""
    lines = body.splitlines()
    for i, text in enumerate(lines):
        if text.strip() != heading:
            continue
        insert_at = i + 1
        while insert_at < len(lines) and not lines[insert_at].startswith("## "):
            insert_at += 1
        while insert_at > i + 1 and lines[insert_at - 1].strip() == "":
            insert_at -= 1
        lines.insert(insert_at, line)
        return "\n".join(lines) + ("\n" if body.endswith("\n") else "")
    separator = (
        ""
        if not body or body.endswith("\n\n")
        else ("\n" if body.endswith("\n") else "\n\n")
    )
    return f"{body}{separator}{heading}\n{line}\n"


def _attachment_bytes(
    ticket_id: str, source: AttachmentSource
) -> Result[tuple[bytes, str], AttachError]:
    """Read attachment `(data, suffix)` from the clipboard or `source.path`."""
    if source.path is None:
        _log.debug("tickets: attach %s from clipboard", ticket_id)
        image_result = clipboard_image()
        if image_result.is_err:
            return Err(image_result.danger_err)
        return Ok((image_result.danger_ok, ".png"))
    _log.debug("tickets: attach %s from %s", ticket_id, source.path)
    try:
        data = source.path.read_bytes()
    except OSError as exc:
        _log.error("tickets: failed to read attachment source %s: %s", source.path, exc)
        return Err(TicketError.WriteFailed)
    return Ok((data, source.path.suffix or ".png"))


# frob:doc docs/modules/tickets.md#public-api
def attach(
    root: Path, ticket_id: str, source: AttachmentSource, caption: str
) -> Result[Attachment, AttachError]:
    """Copy a file (or clipboard image) into tickets/attachments/<id>/ and record it."""
    from frob.tickets import _load_one

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    bytes_result = _attachment_bytes(ticket_id, source)
    if bytes_result.is_err:
        return Err(bytes_result.danger_err)
    data, suffix = bytes_result.danger_ok

    if len(data) > _MAX_WARN_BYTES:
        _log.warning(
            "tickets: attachment for %s is %d bytes (>1MB)", ticket_id, len(data)
        )

    sha256 = hashlib.sha256(data).hexdigest()
    dest_path = _next_attachment_path(root, ticket_id, caption, suffix)

    write_result = atomic_write(dest_path, data)
    if write_result.is_err:
        return Err(write_result.danger_err)

    return _record_attachment(root, ticket, dest_path, caption, sha256)


def _next_attachment_path(
    root: Path, ticket_id: str, caption: str, suffix: str
) -> Path:
    """The next `NN-slug.ext` attachment path under the ticket's attachment dir."""
    dest_dir = attachments_dir(root, ticket_id)
    existing = sorted(dest_dir.glob("[0-9][0-9]-*")) if dest_dir.exists() else []
    next_index = len(existing) + 1
    return dest_dir / f"{next_index:02d}-{slugify(caption)}{suffix}"


def _record_attachment(
    root: Path, ticket: Ticket, dest_path: Path, caption: str, sha256: str
) -> Result[Attachment, AttachError]:
    """Append the written attachment to `ticket` and persist the ticket."""
    rel_path = str(dest_path.relative_to(tickets_dir(root)))
    attachment = Attachment(path=rel_path, caption=caption, sha256=sha256)
    updated = ticket.model_copy(
        update={"attachments": ticket.attachments + (attachment,)}
    )
    frontmatter_write = write_ticket(root, updated)
    if frontmatter_write.is_err:
        return Err(frontmatter_write.danger_err)
    _log.info(
        "tickets: attached %s to %s (sha256=%s)", dest_path.name, ticket.id, sha256
    )
    return Ok(attachment)
