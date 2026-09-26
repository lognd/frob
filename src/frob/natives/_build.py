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

T-5808: measured on every land, "worktree natives stale/unimportable
after auto-rebuild attempt (T-1578)" was followed by a full `maturin
develop --uv --release` of `strata_core`/`frob_core`, 70-190s per land,
even when the worktree's Rust sources were byte-identical to an
extension already built elsewhere (the root checkout, or a sibling
worktree branched from the same commit). `_try_reuse_native` closes
that gap: before spawning `maturin`, it compares this crate's current
GIT-TRACKED source digest (`_tracked_source_digest`, the SAME worktree-
safe digest T-4431/T-4434 already use to seed mtimes -- ignores
untracked build noise like `uv.lock` a fresh worktree never checks
out) plus a toolchain id against a stamp recorded the last time ANY
build (in any worktree of this clone) succeeded for that crate; on a
match, it copies the previously-built compiled artifact into this
root's own site-packages instead of rebuilding. The stamp lives under
the SAME git-common-dir-keyed directory `CARGO_TARGET_DIR` already
does (`_REUSE_STAMP_REL`), so it is visible to every worktree of the
clone, not just the one that built it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.gitio import git_common_dir
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.strata._native_staleness import record_native_build_attempt
from frob.strata._native_staleness_digest import _tracked_source_digest
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
    """One declared native's build outcome: which crate directory built,
    the exit code, and its captured output so a failing build's
    diagnostics survive past the subprocess call. `reused=True` marks a
    result produced by copying a matching prior artifact instead of
    spawning `maturin` -- `returncode` stays `0` and `stdout`/`stderr`
    stay empty either way, so `.ok` reads identically for both (see
    T-5808 for the design rationale)."""

    model_config = {}

    name: str
    crate_dir: str
    returncode: int
    stdout: str
    stderr: str
    reused: bool = False

    # frob:doc docs/modules/cli.md#frob-natives-build-t-0864
    @property
    def ok(self) -> bool:
        """True when `maturin develop` exited zero for this crate (or,
        T-5808, when a matching prior build was reused instead)."""
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


#: T-5808: reuse stamps live inside the SAME git-common-dir-keyed cache
#: `CARGO_CACHE_DIRNAME` already uses, so every worktree of the clone
#: shares one file -- a build in worktree A is discoverable by worktree
#: B's own `build_natives(root=B)` call without either knowing about the
#: other directly.
_REUSE_STAMP_REL = Path(CARGO_CACHE_DIRNAME) / "native-reuse-stamps.json"


def _reuse_stamp_path(common_dir: Path) -> Path:
    """Where T-5808's per-native reuse stamps live under `common_dir`
    (`frob.gitio.git_common_dir`'s return value, NOT `root` -- shared
    across every worktree of the clone, mirroring `CARGO_TARGET_DIR`)."""
    return common_dir / _REUSE_STAMP_REL


def _load_reuse_stamps(common_dir: Path) -> dict[str, dict[str, str]]:
    """The persisted `{name: {"digest": ..., "toolchain": ...,
    "artifact_dir": ...}}` reuse-stamp map, or `{}` for a missing/
    malformed file -- same degrade-to-empty posture as `_native_
    staleness._load_stamps`: a corrupt or absent stamp file means "no
    known prior build to reuse," never a crash, and simply falls through
    to an ordinary `maturin develop` rebuild."""
    path = _reuse_stamp_path(common_dir)
    try:
        raw = path.read_text()
    except OSError:
        return {}
    try:
        loaded = json.loads(raw)
    except Exception:
        _log.warning("build_natives: malformed reuse-stamp file %s, ignoring", path)
        return {}
    if not isinstance(loaded, dict):
        return {}
    return loaded


def _save_reuse_stamps(common_dir: Path, stamps: dict[str, dict[str, str]]) -> None:
    """Persist T-5808's reuse-stamp map, creating the parent dir if
    needed -- best effort: a write failure is logged, not raised, since
    losing this file only costs the NEXT `build_natives` call a real
    rebuild it could otherwise have skipped, never a correctness issue."""
    path = _reuse_stamp_path(common_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stamps, sort_keys=True, indent=2) + "\n")
    except OSError as exc:
        _log.warning(
            "build_natives: could not write reuse-stamp file %s: %s", path, exc
        )


def _toolchain_id() -> str | None:
    """A best-effort string identifying the active Rust toolchain
    (`rustc --version`'s stdout, stripped), or `None` if it cannot be
    determined (no `rustc` on PATH, exec kill switch, a timeout).
    T-5808 reuse is fail-closed on this: `None` here means `_try_reuse_
    native` never treats any stamp as a match, so an environment this
    function cannot fingerprint always falls through to a real rebuild
    rather than risk reusing an artifact built by a DIFFERENT toolchain
    (a real correctness hazard, e.g. across a Rust version bump)."""
    try:
        run_result = guarded_subprocess_run(
            ["rustc", "--version"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if run_result.is_err:
        return None
    proc = run_result.danger_ok
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _crate_digest(root: Path, spec: NativeSpec) -> str | None:
    """T-5808: this native's current GIT-TRACKED source digest under
    `root` (`_tracked_source_digest`, T-4431/T-4434's worktree-safe
    digest -- ignores untracked build noise like `uv.lock` a fresh
    worktree never checks out), or `None` when there is no matching
    crate directory to digest at all."""
    crate_dir = _crate_dir_for(root, spec)
    if crate_dir is None:
        return None
    return _tracked_source_digest(root, crate_dir.name)


def _native_package_dir(spec: NativeSpec) -> Path:
    """Where `maturin develop --uv` installs `spec`'s compiled package
    directory in THIS interpreter's own site-packages (`sysconfig.
    get_paths()["purelib"]`) -- the same `VIRTUAL_ENV=sys.prefix`
    environment `_build_one_crate` already targets its `maturin develop`
    subprocess at, so this is exactly where a genuine build would have
    installed to, and exactly where `_try_reuse_native` copies a reused
    artifact TO."""
    return Path(sysconfig.get_paths()["purelib"]) / spec.name


def _copy_native_package(source_dir: Path, dest_dir: Path) -> bool:
    """Copy every file in `source_dir` (a native's installed package
    directory) into `dest_dir`, overwriting -- best effort: any `OSError`
    aborts the copy and returns `False` (the caller falls through to a
    real `maturin develop` rebuild rather than leave a partially-copied,
    possibly-broken extension in place). `True` on a clean copy. A no-op
    (returns `True`) when the two directories already resolve to the
    same path -- nothing to copy, the artifact is already exactly there."""
    try:
        if source_dir.resolve() == dest_dir.resolve():
            return True
    except OSError:
        return False
    if not source_dir.is_dir():
        return False
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        for item in source_dir.iterdir():
            if item.is_dir():
                shutil.copytree(item, dest_dir / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest_dir / item.name)
    except OSError as exc:
        _log.warning(
            "build_natives: reuse copy from %s to %s failed (%s) -- falling "
            "back to a real rebuild",
            source_dir,
            dest_dir,
            exc,
        )
        return False
    return True


# frob:ticket T-5808
# tests/unit/test_natives_build.py::TestNativeReuse.test_reuses_a_matching_prior_build
# tests/unit/test_natives_build.py::TestNativeReuse.test_digest_mismatch_falls_back_to_a_real_build  # noqa: E501
# tests/unit/test_natives_build.py::TestNativeReuse.test_toolchain_mismatch_falls_back_to_a_real_build  # noqa: E501
def _try_reuse_native(
    root: Path, spec: NativeSpec, common_dir: Path
) -> CrateBuildResult | None:
    """T-5808: `None` if there is nothing to reuse (no matching crate
    directory, no reuse stamp yet, a digest/toolchain mismatch, the
    stamped artifact directory no longer exists, or the copy itself
    failed) -- the caller's signal to fall through to an ordinary
    `maturin develop` build, UNCHANGED. A non-`None` `CrateBuildResult`
    (`reused=True`, `returncode=0`) means a previously-built artifact
    matching this crate's CURRENT source digest and toolchain was
    copied into this root's own site-packages, and `_build_one_crate`
    must not spawn `maturin` at all."""
    crate_dir = _crate_dir_for(root, spec)
    if crate_dir is None:
        return None
    digest = _crate_digest(root, spec)
    if digest is None:
        return None
    toolchain = _toolchain_id()
    if toolchain is None:
        return None
    stamps = _load_reuse_stamps(common_dir)
    entry = stamps.get(spec.name)
    if entry is None:
        return None
    if entry.get("digest") != digest or entry.get("toolchain") != toolchain:
        return None
    source_dir = Path(entry.get("artifact_dir", ""))
    dest_dir = _native_package_dir(spec)
    if not _copy_native_package(source_dir, dest_dir):
        return None
    _log.info(
        "build_natives: reusing %s -- crate tree digest unchanged (source=%s, "
        "toolchain=%s)",
        spec.name,
        source_dir,
        toolchain,
    )
    try:
        crate_dir_display = str(crate_dir.relative_to(root))
    except ValueError:
        crate_dir_display = str(crate_dir)
    return CrateBuildResult(
        name=spec.name,
        crate_dir=crate_dir_display,
        returncode=0,
        stdout="",
        stderr="",
        reused=True,
    )


def _record_reuse_stamp(root: Path, spec: NativeSpec, common_dir: Path) -> None:
    """T-5808: called by `build_natives` immediately after ONE crate's
    `maturin develop` exits ZERO -- records the CURRENT source digest,
    toolchain id, and this root's own freshly-installed package
    directory as "reusable" for the NEXT `build_natives` call (in any
    worktree of this clone) whose crate digest and toolchain still
    match. Best-effort, silent no-op on a digest/toolchain this process
    cannot determine -- matching `_try_reuse_native`'s own fail-closed
    posture, never a crash."""
    digest = _crate_digest(root, spec)
    toolchain = _toolchain_id()
    if digest is None or toolchain is None:
        return
    stamps = _load_reuse_stamps(common_dir)
    stamps[spec.name] = {
        "digest": digest,
        "toolchain": toolchain,
        "artifact_dir": str(_native_package_dir(spec)),
    }
    _save_reuse_stamps(common_dir, stamps)


# frob:ticket T-0864
# frob:doc docs/modules/cli.md#frob-natives-build-t-0864
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
    failing crate's captured output before exiting non-zero.

    T-2805: each crate whose build exits ZERO also calls `frob.strata.
    _native_staleness.record_native_build_attempt` -- see that function's
    own docstring for why this is the only way `stale_natives`'s T-0513
    content-digest check can distinguish "genuinely rebuilt, reproducibly
    byte-identical output" from "never rebuilt at all, mtime faked" (a
    deterministic `maturin --release` build makes those two cases
    otherwise indistinguishable, which was T-2805's own root cause: a
    real rebuild could never clear its own staleness detector). A FAILED
    crate build never calls it -- only `.ok` triggers the hook."""
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
        built = _build_one_crate(root, spec, cargo_target_dir, common_dir.danger_ok)
        if built.is_err:
            return Err(built.danger_err)
        if built.danger_ok is not None:
            results.append(built.danger_ok)
            _record_successful_build(root, spec, built.danger_ok, common_dir.danger_ok)

    return Ok(BuildReport(cargo_target_dir=cargo_target_dir, results=results))


def _record_successful_build(
    root: Path, spec: NativeSpec, result: CrateBuildResult, common_dir: Path
) -> None:
    """`build_natives`'s post-build bookkeeping for ONE crate, split out
    to keep that loop body short (ARCH001): a no-op unless `result.ok`.
    T-2805's `record_native_build_attempt` always runs on a genuine
    exit-zero result (reused or not -- it records the CURRENT source
    digest either way, which is unchanged by a reuse). T-5808's own
    reuse stamp is different: only a GENUINE `maturin` build (never one
    that was itself a reuse) updates it -- re-recording an already-
    reused result would be a no-op at best (same digest/toolchain/
    artifact_dir) and, on a worktree whose own site-packages path
    differs from the stamped one, would needlessly overwrite a good
    stamp with a redundant one."""
    if not result.ok:
        return
    record_native_build_attempt(root, spec.name)
    if not result.reused:
        _record_reuse_stamp(root, spec, common_dir)


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
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to guarded_subprocess_run itself, \
# a cross-module Result-returning wrapper the resolver cannot see through; its one \
# documented raise path (missing uvx/cargo) is caught below"
# frob:waive EXHAUST002 reason="T-1062: same guarded_subprocess_run resolver artifact \
# as EXHAUST001 above"
def _build_one_crate(
    root: Path,
    spec,
    cargo_target_dir: Path,  # noqa: ANN001
    common_dir: Path,
) -> Result[CrateBuildResult | None, NativesError]:
    """One declared native `spec`'s build attempt: `Ok(None)` for a
    silently-skipped entry (non-rust, no matching crate dir, or no
    `uvx`/`cargo` toolchain -- `build_natives`'s docstring), `Err(
    ExecDisabled)` if the exec kill switch refused to spawn, else
    `Ok(CrateBuildResult)` for an attempted build regardless of its own
    pass/fail exit code (that per-crate failure is NOT an `Err`, per
    `build_natives`'s own disclosed contract).

    T-5808: `_try_reuse_native` gets first refusal -- when it finds a
    prior build (in any worktree of this clone) whose source digest and
    toolchain still match `root`'s current crate, it copies that
    artifact in and this function returns its `CrateBuildResult`
    (`reused=True`) WITHOUT ever spawning `maturin`. Only a reuse miss
    falls through to the real build below, unchanged."""
    crate_dir = _resolve_buildable_crate(root, spec)
    if crate_dir is None:
        return Ok(None)

    reused = _try_reuse_native(root, spec, common_dir)
    if reused is not None:
        return Ok(reused)

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
