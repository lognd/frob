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
    NativeExtensionStatus,
    run_diagnosis,
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
    common_dir_and_branch,
    current_branch,
    git_common_dir,
    repo_root,
    reset_common_dir_cache,
    run_argv,
    spawn_recorder,
    working_diff,
)

__all__ = [
    "DerivedArtifactStatus",
    "Diff",
    "DoctorReport",
    "GitError",
    "Hunk",
    "NativeExtensionStatus",
    "ProcResult",
    "SpawnRecorder",
    "common_dir_and_branch",
    "current_branch",
    "git_common_dir",
    "is_excluded",
    "is_skipped_dir",
    "is_test_file",
    "iter_files",
    "load_exclude_globs",
    "repo_root",
    "reset_common_dir_cache",
    "run_argv",
    "run_diagnosis",
    "spawn_recorder",
    "verify_derived_state",
    "walk_pruned",
    "working_diff",
]
