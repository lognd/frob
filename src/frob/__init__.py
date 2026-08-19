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
# guessed): the cycle is bigger than T-2358's original 5-edge description --
# serve/_tools.py has a SECOND, independent module-level edge into
# frob.tickets (`from frob.tickets import doable, load_queue`) that bypasses
# frob.stats entirely, so cutting only the smallest-looking edge (stats ->
# tickets) would not collapse it. Untangling this for real means choosing ONE
# of at least five candidate edges to invert or extract, each a different
# package's public-surface change (full edge-by-edge breakdown in T-draft-
# 4a262fb2's ticket body). Per the repo owner's explicit standing instruction
# ("if that decision is not obvious, stop and tell me rather than guessing; I
# would rather own that call than have it made implicitly"), that pick is
# left to T-2583 rather than made unilaterally here.
#
# This is a DECLARATION, not a suppression: `# frob:waive CYCLE001` was
# tried here and does nothing -- `frob check --only cycle`'s frob-cycle tool
# never consults the waiver pipeline at all (T-2584, filed
# separately since fixing it means editing frob.check/frob.gates, outside
# this file's owning ticket's scope). CYCLE001 stays a live, unwaived error
# on `frob check` until either the wiring gap or the real cycle is fixed.
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
from frob.repo_meta import (
    declared_min_frob_version,
    load_arch_config,
    stale_binary_warning,
    stale_install_warning,
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
    "declared_min_frob_version",
    "excerpt",
    "git_common_dir",
    "global_binary_skew",
    "is_excluded",
    "is_skipped_dir",
    "is_test_file",
    "iter_files",
    "load_arch_config",
    "load_exclude_globs",
    "read_toml_lenient",
    "recent_commits",
    "repo_root",
    "reset_common_dir_cache",
    "run_argv",
    "run_diagnosis",
    "fast_yaml_loader",
    "stale_binary_warning",
    "stale_install_warning",
    "scan_live_land_processes",
    "scan_malformed_ticket_edges",
    "scan_stale_ticket_leases",
    "scan_venv_shims",
    "spawn_recorder",
    "verify_derived_state",
    "walk_pruned",
    "working_diff",
]
