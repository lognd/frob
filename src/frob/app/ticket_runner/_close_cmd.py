# frob:waive LARGE001 reason="T-2830 (T-1651-grade review): a real seam was \
# investigated -- the obligation-checking predicates (_covers_scope_for_ticket, \
# _close_mutation_evidence_for_ticket, _close_gate_claims_for_ticket, \
# _close_own_obligations_for_ticket, _reverify_evidence_for_close, and their own \
# private helpers, ~lines 213-929) look separable from the command entrypoints \
# (_close/_review/_reverify/_fail/_drop, ~lines 951-1756) at first glance. It is not a \
# real consumer-set boundary though: _land_cmd.py's own land-time guard \
# (_covers_scope_for_ticket) and gate-claims check (_close_gate_claims_for_ticket) \
# reuse these EXACT close-time predicates rather than duplicating them (see \
# _land_cmd.py's own comments at those call sites) -- they are shared close/land \
# obligation logic that happens to live here because close was extracted first \
# (T-1089), not a distinct concern of _close_cmd alone. Splitting them into their own \
# module changes nothing about who calls what, only where the call crosses a file \
# boundary, and this dir's own dispatch caution (T-2830's brief) is explicit that a \
# bad split on a file this heavily exercised by the landing path is worse than the \
# warning it would silence. Filed T-2835 (renumbers at land) to evaluate a proper \
# extraction (obligation predicates -> frob.tickets, where _land_cmd already imports \
# similar shared helpers from) as its own carefully- scoped, non-batch ticket."
"""frob.app.ticket_runner._close_cmd -- the `close`/`reverify`/`review`/
`fail`/`drop` command family.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

from ._lifecycle import _load_ticket_or_exit
from ._verify import (
    _apply_cmd_evidence,
    _apply_evidence,
    _check_gate_findings_fn,
    _check_gates_summary_fn,
    _run_tests_count_fn,
    _shared_check_spawn_fn,
)

_CACHE_REL = Path(".frob") / "cache.db"

_log = get_logger("frob.app.ticket_runner")


def _hint_invalid_transition(ticket_id: str, state, verb: str) -> str:  # noqa: ANN001
    """Remedy text for a close/reverify attempted on a not-yet-started ticket."""
    return (
        f"{verb} failed: InvalidTransition -- {ticket_id} is {state.value}, "
        f"not in-progress -- run `frob ticket start {ticket_id}` first"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
def _hint_missing_evidence(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for a close/reverify with no evidence or Done report bound."""
    return (
        f"{verb} failed: {err} -- {ticket_id} is missing evidence or a "
        f"Done report -- add evidence (`frob ticket evidence {ticket_id} "
        f"<node-id>...`, or for a docs-kind ticket `--evidence-cmd "
        f"'<command>'`) and write a '## Done report' heading under "
        f"{ticket_id}'s section in tickets.md"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
def _hint_acceptance_unbound(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for a close/reverify with an unbound acceptance criterion."""
    return (
        f"{verb} failed: {err} -- see the WARNING line above naming "
        f"which acceptance criterion/criteria still have no resolving "
        f"evidence id; bind one with `frob ticket evidence {ticket_id} "
        f"<node-id> --accepts <index>` (0-based, per "
        f"`frob ticket show {ticket_id}`'s acceptance list)"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
def _hint_missing_approved_review(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for a `--strict` close/reverify with no approve-verdict review."""
    return (
        f"{verb} failed: {err} -- {ticket_id} needs an approve-verdict "
        f"review naming the current commit (`frob ticket review "
        f"{ticket_id} --verdict approve --reviewer NAME --findings-file "
        f"PATH`) before `--strict` will succeed"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
def _hint_evidence_confirmatory_only(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for evidence that only confirms, never kills, its mutation."""
    return (
        f"{verb} failed: {err} -- see the WARNING TEST016 line(s) above "
        f"naming the exact file:line + mutation the bound evidence "
        f"never killed; strengthen those tests, then retry `frob "
        f"ticket {verb} {ticket_id}`, or if this is a genuine false "
        f"positive retry with `frob ticket {verb} {ticket_id} "
        f"--skip-mutation-evidence` (logs a loud, justification-"
        f"required override, does not suppress the finding)"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
# frob:ticket T-1556
def _hint_evidence_scope_unbound(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for a close/reverify with no evidence covering a
    touched/scope symbol."""
    return (
        f"{verb} failed: {err} -- {ticket_id} -- no bound evidence id "
        f"covers a touched/scope symbol; bind a test that actually "
        f"exercises the changed code (`frob ticket evidence "
        f"{ticket_id} <node-id>...`), or widen scope "
        f"(`frob ticket scope {ticket_id} --add <glob> --reason "
        f"'...'`) if the real touched files are not yet declared"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
# frob:ticket T-1556
def _hint_evidence_not_passing(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for evidence that has regressed since it was recorded."""
    return (
        f"{verb} failed: {err} -- {ticket_id}'s recorded evidence no "
        f"longer passes against the CURRENT tree (it passed once, at "
        f"record time, but has since regressed) -- fix the break, or "
        f"re-record fresh passing evidence (`frob ticket evidence "
        f"{ticket_id} <node-id>...`), then retry `frob ticket {verb} "
        f"{ticket_id}`"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
# frob:ticket T-1556
def _hint_own_obligations_unclean(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for a ticket's own diff leaving a doc/test/release
    obligation open."""
    return (
        f"{verb} failed: {err} -- {ticket_id}'s own diff leaves a "
        f"new-symbol frob:doc edge, frob:tests declaration, or REL001 "
        f"bump outstanding; run `frob check --delta --ticket "
        f"{ticket_id}` and resolve the finding(s) it names, then "
        f"retry `frob ticket {verb} {ticket_id}`"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
# frob:ticket T-1556
def _hint_gate_claim_unverified(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for a package-wide gate-outcome acceptance criterion
    left unproven."""
    return (
        f"{verb} failed: {err} -- see the WARNING line above naming "
        f"which package-wide gate-outcome acceptance criterion "
        f'("0 <RULE> findings under <glob>") is not established by '
        f"the bound evidence; re-run the named gate against the named "
        f"glob and bind evidence that PROVES the claim (not merely a "
        f"passing, unrelated node id), then retry `frob ticket {verb} "
        f"{ticket_id}`"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
# frob:ticket T-1556
def _hint_live_tracker_cited(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for a ticket still cited as a live tracker elsewhere."""
    return (
        f"{verb} failed: {err} -- see the WARNING line above naming "
        f"every site still citing {ticket_id} as its live tracker "
        f"(a registry deferred:/tracked_by: disposition or a waiver "
        f"ticket= attribute); file a successor ticket and re-point "
        f"those rows to it, or re-point them in this same change, "
        f"then retry `frob ticket {verb} {ticket_id}`"
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
# frob:ticket T-1556
def _hint_new_gate_rule_unaccepted(ticket_id: str, err, verb: str) -> str:  # noqa: ANN001
    """Remedy text for a diff that adds a gate rule with no bound acceptance fixture."""
    return (
        f"{verb} failed: {err} -- see the WARNING line above naming "
        f"the new gate rule id(s) this diff adds; record a bound "
        f"before-fails/after-passes fixture acceptance criterion "
        f"proving the rule fires through the real production "
        f"invocation (`frob ticket accept {ticket_id} --criterion "
        f"'...'`, then `frob ticket evidence {ticket_id} <node-id> "
        f"--accepts <index>`), then retry `frob ticket {verb} "
        f"{ticket_id}`"
    )


# frob:ticket T-1933
def _close_failure_hint(ticket_id: str, state, err, *, verb: str = "close") -> str:  # noqa: ANN001
    """The log message for a failed close: names a concrete remedy instead of
    just echoing the raw error (T-0215 -- both close-on-queued's
    InvalidTransition and MissingEvidence used to log with no next step).

    T-1005: `verb` (default `"close"`) lets `frob ticket reverify` share
    this exact remedy text under its own name (`"reverify"`) instead of
    forking a second copy that could drift -- the remedies themselves
    (start first, add evidence, bind acceptance, get an approved review,
    strengthen mutation-killing tests) are identical for both commands,
    only the failing verb differs.

    T-1933: dispatches to one small per-error `_hint_*` helper instead of a
    single 116-line if-chain (ARCH001 threshold), keeping each remedy's text
    independently readable and editable."""
    from frob.tickets import TicketError, TicketState

    if err == TicketError.InvalidTransition and state in (
        TicketState.QUEUED,
        TicketState.PLANNED,
    ):
        return _hint_invalid_transition(ticket_id, state, verb)

    dispatch = {
        TicketError.MissingEvidence: _hint_missing_evidence,
        TicketError.AcceptanceUnbound: _hint_acceptance_unbound,
        TicketError.MissingApprovedReview: _hint_missing_approved_review,
        TicketError.EvidenceConfirmatoryOnly: _hint_evidence_confirmatory_only,
        TicketError.EvidenceScopeUnbound: _hint_evidence_scope_unbound,
        TicketError.EvidenceNotPassing: _hint_evidence_not_passing,
        TicketError.OwnObligationsUnclean: _hint_own_obligations_unclean,
        TicketError.GateClaimUnverified: _hint_gate_claim_unverified,
        TicketError.LiveTrackerCited: _hint_live_tracker_cited,
        TicketError.NewGateRuleUnaccepted: _hint_new_gate_rule_unaccepted,
    }
    hint_fn = dispatch.get(err)
    if hint_fn is not None:
        return hint_fn(ticket_id, err, verb)
    return f"{verb} failed: {err}"


# frob:ticket T-0398
def _covers_scope_for_ticket(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """D-02 CLI wiring: whether `ticket`'s evidence covers a touched/scope
    symbol, via `frob.tickets.evidence_covers_scope` over the current graph.

    Returns `None` (skip the check entirely) when `ticket` carries NO
    non-cmd evidence at all -- a docs-kind ticket closed purely via
    `--evidence-cmd` has its own separate exit-code/digest verification
    channel (`add_cmd_evidence`) that already substitutes for "coverage";
    `evidence_covers_scope` would otherwise (correctly, by its own
    contract) return `False` for a ticket with zero non-cmd evidence to
    scan, which would wrongly block the docs cmd-evidence path this ticket
    was explicitly warned not to break. Also returns `None` when
    `ticket.scope` itself is empty -- an undeclared scope gives the
    binding check nothing to bind AGAINST, so "does evidence cover scope"
    is not a meaningful question to ask (this is a false-positive guard,
    not a loophole: a ticket that declares a real scope still gets the
    full check). Returns `False` (fail-closed, blocking the close) if the
    graph itself cannot be loaded/built -- "cannot verify" must never
    silently become "verified"."""
    from frob.tickets._models import is_cmd_evidence
    from frob.tickets._scope_coverage import evidence_covers_scope

    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    if not non_cmd or not ticket.scope:
        return None

    from frob.app import ticket_runner as _ticket_runner

    snapshot = _ticket_runner._graph_snapshot(root)
    if snapshot.is_err:
        _log.warning(
            "ticket close: graph unavailable (%s), cannot verify D-02 "
            "scope-binding -- refusing to close on unverifiable evidence",
            snapshot.danger_err,
        )
        return False
    return evidence_covers_scope(ticket, snapshot.danger_ok)


# frob:ticket T-0844
# frob:ticket T-1438
# frob:tests tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd.test_close_refuses_when_evidence_passes_at_parent  # noqa: E501
# frob:tests tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd.test_close_succeeds_when_evidence_fails_at_parent  # noqa: E501
# frob:tests tests/unit/test_ticket_close_bug002_t1438.py::TestCloseMutationEvidenceBaseRef.test_uses_merge_base_not_own_branch_tip  # noqa: E501
# frob:ticket T-2215
# frob:tests tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassCombinesWithBug002.test_close_refuses_on_bug003_alone  # noqa: E501
def _close_mutation_evidence_for_ticket(
    root: Path, ticket, base_ref: str = "main"
) -> bool | None:  # noqa: ANN001
    """T-0844: whether `ticket` carries an unwaived ERROR-severity TEST016
    confirmatory-only-evidence finding, mirroring `frob.tickets._land.
    _check_mutation_evidence`'s land-time computation
    (`frob.gates.mutation_evidence_violations`) so `frob ticket close` (the
    direct, non-land path) is not exempt from the same obligation. Also
    runs (T-1427) the bug/security-kind repro-at-parent obligation
    (`frob.gates.bug_repro_violations`, BUG002, T-1421) through the exact
    same channel -- same call shape, same error/warn accounting, same
    return contract, mirroring `_check_mutation_evidence`'s own T-1427
    treatment on the land path so a `bug`/`security` ticket cannot close
    directly any more than it can land without this check having run.
    T-2215 additionally runs `frob.gates.must_still_pass_violations`
    (BUG003, T-2193) through the same channel, via `frob.tickets._land.
    _must_still_pass_land_violations` -- not kind-restricted, opt-in via
    a `frob:must-still-pass NODE-ID` directive in `ticket.body`.

    T-1438 fix: the base ref this diffs/repros against is the git
    merge-base of HEAD against `base_ref` (`ticket`'s real starting point,
    default `"main"` -- pass `cfg.ticket_base_ref` from the caller), NOT
    `current_branch(root)`. The old `current_branch(root)` call resolved to
    the WORKTREE'S OWN branch in a dispatched agent's normal flow, which by
    close time already carries the ticket's own fix commit at its tip --
    `_bug_repro_outcome_at_ref`'s `git worktree add --detach <scratch>
    <that-branch>` then checked out the FIX itself, not the pre-fix
    parent, so the designated repro test trivially "passed at parent" for
    EVERY bug-kind ticket closed this way and BUG002 refused every close
    with a false `EvidenceConfirmatoryOnly` (forcing
    `--skip-mutation-evidence` on every single bug-kind close). Resolving
    the merge-base instead (mirroring `frob.gitio.working_diff`'s own
    `_merge_base(root, base)` computation) names the commit the ticket's
    work actually branched from, so a bug ticket's repro test is diffed/
    replayed against its true pre-fix parent, not against its own tip.
    Returns `None` (skip the check) when the merge-base cannot be resolved
    -- "cannot verify" must never silently become "verified", but this
    check is additive to the pre-existing evidence gates (T-0755's own
    posture), so it degrades to a no-op rather than fail-closed here."""
    from frob.gates import bug_repro_violations, mutation_evidence_violations
    from frob.gitio import _merge_base
    from frob.tickets._land import _must_still_pass_land_violations

    resolved = _merge_base(root, base_ref)
    if resolved.is_err:
        _log.warning(
            "ticket close: %s could not resolve merge-base against %s, "
            "skipping TEST016/BUG002/BUG003 mutation-evidence checks",
            ticket.id,
            base_ref,
        )
        return None
    parent_ref = resolved.danger_ok
    violations = (
        mutation_evidence_violations(root, ticket, parent_ref)
        + bug_repro_violations(root, ticket, parent_ref)
        + _must_still_pass_land_violations(root, ticket, parent_ref)
    )
    for v in violations:
        _log.warning("ticket close: %s %s %s", ticket.id, v.rule, v.message)
    errors = [v for v in violations if v.severity == "error"]
    return not errors if violations else None


# frob:ticket T-1410
def _matching_gate_claim_files(
    findings: frozenset[tuple[str, str]], rule: str, glob: str
) -> list[str]:
    """The sorted list of files in `findings` (a `(rule_id, file)` identity
    set) that match `rule` and `fnmatch` against `glob` -- split out of
    `_close_gate_claims_for_ticket`'s per-criterion loop (PERF004: a
    `sorted()` call textually inside a `for` loop body) so the sort lives
    in its own single-purpose function instead of inline in the loop."""
    from fnmatch import fnmatch

    return sorted(f for r, f in findings if r == rule and fnmatch(f, glob))


# frob:ticket T-1410
def _close_gate_claims_for_ticket(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """T-1410 CLI wiring: whether every acceptance criterion on `ticket`
    shaped as a package-wide gate-outcome claim ("0 <RULE> findings under
    <glob>", `frob.tickets._evidence._gate_claim_criteria`) actually holds
    against a live `frob check --only gates` run -- the T-1276 defect this
    closes: T-1276's own criterion [0] read "0 TEST005 findings under
    src/frob/app/**", was bound to unrelated passing evidence ids, and
    closed done (LAND-PROOF verified) against 116 live TEST005 findings
    under that exact glob, because nothing computed `gate_claims_verified`
    -- the T-1399 guard clause existed but had no live caller.

    Returns `None` (skip the check) when `ticket` carries no criterion in
    this shape at all -- `_gate_claim_criteria` returning `()` means the
    `gate_claims_verified` guard this feeds is a no-op regardless of what
    is injected, so a ticket with only ordinary criteria is unaffected.

    `frob check` has no CLI-level path-glob filter for gate violations (the
    positional `path` argument scopes the ruff/ty/pytest tool stages, not
    the `gates` stage's own violation set) -- so "scoped to the glob" here
    means running ONLY the `gates` stage (not the full ruff/ty/pytest/gates
    pipeline `_check_gate_findings_fn` runs for the Done-report recap) and
    then filtering the returned `(rule, file)` finding-identity set by
    `fnmatch` against the criterion's glob, once per criterion, rather than
    narrowing what actually runs. Measured ~113s wall for a full `--only
    gates` pass on this repo (docs comment on `frob.check._STAGE_GROUPS`) --
    slow enough to be worth naming, not slow enough to skip; this spawn
    carries its own 600s subprocess timeout (matching every other
    `guarded_subprocess_run` call in this module), independent of any
    foreground/session-level cap.

    Returns `False` (fail-closed, blocking the close) if the spawn is
    refused or its output is unparsable -- "cannot verify" must never
    silently become "verified", the same posture `_covers_scope_for_
    ticket`/`_reverify_evidence_for_close` already take for their own
    unloadable/uncollectable failure modes."""
    from frob.tickets._evidence import _criterion_gate_claim, _gate_claim_criteria

    claims = _gate_claim_criteria(ticket)
    if not claims:
        return None

    from frob.app import ticket_runner as _ticket_runner

    spawned = _ticket_runner.guarded_subprocess_run(
        [
            _ticket_runner._python_for_tree(root),
            "-m",
            "frob",
            "check",
            "--only",
            "gates",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if spawned.is_err:
        _log.warning(
            "ticket close: %s `frob check --only gates` refused to spawn "
            "(%s) -- cannot verify T-1399 gate-claim criteria, refusing to "
            "close on unverifiable evidence",
            ticket.id,
            spawned.danger_err,
        )
        return False
    proc = spawned.danger_ok
    findings = _ticket_runner._parse_error_findings_from_stdout(
        ticket.id, proc.stdout, proc.returncode
    )
    if findings is None:
        _log.warning(
            "ticket close: %s `frob check --only gates` output had no "
            "parsable gate-summary line -- cannot verify T-1399 gate-claim "
            "criteria, refusing to close on unverifiable evidence",
            ticket.id,
        )
        return False

    all_clean = True
    for c in claims:
        parsed = _criterion_gate_claim(c.text)
        if parsed is None:
            continue
        rule, glob = parsed
        matches = _matching_gate_claim_files(findings, rule, glob)
        if matches:
            _log.warning(
                "ticket close: %s criterion %r unmet -- %d live %s "
                "finding(s) under %s: %s",
                ticket.id,
                c.text,
                len(matches),
                rule,
                glob,
                matches,
            )
            all_clean = False
    return all_clean


# frob:ticket T-2462
# frob:tests tests/unit/test_close_rel001_bump.py::TestRel001FragmentExistsForTicket.test_true_when_fragment_present  # noqa: E501
# frob:tests tests/unit/test_close_rel001_bump.py::TestRel001FragmentExistsForTicket.test_false_when_absent  # noqa: E501
def _rel001_fragment_exists_for_ticket(root: Path, ticket_id: str) -> bool:
    """T-2462: whether `root/changelog.d/<ticket_id>.md` exists -- the
    "deferred, not missing" satisfying signal `_own_obligations_rel_bump_
    dirty` accepts alongside "pyproject.toml already covers the diff"
    now that `frob ticket land` no longer bumps `pyproject.toml` per
    land (only writes this fragment). Most useful on a REVERIFY of an
    already-landed ticket (`root` = main, post-land): before this,
    `pyproject.toml` staying frozen between explicit release cuts made
    every such reverify re-flag the SAME already-handled bump as
    outstanding, forever, since nothing ever advances the version to
    satisfy the OTHER check between cuts."""
    from frob.release._fragments import fragment_path

    return fragment_path(root, ticket_id).is_file()


# frob:ticket T-1387
# frob:ticket T-1705
def _own_obligations_rel_bump_dirty(root: Path, ticket) -> bool:  # noqa: ANN001
    """The REL001 half of `_close_own_obligations_for_ticket` (ARCH001
    split): `True` if a version bump is still outstanding against
    `ticket`'s current public API, reusing `_required_release_bump`
    (T-0338's existing read-only bump computation, the SAME one `frob
    ticket land` applies) directly -- no duplicated version-diffing
    logic. An unresolvable bump computation also counts as dirty
    (fail-closed: "cannot verify" must never silently become "clean").

    T-1705: skipped entirely under the `rapid` profile, at the same seam
    every other rapid relaxation uses (`_land_is_rapid`'s own precedent,
    `frob.tickets._land`) -- T-1575 already turns REL001 OFF under
    `rapid` for `frob check`'s own REL gate and the land path; this
    close-time preflight used to be the one place that relaxation did
    NOT reach, demanding a bump `frob ticket land`'s own rapid path
    never requires either. The skip is recorded via `record_rapid_debt`
    like every other rapid relaxation, so it stays auditable."""
    from frob.tickets._evidence import record_rapid_debt
    from frob.tickets._profile import effective_profile
    from frob.verify import settings_for_profile

    resolved_profile = effective_profile(root)
    # T-1696: rel001_preflight_enabled is the settings-record read;
    # unreadable resolves to "not rapid" (keeps the stricter behaviour),
    # matching the prior is-ProfileName.RAPID short-circuit on Err.
    if (
        resolved_profile.is_ok
        and not settings_for_profile(
            resolved_profile.danger_ok
        ).rel001_preflight_enabled
    ):
        record_rapid_debt(root, ticket.id, "close-rel001-preflight-skipped")
        _log.info(
            "ticket close: %s REL001 preflight skipped under rapid profile "
            "(T-1705, recorded as debt)",
            ticket.id,
        )
        return False

    from frob.app import ticket_runner as _ticket_runner

    rel_result = _ticket_runner._required_release_bump(root, ticket.id)
    if rel_result.is_err:
        _log.warning(
            "ticket close: %s could not compute the REL001 bump (%s) -- "
            "treating it as an outstanding own-obligation",
            ticket.id,
            rel_result.danger_err,
        )
        return True
    if rel_result.danger_ok is None:
        return False
    return _own_obligations_rel_bump_outstanding(root, ticket, rel_result.danger_ok)


# frob:ticket T-1684
# frob:ticket T-2462
def _own_obligations_rel_bump_outstanding(root: Path, ticket, needed: str) -> bool:  # noqa: ANN001
    """`_own_obligations_rel_bump_dirty`'s own ARCH001 split (T-2462): the
    "is `needed` actually still outstanding" half, run once a bump has
    already been confirmed non-`None`.

    T-1684: `_required_release_bump` answers "what version does the API
    at HEAD's manifest require", NOT "is that bump still outstanding" --
    it never looks at the version the working tree already DECLARES.
    `_apply_release_bump_for_land` compares the two before writing
    anything; this guard did not, so a developer who had already bumped
    pyproject.toml and re-stamped was told to bump again, forever, with
    no reachable state that satisfied the check. Compare here too.

    T-2462: `pyproject.toml` no longer bumps per land (`_apply_release_
    bump_for_land` defers that to an explicit release cut) -- ONLY the
    `changelog.d/T-####.md` fragment write still happens unconditionally,
    inside `frob ticket land` itself. Before T-2462 the `declared covers
    needed` check below was the ONLY satisfying state, and it could never
    become true again once land stopped bumping pyproject.toml -- every
    API-touching ticket would go permanently un-closeable between release
    cuts. A fragment already present for THIS ticket id (the T-1929-style
    repeat-close/reverify path -- close is re-run on `root` after a land
    already wrote it) is the equivalent satisfying signal under the
    deferred posture: the bump is tracked, not missing."""
    declared = _declared_pyproject_version(root)
    if declared is not None and _version_covers(declared, needed):
        _log.info(
            "ticket close: %s REL001 bump to %s is already applied on disk "
            "(pyproject declares %s) -- satisfied",
            ticket.id,
            needed,
            declared,
        )
        return False
    if _rel001_fragment_exists_for_ticket(root, ticket.id):
        _log.info(
            "ticket close: %s REL001 bump to %s is deferred via an "
            "existing T-2445 changelog.d/%s.md fragment (T-2462) -- "
            "satisfied",
            ticket.id,
            needed,
            ticket.id,
        )
        return False
    # T-1705: name the ACTUAL remedy. The bump is applied by
    # `_apply_release_bump_for_land` during `frob ticket land`, using
    # land's own internal commit channel -- `pyproject.toml`'s version
    # line is land-owned, and the T-0731 pre-commit hook refuses any
    # OTHER commit that touches it. Telling an agent "the bump is
    # outstanding" with no further context reads as "go bump it", which
    # the tooling then forbids -- two agents independently hit exactly
    # this dead end before one discovered, undocumented, that `frob
    # ticket land` performs its own close internally and IS the
    # supported route.
    _log.warning(
        "ticket close: %s REL001 version bump outstanding (needs %s, "
        "pyproject declares %s) -- do NOT bump pyproject.toml by hand, "
        "that commit is land-owned and the T-0731 hook will refuse it; "
        "the supported remedy is `frob ticket land %s`, which applies "
        "the bump and closes this ticket itself -- a hand `frob ticket "
        "close` is not the route for a ticket with a public-API change",
        ticket.id,
        needed,
        declared or "unreadable",
        ticket.id,
    )
    return True


# frob:tests tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion.test_absent_pyproject_is_none  # noqa: E501
# frob:tests tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion.test_unparsable_pyproject_is_none  # noqa: E501
# frob:tests tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion.test_reads_the_declared_version  # noqa: E501
# frob:ticket T-1684
def _declared_pyproject_version(root: Path) -> str | None:
    """`root/pyproject.toml`'s declared `version`, or `None` if the file
    is absent or unparsable -- `None` means "cannot verify", and every
    caller must treat that as NOT satisfying a bump obligation."""
    import tomllib

    path = root / "pyproject.toml"
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("ticket close: %s unparsable for the REL001 check: %s", path, exc)
        return None
    version = doc.get("project", {}).get("version")
    return str(version) if version else None


# frob:tests tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_equal_covers
# frob:tests tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_higher_covers
# frob:tests \
# tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_lower_does_not_cover
# frob:tests \
# tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_non_numeric_never_covers
# frob:ticket T-1684
def _version_covers(declared: str, needed: str) -> bool:
    """Whether `declared` is at least `needed`, compared as numeric
    dotted components (`0.356.0` covers `0.356.0` and `0.355.0`).
    Anything non-numeric compares `False` -- an unrecognizable version
    must never be read as satisfying a release obligation."""
    try:
        left = tuple(int(part) for part in declared.split("."))
        right = tuple(int(part) for part in needed.split("."))
    except ValueError:
        return False
    return left >= right


# frob:ticket T-1648
# frob:tests tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard.test_refuses_when_disclosure_language_has_no_filed_ticket  # noqa: E501
# frob:tests tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard.test_allows_when_filed_ticket_is_open  # noqa: E501
# frob:tests tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard.test_refuses_when_filed_ticket_is_already_closed  # noqa: E501
# frob:tests tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard.test_clean_narrative_is_unaffected  # noqa: E501
def _undisclosed_remainder_reason(root: Path, ticket) -> str | None:  # noqa: ANN001
    """T-1648: `None` if `ticket`'s Done report carries no disclosure-
    shaped language (`disclosure_shaped_language`), OR if it does but a
    `Filed:` line (`filed_followup_tickets`) names at least one real,
    still-OPEN ticket id -- otherwise a human-readable reason string
    naming the matched phrase, refusing the close.

    This is the fix for the T-1420/T-1204 incident: a ticket closed while
    its own Done report disclosed substantial unfinished work (52 files,
    5 PERF rules) with no follow-up ticket anywhere, and the disclosure
    -- being free text -- was invisible to the queue the moment the
    ticket left it. WIRE002 already established the precedent this
    reuses: an escape hatch must bind to a real, open follow-up ticket,
    not free-text prose nobody has to act on.

    Deliberately does NOT try to parse "I did X but not Y" precisely --
    `disclosure_shaped_language` is a generous phrase match, and any
    `Filed:` line naming an open ticket satisfies it, even if that
    ticket does not itself describe the disclosed remainder. The goal
    (per the ticket's own note) is to make the author pause and record
    SOMETHING checkable, not to punish honest disclosure with ceremony
    heavy enough that agents stop disclosing."""
    from frob.gates import _OPEN_STATES
    from frob.tickets import load_queue
    from frob.tickets._reporting import (
        disclosure_shaped_language,
        filed_followup_tickets,
    )

    phrase = disclosure_shaped_language(ticket.body)
    if phrase is None:
        return None

    filed_ids = filed_followup_tickets(ticket.body)
    if not filed_ids:
        return (
            f"Done report contains disclosure-shaped language ({phrase!r}) "
            "but no 'Filed:' line names a follow-up ticket"
        )

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.warning(
            "ticket close: %s could not load queue to verify Filed: "
            "ticket(s) %s (%s) -- refusing to close on an unverifiable "
            "remainder",
            ticket.id,
            filed_ids,
            queue_result.danger_err,
        )
        return (
            f"Done report discloses unfinished work ({phrase!r}) and its "
            f"Filed: ticket(s) {filed_ids} could not be verified"
        )
    queue = queue_result.danger_ok
    for filed_id in filed_ids:
        followup = queue.tickets.get(filed_id)
        if followup is not None and followup.state in _OPEN_STATES:
            return None

    return (
        f"Done report discloses unfinished work ({phrase!r}) but none of "
        f"its Filed: ticket(s) {filed_ids} resolve to a real, open ticket"
    )


# frob:ticket T-3087
# frob:tests tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose.test_open_blocker_names_the_open_ticket_not_the_terminal_one  # noqa: E501
# frob:tests tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose.test_no_blocked_by_returns_empty  # noqa: E501
# frob:tests tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose.test_unresolvable_blocker_id_is_ignored  # noqa: E501
def _open_blockers_at_close(ticket, queue) -> tuple[str, ...]:  # noqa: ANN001
    """T-3087: ids from `ticket.blocked_by` whose CURRENT state is still
    open (not done/dropped) -- the close-time twin of `_transition_guard`'s
    start-time `_start_blockers` check (`TicketError.BlockerOpen`), which
    only ever fired for `IN_PROGRESS`, never for `DONE`.

    MEASURED incident (T-3087): T-3064 reached `done` while still carrying
    `blocked_by=['T-3066']` with T-3066 non-terminal (queued) -- its own
    Done report opened "T-3064 is BLOCKED, not implemented." and its land
    commit touched zero source files. Nothing on the close path looked at
    `blocked_by` at all.

    The check is on the blocker's STATE, not its mere presence: a blocker
    that has itself reached done/dropped never appears here, so a ticket
    whose blockers all resolved closes exactly as before (T-3087's own
    must-stay-quiet requirement -- this must not become 'refuse every
    blocked_by'). A `blocked_by` id that does not resolve to a real ticket
    in `queue` is silently skipped here (not this guard's job to validate
    referential integrity of `blocked_by` -- see TICK-shaped concerns
    elsewhere); it is deliberately not treated as 'open'."""
    from frob.tickets import TicketState

    open_ids: list[str] = []
    for blocker_id in ticket.blocked_by:
        blocker = queue.tickets.get(blocker_id)
        if blocker is None:
            continue
        if blocker.state not in (TicketState.DONE, TicketState.DROPPED):
            open_ids.append(blocker_id)
    return tuple(open_ids)


# frob:ticket T-1387
def _own_obligations_diff_findings(
    root: Path,
    ticket,
    touched: set[str],  # noqa: ANN001
) -> list[str] | None:
    """The COV001/SELFAUDIT001 half of `_close_own_obligations_for_ticket`
    (ARCH001 split): the sorted `"<rule>:<file>"` list of live findings
    under a file in `touched` -- `None` (fail-closed, distinct from an
    empty list) if the `--only gates` spawn itself is refused or
    unparsable, since COV001/SELFAUDIT001 have no diff-scoped `--ticket`
    filter of their own (T-1351: `--ticket` only scopes SCOPE/PREWORK/
    COV002/TODO001/FMT/AFFECT, every other gate family's count is
    repo-wide) -- one `frob check --only gates` run supplies the
    repo-wide `(rule, file)` identity set, filtered here to `touched`.
    This is a deliberate scoping choice, not a full new-symbol-only diff
    parse: a touched file carrying a PRE-EXISTING finding this ticket did
    not itself introduce also counts against it -- stricter than "only
    symbols this ticket newly added", never looser, since the remedy (add
    the missing edge/declaration) is the same either way for a file the
    ticket is already touching."""
    from frob.app import ticket_runner as _ticket_runner

    spawned = _ticket_runner.guarded_subprocess_run(
        [
            _ticket_runner._python_for_tree(root),
            "-m",
            "frob",
            "check",
            "--only",
            "gates",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if spawned.is_err:
        _log.warning(
            "ticket close: %s `frob check --only gates` refused to spawn "
            "(%s) -- cannot verify T-1384 own-obligations, refusing to "
            "close on unverifiable evidence",
            ticket.id,
            spawned.danger_err,
        )
        return None
    proc = spawned.danger_ok
    findings = _ticket_runner._parse_error_findings_from_stdout(
        ticket.id, proc.stdout, proc.returncode
    )
    if findings is None:
        _log.warning(
            "ticket close: %s `frob check --only gates` output had no "
            "parsable gate-summary line -- cannot verify T-1384 "
            "own-obligations, refusing to close on unverifiable evidence",
            ticket.id,
        )
        return None

    obligation_rules = {"COV001", "SELFAUDIT001"}
    return sorted(
        f"{r}:{f}" for r, f in findings if r in obligation_rules and f in touched
    )


# frob:ticket T-1387
def _close_own_obligations_for_ticket(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """T-1387 CLI wiring for T-1384's `own_obligations_clean` guard:
    whether `ticket`'s OWN diff (every file `working_diff(root, "main")`
    reports a hunk in) leaves outstanding (a) a new-symbol `frob:doc` edge
    (COV001), (b) a testsuite strata declaration (SELFAUDIT001), or (c) an
    unapplied REL001 version bump (`_own_obligations_rel_bump_dirty`/
    `_own_obligations_diff_findings`, split out for ARCH001) -- the
    T-1377/T-1379/T-1381 residue class: closed clean, then surprised the
    very next unscoped `frob check` with exactly this obligation, because
    nothing computed it at close time.

    Returns `None` (skip) if `working_diff` itself is unavailable (not a
    git checkout, no merge-base against `main`) or reports no touched
    files at all -- "cannot verify" degrades to a no-op here rather than
    fail-closed, matching `_close_mutation_evidence_for_ticket`'s posture
    for the identical failure mode (additive to the pre-existing evidence
    gates, not the sole gate). Returns `False` (fail-closed) if the
    `--only gates` spawn itself is refused/unparsable, or if any of the
    three obligations is outstanding."""
    from frob.gitio import working_diff

    diff = working_diff(root, "main")
    if diff.is_err:
        _log.warning(
            "ticket close: %s working_diff unavailable (%s), skipping "
            "T-1384 own-obligations check",
            ticket.id,
            diff.danger_err,
        )
        return None
    touched = {h.file for h in diff.danger_ok.hunks}
    if not touched:
        return None

    rel_dirty = _own_obligations_rel_bump_dirty(root, ticket)
    dirty = _own_obligations_diff_findings(root, ticket, touched)
    if dirty is None:
        return False
    if dirty:
        _log.warning(
            "ticket close: %s own-diff obligation(s) outstanding: %s",
            ticket.id,
            dirty,
        )
    return not (rel_dirty or dirty)


# frob:ticket T-0417
# frob:waive DUP001 reason="T-1089 split moved this function to a new file path with \
# an unchanged body, which the diff-scoped DUP001 gate reads as newly-introduced code \
# and compares against the rest of the tree; the 95% r2 match against \
# frob.tickets._land._reverify_test_count_claim is same-shape (a bool|None-returning \
# re-verify-then-log-and-report helper) but different-domain -- this one re-runs \
# close's own recorded evidence ids against the current tree, that one compares a \
# captured test/evidence count claim for regression at land time; no shared logic to \
# extract, pre-existing structural similarity the split did not create"
def _reverify_evidence_for_close(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """N-02 CLI wiring: whether `ticket`'s own non-cmd evidence ids STILL
    pass when actually re-run against the CURRENT tree at `frob ticket
    close` time -- closing a ticket must never trust the pass observation
    made once, back when `frob ticket evidence` first recorded it (round-2
    audit finding N-02, docs/audits/tickets-testing-round2.md): the tree
    can change arbitrarily between `evidence` and `close`, and until this
    fix `close` (unlike `land`, which already re-verifies post-merge via
    `_reverify_evidence_post_merge`, D-05) never re-ran anything -- a test
    recorded green then later broken by an edit to the source or the test
    itself still closed the ticket.

    Returns `None` (skip the check) when the ticket carries no non-cmd
    evidence at all -- a docs-kind ticket closed purely via
    `--evidence-cmd` has its own separate exit-code/digest channel
    (`add_cmd_evidence`) and nothing here to re-run. Returns `False`
    (fail-closed, blocking the close) if collection itself fails --
    "cannot verify" must never silently become "verified", the same
    posture `_covers_scope_for_ticket` already takes for an unloadable
    graph.

    T-2569: the real incident this closes -- `frob check`'s `SpawnFailed`
    (runner process could not be started or timed out, under machine
    contention: load 48.5 on 12 cores) was reported to the operator as
    "evidence no longer passes when re-run" for all 7 of a ticket's
    evidence nodes. ZERO nodes actually executed; the WARNING and refusal
    both claimed a genuine test failure that never happened -- worse than
    a silent zero, since the natural "fix" for a reported failure is to
    weaken the test until the imaginary failure goes away.
    `_verify_ids_passing` already returns a per-id `VerifyOutcome`
    (`PASSED`/`FAILED`/`UNMEASURED`) rather than a bare passing set; this
    function now branches three ways instead of collapsing that
    distinction back down to "in the passing set or not": genuine
    failures still refuse with the original wording (so a real defect is
    reported as a real defect, never silently waved through), while any
    UNMEASURED id refuses with a NEW, distinctly-worded message so an
    operator (or an agent) sees "could not measure" and investigates
    infra/contention, not "the test broke" and starts editing the test.
    Refusing to close on an UNMEASURED batch is still correct -- closing
    on an unmeasurable result would be the opposite error -- only the
    WORDING and the false failure attribution are being fixed here."""
    from frob.app.ticket_runner._verify import VerifyStatus
    from frob.tickets._models import is_cmd_evidence

    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    if not non_cmd:
        return None

    from frob.app import ticket_runner as _ticket_runner

    collected = _ticket_runner._collect_python_and_rust_ids(root)
    if collected.is_err:
        _log.warning(
            "ticket close: %s evidence collection failed (%s), cannot "
            "re-verify N-02 pass state -- refusing to close on "
            "unverifiable evidence",
            ticket.id,
            collected.danger_err,
        )
        return False
    python_ids, rust_ids, runners = collected.danger_ok
    from frob.app import ticket_runner as _ticket_runner

    outcomes = _ticket_runner._verify_ids_passing(
        root, non_cmd, python_ids, rust_ids, runners
    )
    failed = [
        e
        for e in non_cmd
        if e in outcomes and outcomes[e].status is VerifyStatus.FAILED
    ]
    unmeasured = [
        e
        for e in non_cmd
        if e not in outcomes or outcomes[e].status is VerifyStatus.UNMEASURED
    ]
    # An id absent from `outcomes` entirely (resolved against neither
    # collected set) is folded into `unmeasured` by the `e not in outcomes`
    # clause above -- never silently dropped from both lists.

    if failed:
        _log.warning(
            "ticket close: %s evidence no longer passes when re-run: %s",
            ticket.id,
            failed,
        )
        return False
    if unmeasured:
        _log.warning(
            "ticket close: %s evidence could not be measured on re-run "
            "(runner spawn failure/timeout or other infra error, NOT a "
            "test failure -- T-2569): %s -- reasons: %s",
            ticket.id,
            unmeasured,
            {e: outcomes[e].reason for e in unmeasured if e in outcomes},
        )
        return False
    return True


# frob:ticket T-0571
# frob:waive ARCH103 reason="T-0977: best-effort git-rev-parse wrapper -- runs the \
# subprocess, formats the debug log line on failure, returns None; the \
# format-on-failure step is the SAME best-effort-git concern the docstring names, not \
# a distinct one worth splitting out"
def _current_commit(root: Path) -> str | None:
    """Best-effort `git rev-parse HEAD` under `root` (`None` on any git
    failure) -- shared by `_review`'s default `--commit` and `_close`'s
    strict-mode gate so both name the SAME notion of "current commit"."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


# frob:ticket T-0571
# frob:tests tests/test_tickets_review.py::TestReviewCli.test_cli_writes_review_record
# frob:tests tests/test_tickets_review.py::TestReviewCli.test_cli_requires_all_flags
def _review(root: Path, cfg: AppConfig) -> None:
    """`frob ticket review <id> --verdict approve|reject --reviewer NAME
    --findings-file PATH [--commit SHA]`: resolve the findings text and
    commit, then call `frob.tickets.record_review` -- the structured,
    first-class adversarial-review evidence channel (T-0571). `--commit`
    defaults to the current `HEAD` under `root` when omitted."""
    from frob.tickets import ReviewVerdict, record_review

    if (
        cfg.ticket_id is None
        or cfg.ticket_review_verdict is None
        or cfg.ticket_reviewer is None
        or cfg.ticket_findings_file is None
    ):
        _log.error(
            "frob ticket review requires <id> --verdict approve|reject "
            "--reviewer NAME --findings-file PATH"
        )
        sys.exit(1)

    try:
        findings = cfg.ticket_findings_file.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error(
            "review: could not read --findings-file %s: %s",
            cfg.ticket_findings_file,
            exc,
        )
        sys.exit(1)

    from frob.app import ticket_runner as _ticket_runner

    commit = cfg.ticket_review_commit or _ticket_runner._current_commit(root)
    if commit is None:
        _log.error(
            "review: could not resolve --commit and no --commit was given "
            "(is %s a git checkout?)",
            root,
        )
        sys.exit(1)

    result = record_review(
        root,
        cfg.ticket_id,
        verdict=ReviewVerdict(cfg.ticket_review_verdict),
        reviewer=cfg.ticket_reviewer,
        findings=findings,
        commit=commit,
    )
    if result.is_err:
        _log.error("review failed: %s", result.danger_err)
        sys.exit(1)
    _log.info(
        "%s: recorded review verdict=%s reviewer=%s commit=%s",
        cfg.ticket_id,
        cfg.ticket_review_verdict,
        cfg.ticket_reviewer,
        commit,
    )


# frob:ticket T-0571
def _covers_review_for_ticket(root: Path, cfg: AppConfig, ticket) -> bool | None:  # noqa: ANN001
    """T-0571's CLI-side strict-mode predicate: `None` (skip the check)
    unless BOTH `--strict` was passed on this `close` invocation AND
    `[tickets] require_review_for_close` is true in `frob.toml` -- either
    condition missing means "not opted in", never a silent enforcement.
    When both are true, resolves the current commit and asks
    `frob.tickets.has_approved_review_for_commit`."""
    from frob.tickets import (
        has_approved_review_for_commit,
        load_require_review_for_close,
    )

    if not cfg.ticket_close_strict or not load_require_review_for_close(root):
        return None
    from frob.app import ticket_runner as _ticket_runner

    commit = _ticket_runner._current_commit(root)
    if commit is None:
        _log.warning(
            "ticket close --strict: could not resolve current commit under "
            "%s -- refusing to close on unverifiable review",
            root,
        )
        return False
    return has_approved_review_for_commit(ticket, commit)


# frob:ticket T-0976
def _apply_close_time_evidence(root: Path, cfg: AppConfig) -> None:
    """Apply `frob ticket close`'s optional `--evidence`/`--evidence-cmd`/
    `--skip-mutation-evidence` flags before the close transition itself
    runs: validates and appends any evidence given (exiting on failure so
    a bad flag can never close on unvalidated evidence) and logs the
    justification-required warning for the mutation-evidence escape
    hatch. Caller (`_close`) has already verified `cfg.ticket_id is not
    None` before calling this."""
    assert cfg.ticket_id is not None
    if cfg.ticket_evidence_ids:
        added = _apply_evidence(
            root, cfg.ticket_id, cfg.ticket_evidence_ids, cfg.ticket_accepts
        )
        if added.is_err:
            sys.exit(1)

    if cfg.ticket_evidence_cmd:
        cmd_added = _apply_cmd_evidence(
            root, cfg.ticket_id, cfg.ticket_evidence_cmd, cfg.ticket_accepts
        )
        if cmd_added.is_err:
            sys.exit(1)

    if cfg.ticket_close_skip_mutation_evidence:
        _log.warning(
            "ticket close: %s --skip-mutation-evidence set -- a TEST016 "
            "confirmatory-only-evidence finding will be logged but will NOT "
            "refuse this close (justification required: use only for a "
            "genuine false positive)",
            cfg.ticket_id,
        )


# frob:ticket T-0976
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade.test_true_mutation_evidence_with_skip_flag_is_never_downgraded  # noqa: E501
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade.test_false_mutation_evidence_with_skip_flag_is_downgraded_to_none  # noqa: E501
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade.test_false_mutation_evidence_without_skip_flag_stays_false  # noqa: E501
def _close_guards_for_ticket(root: Path, cfg: AppConfig, fresh_ticket) -> tuple:  # noqa: ANN001
    """Compute the six independent close-time guard values `transition`
    needs for `frob ticket close`'s strict default (T-0398 covers_scope,
    T-0571 config-gated review, T-0844 mutation evidence, T-0417 N-02
    post-merge re-verify, T-1410 gate-claim verification, T-1387
    own-obligations) -- each guard is its own existing helper; this just
    threads `cfg.ticket_close_skip_mutation_evidence` through to downgrade
    a `False` mutation-evidence verdict to `None` (skip) when the escape
    hatch was passed."""
    from frob.app import ticket_runner as _ticket_runner

    covers_scope = _ticket_runner._covers_scope_for_ticket(root, fresh_ticket)
    from frob.app import ticket_runner as _ticket_runner

    reviewed = _ticket_runner._covers_review_for_ticket(root, cfg, fresh_ticket)
    from frob.app import ticket_runner as _ticket_runner

    mutation_evidence = _ticket_runner._close_mutation_evidence_for_ticket(
        root, fresh_ticket, cfg.ticket_base_ref
    )
    if mutation_evidence is False and cfg.ticket_close_skip_mutation_evidence:
        mutation_evidence = None
    from frob.app import ticket_runner as _ticket_runner

    evidence_reverified = _ticket_runner._reverify_evidence_for_close(
        root, fresh_ticket
    )
    from frob.app import ticket_runner as _ticket_runner

    gate_claims_verified = _ticket_runner._close_gate_claims_for_ticket(
        root, fresh_ticket
    )
    from frob.app import ticket_runner as _ticket_runner

    own_obligations_clean = _ticket_runner._close_own_obligations_for_ticket(
        root, fresh_ticket
    )
    return (
        covers_scope,
        reviewed,
        mutation_evidence,
        evidence_reverified,
        gate_claims_verified,
        own_obligations_clean,
    )


# frob:ticket T-0106
# frob:ticket T-0215
# frob:ticket T-0398
# frob:ticket T-0571
# frob:ticket T-2393
def _resolve_no_behavior_change_reason(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket close --no-behavior-change`'s reason:
    `--no-behavior-change-reason-file` wins if given (read verbatim,
    T-0737 pattern), else the inline `--no-behavior-change-reason`
    string. Exits 1 if both are given; returns `None` if neither is given
    (the caller reports the "reason required" error), same shape as
    `_resolve_triage_reason`/`_resolve_body_reason`."""
    reason_file = cfg.ticket_close_no_behavior_change_reason_file
    reason = cfg.ticket_close_no_behavior_change_reason
    if reason_file is not None and reason:
        _log.error(
            "frob ticket close --no-behavior-change: --no-behavior-change-reason "
            "and --no-behavior-change-reason-file are mutually exclusive"
        )
        sys.exit(1)
    if reason_file is not None:
        try:
            return reason_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "frob ticket close: could not read --no-behavior-change-reason-file "
                "%s: %s",
                reason_file,
                exc,
            )
            sys.exit(1)
    return reason


# frob:ticket T-2393
# frob:doc docs/modules/tickets-data-storage.md#frob-ticket-body-t-2392
# frob:tests \
# tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli.test_flag_writes_directive_before_close  # noqa: E501
# frob:tests \
# tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli.test_reason_missing_exits_nonzero  # noqa: E501
# frob:waive COV007 reason="docs/modules/tickets-data-storage.md's `frob ticket body` \
# (T-2392) section documents several symbols under one section, not just a public \
# entry point -- the many-symbols- one-section convention this repo already accepted \
# for vet.md (T-2810 declined to touch it), not a T-2810-shaped duplicate"
def _apply_no_behavior_change_directive(root: Path, cfg: AppConfig) -> None:
    """`frob ticket close --no-behavior-change --no-behavior-change-reason
    TEXT`: the first-class front door (T-2393) for BUG002's pre-existing
    `frob:no-behavior-change reason="..."` body directive. Writes the
    directive into the ticket's body via `frob.tickets.set_body` (T-2392)
    -- the validated mutation path -- BEFORE `_close` computes
    `mutation_evidence`, so the SAME `_no_behavior_change_reason` parser
    BUG002 already reads (`frob.gates._mutation_evidence`) sees it without
    a hand-edit of `tickets/T-####/ticket.md` ever being necessary. A
    no-op (returns immediately) unless `--no-behavior-change` was given.
    Exits 1 if the reason is missing -- this must stay mandatory, the same
    prove-or-justify discipline `set_body`'s own reason requirement and
    T-2353's triage-change reasons already enforce, so this front door can
    never become a silent, unaccountable escape hatch from BUG002."""
    if not cfg.ticket_close_no_behavior_change:
        return
    if cfg.ticket_id is None:
        _log.error("frob ticket close requires <id>")
        sys.exit(1)
    from frob.tickets import set_body

    reason = _resolve_no_behavior_change_reason(cfg)
    if not reason or not reason.strip():
        _log.error(
            "frob ticket close --no-behavior-change requires "
            "--no-behavior-change-reason TEXT or --no-behavior-change-reason-file PATH"
        )
        sys.exit(1)

    # The directive's own regex parser (`frob.gates._mutation_evidence.
    # _NO_BEHAVIOR_CHANGE_RE`) expects a double-quoted reason with no
    # embedded double quote -- sanitize rather than let a stray `"` in the
    # reason silently truncate the parsed value.
    safe_reason = reason.strip().replace('"', "'")
    directive = f'frob:no-behavior-change reason="{safe_reason}"'
    result = set_body(
        root,
        cfg.ticket_id,
        directive,
        mode="append",
        reason=f"BUG002 front door (T-2393): {reason.strip()}",
    )
    if result.is_err:
        _log.error("--no-behavior-change directive write failed: %s", result.danger_err)
        sys.exit(1)
    _log.info(
        "%s: recorded frob:no-behavior-change directive before close (T-2393)",
        cfg.ticket_id,
    )


def _close(root: Path, cfg: AppConfig) -> None:
    """Transition a ticket to done; if `--evidence` ids or `--evidence-cmd`
    were given, validate and append them first (`_apply_evidence` /
    `_apply_cmd_evidence`) and refuse to transition at all if either is
    unresolvable/fails, so a bad flag can never close a ticket on
    unvalidated evidence. A failed transition is reported through
    `_close_failure_hint` so the operator gets a concrete next command, not
    just the bare state-machine error (T-0215).

    T-0398: this is the CLI's STRICT default -- `covers_scope` is always
    computed (`_covers_scope_for_ticket`) and always passed to
    `transition`, so evidence that covers none of the ticket's touched/
    scope symbols rejects the close (`EvidenceScopeUnbound`) through the
    real `frob ticket close` command.

    T-0571: `reviewed` is only ever non-`None` when BOTH `--strict` was
    passed AND `[tickets] require_review_for_close` is true in
    `frob.toml` (`_covers_review_for_ticket`) -- config-gated, off by
    default, so this never breaks a repo/workflow that has not opted in.

    T-0844: `mutation_evidence` is ALWAYS computed
    (`_close_mutation_evidence_for_ticket`) and passed to `transition`, so
    a security/bug-kind ticket with an ERROR-severity TEST016
    confirmatory-only-evidence finding refuses the direct close the same
    way it already refuses `frob ticket land` -- unless `--skip-mutation-
    evidence` was passed, the close-path twin of land's own escape hatch.

    T-0417 N-02: `evidence_reverified` is ALWAYS computed
    (`_reverify_evidence_for_close`) and passed to `transition`, so a
    ticket whose recorded evidence passed once but no longer passes
    against the CURRENT tree refuses to close -- the direct-close twin of
    `land`'s own post-merge re-verify (D-05), closing the TOCTOU gap where
    `close` (unlike `land`) never re-ran anything.

    T-1410: `gate_claims_verified` is ALWAYS computed
    (`_close_gate_claims_for_ticket`) and passed to `transition`, so a
    ticket carrying an acceptance criterion shaped "0 <RULE> findings
    under <glob>" refuses to close while a live `frob check --only gates`
    run still reports findings for that rule under that glob -- the T-1276
    defect (closed done, LAND-PROOF verified, against 116 live TEST005
    findings under its own criterion's glob) is now refused at the real
    close path, not just in the T-1399 guard's own unit tests."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket close requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="close")
    # frob:ticket T-2393
    _apply_no_behavior_change_directive(root, cfg)
    _apply_close_time_evidence(root, cfg)

    # Re-load: evidence may have just changed above, and covers_scope must
    # be computed against the ticket's CURRENT evidence, not the state
    # loaded before this call's own --evidence/--evidence-cmd applied.
    fresh_ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="close")

    # frob:ticket T-1648
    remainder_reason = _undisclosed_remainder_reason(root, fresh_ticket)
    if remainder_reason is not None:
        _log.error(
            "close failed: %s -- %s -- file a follow-up (`frob ticket new "
            "...`) and add a 'Filed: T-####' line to the Done report "
            "naming it, or run `frob ticket done-report %s --why-file "
            "PATH` again with the disclosure removed if it does not "
            "actually describe cut work",
            cfg.ticket_id,
            remainder_reason,
            cfg.ticket_id,
        )
        sys.exit(1)

    # frob:ticket T-3087
    if fresh_ticket.blocked_by:
        from frob.tickets import load_queue

        blockers_queue = load_queue(root)
        if blockers_queue.is_err:
            _log.warning(
                "close: %s could not load queue to verify blocked_by %s "
                "(%s) -- refusing to close on an unverifiable blocker set",
                cfg.ticket_id,
                fresh_ticket.blocked_by,
                blockers_queue.danger_err,
            )
            sys.exit(1)
        open_blockers = _open_blockers_at_close(fresh_ticket, blockers_queue.danger_ok)
        if open_blockers:
            _log.error(
                "close failed: BlockerOpenAtClose -- %s cannot close, "
                "blocked_by names open (non-terminal) ticket(s) %s -- "
                "close/drop the blocker(s) first, or `frob ticket unblock "
                "%s --by <id>` if the dependency no longer holds",
                cfg.ticket_id,
                list(open_blockers),
                cfg.ticket_id,
            )
            sys.exit(1)

    (
        covers_scope,
        reviewed,
        mutation_evidence,
        evidence_reverified,
        gate_claims_verified,
        own_obligations_clean,
    ) = _close_guards_for_ticket(root, cfg, fresh_ticket)

    result = transition(
        root,
        cfg.ticket_id,
        TicketState.DONE,
        covers_scope=covers_scope,
        reviewed=reviewed,
        mutation_evidence=mutation_evidence,
        evidence_reverified=evidence_reverified,
        gate_claims_verified=gate_claims_verified,
        own_obligations_clean=own_obligations_clean,
    )
    if result.is_err:
        _log.error(_close_failure_hint(cfg.ticket_id, ticket.state, result.danger_err))
        sys.exit(1)
    _log.info("%s closed (done)", cfg.ticket_id)
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="done")

    # frob:ticket T-1178
    from frob.tickets._leases import commit_ticket_ledger_change

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): close {cfg.ticket_id}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)

    # frob:ticket T-2738
    _promote_pending_drafts_after_close(root, cfg.ticket_id)


# frob:ticket T-2738
def _pending_draft_ids_after_close(root: Path, closed_ticket_id: str) -> list[str]:
    """T-2738: the queue-read half of `_promote_pending_drafts_after_close`,
    split out under ARCH103 -- resolve the closed ticket's queue and
    return the sorted ids of every still-open `T-draft-*` follow-up it
    may have filed (`load_queue` returning the merged active+archive
    view means an already-terminal DONE/DROPPED draft, e.g. one
    deliberately dropped in a past land, is NOT "pending" and must be
    excluded here). A queue load failure is logged as a warning (with
    the hand-recovery command) and degrades to an empty list -- this
    function never raises, matching the caller's best-effort posture."""
    from frob.tickets import TicketState, load_queue
    from frob.tickets._provisional import is_draft_id

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.warning(
            "ticket close: %s: could not load the queue to check for "
            "pending draft follow-ups (%s) -- if this ticket filed any "
            "drafts, they may be stranded; promote by hand with `frob "
            "ticket promote <draft-id>`",
            closed_ticket_id,
            queue_result.danger_err,
        )
        return []
    all_tickets = queue_result.danger_ok.tickets
    return sorted(
        tid
        for tid, t in all_tickets.items()
        if is_draft_id(tid) and t.state not in (TicketState.DONE, TicketState.DROPPED)
    )


# frob:ticket T-2738
def _promote_one_pending_draft(
    root: Path, closed_ticket_id: str, draft_id: str
) -> bool:
    """T-2738: promote a single pending draft (the per-draft half of
    `_promote_pending_drafts_after_close`, split out under ARCH103) via
    `finalize_draft`, logging the outcome by name either way. Returns
    True on success, False if `draft_id` is now stranded and must be
    reported by the caller."""
    from frob.tickets import finalize_draft

    result = finalize_draft(root, draft_id)
    if result.is_err:
        _log.error(
            "ticket close: %s: failed to promote pending draft %s "
            "(%s) -- it is stranded; promote it by hand: `frob "
            "ticket promote %s`",
            closed_ticket_id,
            draft_id,
            result.danger_err,
            draft_id,
        )
        return False
    final_id = result.danger_ok
    if final_id != draft_id:
        _log.info(
            "ticket close: %s: promoted pending draft %s -> %s",
            closed_ticket_id,
            draft_id,
            final_id,
        )
    return True


# frob:ticket T-2738
def _report_stranded_drafts_and_exit(closed_ticket_id: str, failed: list[str]) -> None:
    """T-2738: the failure-report half of `_promote_pending_drafts_after_close`
    (split out under ARCH103) -- log the full list of drafts that could
    not be promoted by name, then exit nonzero so a caller/CI checking
    the exit code sees a problem instead of a bare "closed" success."""
    _log.error(
        "ticket close: %s closed, but %d pending draft(s) could not "
        "be promoted and remain stranded: %s",
        closed_ticket_id,
        len(failed),
        ", ".join(failed),
    )
    sys.exit(1)


# frob:ticket T-2738
# frob:tests tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts.test_close_promotes_a_draft_the_ticket_filed  # noqa: E501
# frob:tests tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts.test_close_with_no_drafts_is_unchanged  # noqa: E501
# frob:tests tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts.test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted  # noqa: E501
def _promote_pending_drafts_after_close(root: Path, closed_ticket_id: str) -> None:
    """T-2738: `frob ticket close` used to leave every `T-draft-*`
    follow-up the closed ticket filed stranded, never promoted to a real
    id, invisible to the queue -- while reporting success. `frob ticket
    land` already promotes leftover drafts in the same ledger via
    `_finalize_sibling_drafts`'s "every draft still active here belongs
    to this unit of work" rule (true because draft ids are only ever
    minted off the default branch, T-0162); this mirrors that rule for
    the direct-close path using the same underlying primitive
    (`finalize_draft`, `frob ticket promote`'s own callable) instead of
    the land-specific `finalize_draft_for_land` (no worktree/main split
    exists here -- `close` never merges anything, it commits directly to
    `root`).

    Runs strictly AFTER `_close`'s own state transition and ledger
    commit -- the ticket is already DONE by the time this executes, so a
    promotion failure here cannot be undone by refusing; instead the
    per-draft outcome is logged loudly by name (with the exact
    hand-recovery command) via `_promote_one_pending_draft`, and any
    stranded drafts are reported and this process exits nonzero via
    `_report_stranded_drafts_and_exit` (both split out under ARCH103).
    `root` carrying no draft-id tickets at all (the common case) is a
    silent no-op -- no new log noise for a ticket that filed no drafts."""
    draft_ids = _pending_draft_ids_after_close(root, closed_ticket_id)
    if not draft_ids:
        return

    failed = [
        draft_id
        for draft_id in draft_ids
        if not _promote_one_pending_draft(root, closed_ticket_id, draft_id)
    ]
    if failed:
        _report_stranded_drafts_and_exit(closed_ticket_id, failed)


# frob:ticket T-1005
# frob:tests tests/test_ticket_reverify.py::TestReverifyCli.test_reruns_verification_and_refreshes_recap_state_unchanged  # noqa: E501
# frob:tests tests/test_ticket_reverify.py::TestReverifyCli.test_surfaces_now_failing_evidence_loudly  # noqa: E501
# frob:tests tests/test_ticket_reverify.py::TestReverifyCli.test_refuses_non_done_ticket
def _reverify(root: Path, cfg: AppConfig) -> None:
    """`frob ticket reverify <id>`: the missing verb for a post-close
    send-back (churn item 6, docs/audits/coordination-churn.md -- ~5
    observed occurrences). After a done ticket gets a TEST016-driven
    evidence strengthening (or any other scope/evidence/done-report edit
    applied post-close), nothing could previously re-run close's own
    verification suite against it: `close` itself refuses a done->done
    transition, and `start`/`sweep` both refuse a done ticket outright --
    so a land had to proceed on trust in the ORIGINAL close-time recap
    alone, even though the ticket's evidence/scope may have changed since.

    Re-runs the exact same five close-time guards `_close` computes
    (`_close_guards_for_ticket` -- D-02 covers_scope, T-0571 reviewed,
    T-0844 mutation_evidence, T-0417 evidence_reverified, T-1410
    gate_claims_verified, all shared, no duplicated computation) and the
    exact same state-machine verification
    `transition(..., TicketState.DONE, ...)` runs at close time
    (`frob.tickets.reverify_close_guard`, which wraps the SAME
    `_done_transition_guard` -- structural + T-0854 live-tracker-citation
    + T-0756 new-gate-rule-acceptance too), against the ALREADY-done
    ticket -- but NEVER calls `transition`, so no write, no state change,
    either way. `--evidence`/`--evidence-cmd`/`--accepts`/`--strict`/
    `--skip-mutation-evidence` behave identically to `close`'s own flags
    (`_apply_close_time_evidence`, shared).

    A failing guard exits 1 loudly via the SAME `_close_failure_hint`
    remedy text `close` itself would show (now under the `"reverify"`
    verb) and leaves the recap untouched -- this is the "surfaces a
    now-failing evidence id loudly" half of the contract. A fully passing
    reverify refreshes the recap: `frob.tickets.recover_done_report_why`
    recovers the ticket's existing Done-report narrative verbatim (the
    mechanical inverse of `compose_done_report`'s own narrative half, so
    the operator never retypes it), and a fresh `set_done_report` call
    (same T-0754 claims-capture callables `_done_report` already supplies)
    rewrites Changed/Evidence/Captured-claims against the CURRENT tree --
    the "refreshes the recap" half."""
    from frob.tickets import TicketState, recover_done_report_why, reverify_close_guard
    from frob.tickets import set_done_report as _set_done_report

    if cfg.ticket_id is None:
        _log.error("frob ticket reverify requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="reverify")
    if ticket.state is not TicketState.DONE:
        _log.error(
            "reverify failed: %s is %s, not done -- reverify re-checks an "
            "already-closed ticket, it does not close one (use `frob "
            "ticket close %s` instead)",
            cfg.ticket_id,
            ticket.state.value,
            cfg.ticket_id,
        )
        sys.exit(1)

    _apply_close_time_evidence(root, cfg)

    # Re-load: --evidence/--evidence-cmd may have just changed the ticket's
    # recorded evidence, and every guard below must see the CURRENT
    # evidence, not the state loaded before those flags applied (mirrors
    # `_close`'s own re-load-after-apply sequencing exactly).
    fresh_ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="reverify")

    # frob:ticket T-1648
    remainder_reason = _undisclosed_remainder_reason(root, fresh_ticket)
    if remainder_reason is not None:
        _log.error(
            "reverify failed: %s -- %s -- file a follow-up (`frob ticket "
            "new ...`) and add a 'Filed: T-####' line to the Done report "
            "naming it",
            cfg.ticket_id,
            remainder_reason,
        )
        sys.exit(1)

    (
        covers_scope,
        reviewed,
        mutation_evidence,
        evidence_reverified,
        gate_claims_verified,
        own_obligations_clean,
    ) = _close_guards_for_ticket(root, cfg, fresh_ticket)

    guard_result = reverify_close_guard(
        root,
        cfg.ticket_id,
        covers_scope=covers_scope,
        reviewed=reviewed,
        mutation_evidence=mutation_evidence,
        evidence_reverified=evidence_reverified,
        gate_claims_verified=gate_claims_verified,
        own_obligations_clean=own_obligations_clean,
    )
    if guard_result.is_err:
        _log.error(
            _close_failure_hint(
                cfg.ticket_id,
                fresh_ticket.state,
                guard_result.danger_err,
                verb="reverify",
            )
        )
        sys.exit(1)

    why = recover_done_report_why(fresh_ticket.body)
    if why is None:
        _log.error(
            "reverify failed: %s verification passed but no recoverable "
            "Done-report narrative was found to replay -- recap NOT "
            "refreshed (state remains done, unchanged); this can only "
            "happen for a Done report predating T-0458's auto-fill "
            "sections -- run `frob ticket done-report %s --why TEXT` once "
            "to give it one, then retry `frob ticket reverify %s`",
            cfg.ticket_id,
            cfg.ticket_id,
            cfg.ticket_id,
        )
        sys.exit(1)

    _shared_spawn = _shared_check_spawn_fn(root, cfg.ticket_id)
    report_result = _set_done_report(
        root,
        cfg.ticket_id,
        why=why,
        base_ref=cfg.ticket_base_ref,
        run_tests=_run_tests_count_fn(root),
        check_gates=_check_gates_summary_fn(root, cfg.ticket_id, spawn=_shared_spawn),
        check_gate_findings=_check_gate_findings_fn(
            root, cfg.ticket_id, spawn=_shared_spawn
        ),
    )
    if report_result.is_err:
        _log.error(
            "reverify: %s verification passed but the recap refresh "
            "failed (%s) -- state remains done, unchanged",
            cfg.ticket_id,
            report_result.danger_err,
        )
        sys.exit(1)
    _log.info(
        "%s reverified: full close-time verification suite passed, recap "
        "refreshed, state unchanged (done)",
        cfg.ticket_id,
    )


# frob:ticket T-1162
def _load_ticket_for_fail(root: Path, ticket_id: str):
    """T-1162: pure I/O -- load the queue and return the named ticket, or
    `sys.exit(1)` (with a logged reason) on a load error or unknown id.
    Extracted from `_fail` to isolate its I/O from the decision/formatting
    steps that follow."""
    from frob.tickets import load_queue

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("fail failed: %s", queue_result.danger_err)
        sys.exit(1)
    ticket = queue_result.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        _log.error("no ticket %s", ticket_id)
        sys.exit(1)
    return ticket


# frob:ticket T-1162
def _record_fail_entry(root: Path, ticket_id: str, ticket, summary: str) -> None:
    """T-1162: pure I/O -- append a `FailureEntry` (attempt number derived
    from the ticket's existing body) via `record_failure`, or `sys.exit(1)`
    on error. Extracted from `_fail`."""
    from frob.tickets import FailureEntry, record_failure

    attempt = ticket.body.count("attempt ") + 1
    entry = FailureEntry(date=date.today(), attempt=attempt, summary=summary)
    result = record_failure(root, ticket_id, entry)
    if result.is_err:
        _log.error("fail failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s: recorded failure attempt %d", ticket_id, attempt)


# frob:ticket T-1162
def _requeue_if_in_progress(root: Path, ticket_id: str, ticket) -> None:
    """T-1162: decision (was the ticket IN_PROGRESS?) plus the I/O that
    follows it -- requeue (IN_PROGRESS -> QUEUED) to release the
    cross-worktree lease, per the T-1131 incident documented on `_fail`.
    A ticket not IN_PROGRESS is left unchanged, matching pre-T-1131
    behavior for that case."""
    from frob.tickets import TicketState, transition

    if ticket.state is not TicketState.IN_PROGRESS:
        return
    requeued = transition(root, ticket_id, TicketState.QUEUED)
    if requeued.is_err:
        _log.error(
            "fail: %s failure log recorded but requeue failed (%s) -- "
            "lease NOT released, needs manual attention",
            ticket_id,
            requeued.danger_err,
        )
        sys.exit(1)
    _log.info("%s: requeued (in-progress -> queued), lease released", ticket_id)


# frob:ticket T-3137
# frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestFailNotVisibleOnPrimaryWarning.test_fail_from_worktree_warns_when_not_visible_on_primary  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestFailNotVisibleOnPrimaryWarning.test_fail_from_primary_is_quiet  # noqa: E501
def _warn_if_fail_not_visible_on_primary(root: Path, ticket_id: str) -> None:
    """T-3137: `fail` (unlike `scope`/`block`/`attach`/... T-2563's
    `MIRRORED_LEDGER_VERBS`) commits its failure-log entry to `root`'s
    own branch ONLY -- `LEDGER_VERB_STRATEGY["fail"]` is deliberately
    GENERIC_COMMIT_UNMIRRORED (T-2603), on the assumption that a future
    `frob ticket land` for THIS ticket will always carry it. That
    assumption breaks exactly when an agent fail-logs a SECOND ticket
    after its own series' landing ticket is already done: no further
    land ever touches this worktree branch again, so the failure log
    -- the SANCTIONED way this repo records a dead end -- silently never
    reaches main. `frob ticket promote` has the identical worktree-only-
    commit shape and already warns loudly
    (`_draft_finalize._warn_if_promote_not_visible_on_primary`); this is
    the same warning for `fail`, reusing the same `_resolve_primary_
    checkout` primary-detection rather than duplicating it.

    A no-op when `root` IS the resolved primary checkout (the common,
    already-visible case) or when the primary cannot be resolved at all
    (best-effort disclosure, never a hard failure of `fail` itself)."""
    from frob.tickets._land import _resolve_primary_checkout

    primary = _resolve_primary_checkout(root)
    if primary is None or primary.resolve() == root.resolve():
        return
    _log.error(
        "ticket fail: %s recorded ONLY on this worktree's own branch (%s) "
        "-- NOT yet visible on %s, and no future land is guaranteed to "
        "carry it (the exact trap if this ticket's series already landed). "
        "Run `frob ticket fail --path %s ...` (or the equivalent) from %s "
        "now, or land this ticket's own branch, to make the failure log "
        "visible to the fleet.",
        ticket_id,
        root,
        primary,
        primary,
        primary,
    )


# frob:ticket T-1131
# frob:ticket T-1130
# frob:ticket T-1162
def _fail(root: Path, cfg: AppConfig) -> None:
    """`frob ticket fail <id> --summary TEXT`: record a dead-end failure
    log entry, then requeue the ticket (T-1131).

    T-1131 (the T-1050 incident): `record_failure` only ever appended the
    failure-log entry -- it never called `transition`, so a ticket that
    was IN_PROGRESS when fail-logged stayed IN_PROGRESS forever, holding
    its cross-worktree lease (`_sync_cross_worktree_lease` only releases a
    lease on a `transition` call OUT of IN_PROGRESS, and `record_failure`
    never made one). An agent fail-logged a superseded ticket, removed its
    worktree, and the ticket sat in-progress pointing at a now-nonexistent
    path until a coordinator noticed and hand-dropped it. Requeuing
    (IN_PROGRESS -> QUEUED, a legal `_TRANSITIONS` edge) after a fail-log
    is the correct semantics anyway: a failed attempt is a retry
    candidate, not a permanently stuck ticket -- and it is the one
    `transition` call that actually releases the lease. A ticket that was
    NOT IN_PROGRESS when fail-logged (no lease to release) is left in its
    current state unchanged, matching pre-T-1131 behavior for that case.

    T-1130: auto-commits the fail-log (plus any requeue transition) as ONE
    ledger change, the same way `start` auto-commits its own transition
    (T-1054 parity) -- `--no-commit` (`cfg.ticket_no_commit`) opts out.

    T-1162 split this into `_load_ticket_for_fail` (I/O),
    `_record_fail_entry` (I/O), and `_requeue_if_in_progress`
    (decision+I/O) -- this function is now their composition plus the
    final ledger commit."""
    from frob.tickets._leases import commit_ticket_ledger_change

    if cfg.ticket_id is None or cfg.ticket_summary is None:
        _log.error("frob ticket fail requires <id> and --summary")
        sys.exit(1)

    ticket = _load_ticket_for_fail(root, cfg.ticket_id)
    _record_fail_entry(root, cfg.ticket_id, ticket, cfg.ticket_summary)
    _requeue_if_in_progress(root, cfg.ticket_id, ticket)

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): {cfg.ticket_id} fail-logged",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)
    _warn_if_fail_not_visible_on_primary(root, cfg.ticket_id)


# frob:ticket T-0579
# frob:ticket T-1130
def _drop(root: Path, cfg: AppConfig) -> None:
    """CLI wiring for `frob ticket drop <id> --reason TEXT [--absorbed-by
    T-####]` (T-0579): the first-class replacement for hand-editing
    `state: dropped` directly. Delegates entirely to `frob.tickets.
    drop_ticket` for the reason-line + transition + lease-release
    mechanics; this layer only validates required args and reports the
    Result.

    T-1130: auto-commits the drop's ledger change (reason line + DROPPED
    transition) the same way `start` auto-commits its own transition
    (T-1054 parity) -- `--no-commit` (`cfg.ticket_no_commit`) opts out."""
    from frob.tickets import drop_ticket
    from frob.tickets._leases import commit_ticket_ledger_change

    if cfg.ticket_id is None or not cfg.ticket_reason:
        _log.error("frob ticket drop requires <id> and --reason")
        sys.exit(1)

    result = drop_ticket(
        root, cfg.ticket_id, cfg.ticket_reason, absorbed_by=cfg.ticket_absorbed_by
    )
    if result.is_err:
        _log.error("drop failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s dropped", cfg.ticket_id)

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): drop {cfg.ticket_id}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)


# frob:ticket T-3087
def _reopen(root: Path, cfg: AppConfig) -> None:
    """CLI wiring for `frob ticket reopen <id> --reason TEXT` (T-3087):
    the explicit, reason-carrying, audited escape hatch for a
    FALSELY-closed ticket. Delegates entirely to `frob.tickets.
    reopen_ticket` for the reason-line + DONE-only gate + state write;
    this layer only validates required args and reports the Result --
    the same shape `_drop` already uses for `drop_ticket`.

    T-1130 parity: auto-commits the reopen's ledger change (reason line +
    DONE -> QUEUED write) the same way `drop`/`fail`/`start` auto-commit
    their own transitions -- `--no-commit` (`cfg.ticket_no_commit`) opts
    out."""
    from frob.tickets import reopen_ticket
    from frob.tickets._leases import commit_ticket_ledger_change

    if cfg.ticket_id is None or not cfg.ticket_reason:
        _log.error("frob ticket reopen requires <id> and --reason")
        sys.exit(1)

    result = reopen_ticket(root, cfg.ticket_id, cfg.ticket_reason)
    if result.is_err:
        _log.error("reopen failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s reopened (done -> queued)", cfg.ticket_id)

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): reopen {cfg.ticket_id}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)


# frob:ticket T-0094
# frob:ticket T-0106
# frob:ticket T-0215
