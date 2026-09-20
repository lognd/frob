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

# see T-3350 for the history behind this
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

# frob:ticket T-3443
# frob:tests tests/unit/test_exports.py::TestFrobExportsPolicyResidue.test_all_nine_packages_report_zero_missing_symbols kind="unit"  # noqa: E501
from frob.doctor import (
    DerivedArtifactStatus,
    DoctorReport,
    ExternalToolStatus,
    GlobalBinarySkew,
    ImportSourceStatus,
    LiveLandProcess,
    MalformedTicketEdge,
    NativeExtensionStatus,
    ToolCategory,
    UnityEditorStatus,
    VenvShimDrift,
    global_binary_skew,
    native_degrade_warning,
    run_diagnosis,
    scan_external_tools,
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
    "ExternalToolStatus",
    "FailureCluster",
    "GhEnvironment",
    "GhError",
    "GitError",
    "GlobalBinarySkew",
    "Hunk",
    "ImportSourceStatus",
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
    "ToolCategory",
    "UnityEditorStatus",
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
    "scan_external_tools",
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
