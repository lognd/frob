"""T-2982 part 3 (T-2985): CI result validity -- classify each test outcome
from a `frob.ci_report` job/run report as `STILL_VALID`, `STALE`, or
`UNKNOWN` against the CURRENT tree, so a green CI run from three commits
ago is never rendered as evidence about the tree as it stands today
(docs/modules/ci_validity.md).

THE RULE. A CI run is evidence about ONE commit (`RunSummary.head_sha`).
The moment code changes, some of that evidence goes stale, but a raw
`gh run view` never says WHICH part. This module answers that per test:

  - `STILL_VALID` -- no commit since the run's `head_sha` touched any
    symbol reaching this test (directly, or transitively through a
    `frob:uses-contract` chain) -- the result stands for the tree as it
    is now.
  - `STALE` -- something changed since the run either IN the test itself
    or in code the test's `affects()` closure reaches -- the result is
    UNMEASURED for the current tree, explicitly never reported as
    "passing".
  - `UNKNOWN` -- reachability could not be determined (the test symbol is
    not resolvable in the graph, the diff against `head_sha` could not be
    computed, or the reachability walk was truncated before it could
    positively confirm no touched symbol reaches the test) -- named
    honestly rather than defaulted to either of the other two.

REUSE, NOT A PARALLEL NOTION OF FRESHNESS. This module invents NO new
staleness machinery. It is built entirely on:

  - `frob.gitio.working_diff` -- the SAME diff primitive `frob.gates`'
    own `affect_drift_gate` (AFFECT001/AFFECT002) and `frob.tickets._land`
    use to find what a range of commits touched;
  - `frob.graph.affects.affects` -- the SAME `uses-contract` closure walk
    `affect_drift_gate` and the north-star `affects()` query already
    perform, unmodified, just applied per touched symbol here to answer
    "does S reach this test" instead of "what does S's own change
    obligate";
  - the same touched-symbol-by-span-overlap algorithm
    `frob.verify._attribution._touched_symrefs` and
    `frob.tickets._land._touched_symrefs_for_intent` already implement
    (T-2018's own precedent: a small, stable, span-overlap function is
    duplicated locally rather than reached through a private cross-
    package import -- this module's own `_touched_symrefs` matches that
    established precedent, not a new one).

This module never talks to `gh` directly (that is `frob.ghio`'s and
`frob.ci_report`'s job) and never persists its own verdict -- a CI
verdict must never outlive its validity without saying so (T-2982's own
constraint), so nothing here is cached; every call recomputes against
whatever `snapshot`/tree state the caller passes in, the same posture
`frob.graph.affects.affects` itself already takes (pure, snapshot-only,
no disk IO of its own).

THE DOCTRINE THIS MATCHES. `frob.verify` already refuses to attribute
against a stale baseline (T-2929) and gate results render `UNRES` rather
than `pass` when unmeasured (T-2891, `frob.gates`). A CI result whose
code changed underneath it gets the identical treatment here -- `STALE`
is a first-class outcome, never silently rendered as a green tick."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.error_set import ErrorSet
from typani.result import Result

from frob.ci_report import JobReport, RunReport
from frob.gitio import working_diff
from frob.graph._models import GraphSnapshot
from frob.graph.affects import affects
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/ci_validity.md#error-types
# frob:tests tests/test_ci_validity.py::TestValidityForRunHeadSha.test_diff_failure_is_err  # noqa: E501
class ValidityError(ErrorSet):
    """Fallible outcomes of this module's own operations (never the
    per-test classification itself, which always succeeds with an
    honest verdict -- see `Validity.UNKNOWN` for the "could not tell"
    case at the classification level)."""

    DiffUnavailable = "could not compute the diff since the run's head_sha"


# frob:doc docs/modules/ci_validity.md#data-models
# frob:tests tests/test_ci_validity.py::TestClassifyTest.test_still_valid_when_nothing_relevant_changed  # noqa: E501
class Validity:
    """The three classification values `classify_test` can return. Not a
    `StrEnum` deliberately -- plain string constants keep byte-stable
    `--json` rendering trivial (a bare string field, matching
    `frob.ci_report.JobReport.outcome`'s own convention) without an enum
    serialization decision to make."""

    STILL_VALID = "still_valid"
    STALE = "stale"
    UNKNOWN = "unknown"


# frob:doc docs/modules/ci_validity.md#data-models
# frob:tests tests/test_ci_validity.py::TestClassifyTest.test_still_valid_when_nothing_relevant_changed  # noqa: E501
# frob:tests tests/test_ci_validity.py::TestClassifyTest.test_stale_when_reached_by_a_touched_symbol  # noqa: E501
class TestValidity(BaseModel):
    """One test node's classification against the current tree: `status`
    is one of `Validity`'s three values, `reason` is a short human-
    readable justification (which touched symbol reached it, or why it
    could not be determined) -- never left implicit, since `STALE`/
    `UNKNOWN` without a reason would just reinvent the silent-zero
    problem one field over."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    status: str
    reason: str


def _node_id_to_symref(node_id: str) -> str:
    """`path::Class::method` (pytest's own node id shape) to
    `path::Class.method` (`frob.graph.SymbolId.__str__`'s canonical
    symref shape, dotted qualname) -- the one shape translation every
    caller in this module needs, so it lives here once rather than at
    each call site."""
    if "::" not in node_id:
        return node_id
    path, rest = node_id.split("::", 1)
    qualname = rest.replace("::", ".")
    # pytest parametrize ids look like `test_foo[case0]` -- keep verbatim,
    # the graph does not resolve per-parameter symbols separately.
    return f"{path}::{qualname}"


def _touched_symrefs(diff, snapshot: GraphSnapshot) -> frozenset[str]:  # noqa: ANN001
    """Every symbol in `snapshot` whose span overlaps a `diff` hunk in
    the same file -- the SAME span-overlap algorithm
    `frob.verify._attribution._touched_symrefs` and
    `frob.tickets._land._touched_symrefs_for_intent` already implement,
    duplicated locally per T-2018's own established precedent (module
    docstring) rather than imported across a package boundary."""
    hunks_by_file: dict[str, list[tuple[int, int]]] = {}
    for hunk in diff.hunks:
        hunks_by_file.setdefault(hunk.file, []).append(hunk.span)
    touched: set[str] = set()
    for record in snapshot.symbols.values():
        for span in hunks_by_file.get(record.id.path, ()):
            if span[0] <= record.span[1] and record.span[0] <= span[1]:
                touched.add(record.symref)
                break
    return frozenset(touched)


# frob:doc docs/modules/ci_validity.md#public-api
# frob:tests tests/test_ci_validity.py::TestClassifyTest.test_still_valid_when_nothing_relevant_changed  # noqa: E501
# frob:tests tests/test_ci_validity.py::TestClassifyTest.test_stale_when_reached_by_a_touched_symbol  # noqa: E501
# frob:tests \
# tests/test_ci_validity.py::TestClassifyTest.test_stale_when_test_itself_touched
# frob:tests \
# tests/test_ci_validity.py::TestClassifyTest.test_unknown_when_symbol_unresolvable
# frob:tests \
# tests/test_ci_validity.py::TestClassifyTest.test_unknown_when_closure_truncated
def classify_test(
    snapshot: GraphSnapshot,
    touched: frozenset[str],
    node_id: str,
    *,
    _max_depth: int | None = None,
    _max_nodes: int | None = None,
) -> TestValidity:
    """Classify one pytest `node_id` against an already-computed `touched`
    symbol set (from `_touched_symrefs` over a diff since the run's
    `head_sha`): `STALE` if `node_id`'s own symbol was touched directly
    or is named in the `tests` set of any touched symbol's `affects()`
    closure (module docstring's reuse note); `UNKNOWN` if the test's own
    symbol cannot be resolved in `snapshot` at all, or if a closure walk
    that did NOT already find a positive match was truncated (a
    truncated walk under-reports reachability -- module docstring's
    `affects()` reuse note -- so a truncated "no match" is honestly
    `UNKNOWN`, never `STILL_VALID`); `STILL_VALID` otherwise.
    `_max_depth`/`_max_nodes` (private, test-only) tighten `affects()`'s
    own bounds to exercise the truncation path deterministically without
    building a graph 500 nodes deep."""
    test_ref = _node_id_to_symref(node_id)
    if test_ref not in snapshot.symbols:
        _log.info(
            "ci_validity: classify_test: %r (symref=%r) not resolvable in graph "
            "-- UNKNOWN",
            node_id,
            test_ref,
        )
        return TestValidity(
            node_id=node_id,
            status=Validity.UNKNOWN,
            reason=f"test symbol {test_ref!r} not found in the graph snapshot",
        )

    if test_ref in touched:
        return TestValidity(
            node_id=node_id,
            status=Validity.STALE,
            reason=f"{test_ref} was itself touched since the run's commit",
        )

    return _classify_via_closure(
        snapshot, touched, node_id, test_ref, _max_depth, _max_nodes
    )


def _classify_via_closure(
    snapshot: GraphSnapshot,
    touched: frozenset[str],
    node_id: str,
    test_ref: str,
    max_depth: int | None,
    max_nodes: int | None,
) -> TestValidity:
    """The `affects()`-closure half of `classify_test` (extracted per this
    module's own ARCH001 line budget): walk every touched symbol's
    closure looking for `test_ref`, `STALE` on the first hit, `UNKNOWN`
    if no hit was found but some walk was truncated (module docstring's
    reachability-under-reports-when-truncated note), `STILL_VALID`
    otherwise."""
    kwargs: dict[str, int] = {}
    if max_depth is not None:
        kwargs["max_depth"] = max_depth
    if max_nodes is not None:
        kwargs["max_nodes"] = max_nodes

    any_truncated = False
    for ref in sorted(touched):
        aff = affects(snapshot, ref, **kwargs)
        any_truncated = any_truncated or aff.truncated
        if test_ref in aff.tests:
            return TestValidity(
                node_id=node_id,
                status=Validity.STALE,
                reason=f"{ref} changed since the run and its affects()-closure covers this test",  # noqa: E501
            )

    if any_truncated:
        _log.info(
            "ci_validity: classify_test: %r not positively reached, but a "
            "closure walk truncated -- UNKNOWN, not still_valid",
            node_id,
        )
        return TestValidity(
            node_id=node_id,
            status=Validity.UNKNOWN,
            reason="no touched symbol's affects()-closure reached this test, "
            "but at least one closure walk was truncated (max_depth/max_nodes)",
        )

    return TestValidity(
        node_id=node_id,
        status=Validity.STILL_VALID,
        reason="no commit since the run's head_sha touched a symbol reaching this test",  # noqa: E501
    )


# frob:doc docs/modules/ci_validity.md#public-api
# frob:tests tests/test_ci_validity.py::TestValidityForRunHeadSha.test_diff_failure_is_err  # noqa: E501
# frob:tests \
# tests/test_ci_validity.py::TestValidityForRunHeadSha.test_classifies_every_failing_no\
# de
def validity_for_run_head_sha(
    root: Path, snapshot: GraphSnapshot, run_head_sha: str, node_ids: tuple[str, ...]
) -> Result[tuple[TestValidity, ...], ValidityError]:
    """`working_diff(root, run_head_sha)` (the SAME diff primitive
    `frob.gates.affect_drift_gate` uses) plus `_touched_symrefs`, then
    `classify_test` for every id in `node_ids`. A diff that cannot be
    computed at all (`run_head_sha` unresolvable, git failure) fails the
    WHOLE batch as `Err(ValidityError.DiffUnavailable)` rather than
    reporting some ids and silently omitting others -- matching
    `frob.graph.affects`'s own "cannot verify is never verified"
    posture one layer up."""
    diff_result = working_diff(root, run_head_sha)
    if diff_result.is_err:
        _log.warning(
            "ci_validity: validity_for_run_head_sha: working_diff(%r) failed: %s",
            run_head_sha,
            diff_result.danger_err,
        )
        return Err(ValidityError.DiffUnavailable)
    touched = _touched_symrefs(diff_result.danger_ok, snapshot)
    _log.info(
        "ci_validity: validity_for_run_head_sha(%r): %d touched symbol(s), "
        "classifying %d node id(s)",
        run_head_sha,
        len(touched),
        len(node_ids),
    )
    return Ok(tuple(classify_test(snapshot, touched, nid) for nid in node_ids))


# frob:doc docs/modules/ci_validity.md#data-models
# frob:tests tests/test_ci_validity.py::TestJobAndRunValidity.test_job_validity_covers_named_failures  # noqa: E501
class JobValidity(BaseModel):
    """`classify_test` applied to every failing node id a `JobReport`
    named, plus the job's own identity -- the per-job answer to "which of
    these reported failures still say something about the tree as it
    stands now"."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    name: str
    tests: tuple[TestValidity, ...]


# frob:doc docs/modules/ci_validity.md#public-api
# frob:tests tests/test_ci_validity.py::TestJobAndRunValidity.test_job_validity_covers_named_failures  # noqa: E501
def job_validity(
    root: Path, snapshot: GraphSnapshot, run_head_sha: str, job: JobReport
) -> Result[JobValidity, ValidityError]:
    """`validity_for_run_head_sha` restricted to the node ids `job`
    actually named as failures -- a job with `outcome="not_recoverable"`
    (module docstring, `frob.ci_report`) has no node ids to classify and
    gets back an empty `tests` tuple, never fabricated ones."""
    node_ids = tuple(f.node_id for f in job.failures)
    result = validity_for_run_head_sha(root, snapshot, run_head_sha, node_ids)
    if result.is_err:
        return Err(result.danger_err)
    return Ok(JobValidity(job_id=job.job_id, name=job.name, tests=result.danger_ok))


# frob:doc docs/modules/ci_validity.md#data-models
# frob:tests tests/test_ci_validity.py::TestJobAndRunValidity.test_run_validity_covers_every_job  # noqa: E501
class RunValidity(BaseModel):
    """`job_validity` for every job in a `RunReport` -- the whole run's
    validity answer, one `JobValidity` per job."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    jobs: tuple[JobValidity, ...]


# frob:doc docs/modules/ci_validity.md#public-api
# frob:tests tests/test_ci_validity.py::TestJobAndRunValidity.test_run_validity_covers_every_job  # noqa: E501
def run_validity(
    root: Path, snapshot: GraphSnapshot, run_head_sha: str, run: RunReport
) -> Result[RunValidity, ValidityError]:
    """`job_validity` for every `JobReport` in `run.jobs`. Fails the
    whole call as `Err` if the underlying diff cannot be computed at all
    (`validity_for_run_head_sha`'s own posture) -- a run-wide "cannot
    verify" is never split into some jobs succeeding and others silently
    omitted."""
    jobs: list[JobValidity] = []
    for job in run.jobs:
        result = job_validity(root, snapshot, run_head_sha, job)
        if result.is_err:
            return Err(result.danger_err)
        jobs.append(result.danger_ok)
    return Ok(RunValidity(run_id=run.run_id, jobs=tuple(jobs)))


__all__ = [
    "JobValidity",
    "RunValidity",
    "TestValidity",
    "Validity",
    "ValidityError",
    "classify_test",
    "job_validity",
    "run_validity",
    "validity_for_run_head_sha",
]
