"""frob-owned native crate build (T-0864/T-0735 child 1): `maturin develop`
per declared `[[native]]` rust crate, sharing one git-common-dir-keyed
`CARGO_TARGET_DIR` across every linked worktree of a clone (T-0732's
verified design) instead of each worktree recompiling into its own cargo
target dir. `frob.app.natives_runner` is the CLI wiring; this package is the
library surface it (and any other caller, e.g. a future scaffold/doctor
integration) calls into.
"""

from __future__ import annotations

from frob.natives._build import (
    CARGO_CACHE_DIRNAME,
    BuildReport,
    CrateBuildResult,
    NativesError,
    build_natives,
)

__all__ = [
    "CARGO_CACHE_DIRNAME",
    "BuildReport",
    "CrateBuildResult",
    "NativesError",
    "build_natives",
]
