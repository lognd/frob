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

from frob.doctor import (
    DerivedArtifactStatus,
    DoctorReport,
    GlobalBinarySkew,
    LiveLandProcess,
    MalformedTicketEdge,
    NativeExtensionStatus,
    VenvShimDrift,
    global_binary_skew,
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
from frob.tomlio import read_toml_lenient
from frob.yaml_io import fast_yaml_loader

__all__ = [
    "DerivedArtifactStatus",
    "Diff",
    "DoctorReport",
    "GitError",
    "GlobalBinarySkew",
    "Hunk",
    "LiveLandProcess",
    "MalformedTicketEdge",
    "NativeExtensionStatus",
    "ProcResult",
    "SpawnRecorder",
    "VenvShimDrift",
    "commit_diff",
    "common_dir_and_branch",
    "current_branch",
    "excerpt",
    "git_common_dir",
    "global_binary_skew",
    "is_excluded",
    "is_skipped_dir",
    "is_test_file",
    "iter_files",
    "load_exclude_globs",
    "read_toml_lenient",
    "recent_commits",
    "repo_root",
    "reset_common_dir_cache",
    "run_argv",
    "run_diagnosis",
    "fast_yaml_loader",
    "scan_live_land_processes",
    "scan_malformed_ticket_edges",
    "scan_stale_ticket_leases",
    "scan_venv_shims",
    "spawn_recorder",
    "verify_derived_state",
    "walk_pruned",
    "working_diff",
]
