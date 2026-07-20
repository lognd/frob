"""frob -- the enforcement layer for agentic development (docs/index.md).

Package-level re-exports: `frob.gitio`'s process/diff primitives and
`frob.excludes`'s scan-exclusion helpers are used across nearly every
sub-package, so they are surfaced here (T-0362). `frob.__main__.main` is
deliberately NOT re-exported: it is reached by `pyproject.toml`'s
`[project.scripts]` entry (`frob.__main__:main`), a direct module:function
path that bypasses this file, and re-exporting it here would force every
`import frob.<anything>` in the codebase to pay for building the full CLI
dispatch table at import time.
"""

from __future__ import annotations

from frob.excludes import is_excluded, is_skipped_dir, is_test_file, load_exclude_globs
from frob.gitio import (
    Diff,
    GitError,
    Hunk,
    ProcResult,
    current_branch,
    repo_root,
    run_argv,
    working_diff,
)

__all__ = [
    "Diff",
    "GitError",
    "Hunk",
    "ProcResult",
    "current_branch",
    "is_excluded",
    "is_skipped_dir",
    "is_test_file",
    "load_exclude_globs",
    "repo_root",
    "run_argv",
    "working_diff",
]
