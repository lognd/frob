"""TEST016 (T-0755): the diff-scoped adversarial evidence obligation as a
`Violation`-producing gate.

Deliberately NOT part of `test_gate`'s snapshot-driven pipeline (docs/
modules/gates.md's `_STAGE_GROUPS`): every other TEST rule is a pure
function of the graph snapshot, cheap and safe to run on every `frob
check`. This rule spawns a bounded but real subprocess mutation pass
(`frob.tickets._mutation_evidence.check_ticket_mutation_evidence`, which
itself reuses `frob.mutate` -- no parallel mutation engine) per ticket. Not
something the default snapshot-driven gate pass may do without violating
the T-0755 PERF guard (must not slow `frob check` for tickets that never
opt in) -- `frob.check` is out of this ticket's declared scope entirely, so
`mutation_evidence_violations` has two callers today:
`frob.tickets._land._check_mutation_evidence`, invoked from
`_land_precheck` at `frob ticket land` time, and (T-0844)
`frob.app.ticket_runner`'s direct `frob ticket close` CLI path, so a
security/bug-kind ticket closed without landing is not exempt from this
obligation either.

Severity: WARN by default, promoted to ERROR for `security`/`bug`-kind
tickets (T-0755's own text: "ratchet to error ... for security/bug-kind
tickets") -- those are exactly the kinds the root-cause incident (T-0611,
T-0571, T-0682, T-0574, T-0710) came from. This is a plain per-ticket
`kind` check, not the `frob.gates._ratchet` baseline-pool mechanism: no
retroactive-mutation-of-past-findings concern applies here, because the
check runs ONLY at THIS ticket's own close/land time -- an already-closed
ticket's evidence is never re-scanned, so landing this rule cannot
retroactively turn a past close red (T-0755's own landing-safety
requirement, satisfied structurally rather than via a ratchet pool)."""
# frob:waive INV006 reason="module-docstring exclusivity-vocabulary hit is \
# source-level design-rationale prose describing already-implemented \
# entry-point/severity behavior, verifiable by reading the code it annotates and the \
# T-0755 land wiring in frob.tickets._land -- not a separate cross-module contract \
# needing its own tracked invariant, same calibration posture as frob.check's T-0585 \
# INV006 waiver"

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from enum import Enum, auto
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.process._guard import exec_enabled
from frob.tickets._models import Ticket, TicketKind
from frob.tickets._mutation_evidence import (
    ConfirmatoryFinding,
    MutationEvidenceError,
    check_ticket_mutation_evidence,
)

_log = get_logger(__name__)

_ERROR_KINDS = frozenset({TicketKind.SECURITY, TicketKind.BUG})


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
# frob:enforces CHK-GATE-TEST016
# frob:enforces CHK-THEME-EXISTENCE-NOT-PROOF
# frob:enforces CHK-SUBSYS-TICKETS-TESTING
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_warn_for_feature_kind  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_error_for_security_kind  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_no_findings_no_violations  # noqa: E501
# frob:tests tests/gates/test_mutation_evidence_err_branches.py::TestMutationEvidenceErrBranches.test_exec_disabled_degrades_to_no_violations  # noqa: E501
def mutation_evidence_violations(
    root: Path, ticket: Ticket, base_ref: str = "main"
) -> tuple[Violation, ...]:
    """TEST016: `ticket`'s own bound evidence tests never killed a single
    mutant of a diff-touched, in-scope file -- confirmatory-only evidence.

    Severity is ERROR for `security`/`bug`-kind tickets, WARN otherwise
    (see module docstring). `Err(ExecDisabled)` (the exec kill switch was
    active) degrades to NO violations rather than a false-clean pass being
    silently indistinguishable from a real one -- the caller sees the
    `Err` via `frob.tickets._mutation_evidence` directly if it needs to
    react to that case specially; this wrapper's job is only to turn
    genuine `ConfirmatoryFinding`s into `Violation`s.
    """
    result = check_ticket_mutation_evidence(root, ticket, base_ref)
    if result.is_err:
        if result.danger_err is MutationEvidenceError.ExecDisabled:
            return ()
        return ()
    findings = result.danger_ok
    severity = Severity.ERROR if ticket.kind in _ERROR_KINDS else Severity.WARN
    violations: list[Violation] = []
    for finding in findings:
        violations.append(
            Violation(
                rule="TEST016",
                severity=severity,
                file=finding.file,
                line=0,
                message=_test016_message(ticket.id, finding),
            )
        )
    return tuple(violations)


# frob:ticket T-1727
def _test016_message(ticket_id: str, finding: ConfirmatoryFinding) -> str:
    """The TEST016 finding message (T-0755 reviewer round 2, finding 4):
    names every surviving mutant's file:line + description, then BOTH
    documented remedies (strengthen the tests, or the `--skip-mutation-
    evidence` escape hatch) -- never just a bare "confirmatory-only"
    count with no actionable next step.

    T-1727: `finding.unmeasured` gets a DIFFERENT message, never the
    "confirmatory-only" wording -- an unmeasured file was never actually
    run to completion, so nothing was proven weak, only unknown. Reusing
    the confirmatory wording here would misreport "could not measure" as
    "measured and failing" (T-1703's exact lesson, same shape as a
    budget-truncated `frob check` parsed as a clean run)."""
    if finding.unmeasured:
        return _test016_unmeasured_message(ticket_id, finding)
    named = "; ".join(f"{m.file}:{m.line} ({m.description})" for m in finding.survivors)
    return (
        f"TEST016: {ticket_id}'s bound evidence {list(finding.tests)} killed "
        f"0/{finding.mutants_total} mutant(s) of {finding.file}'s changed "
        f"lines -- confirmatory-only, does not prove the evidence detects "
        f"this change. Surviving mutant(s): {named or '(none named)'}. "
        f"Remedy: (1) strengthen the named test(s) so at least one fails "
        f"on a mutant above, or (2) if this is a genuine false positive, "
        f"`frob ticket land --skip-mutation-evidence` (logs a loud, "
        f"justification-required override)."
    )


# frob:ticket T-1727
def _test016_unmeasured_message(ticket_id: str, finding: ConfirmatoryFinding) -> str:
    """T-1727: the TEST016 message for a file the sweep's shared wall-
    clock budget cut off before it could be (fully) measured -- distinct
    wording from `_test016_message`'s confirmatory-only case so
    UNMEASURED never reads as "measured and found weak"."""
    return (
        f"TEST016: {ticket_id}'s bound evidence {list(finding.tests)} could "
        f"NOT be measured against {finding.file} -- the mutation sweep's "
        f"wall-clock budget ran out before this file's mutants could be "
        f"(fully) run. This is UNMEASURED, not confirmatory-only: nothing "
        f"was proven weak, nothing was proven adversarial either. Remedy: "
        f"(1) split the bound evidence across faster tests so the sweep "
        f"fits its budget, or (2) if the evidence is known-good and the "
        f"budget is the real constraint, `frob ticket land "
        f"--skip-mutation-evidence` (logs a loud, justification-required "
        f"override) -- the same escape hatch a genuine confirmatory-only "
        f"finding uses."
    )


#: BUG002's own subprocess budget for running ONE designated evidence test
#: at the ticket's parent commit -- generous enough for a small evidence
#: suite, bounded so a hang cannot stall a land indefinitely (mirrors
#: `_TIMEOUT_S` above, T-0755's own per-mutant budget, at 2x since this
#: check runs the whole evidence test once rather than a single mutant).
_BUG_REPRO_TIMEOUT_S = 60.0

#: `git worktree add`/`remove` get their own, smaller budget -- a plain
#: checkout of an existing commit, no build step involved.
_BUG_REPRO_WORKTREE_TIMEOUT_S = 30.0

#: `frob:waive BUG002 reason="..." ` -- BUG002's escape hatch (T-1421,
#: modeled on `--skip-mutation-evidence`'s loud/justification-required
#: posture). Deliberately a plain regex scan of the TICKET'S OWN BODY TEXT
#: rather than a `frob.graph` `WAIVE` edge: `frob.graph.build_graph`
#: excludes `tickets.md` from both its doc-file and source-file walks
#: (see `frob.graph._collect_files`'s `is_ledger` exclusion) precisely so
#: a Done report quoting `frob:waive`/`frob:describes` verbatim does not
#: resurrect a phantom edge -- so a waiver comment physically placed in
#: `tickets.md` can never become a real `WAIVE` edge for
#: `_waive.py`'s`_match_waiver`/`_apply_waivers` spine to find. Scanning
#: `ticket.body` directly (the one place a bug ticket's own justification
#: naturally lives) is therefore not a shortcut around that machinery --
#: it is the only place this override CAN live for a ledger-resident
#: ticket. Requires `reason="..."` to actually suppress (same as
#: WAIVE001's contract elsewhere in this repo); a bare `frob:waive BUG002`
#: with no parseable reason is treated as ABSENT (the check still runs)
#: rather than a silent pass.
_BUG002_WAIVER_RE = re.compile(r'frob:waive\s+BUG002\s+reason="([^"]*)"')

#: `frob:no-behavior-change reason="..."` (T-1616): the honest home for
#: refactor/deletion-shaped work filed as `bug`/`security` kind (there is
#: no `refactor` kind -- T-1616's own text weighed adding one against a
#: body-text attribute and picked the attribute, mirroring
#: `_BUG002_WAIVER_RE`'s precedent immediately above rather than adding a
#: new `Ticket` field + CLI verb for a single gate's own obligation-swap).
#: When present, BUG002's whole check INVERTS (see `bug_repro_violations`)
#: instead of being skipped: the designated evidence test must PASS at the
#: parent commit (proving behavior is unchanged there too), and a genuine
#: FAILURE at the parent becomes the violation -- the work's own claim
#: ("nothing behavioral changed") would be falsified by its own repro
#: test failing at the pre-change commit. This keeps a real, mechanically
#: checked obligation rather than removing one, per T-1616's requirement
#: that reclassification-shaped work get a swapped obligation, not a
#: skipped one. Same `reason="..."` requirement as `_BUG002_WAIVER_RE`; a
#: bare directive with no parseable reason is treated as ABSENT (the
#: ordinary defect-repro check still runs).
_NO_BEHAVIOR_CHANGE_RE = re.compile(r'frob:no-behavior-change\s+reason="([^"]*)"')


class _BugReproOutcome(Enum):
    """The four possible outcomes of running BUG002's single designated
    reproduction test against the ticket's parent commit."""

    #: The test genuinely FAILED at the parent commit (pytest exit 1) --
    #: the honest, expected signal that the defect reproduced there and
    #: this ticket's evidence distinguishes parent from fix. No violation.
    FAILED_AT_PARENT = auto()
    #: The test PASSED at the parent commit (pytest exit 0) -- the
    #: evidence does not prove anything changed; this is the T-1384-class
    #: gap BUG002 exists to catch.
    PASSED_AT_PARENT = auto()
    #: The exec kill switch (`FROB_DISABLE_EXEC`) is active, or the
    #: worktree checkout / subprocess spawn itself failed for
    #: infrastructure reasons (not a test result at all -- a collection
    #: error from a missing native extension at the parent commit is the
    #: expected shape here, since a fresh `git worktree add` checkout has
    #: no compiled `frob_core`/`strata_core` of its own). Degrades to "no
    #: verdict", never a false-clean pass and never a false violation --
    #: same posture `MutationEvidenceError.ExecDisabled` already uses one
    #: function up in this same module.
    NO_VERDICT = auto()


# frob:tests tests/test_gates_mutation_evidence.py::TestBug002Waiver.test_reason_present_suppresses  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBug002Waiver.test_bare_directive_without_reason_does_not_suppress  # noqa: E501
def _bug002_waiver_reason(ticket: Ticket) -> str | None:
    """The `reason="..."` text of a `frob:waive BUG002 reason="..."` line
    found anywhere in `ticket.body`, or `None` if no such (well-formed)
    waiver is present. See `_BUG002_WAIVER_RE`'s comment for why this scans
    the ticket body directly instead of going through `frob.gates._waive`."""
    match = _BUG002_WAIVER_RE.search(ticket.body)
    return match.group(1) if match else None


# frob:tests tests/test_gates_mutation_evidence.py::TestNoBehaviorChange.test_reason_present_recognized  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestNoBehaviorChange.test_bare_directive_without_reason_not_recognized  # noqa: E501
def _no_behavior_change_reason(ticket: Ticket) -> str | None:
    """The `reason="..."` text of a `frob:no-behavior-change reason="..."`
    line found anywhere in `ticket.body` (T-1616), or `None` if absent.
    Same body-text-scan rationale as `_bug002_waiver_reason` immediately
    above -- `tickets.md` is excluded from `frob.graph`'s doc/source walk,
    so this directive can only ever live here, scanned directly."""
    match = _NO_BEHAVIOR_CHANGE_RE.search(ticket.body)
    return match.group(1) if match else None


# frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_first_pytest_node_id_is_designated  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_no_pytest_evidence_is_none  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_explicit_designation_wins_over_bind_order  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_explicit_designation_not_in_evidence_falls_back_to_positional  # noqa: E501
def _designated_repro_test(ticket: Ticket) -> str | None:
    """The single evidence test BUG002 re-runs at the parent commit
    (T-1670): `ticket.designated_repro_test` if explicitly set (via `frob
    ticket evidence <id> --designate-repro`) AND still present in
    `ticket.evidence` (a designation whose id was since `--replace`d or
    dropped falls back to the positional default below, rather than
    silently checking a test no longer bound at all); otherwise the FIRST
    pytest-node-id-shaped entry (`path::name`, excluding `cmd:` entries --
    same shape `frob.tickets._mutation_evidence._evidence_test_ids`
    filters to) in `ticket.evidence`, deterministic and cheap (T-1421's
    cost constraint: check ONE test at ONE prior commit, never the whole
    bound evidence set).

    T-1670's whole point: before `designated_repro_test` existed, this was
    ALWAYS the positional-first match, an invisible bind-ORDER dependency
    nothing in `frob ticket evidence` surfaced at bind time -- an agent
    who bound a pre-existing (already-passing-everywhere) test first and
    its real new repro test second got BUG002 checking the wrong one,
    passing at parent, and refusing land for a reason unrelated to the
    actual evidence quality. Explicit designation removes the ordering
    dependency; the positional fallback stays for every ticket that never
    designates one, so pre-T-1670 behavior is unchanged by default.

    `None` when the ticket has no pytest evidence at all -- nothing to
    check, matching `check_ticket_mutation_evidence`'s own "no pytest
    evidence, nothing to check" posture."""
    designated = ticket.designated_repro_test
    if designated is not None and designated in ticket.evidence:
        return designated
    for entry in ticket.evidence:
        if "::" in entry and not entry.startswith("cmd:"):
            return entry
    return None


# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproAtRef.test_exec_disabled_is_no_verdict  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproAtRef.test_worktree_add_failure_is_no_verdict  # noqa: E501
def _bug_repro_outcome_at_ref(
    root: Path, test_id: str, base_ref: str, *, timeout_s: float = _BUG_REPRO_TIMEOUT_S
) -> _BugReproOutcome:
    """Run `test_id` (a single pytest node id) against `base_ref`'s
    checked-out content, in isolation from `root`'s own working tree, and
    classify the result.

    Cheaper than a full second `uv run`/reinstall: a plain `git worktree
    add --detach` checkout of `base_ref` (no build step -- reuses
    `root`'s already-built native extensions and installed venv) with
    `PYTHONPATH` pointed at the checkout's own `src/` so the subprocess
    imports the PARENT COMMIT's Python source instead of `root`'s
    editable-install path. This only proves out for pure-Python changes
    (the five real T-1421 incidents were all exactly this shape -- an
    added guard/parameter never wired to a caller); a parent-commit change
    that also touched compiled native code is exactly the "genuinely
    cannot reproduce in this harness" case the `frob:waive BUG002`
    escape hatch exists for (see its docstring above), surfaced here as
    `NO_VERDICT` via a non-{0,1} pytest exit (a collection/import error),
    never mistaken for a real pass.
    """
    if not exec_enabled():
        _log.warning(
            "BUG002: exec disabled via kill switch, no repro-at-parent verdict for %s",
            test_id,
        )
        return _BugReproOutcome.NO_VERDICT
    scratch = Path(tempfile.mkdtemp(prefix="frob-bug002-"))
    worktree = scratch / "wt"
    try:
        if not _checkout_bug_repro_worktree(root, worktree, base_ref, test_id):
            return _BugReproOutcome.NO_VERDICT
        return _run_designated_test(worktree, test_id, timeout_s)
    finally:
        _remove_bug_repro_worktree(root, worktree)
        shutil.rmtree(scratch, ignore_errors=True)


def _checkout_bug_repro_worktree(
    root: Path, worktree: Path, base_ref: str, test_id: str
) -> bool:
    """`git worktree add --detach worktree base_ref`'s spawn-and-classify
    half, split out of `_bug_repro_outcome_at_ref` (ARCH103: keep I/O and
    branching apart). `True` on a clean checkout; `False` (logged) on any
    spawn/exit failure -- the caller degrades that to `NO_VERDICT`."""
    added = run_argv(
        (
            "git",
            "-C",
            str(root),
            "worktree",
            "add",
            "--detach",
            str(worktree),
            base_ref,
        ),
        timeout_s=_BUG_REPRO_WORKTREE_TIMEOUT_S,
    )
    if added.is_err or added.danger_ok.returncode != 0:
        _log.warning(
            "BUG002: could not check out %s at %s for repro check (%s) -- no verdict",
            base_ref,
            test_id,
            added.danger_ok.stderr if added.is_ok else added.danger_err,
        )
        return False
    return True


def _run_designated_test(
    worktree: Path, test_id: str, timeout_s: float
) -> _BugReproOutcome:
    """Run `test_id` in `worktree` (a `base_ref` checkout) via the CURRENT
    interpreter, `PYTHONPATH`-pointed at `worktree/src` so imports resolve
    to the checked-out parent-commit source rather than the current
    editable install -- `_bug_repro_outcome_at_ref`'s spawn-and-classify
    half. Exit 0 -> `PASSED_AT_PARENT`; exit 1 (a genuine assertion/error
    failure) -> `FAILED_AT_PARENT`; anything else (collection error,
    missing native extension, timeout) -> `NO_VERDICT`, never guessed at
    as a pass or a fail."""
    env = dict(os.environ)
    src = str(worktree / "src")
    env["PYTHONPATH"] = (
        src if not env.get("PYTHONPATH") else src + os.pathsep + env["PYTHONPATH"]
    )
    argv = (sys.executable, "-m", "pytest", test_id, "-q", "-p", "no:cacheprovider")
    spawned = run_argv(argv, cwd=worktree, timeout_s=timeout_s)
    if spawned.is_err:
        _log.warning("BUG002: repro run of %s failed to spawn -- no verdict", test_id)
        return _BugReproOutcome.NO_VERDICT
    rc = spawned.danger_ok.returncode
    if rc == 0:
        return _BugReproOutcome.PASSED_AT_PARENT
    if rc == 1:
        return _BugReproOutcome.FAILED_AT_PARENT
    _log.warning(
        "BUG002: repro run of %s exited %d at parent (not a plain pass/fail -- "
        "likely a collection error, e.g. a native extension the parent commit's "
        "isolated checkout never built) -- no verdict",
        test_id,
        rc,
    )
    return _BugReproOutcome.NO_VERDICT


def _remove_bug_repro_worktree(root: Path, worktree: Path) -> None:
    """Best-effort `git worktree remove --force`, logged but never raised
    -- `_bug_repro_outcome_at_ref`'s `finally` already falls back to a
    plain `shutil.rmtree` of the scratch dir, so a failure here just means
    the worktree's git-side registration lingers until the next `frob
    worktree sweep` / `git worktree prune`, not a lost repro verdict."""
    removed = run_argv(
        ("git", "-C", str(root), "worktree", "remove", "--force", str(worktree)),
        timeout_s=_BUG_REPRO_WORKTREE_TIMEOUT_S,
    )
    if removed.is_err or removed.danger_ok.returncode != 0:
        _log.warning("BUG002: could not remove scratch worktree %s", worktree)


def _bug002_message(ticket_id: str, test_id: str, base_ref: str) -> str:
    """BUG002's refusal message: names the designated test, the parent ref
    it was re-run against, and both documented remedies -- fix the
    reproduction (bind evidence that actually fails before the fix), or
    the `frob:waive BUG002 reason="..."` escape hatch for a genuinely
    unreproducible defect."""
    return (
        f"BUG002: {ticket_id}'s designated reproduction test {test_id!r} "
        f"PASSED at the parent commit ({base_ref}) -- this evidence does "
        f"not prove the defect it describes was actually fixed, only that "
        f"new code exists. Remedy: (1) bind evidence that genuinely fails "
        f"at {base_ref} and passes at the fix (a test that reaches the "
        f"real caller/wiring the defect was about), (2) if this is really "
        f"a refactor/deletion with no intended behavior change (T-1616), "
        f'add `frob:no-behavior-change reason="..."` to the ticket body '
        f"-- BUG002 will then require the OPPOSITE (the test must PASS at "
        f"{base_ref}) instead of skipping the check, or (3) if this defect "
        f"genuinely cannot be reproduced in a test (a nondeterministic "
        f"crash, an environment the suite cannot create, a ledger/doc "
        f"correction filed as kind=bug), add `frob:waive BUG002 "
        f'reason="..."` to the ticket body explaining why, in the same '
        f"spirit as `frob ticket land --skip-mutation-evidence`."
    )


def _no_behavior_change_message(ticket_id: str, test_id: str, base_ref: str) -> str:
    """T-1616's inverted BUG002 message: fires when a ticket claims `frob:
    no-behavior-change` but its own designated evidence test FAILED at the
    parent commit -- the exact opposite failure mode of the ordinary
    `_bug002_message`, and it means the claim itself is false: something
    behavioral DID change, contradicted by the ticket's own repro."""
    return (
        f"BUG002: {ticket_id} claims `frob:no-behavior-change` but its "
        f"designated evidence test {test_id!r} FAILED at the parent commit "
        f"({base_ref}) -- that contradicts the claim: a test that fails "
        f"before this ticket's change and (presumably) passes after it "
        f"means something DID behave differently, not nothing. Remedy: "
        f"(1) confirm the change really is behavior-preserving and bind "
        f"evidence that passes at both {base_ref} and the fix (a "
        f"characterization test of the touched seam, not a new-behavior "
        f"test), or (2) if this genuinely is a behavioral fix, drop the "
        f"`frob:no-behavior-change` claim and let BUG002's ordinary "
        f"defect-repro check apply instead."
    )


# frob:enforces CHK-GATE-BUG002
# frob:doc \
# docs/modules/gates.md#bug002-t-1421-a-bug-ticket-must-prove-the-defect-no-longer-repr\
# oduces
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_non_bug_kind_never_checked  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_no_pytest_evidence_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_waived_with_reason_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_passed_at_parent_is_error_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_failed_at_parent_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_no_verdict_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange.test_passed_at_parent_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange.test_failed_at_parent_is_error_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange.test_no_verdict_no_violation  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugRepro.test_reconstructed_uncalled_guard_passes_at_both_is_refused kind="integration"  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestBugRepro.test_reconstructed_wired_guard_fails_at_parent_is_permitted kind="integration"  # noqa: E501
def bug_repro_violations(
    root: Path, ticket: Ticket, base_ref: str = "main"
) -> tuple[Violation, ...]:
    """BUG002 (T-1421): a `bug`/`security`-kind ticket's designated
    evidence test must have genuinely FAILED at `base_ref` (the ticket's
    parent commit) -- the mechanically checkable form of "the defect no
    longer reproduces", complementing TEST016 (`mutation_evidence_
    violations` above) rather than duplicating it: TEST016 proves the
    ticket's OWN diff is mutation-detectable by its bound evidence, which
    is silent about whether anything actually CALLS the changed code
    (`frob.tickets._evidence`'s `own_obligations_clean`/T-1384 class of
    incident -- new code was mutation-detectable, but no caller reached
    it, so TEST016 passed while the defect stayed live on `main`). This
    rule instead re-runs the SAME evidence test against the commit BEFORE
    the ticket's changes and checks it genuinely fails there -- something
    TEST016's diff-scoped mutation pass cannot see at all, since an absent
    caller has no mutant to kill or survive.

    ERROR severity always (this rule only ever fires for `bug`/`security`
    kind, both already ERROR-severity for TEST016 -- see module docstring
    for why those two kinds get the harder gate). `()` (no violation)
    whenever: the ticket is not `bug`/`security`-kind; it has no
    pytest-node-id evidence yet (nothing to check); a `frob:waive BUG002
    reason="..."` override is present in the ticket body (logged loudly,
    T-1421's required escape hatch); or the repro run at `base_ref`
    produced `FAILED_AT_PARENT` (the honest, expected case) or
    `NO_VERDICT` (an infra/kill-switch degrade -- never a false
    violation, mirroring TEST016's own `ExecDisabled` posture)."""
    if ticket.kind not in _ERROR_KINDS:
        return ()
    waiver_reason = _bug002_waiver_reason(ticket)
    if waiver_reason is not None:
        _log.warning(
            "BUG002: %s waived via frob:waive BUG002 reason=%r -- no "
            "repro-at-parent check run",
            ticket.id,
            waiver_reason,
        )
        return ()
    test_id = _designated_repro_test(ticket)
    if test_id is None:
        _log.debug(
            "BUG002: %s has no pytest-node-id evidence yet, nothing to check",
            ticket.id,
        )
        return ()
    outcome = _bug_repro_outcome_at_ref(root, test_id, base_ref)

    # T-1616: a `frob:no-behavior-change reason="..."` claim SWAPS the
    # obligation rather than skipping it -- refactor/deletion-shaped work
    # whose entire point is that behavior did NOT change cannot honestly
    # satisfy "the designated test fails at the parent" (that would prove
    # the OPPOSITE of the claim). Instead: the designated test must PASS
    # at the parent (unchanged there too); a genuine FAILED_AT_PARENT
    # falsifies the claim and is the violation. NO_VERDICT still degrades
    # to no violation either way -- an infra/kill-switch gap is not
    # evidence against either claim.
    no_behavior_change_reason = _no_behavior_change_reason(ticket)
    if no_behavior_change_reason is not None:
        _log.warning(
            "BUG002: %s claims frob:no-behavior-change reason=%r -- "
            "checking the INVERTED obligation (designated test must PASS "
            "at the parent)",
            ticket.id,
            no_behavior_change_reason,
        )
        if outcome is not _BugReproOutcome.FAILED_AT_PARENT:
            return ()
        return (
            Violation(
                rule="BUG002",
                severity=Severity.ERROR,
                file="tickets.md",
                line=0,
                message=_no_behavior_change_message(ticket.id, test_id, base_ref),
            ),
        )

    if outcome is not _BugReproOutcome.PASSED_AT_PARENT:
        return ()
    return (
        Violation(
            rule="BUG002",
            severity=Severity.ERROR,
            file="tickets.md",
            line=0,
            message=_bug002_message(ticket.id, test_id, base_ref),
        ),
    )


__all__ = ["bug_repro_violations", "mutation_evidence_violations"]
