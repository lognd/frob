"""`frob ticket land` -- post-merge claim/evidence reverification.

See docs/modules/tickets.md#frob-ticket-land.

Split out of `frob.tickets._land` (T-1186, following the verbatim-move
pattern `_evidence.py`/`_reporting.py` set at T-1171): the family of
checks `_land_locked` runs AFTER the worktree/main merge has landed --
re-resolving evidence against the merged tree, re-checking Done-report
claims (test counts, gate state, gate findings) against what actually
holds post-merge rather than trusting what was true pre-merge. Zero
caller-visible behavior change -- every moved function keeps its
original body, docstring, and `frob:ticket`/`frob:tests` directives
verbatim; `frob.tickets._land` re-exports the public surface via
explicit import.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import (
    LandError,
    Ticket,
    is_cmd_evidence,
    matches_collected,
    render_claims_block,
    scope_matches,
)
from frob.tickets._store import write_ticket

_log = get_logger(__name__)


def _reverify_evidence_post_merge(
    worktree: Path,
    ticket_id: str,
    collected: Callable[[], frozenset[str]] | None,
    passed: Callable[[Sequence[str]], frozenset[str]] | None,
) -> Result[frozenset[str] | None, LandError]:
    """D-05: re-load `ticket_id` from the POST-MERGE worktree ledger and
    re-check every non-cmd evidence id still resolves against
    `collected()` and still shows passing in `passed(non_cmd_ids)` -- the
    ledger state `land` is about to finalize/close/squash-apply may differ
    from what `_land_precheck` validated pre-merge (a splice can rewrite
    `ticket.evidence`, see `_newer`/`_union_evidence`). `collected=None`
    and `passed=None` (both defaults) skip this entirely, so `land`'s
    behavior is unchanged unless a caller opts in.

    T-0754 review round 2 fix #3: on success, returns the exact `passed()`
    result (`Ok(frozenset[str])`) when `passed` was supplied, else
    `Ok(None)` -- letting `_reverify_done_report_claims_post_merge` derive
    its own re-verified test count from this SAME real run instead of
    paying for a second collect+run of the identical evidence set."""
    if collected is None and passed is None:
        return Ok(None)
    from frob.tickets import _load_one

    loaded = _load_one(worktree, ticket_id)
    if loaded.is_err:
        _log.error(
            "land: %s not found post-merge in %s -- cannot re-verify evidence",
            ticket_id,
            worktree,
        )
        return Err(LandError.NotFound)
    ticket = loaded.danger_ok
    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]

    if collected is not None:
        collected_ids = collected()
        unresolved = [e for e in non_cmd if not matches_collected(e, collected_ids)]
        if unresolved:
            _log.error(
                "land: %s evidence no longer resolves post-merge: %s -- "
                "the merged tree may have renamed/removed the covering "
                "test(s); refresh evidence (`frob ticket evidence %s "
                "<node-id>...`) and retry",
                ticket_id,
                unresolved,
                ticket_id,
            )
            return Err(LandError.NotCloseable)

    passing_ids: frozenset[str] | None = None
    if passed is not None:
        passing_ids = passed(non_cmd)
        failing = [e for e in non_cmd if e not in passing_ids]
        if failing:
            _log.error(
                "land: %s evidence did not pass post-merge: %s -- fix the "
                "failure and re-record evidence before retrying",
                ticket_id,
                failing,
            )
            return Err(LandError.NotCloseable)
    return Ok(passing_ids)


# frob:ticket T-0754
# frob:ticket T-0832
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds kind="integration"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_two_unmeasured_gate_claims_never_vacuously_match kind="integration"  # noqa: E501
# frob:ticket T-0846
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_lower_gate_error_count_than_claim_still_lands kind="integration"  # noqa: E501
def _reverify_done_report_claims_post_merge(
    worktree: Path,
    ticket_id: str,
    passing_ids: frozenset[str] | None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None = None,
) -> Result[None, LandError]:
    """T-0754's land-side half: re-load `ticket_id` from the POST-MERGE
    worktree ledger, recover any `### Captured claims` section its Done
    report carries (`parse_claims_from_done_report`), and -- when BOTH
    `passing_ids` (D-05's own real `passed()` run, review round 2 fix #3 --
    NOT a second collect+run) and `check_gates` are supplied -- compare
    against what was recorded at done-report time, erroring
    (`ClaimDivergence`) on a mismatch. `passing_ids=None` (D-05's evidence
    re-verify itself was skipped, i.e. the caller never supplied `passed`)
    or `check_gates=None` skips this entirely, matching
    `_reverify_evidence_post_merge`'s own permissive-by-default shape. A
    ticket with no Captured claims section (no capture callables were
    supplied at done-report time, or the Done report predates T-0754) is
    also skipped -- there is nothing recorded to diverge from.

    T-0754 review round 2 fix #1: only `gate_errors` -- the actual pass/
    fail signal -- is compared. `gate_warnings`/`gate_waived` are recovered
    from the claim and the fresh check but deliberately NOT compared: a
    repo-global warning/waived count legitimately drifts on a busy shared
    branch for reasons that have nothing to do with THIS ticket's own
    work, and gating on it would reproduce the same false-refusal failure
    mode this round's fix closes for the timing blob.

    T-0832: the test-count half and the gate-state half are independently
    measurable, and are now verified independently -- a ticket's test
    claim is checked whenever `passing_ids` is real (the common case), even
    on a run where the gate-state half cannot be re-verified at all. The
    gate-state half is SKIPPED, with an explicit logged notice (never a
    silent no-op and never a `-1`-vs-`-1` comparison), whenever either side
    of the comparison is unmeasured: `claims.gate_errors is None` (the Done
    report itself captured no gate state -- see `set_done_report`) or
    `check_gates()` returns `None` (the fresh post-merge check produced no
    parsable gate-summary -- missing lease, crash, unparsable output; this
    is exactly what happened for T-0830's self-closed, lease-released
    ticket). A skip is NOT a pass: it means the recorded gate-state claim,
    if any, could not be re-verified this land, and the notice says so; it
    does not by itself fail the land, matching this function's existing
    permissive-by-default posture for claims a caller opted out of
    measuring.

    T-0846: the gate-state half now refuses only on an INCREASE
    (`real_errors > claims.gate_errors`), never on exact-count inequality
    -- a fresh count strictly LOWER than the claim (a sibling land fixed
    something on main between done-report time and this post-merge check)
    is logged and allowed through instead of refusing. See the inline
    comment at the comparison itself for the full incident history (5
    burned land attempts, T-0755/T-0640) and the WAIVE004 limitation this
    does not fully close (needs a `frob.gates`/`frob.check` change outside
    this ticket's scope).

    T-0846 review (reject #1): the count-only `>` comparison above has its
    OWN masking gap -- a land whose own diff introduces N new errors sails
    through whenever an UNRELATED fix on the SAME branch removed more than
    N (a self-introduced regression laundered by a net-better scope-wide
    total). `check_gate_findings` (opt-in, alongside `check_gates`) closes
    this: when BOTH the captured claim (`claims.error_findings`) and a
    fresh `check_gate_findings()` call carry a real `frozenset[(rule_id,
    file)]`, the comparison is IDENTITY-based and scoped to `ticket.scope`
    (the diff-touched-files proxy available in this module -- see the
    inline comment below for why `ticket.scope` stands in for "this land's
    own diff") instead of a raw count: any NEW (rule, file) pair inside the
    ticket's own scope refuses, regardless of how the aggregate count
    moved. Either side missing an identity set (an old capture, or a
    caller that only ever wired `check_gates`) falls back to the count-only
    `>` comparison unchanged -- this is strictly additive, never a
    behavior change for a claim that never captured identities."""
    if passing_ids is None or check_gates is None:
        return Ok(None)
    from frob.tickets import _load_one
    from frob.tickets._models import parse_claims_from_done_report

    loaded = _load_one(worktree, ticket_id)
    if loaded.is_err:
        _log.error(
            "land: %s not found post-merge in %s -- cannot re-verify "
            "captured Done-report claims",
            ticket_id,
            worktree,
        )
        return Err(LandError.NotFound)
    ticket = loaded.danger_ok
    claims = parse_claims_from_done_report(ticket.body)
    if claims is None:
        return Ok(None)

    test_count_check = _reverify_test_count_claim(
        worktree, ticket, claims, passing_ids, ticket_id
    )
    if test_count_check.is_err:
        return test_count_check
    return _reverify_gate_state_claim(
        ticket, claims, ticket_id, check_gates, check_gate_findings
    )


# frob:ticket T-0976
# frob:ticket T-1000
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_matching_claims_land_succeeds kind="integration"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_divergent_test_count_refuses_land kind="integration"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_strictly_improved_test_count_auto_accepts_and_rewrites_recap kind="integration"  # noqa: E501
# frob:waive DUP001 reason="T-1186 split-induced false positive: the DUP001 template \
# similarity heuristic matches this claim-reverification shape against \
# frob.app.ticket_runner._close_cmd._reverify_evidence_for_close purely on \
# control-flow resemblance (both re-check a stored claim against a freshly-measured \
# value and return a bool|None) -- they reverify different claim kinds (test-count vs \
# evidence-passing) against different call sites (post-merge land vs interactive \
# close) and share no data type; this function moved verbatim from frob.tickets._land \
# as part of T-1186's split"
def _reverify_test_count_claim(
    worktree: Path,
    ticket: Ticket,
    claims,
    passing_ids: frozenset[str],
    ticket_id: str,  # noqa: ANN001
) -> Result[None, LandError]:
    """`_reverify_done_report_claims_post_merge`'s test-count-half check
    (T-1000, churn item 1): compares the fresh non-cmd-evidence passing/
    total counts against the captured claim. An EXACT match is a no-op
    (`Ok(None)`). A STRICT IMPROVEMENT -- the fresh counts are both `>=`
    what was recorded, and (by the caller's own upstream guarantee, see
    `_reverify_evidence_post_merge`) every non-cmd evidence id present now
    actually passes -- auto-accepts and rewrites the ticket's Captured
    claims section in place (`_rewrite_claims_section`) so the landing
    commit carries the fresh numbers instead of the stale ones, rather
    than refusing and forcing the identical manual `frob ticket done-
    report` + re-land cycle every time (~10 occurrences in one drive,
    docs/audits/coordination-churn.md#1). Only a genuine REGRESSION --
    either count now LOWER than recorded -- still refuses
    (`Err(ClaimDivergence)`); a fresh run with any failing evidence never
    reaches this function at all (`_reverify_evidence_post_merge` already
    refused it upstream, before this claims check ever runs)."""
    from frob.tickets._models import is_cmd_evidence

    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    real_test_count = len(passing_ids)
    real_evidence_count = len(non_cmd)
    tests_match = real_test_count == claims.test_count
    evidence_match = real_evidence_count == claims.evidence_count
    if tests_match and evidence_match:
        return Ok(None)
    tests_regressed = real_test_count < claims.test_count
    evidence_regressed = real_evidence_count < claims.evidence_count
    if tests_regressed or evidence_regressed:
        _log.error(
            "land: %s captured test-count claim regressed post-merge "
            "-- recorded %d/%d passing, re-run shows %d/%d passing; the "
            "merged tree may have changed the evidence set or a test's "
            "outcome since the Done report was written; refresh with "
            "`frob ticket done-report %s` and retry",
            ticket_id,
            claims.test_count,
            claims.evidence_count,
            real_test_count,
            real_evidence_count,
            ticket_id,
        )
        return Err(LandError.ClaimDivergence)
    # T-1000: strict improvement (both counts >= recorded, at least one
    # strictly greater) -- auto-accept and rewrite the recap rather than
    # refuse a land that introduced no regression at all.
    _log.info(
        "land: %s captured test-count claim strictly improved post-merge "
        "-- recorded %d/%d passing, re-run shows %d/%d passing; "
        "auto-accepting and rewriting the recap (T-1000, no manual "
        "done-report refresh needed)",
        ticket_id,
        claims.test_count,
        claims.evidence_count,
        real_test_count,
        real_evidence_count,
    )
    _rewrite_claims_section(
        worktree, ticket, claims, real_test_count, real_evidence_count, ticket_id
    )
    return Ok(None)


# frob:ticket T-1000
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_strictly_improved_test_count_auto_accepts_and_rewrites_recap kind="integration"  # noqa: E501
def _rewrite_claims_section(
    worktree: Path,
    ticket: Ticket,
    claims,  # noqa: ANN001
    real_test_count: int,
    real_evidence_count: int,
    ticket_id: str,
) -> None:
    """Rewrite `ticket`'s Done-report `### Captured claims` section in the
    post-merge worktree ledger to carry the fresh, strictly-improved
    test-count numbers (T-1000) -- the mechanical half of
    `_reverify_test_count_claim`'s auto-accept path, so the landing commit
    itself carries the corrected recap instead of the stale one that
    triggered the (no longer refused) divergence. Reconstructs the OLD
    rendered claims block via `render_claims_block` (the exact inverse of
    the `parse_claims_from_done_report` call that produced `claims`, so
    the text is guaranteed to appear verbatim in `ticket.body`) and
    replaces it with the NEW block carrying only the two test-count
    fields updated -- `gate_errors`/`gate_warnings`/`gate_waived`/
    `error_findings` are left exactly as captured, since only the test-
    count half was re-verified here.

    Best-effort: a write failure is logged and does not block the land --
    the underlying claim has already been judged safe to accept above;
    losing the cosmetic recap-rewrite is not worth refusing a good land
    over."""
    old_block = render_claims_block(claims)
    new_claims = claims.model_copy(
        update={
            "test_count": real_test_count,
            "evidence_count": real_evidence_count,
        }
    )
    new_block = render_claims_block(new_claims)
    if old_block not in ticket.body:
        _log.warning(
            "land: %s could not locate the exact captured-claims block in "
            "the ticket body to rewrite post-merge -- leaving the stale "
            "recap in place (cosmetic only, the land itself still "
            "proceeds)",
            ticket_id,
        )
        return
    new_body = ticket.body.replace(old_block, new_block, 1)
    updated = ticket.model_copy(update={"body": new_body})
    written = write_ticket(worktree, updated)
    if written.is_err:
        _log.warning(
            "land: %s failed to write the rewritten captured-claims recap "
            "(%s) -- leaving the stale recap in place (cosmetic only, the "
            "land itself still proceeds)",
            ticket_id,
            written.danger_err,
        )


# frob:ticket T-0976
def _reverify_gate_state_claim(
    ticket: Ticket,
    claims,  # noqa: ANN001
    ticket_id: str,
    check_gates: Callable[[], tuple[int, int, int] | None],
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None,
) -> Result[None, LandError]:
    """`_reverify_done_report_claims_post_merge`'s gate-state-half check
    (T-0832/T-0846): skips explicitly (never comparing a `-1` sentinel)
    when either side is unmeasured, tries the identity-based scope-
    filtered comparison first (T-0846 review), and falls back to the
    count-only "refuse only on an increase" comparison otherwise. See
    `_reverify_done_report_claims_post_merge`'s own docstring for the
    full incident history behind each branch here."""
    # T-0832: the gate-state claim can only be re-verified when BOTH sides
    # are actually measured. Never compare sentinels -- skip explicitly.
    if claims.gate_errors is None:
        _log.warning(
            "land: %s recorded Done report has no measured gate-state "
            "claim (it was unmeasured at done-report time) -- skipping "
            "gate-state re-verification; only the test-count claim was "
            "checked",
            ticket_id,
        )
        return Ok(None)

    fresh = check_gates()
    if fresh is None:
        _log.warning(
            "land: %s fresh `frob check --ticket %s` produced no parsable "
            "gate-summary post-merge (no lease, a crash, or unparsable "
            "output) -- cannot re-verify the recorded gate-state claim "
            "(%d error(s)); skipping gate-state re-verification, not "
            "comparing against a sentinel; only the test-count claim was "
            "checked",
            ticket_id,
            ticket_id,
            claims.gate_errors,
        )
        return Ok(None)

    real_errors, real_warnings, real_waived = fresh

    # T-0846 review (reject #1): try the IDENTITY-based, scope-filtered
    # comparison first -- it is strictly more precise than the count-only
    # fallback below and closes the masking gap a raw count can never
    # close (an unrelated fix elsewhere on the branch removing more errors
    # than this land's own diff introduced would otherwise net out to a
    # LOWER total and sail through). Only attempted when both sides
    # actually captured an identity set; either side missing one (an old
    # claim, or `check_gate_findings` not wired) falls through to the
    # count-only comparison unchanged.
    if claims.error_findings is not None and check_gate_findings is not None:
        identity_result = _reverify_gate_findings_by_identity(
            ticket, claims, ticket_id, check_gate_findings
        )
        if identity_result is not None:
            return identity_result

    # T-0846: count-only fallback, refusing only on an INCREASE over the
    # captured claim, never on exact-count equality. The prior strict `!=`
    # compared a count captured at done-report time against a fresh
    # post-merge count taken in a DIFFERENT tree state (main keeps moving
    # between the two captures) -- any main-side drift diverged the count
    # even when the drift was a genuine IMPROVEMENT (a sibling land fixing
    # an unrelated error this ticket never touched), refusing a land that
    # introduced no new problem at all and forcing a manual refresh-done-
    # report-and-retry loop (5 land attempts burned in one session,
    # T-0755/T-0640). A fresh count strictly GREATER than the claim is
    # still the meaningful, actionable signal (something this land or the
    # merge introduced got worse) and still refuses. A count that only
    # went down, or stayed the same, no longer refuses.
    #
    # T-0846 review (reject #1): this count-only path has a KNOWN masking
    # gap the identity-based path above closes whenever both sides capture
    # identities -- a land whose own diff introduces N new errors can
    # still sail through HERE (count-only) whenever an unrelated fix on
    # the same branch removed more than N. This path is now only reached
    # when at least one side of the claim never captured identities (an
    # old Done report, or a caller that only ever wired `check_gates`);
    # accepted as a deliberate, documented fallback for that case, not a
    # silent gap -- `check_gate_findings` closes it going forward for every
    # ticket whose Done report is written (or refreshed) after this fix.
    if real_errors > claims.gate_errors:
        _log.error(
            "land: %s captured gate-state claim no longer holds post-merge "
            "-- recorded %d error(s), a fresh `frob check --ticket %s` now "
            "shows %d error(s) (warnings %d->%d, waived %d->%d, informational "
            "only); refresh with `frob ticket done-report %s` and retry",
            ticket_id,
            claims.gate_errors,
            ticket_id,
            real_errors,
            claims.gate_warnings,
            real_warnings,
            claims.gate_waived,
            real_waived,
            ticket_id,
        )
        return Err(LandError.ClaimDivergence)
    if real_errors < claims.gate_errors:
        _log.info(
            "land: %s fresh post-merge gate-error count (%d) is LOWER than "
            "the captured claim (%d) -- not a divergence (T-0846: only an "
            "increase refuses), proceeding without refresh",
            ticket_id,
            real_errors,
            claims.gate_errors,
        )
    return Ok(None)


# frob:ticket T-0976
def _reverify_gate_findings_by_identity(
    ticket: Ticket,
    claims,  # noqa: ANN001
    ticket_id: str,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None],
) -> Result[None, LandError] | None:
    """The identity-based, scope-filtered half of `_reverify_gate_state_
    claim` (T-0846 review #1): `None` (not a `Result`) means "fall back to
    the count-only comparison" -- either `check_gate_findings()` itself
    produced nothing parsable, in which case the caller falls back, or a
    real `Result` deciding the comparison outright."""
    fresh_findings = check_gate_findings()
    if fresh_findings is None:
        _log.warning(
            "land: %s fresh `frob check --ticket %s` produced no "
            "parsable per-finding identities post-merge -- falling "
            "back to the count-only gate-state comparison",
            ticket_id,
            ticket_id,
        )
        return None
    new_findings = fresh_findings - claims.error_findings
    # T-0846: `ticket.scope` is the diff-touched-files PROXY this module
    # has on hand -- `frob.tickets` deliberately has no `frob.gitio`/
    # `frob.gates` diff-computation access (docs/rework.md cycle-
    # avoidance), so "a file this land's own diff touched" is
    # approximated by "a file this ticket's own declared scope covers." A
    # new error outside the ticket's own scope is attributable to
    # something else on the branch (an unrelated sibling ticket's own
    # work, still that ticket's own responsibility to catch at ITS land)
    # and does not refuse here -- only a new error inside this ticket's
    # own scope does.
    scoped_new = [
        (rule, file) for rule, file in new_findings if scope_matches(file, ticket.scope)
    ]
    if scoped_new:
        _log.error(
            "land: %s captured gate-state claim no longer holds "
            "post-merge -- %d NEW error finding(s) inside this "
            "ticket's own scope that were not in the captured "
            "claim: %s; refresh with `frob ticket done-report %s` "
            "and retry",
            ticket_id,
            len(scoped_new),
            sorted(scoped_new),
            ticket_id,
        )
        return Err(LandError.ClaimDivergence)
    _log.info(
        "land: %s identity-based gate-state re-verification found "
        "no new in-scope error finding (claim=%d, fresh=%d, "
        "new-out-of-scope=%d) -- proceeding without refresh",
        ticket_id,
        len(claims.error_findings),
        len(fresh_findings),
        len(new_findings) - len(scoped_new),
    )
    return Ok(None)
