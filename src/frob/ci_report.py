"""T-2982 part 2 (T-2984): structured CI failure reporting on top of
`frob.ghio` (docs/modules/ci_report.md) -- typed run/job/test-node
records, failures clustered by signature, so the operator asks "what is
failing" and gets an answer instead of a raw log dump.

THE MOTIVATING INCIDENT (T-2982's own body). Pulling 156 macOS failure
node ids out of a raw job log by hand, hand-clustering them, and a
~100-failure cluster mis-attributed as macOS-specific for an entire
investigation because the ubuntu job had been cancelled mid-run and
nothing surfaced that fact. This module exists so neither mistake is
possible again: `build_job_report` parses `frob.ghio.JobLog.text` into
named `TestFailure` records grouped into `FailureCluster`s, and NEVER
reports zero failures when it cannot actually see pytest's own summary --
that state is the explicit `JobOutcome.NOT_RECOVERABLE` value, never an
empty tuple that reads as "nothing failed".

WHY NOT POSITIONAL. Under this repo's own `-n auto --dist=loadgroup`
pytest-xdist addopts, the live progress stream (`.` / `F` characters) is
written in COMPLETION order interleaved across worker processes, so a
character's position in that stream cannot be mapped back to a test node
id -- attempting that mapping is unsound and this module does not do it.
The ONLY source of truth for which node ids failed is pytest's own
"short test summary info" block and its final result-count line, both
emitted once at the end of a run that actually reached that point. A log
with neither is treated as `NOT_RECOVERABLE`, not zero failures -- this
is true independent of `JobLog.truncated` (a cancelled run's log is the
measured case that produces this state, but a worker-killed or otherwise
truncated-without-cancellation log gets the same honest treatment).

CLUSTERING. `_signature` collapses a failure's reason line to its
exception type plus a value-stripped message (`_VALUE_TOKEN` regex
removes digits, hex, and quoted literals) so that the SAME root cause
failing across many parametrized/platform-specific node ids clusters
into one `FailureCluster` -- exactly the aggregation step that was done
by hand, incorrectly, in the incident this ticket exists to close.
Clustering happens PER JOB (each `gh` job already corresponds to one CI
matrix leg, e.g. one OS), so a cluster's membership never crosses a job
boundary and can never again produce a mis-attributed "macOS-specific"
claim built from a merged pool of failures from different platforms.

This module builds ONLY on `frob.ghio`'s public surface (`view_run`,
`job_log`) -- no second `gh` subprocess seam. CI-result validity against
the obligation graph (T-2985) is a separate, later module built on TOP of
these records, not merged into this one."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.result import Result

from frob.ghio import GhError, JobSummary, job_log, view_run
from frob.logging import get_logger

_log = get_logger(__name__)

#: `FAILED`/`ERROR` lines pytest emits in its "short test summary info"
#: block: `FAILED path::Class::test - ExceptionType: message` (the
#: reason clause is optional -- a bare `FAILED path::test` line is valid
#: pytest output for a failure with no captured exception summary).
_SUMMARY_LINE = re.compile(r"^(FAILED|ERROR)\s+(\S+)(?:\s+-\s+(.*))?$", re.MULTILINE)

#: pytest's final one-line result count, e.g. `==== 3 failed, 40 passed
#: in 12.34s ====`. Its PRESENCE is the signal pytest actually reached
#: the end of the run and wrote its own summary; its absence is exactly
#: the `NOT_RECOVERABLE` case this module exists to name.
_RESULT_LINE = re.compile(
    r"^=+.*\b(\d+) (?:failed|error)\b.*in [\d.]+s.*=+\s*$"
    r"|^=+ \d+ passed.* in [\d.]+s =+\s*$",
    re.MULTILINE,
)

#: T-5477: a `gh api .../logs` line prefix -- every line of a REST-
#: fetched job log carries a leading ISO-8601 timestamp
#: (`2026-09-24T03:43:26.1010000Z `, fractional seconds and the literal
#: `Z` both present) that defeats every `^`-anchored regex above unless
#: stripped or matched around. Optional (a locally captured log, or one
#: already stripped by the caller, has no such prefix).
_GH_LOG_TIMESTAMP_PREFIX = r"(?:\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\s+)?"

#: T-5477: this repo's OWN end-of-run summary line
#: (`tests/conftest.py`'s `pytest_sessionfinish` hook), written instead
#: of trusting vanilla pytest's positional dot-stream under `-n auto
#: --dist=loadgroup` (module docstring's WHY NOT POSITIONAL section) --
#: `SUITE-RESULT: exitstatus=N collected=N failed=N`. Only the
#: `completed` shape (module docstring's own `_EXIT_STATUS_LABELS`
#: branch is NOT matched here on purpose: a partial/interrupted run's
#: line carries an extra label token this pattern's `$` anchor refuses,
#: correctly falling through to `not_recoverable` for that case exactly
#: like an absent `_RESULT_LINE` already does).
_SUITE_RESULT_LINE = re.compile(
    _GH_LOG_TIMESTAMP_PREFIX
    + r"SUITE-RESULT: exitstatus=(\d+) collected=(\d+) failed=(\d+)\s*$",
    re.MULTILINE,
)

#: T-5477: one `SUITE-RESULT-FAILED: <nodeid> (failed|error)[ -- <cause>]`
#: line per named failure -- `tests/conftest.py` also emits a non-node-id
#: continuation line (`SUITE-RESULT-FAILED: and N more`, once the
#: `_suite_result_max_node_ids()` cap is hit) that this pattern's
#: `\((failed|error)\)` requirement deliberately does NOT match, so that
#: continuation is silently skipped rather than misread as a node id.
_SUITE_RESULT_FAILED_LINE = re.compile(
    _GH_LOG_TIMESTAMP_PREFIX
    + r"SUITE-RESULT-FAILED: (\S+) \((failed|error)\)(?:\s+--\s+(.*))?\s*$",
    re.MULTILINE,
)

#: Digits, hex blobs, and quoted literals -- stripped from a failure's
#: reason line so two failures differing only in a specific value (an id,
#: a path, a timestamp) still cluster under the same signature.
_VALUE_TOKEN = re.compile(r"0x[0-9a-fA-F]+|'[^']*'|\"[^\"]*\"|\d+")


# frob:doc docs/modules/ci_report.md#data-models
class TestFailure(BaseModel):
    """One `FAILED`/`ERROR` line pytest's own short summary named --
    never inferred positionally (see module docstring)."""

    model_config = ConfigDict(frozen=True)
    #: Not a pytest test class -- silences pytest's `Test*`-prefix
    #: collection heuristic, which would otherwise warn on this model
    #: (it has an `__init__`) every time a test file imports it.
    __test__ = False

    node_id: str
    kind: str  # "failed" | "error"
    reason: str
    signature: str


# frob:doc docs/modules/ci_report.md#data-models
class FailureCluster(BaseModel):
    """Every `TestFailure` in one job sharing the same `signature`,
    grouped so the operator reads one root cause plus its member node
    ids instead of a flat list to re-cluster by hand."""

    model_config = ConfigDict(frozen=True)

    signature: str
    node_ids: tuple[str, ...]
    sample_reason: str


# frob:doc docs/modules/ci_report.md#data-models
class JobReport(BaseModel):
    """One job's structured outcome: `outcome` is the honest tri-state
    this module exists to add -- `"clean"` (pytest's own summary says
    zero failed/errored), `"failures"` (named failures below), or
    `"not_recoverable"` (pytest's summary was never observed in this log
    -- cancelled run, killed worker, or any other reason the log ends
    before a result count line -- NEVER collapsed to an empty
    `failures` tuple, which would silently read as a clean run)."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    name: str
    conclusion: str
    outcome: str
    failures: tuple[TestFailure, ...]
    clusters: tuple[FailureCluster, ...]
    truncated: bool


# frob:doc docs/modules/ci_report.md#data-models
class RunReport(BaseModel):
    """A whole run's structured report: one `JobReport` per job `gh`
    reported for it. A job whose log could not be retrieved AT ALL (a
    `GhError` from `frob.ghio.job_log` itself, e.g. `NotFound`/
    `RunInProgress`) is still represented -- as a `not_recoverable`
    `JobReport` naming the reason in `failures` being empty and
    `outcome` never silently omitted from the run's job list."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    conclusion: str
    jobs: tuple[JobReport, ...]


def _signature(kind: str, reason: str) -> str:
    """Collapse one failure's `(kind, reason)` to a clustering key:
    value-stripped so failures differing only in a specific literal
    still cluster together (module docstring's own clustering note)."""
    if not reason:
        return f"{kind}:<no reason captured>"
    normalized = _VALUE_TOKEN.sub("#", reason.strip())
    # Keep only the exception-type-ish head (before the first colon, if
    # any) plus a bounded slice of the rest -- long multi-line reasons
    # (a full assertion diff) would otherwise make every failure its own
    # singleton cluster, defeating the point of clustering at all.
    head = normalized.split(":", 1)
    exc_type = head[0].strip()
    rest = head[1].strip()[:80] if len(head) > 1 else ""
    return f"{kind}:{exc_type}:{rest}" if rest else f"{kind}:{exc_type}"


# frob:ticket T-5477
def _parse_suite_result_log(
    text: str, *, truncated: bool
) -> tuple[str, tuple[TestFailure, ...]] | None:
    """T-5477: `parse_pytest_log`'s SUITE-RESULT half -- this repo's OWN
    `tests/conftest.py` xdist summary (`_SUITE_RESULT_LINE`/
    `_SUITE_RESULT_FAILED_LINE`, module docstring's WHY NOT POSITIONAL
    section explains why this repo emits it instead of trusting vanilla
    pytest's positional dot-stream). `None` when no `_SUITE_RESULT_LINE`
    is present at all, telling the caller to fall back to the vanilla-
    pytest path unchanged -- this function NEVER returns `None` once a
    real `SUITE-RESULT:` line is found, so a repo that emits BOTH this
    line and (inside some nested subprocess-captured output, e.g.
    `tests/system/test_scaffold_dx.py`'s generated-project pytest run)
    vanilla `FAILED`/summary text never has that nested text mistaken for
    the OUTER run's own result -- SUITE-RESULT, when present, is always
    authoritative over vanilla parsing, never merely a tie-breaker.

    Takes the LAST `_SUITE_RESULT_LINE` match (a partial/interrupted run
    can write more than one across retries; the last is the most recent
    state) and every `_SUITE_RESULT_FAILED_LINE` in the text (which may
    appear before OR after that line, so this is a full-text scan, not
    scoped to follow the chosen result line)."""
    result_matches = list(_SUITE_RESULT_LINE.finditer(text))
    if not result_matches:
        return None
    last = result_matches[-1]
    failed_count = int(last.group(3))
    failures = tuple(
        TestFailure(
            node_id=m.group(1),
            kind=m.group(2).lower(),
            reason=(m.group(3) or "").strip(),
            signature=_signature(m.group(2).lower(), (m.group(3) or "").strip()),
        )
        for m in _SUITE_RESULT_FAILED_LINE.finditer(text)
    )
    if failures:
        return "failures", failures
    if failed_count > 0:
        # The line claims failures but no SUITE-RESULT-FAILED line
        # matched (e.g. every one fell past the _suite_result_max_
        # node_ids() cap and only an "and N more" continuation
        # survived) -- honest not_recoverable, never a silent "clean"
        # for a run that named failures it could not enumerate.
        _log.warning(
            "ci_report: SUITE-RESULT claims %d failure(s) but no "
            "SUITE-RESULT-FAILED node id matched -- not_recoverable, "
            "not clean",
            failed_count,
        )
        return "not_recoverable", ()
    if truncated:
        _log.warning(
            "ci_report: SUITE-RESULT line present and clean but log is "
            "truncated -- not_recoverable, not clean"
        )
        return "not_recoverable", ()
    return "clean", ()


# frob:doc docs/modules/ci_report.md#public-api
# tests/test_ci_report.py::TestParsePytestLog.test_truncated_with_no_evidence_is_not_recoverable  # noqa: E501
def parse_pytest_log(
    text: str, *, truncated: bool
) -> tuple[str, tuple[TestFailure, ...]]:
    """Parse raw pytest stdout/stderr `text` into `(outcome, failures)`.
    `outcome` is one of `"clean"`, `"failures"`, `"not_recoverable"` (see
    `JobReport.outcome`). Never returns `("clean", ())` when `truncated`
    is `True` and no `_RESULT_LINE` was actually observed -- a truncated
    log's silence is `"not_recoverable"`, never read as a clean run
    (module docstring's own doctrine, matching `frob.ghio.JobLog`'s own
    `truncated` field this function is the direct consumer of).

    T-5477: tries `_parse_suite_result_log` FIRST -- this repo's own
    `tests/conftest.py` xdist summary is authoritative whenever present
    (see that function's own docstring for why nested vanilla-pytest text
    from a subprocess-under-test must never override it); only when no
    `SUITE-RESULT:` line exists at all does this fall through to the
    vanilla-pytest `_RESULT_LINE`/`_SUMMARY_LINE` path unchanged."""
    suite_result = _parse_suite_result_log(text, truncated=truncated)
    if suite_result is not None:
        return suite_result

    result_matches = list(_RESULT_LINE.finditer(text))
    if not result_matches:
        _log.info(
            "ci_report: parse_pytest_log: no result line found (truncated=%s) "
            "-- reporting not_recoverable, never zero failures",
            truncated,
        )
        return "not_recoverable", ()

    failures = tuple(
        TestFailure(
            node_id=m.group(2),
            kind=m.group(1).lower(),
            reason=(m.group(3) or "").strip(),
            signature=_signature(m.group(1).lower(), (m.group(3) or "").strip()),
        )
        for m in _SUMMARY_LINE.finditer(text)
    )

    if not failures:
        if truncated:
            # The result line claims a clean end, but this run was
            # cancelled -- do not trust an apparently-clean summary that
            # arrived from a truncated log; treat as unrecoverable rather
            # than silently reporting zero failures for a run that never
            # legitimately finished.
            _log.warning(
                "ci_report: parse_pytest_log: result line present but log is "
                "truncated and named zero failures -- not_recoverable, not clean"
            )
            return "not_recoverable", ()
        return "clean", ()
    return "failures", failures


def _cluster(failures: tuple[TestFailure, ...]) -> tuple[FailureCluster, ...]:
    """Group `failures` by `signature`, preserving first-seen order."""
    order: list[str] = []
    by_sig: dict[str, list[TestFailure]] = {}
    for failure in failures:
        if failure.signature not in by_sig:
            order.append(failure.signature)
            by_sig[failure.signature] = []
        by_sig[failure.signature].append(failure)
    return tuple(
        FailureCluster(
            signature=sig,
            node_ids=tuple(f.node_id for f in by_sig[sig]),
            sample_reason=by_sig[sig][0].reason,
        )
        for sig in order
    )


# frob:doc docs/modules/ci_report.md#public-api
def build_job_report(
    root: Path, run_id: str, job: JobSummary
) -> Result[JobReport, GhError]:
    """`frob.ghio.job_log` for `job`, parsed via `parse_pytest_log` and
    clustered via `_cluster`. Propagates `Err(GhError...)` for a log that
    could not be retrieved AT ALL (environment failures, or the named
    `EmptyLog` outcome) -- `build_run_report` is the caller that decides
    whether to degrade a single job's failure to a `not_recoverable`
    `JobReport` rather than abort the whole run."""
    log_result = job_log(root, run_id, job.job_id)
    if log_result.is_err:
        return Err(log_result.danger_err)
    log = log_result.danger_ok
    outcome, failures = parse_pytest_log(log.text, truncated=log.truncated)
    return Ok(
        JobReport(
            job_id=job.job_id,
            name=job.name,
            conclusion=job.conclusion,
            outcome=outcome,
            failures=failures,
            clusters=_cluster(failures),
            truncated=log.truncated,
        )
    )


# frob:doc docs/modules/ci_report.md#public-api
# tests/test_ci_report.py::TestBuildRunReport.test_one_job_log_failure_degrades_not_abo\
# rts
def build_run_report(root: Path, run_id: str) -> Result[RunReport, GhError]:
    """`frob.ghio.view_run` for `run_id`, then `build_job_report` for
    every job it names. A per-job `Err` (job log unavailable for a
    reason specific to that job -- `NotFound`, `RunInProgress`,
    `EmptyLog`) degrades to a `not_recoverable` `JobReport` for that job
    alone rather than aborting the whole run's report -- one job's log
    being unavailable says nothing about whether the OTHER jobs' reports
    are trustworthy. A run-level failure (`view_run` itself erring --
    `NotFound`, auth/network/rate-limit) propagates as `Err`, since there
    is nothing to report at all in that case."""
    detail_result = view_run(root, run_id)
    if detail_result.is_err:
        return Err(detail_result.danger_err)
    detail = detail_result.danger_ok

    jobs: list[JobReport] = []
    for job in detail.jobs:
        report_result = build_job_report(root, run_id, job)
        if report_result.is_err:
            _log.warning(
                "ci_report: build_run_report: job %s (%s) log unavailable (%s) "
                "-- degrading to not_recoverable, not aborting the run report",
                job.job_id,
                job.name,
                report_result.danger_err,
            )
            jobs.append(
                JobReport(
                    job_id=job.job_id,
                    name=job.name,
                    conclusion=job.conclusion,
                    outcome="not_recoverable",
                    failures=(),
                    clusters=(),
                    truncated=False,
                )
            )
        else:
            jobs.append(report_result.danger_ok)

    return Ok(RunReport(run_id=run_id, conclusion=detail.conclusion, jobs=tuple(jobs)))


__all__ = [
    "FailureCluster",
    "JobReport",
    "RunReport",
    "TestFailure",
    "build_job_report",
    "build_run_report",
    "parse_pytest_log",
]
