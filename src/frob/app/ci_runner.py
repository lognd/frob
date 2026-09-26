"""CLI wiring for `frob ci report <run-id>` (T-2982's command surface,
CI-1): the operator-facing wrapper over `frob.ci_report.build_run_report`.

Before this leaf, `build_run_report`/`build_job_report` existed as a
library-only seam (`frob.ci_report`'s own module docstring) -- an operator
chasing a CI failure still had to open a Python shell or write a one-off
script to call them. This module is the porcelain: it renders the SAME
`RunReport` `build_run_report` returns (parity is this leaf's own control,
`tests/unit/cli/test_ci_report.py`), grouped per job/platform, with the
cross-platform diff (shared vs platform-only failure signatures) and the
per-file cluster grouping `build_run_report`'s clustering step already
computed -- this module adds no new clustering logic of its own, only
rendering.

ERROR DISCIPLINE: every `GhError` `build_run_report` can hand back is
rendered as its own named `str()` (which already carries the remedy, see
`GhError`'s docstring) and a non-zero exit -- never a traceback, never an
empty report standing in for an error.
"""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.ci_report import FailureCluster, JobReport, RunReport, build_run_report
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)


def _resolve_root(cfg: AppConfig) -> Path:
    """`cfg.ci_path` if given, else the current directory, resolved --
    mirrors `frob.app.verify_runner._resolve_root`'s own precedent."""
    return (cfg.ci_path or Path(".")).resolve()


def _renderer(cfg: AppConfig) -> Renderer:
    """The one `Renderer` `frob ci report`'s human-facing output prints
    through (RENDER001, `frob verify`'s own T-0448 precedent)."""
    return Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )


def _cross_platform_diff(
    jobs: tuple[JobReport, ...],
) -> tuple[frozenset[str], dict[str, frozenset[str]]]:
    """Split every job's `FailureCluster.signature` set into the
    signatures SHARED across every job that has at least one failure, and
    the signatures unique to one job -- the exact aggregation this ticket
    exists to stop an operator doing by hand (`frob.ci_report`'s own
    module docstring names the incident: a shared cluster mis-attributed
    as platform-specific because one job's log was silently unusable).
    Jobs with zero failures contribute an empty signature set and are
    excluded from the shared-signature intersection so a clean job never
    forces the shared set to empty."""
    per_job: dict[str, frozenset[str]] = {
        job.name: frozenset(c.signature for c in job.clusters)
        for job in jobs
        if job.clusters
    }
    if not per_job:
        return frozenset(), {}
    shared = frozenset.intersection(*per_job.values())
    only: dict[str, frozenset[str]] = {
        name: sigs - shared for name, sigs in per_job.items()
    }
    return shared, only


def _clusters_by_file(job: JobReport) -> dict[str, list[FailureCluster]]:
    """Group one job's `FailureCluster`s by the source file their first
    node id names (`node_id` up to the first `::`) -- the per-file view
    this leaf's brief asks for, built entirely from `build_run_report`'s
    own clustering output, no new signature logic."""
    by_file: dict[str, list[FailureCluster]] = {}
    for cluster in job.clusters:
        first_node = cluster.node_ids[0] if cluster.node_ids else ""
        file = first_node.split("::", 1)[0] or "<unknown file>"
        by_file.setdefault(file, []).append(cluster)
    return by_file


def _print_report_human(r: Renderer, report: RunReport) -> None:
    """Render `report` (per job/platform failures and failing steps, the
    cross-platform diff, and the per-file cluster grouping) as the human-
    readable form of `frob ci report`. A fully green run (every job
    `outcome == "clean"`) prints an explicit "no failures" line -- never
    silence, which would be indistinguishable from a report that failed
    to run at all (the silent-zero doctrine this drive applies
    everywhere else, `frob.ci_report`'s own module docstring)."""
    r.line(f"run {report.run_id}: conclusion={report.conclusion}")
    any_failures = False
    for job in report.jobs:
        r.line(f"job {job.name} ({job.job_id}): outcome={job.outcome}")
        if job.outcome == "not_recoverable":
            r.line("  (log unavailable or truncated before a result -- not clean)")
            continue
        if not job.failures:
            r.line("  no failures")
            continue
        any_failures = True
        for failure in job.failures:
            r.line(f"  {failure.kind}: {failure.node_id}")
        by_file = _clusters_by_file(job)
        if by_file:
            r.line("  clusters by file:")
            for file, clusters in by_file.items():
                r.line(f"    {file}:")
                for cluster in clusters:
                    r.line(
                        f"      [{cluster.signature}] "
                        f"{len(cluster.node_ids)} node id(s)"
                    )

    shared, only = _cross_platform_diff(report.jobs)
    if shared or only:
        r.line("cross-platform diff:")
        if shared:
            r.line(f"  shared: {sorted(shared)}")
        for name, sigs in only.items():
            if sigs:
                r.line(f"  {name}-only: {sorted(sigs)}")

    if not any_failures and all(job.outcome == "clean" for job in report.jobs):
        r.line("no failures across any job")


# frob:doc docs/modules/ci_report.md#public-api
# tests/unit/cli/test_ci_report.py::TestCiReportParity::test_parity_with_build_run_r\
# eport  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob ci report <run-id>`: build a `RunReport` via
    `frob.ci_report.build_run_report` and render it -- per job/platform
    failing test node ids and failing steps, the cross-platform diff, and
    the per-file cluster grouping. `--json` prints the SAME `RunReport`
    `build_run_report` returns via `model_dump_json`, so a scripted
    caller gets the identical structured record a human's rendering is
    built from (this leaf's own parity control). A `GhError` from
    `build_run_report` renders as its own named message (never a
    traceback) and exits non-zero."""
    if cfg.ci_command != "report":
        _log.error("frob ci requires a subcommand: report")
        sys.exit(1)
    if not cfg.ci_run_id:
        _log.error("frob ci report requires a run id")
        sys.exit(1)

    root = _resolve_root(cfg)
    result = build_run_report(root, cfg.ci_run_id)
    r = _renderer(cfg)
    if result.is_err:
        error = result.danger_err
        _log.error("ci report: %s", error)
        r.line(f"error: {error}")
        sys.exit(1)

    report = result.danger_ok
    if cfg.ci_json:
        r.line(report.model_dump_json(indent=2))
    else:
        _print_report_human(r, report)
