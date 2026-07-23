"""Diff-scoped adversarial evidence obligation (T-0755).

Root cause this closes: several rejected tickets' own tests PASSED before
the fix was even made, because they were written CONFIRMATORY ("assert the
thing I just built does the thing") rather than ADVERSARIAL ("prove a
plausible mutant of this logic gets caught") -- a confirmatory test that
would pass on both the pre-change and post-change code proves nothing about
the change it claims to cover.

This module runs a BOUNDED mutation pass (`frob.mutate`, no parallel
mutation engine) over the ticket's own diff-touched Python files, using the
ticket's OWN bound evidence test ids as the kill oracle: if at least one
mutant of the touched code makes the evidence-test command fail, the
evidence proved it distinguishes the change (a real kill). If EVERY mutant
of a touched file still passes the evidence tests, those tests are
confirmatory-only for that file -- `frob.gates` surfaces this as TEST016
(see `docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755`).

Deliberately narrow in v1, matching `frob.mutate`'s own Python-only v1
scope (docs/modules/mutate.md): non-Python touched files are silently
skipped (nothing to mutate, not a finding), and only files the ticket's OWN
`scope` covers are considered -- a ticket cannot be flagged for a file it
never claimed to touch. Bounded by `_MAX_FILES` and `_MAX_MUTANTS_PER_FILE`
so a large ticket's check stays a matter of seconds, not minutes (docs/
guides/agent-playbook.md section 3b's foreground-cap concern applies here
just as much as to `frob check`)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.gitio import working_diff
from frob.logging import get_logger
from frob.mutate import Mutant, MutateError, run_mutations
from frob.tickets._models import Ticket, scope_matches

_log = get_logger(__name__)

#: How many diff-touched files a single evidence-quality check will mutate.
#: Bounded so the obligation stays a few-second check, not a minutes-long
#: sweep, even for a ticket touching a wide scope (T-0755 PERF guard).
_MAX_FILES = 3

#: How many single-point mutants per file are actually run. `frob.mutate`
#: generates every point in source order; `run_mutations`' `max_mutants`
#: takes the first N of them (deterministic, not sampled). T-0755 reviewer
#: round 2: applied AFTER hunk-scoping (`line_ranges`), so this caps points
#: that actually fall inside the diff's changed lines, not the whole file.
_MAX_MUTANTS_PER_FILE = 8

#: Per-mutant test-command timeout. T-0755 reviewer round 2: reduced from
#: 90s to 30s -- generous enough for a small bound evidence suite, bounded
#: enough that a typical land's worst case (max_files * max_mutants_per_file
#: mutants, hunk-scoped so usually far fewer than the cap) stays well under
#: agent-playbook 3b's foreground budget (a `TimeoutExpired` still counts
#: as a kill, matching `run_mutations`' existing "a hang is real observed
#: behavior" semantics).
_TIMEOUT_S = 30.0


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
class MutationEvidenceError(ErrorSet):
    """Fallible outcomes of the diff-scoped evidence-quality check."""

    ExecDisabled = "exec capability disabled -- mutation check aborted, no verdict"


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
class ConfirmatoryFinding(BaseModel):
    """One touched file whose ticket-bound evidence tests killed ZERO of
    its bounded mutant set -- every recorded evidence test for this ticket
    is confirmatory-only with respect to this file's changed logic.

    `survivors` (T-0755 reviewer round 2) names every surviving mutant
    (file:line + description) so the eventual refusal message can point at
    exactly what the evidence failed to catch, not just a bare count."""

    model_config = ConfigDict(frozen=True)

    ticket_id: str
    file: str
    tests: tuple[str, ...]
    mutants_total: int
    survivors: tuple[Mutant, ...] = ()


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
# frob:tests tests/test_tickets_mutation_evidence.py::TestEvidenceTestIds.test_filters_non_node_id_entries  # noqa: E501
def evidence_test_ids(ticket: Ticket) -> tuple[str, ...]:
    """The subset of `ticket.evidence` that look like pytest node ids
    (`path::name`), excluding `cmd:` entries and any other non-pytest
    evidence shape -- the only entries `frob.mutate`'s `test_argv` can
    meaningfully re-run as the kill oracle."""
    return tuple(e for e in ticket.evidence if "::" in e and not e.startswith("cmd:"))


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
# frob:tests tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles.test_filters_to_scope_and_python  # noqa: E501
def touched_python_files(root: Path, ticket: Ticket, base_ref: str) -> tuple[Path, ...]:
    """Python files under `ticket.scope` that differ from `base_ref` in the
    working tree (`frob.gitio.working_diff`, the ONE diff seam this repo
    already uses everywhere else -- no second diff implementation).

    Deterministically sorted so the first `_MAX_FILES` taken by the caller
    is a stable, reproducible subset run-to-run, not dependent on git's own
    unspecified hunk ordering."""
    diff = working_diff(root, base_ref)
    if diff.is_err:
        _log.debug(
            "mutation-evidence: %s working_diff unavailable (%s), no files",
            ticket.id,
            diff.danger_err,
        )
        return ()
    files = sorted({h.file for h in diff.danger_ok.hunks})
    return tuple(
        Path(f)
        for f in files
        if f.endswith(".py")
        and not _is_test_file(f)
        and scope_matches(f, ticket.scope, kind=ticket.kind)
        and (root / f).is_file()
    )


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
# frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_confirmatory_test_flagged  # noqa: E501
# frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_large_file_unmutable_changed_lines_is_skipped_not_flagged  # noqa: E501
def changed_line_ranges(
    root: Path, base_ref: str
) -> dict[str, tuple[tuple[int, int], ...]]:
    """Every diff-touched file's changed line spans (`frob.gitio.Hunk.span`,
    1-indexed inclusive), keyed by file path -- feeds `run_mutations`'
    `line_ranges` filter so mutation points are scoped to the lines a
    ticket's diff actually changed, not the whole file (T-0755 reviewer
    round 2 CRITICAL fix: a file-wide point selection let an unrelated
    pre-existing line supply every mutant for a 2-line diff, a false
    positive reproduced on this ticket's own diff against `gates/
    __init__.py`). Empty dict on a `working_diff` failure, matching
    `touched_python_files`'s own best-effort posture."""
    diff = working_diff(root, base_ref)
    if diff.is_err:
        return {}
    by_file: dict[str, list[tuple[int, int]]] = {}
    for hunk in diff.danger_ok.hunks:
        by_file.setdefault(hunk.file, []).append(hunk.span)
    return {f: tuple(spans) for f, spans in by_file.items()}


def _is_test_file(path: str) -> bool:
    """Whether `path` is itself a test file, not production logic --
    mutating a test file and re-running THAT SAME test file as the kill
    oracle is a self-referential no-op (the boundary this obligation
    exists to check is test-vs-logic, not test-vs-itself), so test files
    are never candidates for mutation, only the tests bound as evidence
    against them (T-0755)."""
    name = Path(path).name
    parts = Path(path).parts
    return name.startswith("test_") or name.endswith("_test.py") or "tests" in parts


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
# frob:invariant INV-017
# frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_confirmatory_test_flagged  # noqa: E501
# frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_adversarial_test_not_flagged  # noqa: E501
# frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_no_test_evidence_is_ok_empty  # noqa: E501
def check_ticket_mutation_evidence(
    root: Path,
    ticket: Ticket,
    base_ref: str = "main",
    *,
    max_files: int = _MAX_FILES,
    max_mutants_per_file: int = _MAX_MUTANTS_PER_FILE,
    timeout_s: float = _TIMEOUT_S,
) -> Result[tuple[ConfirmatoryFinding, ...], MutationEvidenceError]:
    """The T-0755 obligation itself: for each of `ticket`'s diff-touched,
    in-scope Python files (bounded to `max_files`), mutate up to
    `max_mutants_per_file` points FALLING WITHIN THE DIFF'S OWN CHANGED
    LINES (`changed_line_ranges`, T-0755 reviewer round 2 -- a file-wide
    point selection previously let an unrelated pre-existing line supply
    every mutant for a tiny diff) and re-run `ticket`'s own bound pytest
    evidence ids as the kill command. A file where every (hunk-scoped)
    mutant SURVIVED (the evidence tests passed regardless) is reported as
    a `ConfirmatoryFinding` -- `frob.gates` turns this into TEST016.

    `Ok(())` (no findings, nothing wrong) covers every "nothing to check"
    case uniformly: no pytest-shaped evidence recorded yet (a docs-kind
    ticket, or one not yet at close time), no in-scope touched Python
    files, or every touched file having zero mutable points WITHIN ITS
    CHANGED LINES (an unmutable one-line diff, a docstring-only change,
    etc -- `run_mutations` returns `total=0` for that file, and it is
    SKIPPED, never flagged: there is nothing in the actual diff this check
    could possibly ask evidence to distinguish, regardless of what else
    the file contains).

    `Err(ExecDisabled)` if the FIRST mutant run aborts under the exec kill
    switch (`FROB_DISABLE_EXEC=1`) -- mirrors `run_mutations`' own T-0803
    refusal-is-not-a-verdict posture: reporting "no findings" under a
    disabled exec capability would be a false-clean rubber stamp, not an
    honest empty result."""
    test_ids = evidence_test_ids(ticket)
    if not test_ids:
        _log.debug(
            "mutation-evidence: %s has no pytest-node-id evidence, nothing to check",
            ticket.id,
        )
        return Ok(())
    files = touched_python_files(root, ticket, base_ref)
    if not files:
        _log.debug(
            "mutation-evidence: %s has no in-scope touched .py files, nothing to check",
            ticket.id,
        )
        return Ok(())
    ranges_by_file = changed_line_ranges(root, base_ref)
    argv = ("uv", "run", "pytest", *test_ids, "-q")
    findings: list[ConfirmatoryFinding] = []
    for file in files[:max_files]:
        ranges = ranges_by_file.get(str(file))
        if not ranges:
            # No changed-line spans recorded for this file (diff vanished
            # between the two working_diff calls, or a rename/mode-only
            # change) -- nothing to mutate, not a finding.
            _log.debug(
                "mutation-evidence: %s no changed-line spans for %s, skipping",
                ticket.id,
                file,
            )
            continue
        result = run_mutations(
            root,
            file,
            argv,
            timeout_s=timeout_s,
            max_mutants=max_mutants_per_file,
            line_ranges=ranges,
        )
        if result.is_err:
            err = result.danger_err
            if err is MutateError.ExecDisabled:
                return Err(MutationEvidenceError.ExecDisabled)
            _log.debug("mutation-evidence: %s skipping %s (%s)", ticket.id, file, err)
            continue
        report = result.danger_ok
        if report.total == 0:
            _log.debug(
                "mutation-evidence: %s %s -- 0 mutable point(s) in changed lines %s, "
                "skipping (not a finding)",
                ticket.id,
                file,
                ranges,
            )
            continue
        if report.killed == 0:
            _log.warning(
                "mutation-evidence: %s %s -- %d mutant(s) in changed lines %s, "
                "0 killed by %s, confirmatory-only: %s",
                ticket.id,
                file,
                report.total,
                ranges,
                test_ids,
                [(m.file, m.line, m.description) for m in report.survivors],
            )
            findings.append(
                ConfirmatoryFinding(
                    ticket_id=ticket.id,
                    file=str(file),
                    tests=test_ids,
                    mutants_total=report.total,
                    survivors=report.survivors,
                )
            )
        else:
            _log.info(
                "mutation-evidence: %s %s -- %d/%d mutant(s) killed, evidence proven adversarial",  # noqa: E501
                ticket.id,
                file,
                report.killed,
                report.total,
            )
    return Ok(tuple(findings))


__all__ = [
    "ConfirmatoryFinding",
    "MutationEvidenceError",
    "changed_line_ranges",
    "check_ticket_mutation_evidence",
    "evidence_test_ids",
    "touched_python_files",
]
