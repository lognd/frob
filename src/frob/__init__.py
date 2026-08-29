"""frob -- the enforcement layer for agentic development (docs/index.md).

Package-level re-exports: `frob.gitio`'s process/diff primitives,
`frob.excludes`'s scan-exclusion helpers, and `frob.doctor`'s
derived-state diagnostics are used across nearly every sub-package, so
they are surfaced here (T-0362, T-0599). `frob.__main__.main` is
deliberately NOT re-exported: it is reached by `pyproject.toml`'s
`[project.scripts]` entry (`frob.__main__:main`), a direct module:function
path that bypasses this file, and re-exporting it here would force every
`import frob.<anything>` in the codebase to pay for building the full CLI
dispatch table at import time.
"""

from __future__ import annotations

# T-2363: this file is the representative (lowest-sorted) node of a live,
# 160-node CYCLE001 import cycle spanning frob.serve/frob.stats/frob.tickets/
# frob.testing/frob.app. Measured directly (frob.check._python._build_import_
# graph + frob.cycle.graph.find_cycles against the real src/ tree, not
# guessed).
#
# CORRECTED PREMISE (T-2667, superseding T-2363's original claim below):
# the owner picked candidate 2 (stats/__init__.py's `from frob.tickets
# import TicketQueue, TicketState, load_queue`) and it landed -- but the
# SCC did NOT collapse. Re-measurement after that land shows it is still
# 160 nodes, still closed, now entirely by edges that never route through
# frob.stats: at least five of them (serve/_tools.py:24 and :606,
# tickets/_land.py, testing/_coverage_wait.py:163, and several
# app/_daemon_proxy.py sites), full edge-by-edge breakdown in T-2667's
# ticket body. T-2363's original claim -- that cutting only the smallest-
# looking edge (stats -> tickets) would not collapse it -- is confirmed,
# but its assumption that a SECOND cut would suffice was wrong; a second
# cut has now also been measured insufficient. Of the five remaining
# edges, exactly ONE (serve/_tools.py:24) is a top-level import that could
# actually deadlock at import time -- the other four are function-local
# and only make this graph-level SCC finding fire. Real decomposition
# means choosing among these edges to invert or extract, each a different
# package's public-surface change; per the repo owner's explicit standing
# instruction ("if that decision is not obvious, stop and tell me rather
# than guessing; I would rather own that call than have it made
# implicitly"), that pick is deferred to a dedicated post-1.0.0 epic
# rather than made unilaterally here.
#
# This is TRACKED DEBT, not a permanent exception: the cycle is real, it
# is not a release blocker (not among the 213 CI-hard release-blocking
# errors), and it WILL be fixed by the epic named below.
# frob:debt CYCLE001 reason="160-node serve/tickets/testing/app SCC, corrected and \
# re-measured by T-2667 after candidate 2 (stats->tickets) landed without collapsing \
# it; real decomposition deferred to a dedicated post-1.0.0 epic, not a release \
# blocker" ticket="T-3350"
from frob.ci_report import (
    FailureCluster,
    JobReport,
    RunReport,
    TestFailure,
    build_job_report,
    build_run_report,
    parse_pytest_log,
)
from frob.ci_validity import (
    JobValidity,
    RunValidity,
    TestValidity,
    Validity,
    ValidityError,
    classify_test,
    job_validity,
    run_validity,
    validity_for_run_head_sha,
)
from frob.doctor import (
    DerivedArtifactStatus,
    DoctorReport,
    GlobalBinarySkew,
    LiveLandProcess,
    MalformedTicketEdge,
    NativeExtensionStatus,
    VenvShimDrift,
    global_binary_skew,
    native_degrade_warning,
    run_diagnosis,
    scan_live_land_processes,
    scan_malformed_ticket_edges,
    scan_stale_ticket_leases,
    scan_venv_shims,
    verify_derived_state,
)
from frob.excludes import (
    is_excluded,
    is_skipped_dir,
    is_test_file,
    iter_files,
    load_exclude_globs,
    walk_pruned,
)
from frob.findings import (
    DebtEntry,
    Severity,
    Violation,
    WaiverRef,
)
from frob.ghio import (
    GhEnvironment,
    GhError,
    JobLog,
    JobSummary,
    RunDetail,
    RunSummary,
    job_log,
    list_runs,
    preflight,
    view_run,
)
from frob.gitio import (
    Diff,
    GitError,
    Hunk,
    ProcResult,
    SpawnRecorder,
    commit_diff,
    common_dir_and_branch,
    current_branch,
    excerpt,
    git_common_dir,
    recent_commits,
    repo_root,
    reset_common_dir_cache,
    run_argv,
    spawn_recorder,
    working_diff,
)
from frob.repo_meta import (
    declared_min_frob_version,
    is_frob_own_repo,
    load_arch_config,
    stale_binary_warning,
    stale_install_warning,
)
from frob.tomlio import read_toml_lenient
from frob.yamlio import fast_yaml_loader

__all__ = [
    "DebtEntry",
    "DerivedArtifactStatus",
    "Diff",
    "DoctorReport",
    "FailureCluster",
    "GhEnvironment",
    "GhError",
    "GitError",
    "GlobalBinarySkew",
    "Hunk",
    "JobLog",
    "JobReport",
    "JobSummary",
    "JobValidity",
    "LiveLandProcess",
    "MalformedTicketEdge",
    "NativeExtensionStatus",
    "ProcResult",
    "RunDetail",
    "RunReport",
    "RunSummary",
    "RunValidity",
    "Severity",
    "SpawnRecorder",
    "TestFailure",
    "TestValidity",
    "Validity",
    "ValidityError",
    "VenvShimDrift",
    "Violation",
    "WaiverRef",
    "build_job_report",
    "build_run_report",
    "classify_test",
    "commit_diff",
    "common_dir_and_branch",
    "current_branch",
    "declared_min_frob_version",
    "excerpt",
    "git_common_dir",
    "global_binary_skew",
    "is_excluded",
    "is_frob_own_repo",
    "is_skipped_dir",
    "is_test_file",
    "iter_files",
    "job_log",
    "job_validity",
    "list_runs",
    "load_arch_config",
    "load_exclude_globs",
    "native_degrade_warning",
    "parse_pytest_log",
    "preflight",
    "read_toml_lenient",
    "recent_commits",
    "repo_root",
    "reset_common_dir_cache",
    "run_argv",
    "run_diagnosis",
    "run_validity",
    "fast_yaml_loader",
    "stale_binary_warning",
    "stale_install_warning",
    "scan_live_land_processes",
    "scan_malformed_ticket_edges",
    "scan_stale_ticket_leases",
    "scan_venv_shims",
    "spawn_recorder",
    "validity_for_run_head_sha",
    "verify_derived_state",
    "view_run",
    "walk_pruned",
    "working_diff",
]
