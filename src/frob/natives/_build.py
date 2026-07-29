"""Core `maturin develop`-per-declared-crate build logic (T-0864).

User directive 2026-07-22 (tickets.md T-0732 note): the shared
`CARGO_TARGET_DIR` fix used to live in THIS repo's `Makefile` -- the wrong
layer, since every sibling repo that declares `[[native]]` crates would
need to hand-copy the same recipe. This module is the fix moved to the
right layer: read `frob.toml`'s `[[native]]` entries (`frob.testing.
_runners.load_natives`, T-0333's existing parser -- not reimplemented
here) and, for each declared RUST native with a matching crate directory
on disk, run `maturin develop --uv --release` against it with
`CARGO_TARGET_DIR` pointed at a directory keyed off the clone's
git-common-dir (`frob.gitio.git_common_dir`) rather than the calling
worktree's own path. Every worktree of the same clone therefore shares one
compiled cargo target dir; cargo's own file locking (not a mutex this
module adds) makes concurrent builds from separate worktrees safe -- this
is T-0732's verified design, moved here from the Makefile recipe it used
to live in.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.gitio import git_common_dir
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.testing._models import NativeSpec
from frob.testing._runners import load_natives

_log = get_logger(__name__)

#: T-0732: the shared cargo build-artifact cache dirname, created directly
#: under the clone's git-common-dir (NOT under any one worktree) so every
#: linked worktree of the same clone resolves to the identical path.
# frob:doc docs/modules/cli.md#frob-natives-build-t-0864
CARGO_CACHE_DIRNAME = "frob-cargo-target-cache"


# frob:doc docs/modules/cli.md#frob-natives-build-t-0864
class NativesError(ErrorSet):
    """Failure values `build_natives` can return."""

    NoNatives = "no [[native]] entries declared in frob.toml"
    LoadFailed = "frob.toml [[native]] table failed to parse"
    NotAGitRepo = "root is not inside a git repository (git-common-dir lookup failed)"
    ExecDisabled = "exec kill switch (FROB_DISABLE_EXEC) refused to spawn maturin"


# frob:doc docs/modules/cli.md#frob-natives-build-t-0864
class CrateBuildResult(BaseModel):
    """One declared native's `maturin develop` outcome: which crate
    directory built, the process's exit code, and its captured output so a
    failing build's diagnostics survive past the subprocess call."""

    model_config = {}

    name: str
    crate_dir: str
    returncode: int
    stdout: str
    stderr: str

    # frob:doc docs/modules/cli.md#frob-natives-build-t-0864
    @property
    def ok(self) -> bool:
        """True when `maturin develop` exited zero for this crate."""
        return self.returncode == 0


# frob:doc docs/modules/cli.md#frob-natives-build-t-0864
class BuildReport(BaseModel):
    """The full `build_natives` run: one `CrateBuildResult` per attempted
    rust native, plus the shared `CARGO_TARGET_DIR` every crate built
    against."""

    model_config = {}

    cargo_target_dir: Path
    results: list[CrateBuildResult] = []

    # frob:doc docs/modules/cli.md#frob-natives-build-t-0864
    @property
    def ok(self) -> bool:
        """True when every attempted crate in this report built cleanly
        (vacuously true if no rust native had a matching crate directory)."""
        return all(r.ok for r in self.results)


def _crate_dir_for(root: Path, spec: NativeSpec) -> Path | None:
    """The rust crate directory backing `spec`, via the underscore/hyphen
    convention every native crate in this repo follows (`strata_core`'s
    python import name <-> `strata-core/Cargo.toml`'s crate directory --
    the same convention `frob.strata._native_staleness._source_dir_for`
    already checks against a fixed allowlist for staleness detection).
    Checked directly against the filesystem here (not the staleness
    module's allowlist) since this IS the ground-truth build step that
    allowlist exists to detect drift against -- a repo just needs to add a
    new `[[native]]` entry plus a matching crate directory for this to pick
    it up, no second registration point. `None` (a silent, logged skip) when
    no matching crate directory exists, e.g. a non-rust native or a
    declared native this checkout does not vendor the crate for."""
    candidate = root / spec.name.replace("_", "-")
    if (candidate / "Cargo.toml").is_file():
        return candidate
    _log.debug(
        "build_natives: no crate directory for native %s under %s", spec.name, root
    )
    return None


# frob:ticket T-0864
# frob:doc docs/modules/cli.md#frob-natives-build-t-0864
# frob:tests \
# tests/unit/test_natives_build.py::TestBuildNatives.test_builds_declared_rust_natives
def build_natives(root: Path) -> Result[BuildReport, NativesError]:
    """Build every declared rust `[[native]]` crate via `maturin develop
    --uv --release`, all sharing one `CARGO_TARGET_DIR` keyed off `root`'s
    git-common-dir (T-0732's verified design -- see this module's
    docstring). Non-rust natives and rust natives with no matching crate
    directory on disk are silently skipped (logged at DEBUG), matching
    `load_natives`'s own best-effort posture for entries this checkout does
    not fully vendor. `Err` is reserved for an infrastructure-level failure
    that stops the whole run before any crate is attempted (no declared
    natives, an unparseable `frob.toml`, `root` not being a git checkout,
    or the exec kill switch refusing to spawn); a per-crate build failure
    is NOT an `Err` -- it is recorded in the returned `Ok(BuildReport)`,
    whose own `.ok` property is `False` when any attempted crate failed,
    so a caller (e.g. `frob.app.natives_runner.run`) can print each
    failing crate's captured output before exiting non-zero."""
    loaded = load_natives(root)
    if loaded.is_err:
        _log.error("build_natives: could not load [[native]] entries under %s", root)
        return Err(NativesError.LoadFailed)
    specs = loaded.danger_ok
    if not specs:
        _log.info("build_natives: no [[native]] entries declared under %s", root)
        return Err(NativesError.NoNatives)

    common_dir = git_common_dir(root)
    if common_dir.is_err:
        _log.error("build_natives: %s is not inside a git repository", root)
        return Err(NativesError.NotAGitRepo)
    cargo_target_dir = common_dir.danger_ok / CARGO_CACHE_DIRNAME

    results: list[CrateBuildResult] = []
    for spec in specs:
        built = _build_one_crate(root, spec, cargo_target_dir)
        if built.is_err:
            return Err(built.danger_err)
        if built.danger_ok is not None:
            results.append(built.danger_ok)

    return Ok(BuildReport(cargo_target_dir=cargo_target_dir, results=results))


# frob:ticket T-0979
def _resolve_buildable_crate(root: Path, spec) -> Path | None:  # noqa: ANN001
    """`_build_one_crate`'s skip-check half: a non-rust native, or a rust
    native with no matching crate directory on disk, is silently skipped
    (logged at DEBUG) -- matching `build_natives`'s documented best-effort
    posture for entries this checkout does not fully vendor. Returns the
    resolved crate directory for anything else."""
    if spec.language != "rust":
        _log.debug(
            "build_natives: skipping non-rust native %s (language=%r)",
            spec.name,
            spec.language,
        )
        return None
    return _crate_dir_for(root, spec)


# frob:ticket T-0979
# frob:waive ARCH103 reason="T-0979: _resolve_buildable_crate (above) already \
# extracted the separable skip-check concern; what remains here is a single \
# guarded-subprocess run-and-report job (spawn maturin, classify its outcome, log each \
# transition) -- the same cohesive shape T-0977 already waived for this module's \
# sibling wrappers (_cargo_env, _run_ctest_list) and frob.exec's _run_npx. Splitting \
# the log/branch pairs further would add indirection, not cohesion."
# frob:waive EXHAUST001 reason="T-1062: leaked Unknown traces to \
# guarded_subprocess_run itself, a cross-module Result-returning wrapper the resolver \
# cannot see through; its one documented raise path (missing uvx/cargo) is caught below"
# frob:waive EXHAUST002 reason="T-1062: same guarded_subprocess_run resolver artifact \
# as EXHAUST001 above"
def _build_one_crate(
    root: Path,
    spec,
    cargo_target_dir: Path,  # noqa: ANN001
) -> Result[CrateBuildResult | None, NativesError]:
    """One declared native `spec`'s build attempt: `Ok(None)` for a
    silently-skipped entry (non-rust, no matching crate dir, or no
    `uvx`/`cargo` toolchain -- `build_natives`'s docstring), `Err(
    ExecDisabled)` if the exec kill switch refused to spawn, else
    `Ok(CrateBuildResult)` for an attempted build regardless of its own
    pass/fail exit code (that per-crate failure is NOT an `Err`, per
    `build_natives`'s own disclosed contract)."""
    crate_dir = _resolve_buildable_crate(root, spec)
    if crate_dir is None:
        return Ok(None)

    _log.info(
        "build_natives: building %s via maturin develop "
        "(crate=%s, cargo_target_dir=%s)",
        spec.name,
        crate_dir,
        cargo_target_dir,
    )
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = sys.prefix
    env["CARGO_TARGET_DIR"] = str(cargo_target_dir)
    try:
        run_result = guarded_subprocess_run(
            [
                "uvx",
                "maturin",
                "develop",
                "--uv",
                "--release",
                "-m",
                str(crate_dir / "Cargo.toml"),
            ],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        # Matches the old `make core` recipe's own posture (T-0732): a
        # missing toolchain (no `uvx`/`cargo` on PATH) is a best-effort
        # skip, not a hard failure -- Smart-dup R3+ and strata design-model
        # parsing degrade gracefully without the native extension (T-0133),
        # everything else keeps working.
        _log.warning(
            "build_natives: uvx/cargo not found, skipping %s "
            "(native extension disabled)",
            spec.name,
        )
        return Ok(None)
    if run_result.is_err:
        _log.error("build_natives: exec disabled, refusing to build %s", spec.name)
        return Err(NativesError.ExecDisabled)
    proc: subprocess.CompletedProcess[str] = run_result.danger_ok
    try:
        crate_dir_display = str(crate_dir.relative_to(root))
    except ValueError:
        crate_dir_display = str(crate_dir)
    result = CrateBuildResult(
        name=spec.name,
        crate_dir=crate_dir_display,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
    if proc.returncode != 0:
        _log.error(
            "build_natives: %s failed to build (exit %d)", spec.name, proc.returncode
        )
    else:
        _log.info("build_natives: %s built cleanly", spec.name)
    return Ok(result)
