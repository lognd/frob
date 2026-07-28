"""`pytest --collect-only`, `cargo test -- --list`, `vitest list --json`, and
`ctest --show-only=json-v1`, each cached by source content hash under
`.frob/` (T-0587 added the vitest/ctest collectors, mirroring the rust
collector's shape)."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/testing/_collect.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import tomllib
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs, walk_pruned
from frob.gitio import GitError, ProcResult, run_argv
from frob.logging import get_logger
from frob.testing._models import CollectedTests, NativeSpec, RunnerSpec
from frob.testing._runners import (
    TestingError,
    _cargo_env,
    _env_overlay,
    load_natives,
    load_runners,
)

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "pytest-collect.json"
_RUST_CACHE_REL = Path(".frob") / "cargo-collect.json"
_TS_CACHE_REL = Path(".frob") / "vitest-collect.json"
_CTEST_CACHE_REL = Path(".frob") / "ctest-collect.json"
_COLLECT_TIMEOUT_S = 300.0
_NO_TESTS_COLLECTED_EXIT = 5
_CARGO_TEST_LINE_RE = re.compile(r"^(?P<path>[\w:]+): test$")

# cargo's own wording (stable across recent toolchains) when `--lib` is
# passed to a crate that declares no library target (e.g. a `cargo-fuzz`
# harness crate: bin-only, no `src/lib.rs`). This is a crate SHAPE, not a
# broken build -- `cargo test --lib -- --list` exits 101 for it exactly the
# same way it would for a genuine compile error, so the two must be told
# apart by message text (T-0301: a lib-less crate anywhere in the workspace
# was silently failing the ENTIRE collection, unvalidating every rust
# binding repo-wide).
_NO_LIB_TARGET_RE = re.compile(r"no library targets found in package")


def _prune_dirnames(
    dirpath: Path, root: Path, dirnames: list[str], exclude_globs: tuple[str, ...]
) -> list[str]:
    """`dirnames` filtered to drop built-in-skipped names AND any child
    whose root-relative POSIX path matches `[graph].exclude` (T-0274: a
    file-walking surface that does not consult frob.excludes is exactly
    the desync that module exists to prevent -- docs/strata/surface.md).
    Shared by every `os.walk`-based collector in this module so the rule
    lives once."""
    rel_dir = dirpath.relative_to(root)
    kept: list[str] = []
    for name in dirnames:
        if is_skipped_dir(name):
            continue
        rel_child = (rel_dir / name).as_posix()
        if exclude_globs and is_excluded(rel_child, exclude_globs):
            continue
        kept.append(name)
    return kept


def _walk_test_files(root: Path) -> list[Path]:
    """Unordered `test_*.py` / `*_test.py` files under `root`, exclusions
    pruned (built-in skip set AND `[graph].exclude`, T-0274)."""
    exclude_globs = load_exclude_globs(root)
    found: list[Path] = []
    for path in walk_pruned(root, exclude_globs=exclude_globs):
        name = path.name
        if name.startswith("test_") and name.endswith(".py"):
            found.append(path)
        elif name.endswith("_test.py"):
            found.append(path)
    return found


def _find_test_files(root: Path) -> list[Path]:
    """Every `test_*.py` / `*_test.py` file under `root`, sorted, exclusions pruned."""
    return sorted(_walk_test_files(root))


def _content_key(root: Path) -> str:
    """Sha256 over every test file's `(relpath, sha256)` pair -- the cache
    key. Includes nested `language = "python"` `[[test.runner]] cwd`
    directories (T-0317) even when `[graph].exclude` keeps them out of
    `_find_test_files(root)`'s own walk -- their content is now part of
    what `collect_python_tests` collects, so it must be part of what
    invalidates the cache."""
    hasher = hashlib.sha256()
    all_files = list(_find_test_files(root))
    for cwd_rel in _python_runner_cwds(root):
        nested_root = root / cwd_rel
        if nested_root.is_dir():
            all_files.extend(_find_test_files(nested_root))
    for path in sorted(set(all_files)):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            _log.warning("collect_python_tests: could not read %s: %s", path, exc)
            continue
        rel = path.relative_to(root).as_posix()
        hasher.update(f"{rel}:{digest}\n".encode())
    return hasher.hexdigest()


_COMPILED_EXT_SUFFIXES = (".so", ".pyd", ".dylib")


def _is_compiled_artifact(path: Path) -> bool:
    """Whether `path` is a compiled extension artifact (`.so`/`.pyd`/`.dylib`),
    matching a leading suffix so abi3/platform-tagged names like
    `strata_core.abi3.so` or `_ext.cpython-311-x86_64-linux-gnu.so` count."""
    return any(suffix in path.suffixes for suffix in _COMPILED_EXT_SUFFIXES)


def _compiled_artifacts(found: importlib.machinery.ModuleSpec) -> list[Path]:
    """Every compiled artifact backing a resolved module spec. A single-file
    extension resolves directly to its `.so`/`.pyd`/`.dylib` origin; a
    maturin/pyo3 or pybind11 PACKAGE resolves to an `__init__.py` origin with
    the real compiled module(s) sitting alongside it in the package
    directory (`submodule_search_locations`) -- those are what a rebuild
    changes, so they, not the unchanged `__init__.py`, must be fingerprinted
    (T-0333)."""
    artifacts: list[Path] = []
    if found.origin and found.origin not in ("built-in", "namespace"):
        origin = Path(found.origin)
        if _is_compiled_artifact(origin):
            artifacts.append(origin)
    for location in found.submodule_search_locations or ():
        pkg_dir = Path(location)
        # frob:waive WALK001 reason="bounded to a single already-resolved package dir's own compiled-artifact siblings, not a repo-wide walk"  # noqa: E501
        # frob:waive PERF008 reason="the PERF008 finding treats the literal '*' \
        # argument as loop-invariant, but pkg_dir is freshly rebound from location \
        # on every iteration of the enclosing for-loop -- each rglob('*') walks a \
        # DIFFERENT package directory, not a repeated identical walk. A resolver \
        # limit (argument-text equality does not account for a differing receiver \
        # object), not a real redundant walk to hoist"  # noqa: E501
        artifacts.extend(p for p in pkg_dir.rglob("*") if _is_compiled_artifact(p))
    return sorted(set(artifacts))


def _native_artifact_digest(spec: NativeSpec) -> str:
    """`(name, build-state)` fingerprint term for one declared native module.

    Resolves the import NAME (not a path) via `importlib.util.find_spec`, so
    it is toolchain-agnostic: an unbuilt module resolves to nothing
    ("absent"); a built one is fingerprinted over its compiled artifacts
    (`.so`/`.pyd`/`.dylib`, found via `_compiled_artifacts`) -- identical
    whether produced by maturin/pyo3 (rust) or setuptools/pybind11/
    scikit-build (c/c++). Any recompile changes those bytes, so folding this
    into the collection cache key forces re-collection the moment a native
    goes unbuilt->built OR is rebuilt (T-0333: the recurring
    strata_core/frob_core stale-COV003 footgun)."""
    try:
        found = importlib.util.find_spec(spec.name)
    except (ImportError, ValueError) as exc:
        # a half-installed / shadowed name: treat as absent, do not crash
        # collection over one bad declared native.
        _log.warning("native fingerprint: find_spec(%r) raised %s", spec.name, exc)
        return f"{spec.name}:error"
    if found is None:
        _log.debug("native fingerprint: %r absent (not built)", spec.name)
        return f"{spec.name}:absent"
    artifacts = _compiled_artifacts(found)
    if not artifacts:
        # resolvable but no compiled artifact found (e.g. a pure-python stub
        # standing in for an unbuilt native): treat as absent so building it
        # still invalidates the cache.
        _log.debug("native fingerprint: %r resolved, no compiled artifact", spec.name)
        return f"{spec.name}:absent"
    hasher = hashlib.sha256()
    for artifact in artifacts:
        try:
            hasher.update(hashlib.sha256(artifact.read_bytes()).digest())
        except OSError as exc:
            _log.warning("native fingerprint: could not read %s: %s", artifact, exc)
            return f"{spec.name}:unreadable"
    _log.debug(
        "native fingerprint: %r built, %d artifact(s)", spec.name, len(artifacts)
    )
    return f"{spec.name}:{hasher.hexdigest()}"


def _native_fingerprint(natives: tuple[NativeSpec, ...]) -> str:
    """Order-stable fingerprint over every declared native module's build
    state -- the term unioned into the collection cache key (T-0333)."""
    hasher = hashlib.sha256()
    for spec in sorted(natives, key=lambda s: s.name):
        hasher.update(f"{_native_artifact_digest(spec)}\n".encode())
    return hasher.hexdigest()


def _missing_natives(natives: tuple[NativeSpec, ...]) -> tuple[NativeSpec, ...]:
    """Declared natives that `find_spec` cannot resolve to a built artifact --
    the ones whose `importorskip`-gated tests will be silently absent from
    collection (T-0333). Surfaced on `CollectedTests.missing_natives` so
    COV003 can name the real remedy (build them) instead of the evidence id."""
    missing: list[NativeSpec] = []
    for spec in natives:
        try:
            found = importlib.util.find_spec(spec.name)
        except (ImportError, ValueError):
            found = None
        if found is None or not _compiled_artifacts(found):
            missing.append(spec)
    return tuple(missing)


def _load_natives_or_empty(root: Path) -> tuple[NativeSpec, ...]:
    """Declared `[[native]]` entries, or `()` if the config is absent/malformed
    -- a bad native table must not take down test collection."""
    loaded = load_natives(root)
    if loaded.is_err:
        _log.warning(
            "collect_python_tests: could not load [[native]] entries (%s); "
            "collecting without a native fingerprint",
            loaded.danger_err,
        )
        return ()
    return loaded.danger_ok


# frob:doc docs/modules/testing.md#public-api
def drop_collection_cache(root: Path) -> bool:
    """Delete the pytest collection cache so the next collection re-runs from
    scratch (`frob test --collect`, T-0333). Returns whether a cache file was
    actually removed. The honest escape hatch for the rare case the native
    fingerprint cannot cover (e.g. a hand-edited cache)."""
    cache_path = root / _CACHE_REL
    if not cache_path.exists():
        _log.info("drop_collection_cache: no cache at %s", cache_path)
        return False
    try:
        cache_path.unlink()
    except OSError as exc:
        _log.warning("drop_collection_cache: could not remove %s: %s", cache_path, exc)
        return False
    _log.info("drop_collection_cache: removed %s", cache_path)
    return True


def _load_cache(cache_path: Path, key: str) -> frozenset[str] | None:
    """The cached node id set if `cache_path` exists and matches `key`, else `None`."""
    if not cache_path.exists():
        return None
    try:
        doc = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("collect_python_tests: unreadable cache %s: %s", cache_path, exc)
        return None
    if doc.get("key") != key:
        return None
    return frozenset(doc.get("node_ids", []))


def _store_cache(cache_path: Path, key: str, node_ids: frozenset[str]) -> None:
    """Persist `node_ids` keyed by `key` to `cache_path`."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"key": key, "node_ids": sorted(node_ids)}, indent=2),
        encoding="utf-8",
    )


def _run_collect_only(cwd: Path) -> Result[frozenset[str], TestingError]:
    """Spawn `pytest --collect-only -q` in `cwd` and parse its stdout into
    node ids relative to `cwd` (the caller reroots them if `cwd` is not the
    repo root, T-0317)."""
    # -o addopts= neutralizes the project's own addopts: a configured -q
    # would stack with ours into -qq, which switches --collect-only from
    # node ids to per-file counts (and -n auto adds xdist noise) -- the
    # evidence oracle would silently see an empty set (observed: INV001
    # false positives on every invariant).
    argv = ("uv", "run", "pytest", "--collect-only", "-q", "-o", "addopts=")
    spawned = run_argv(argv, cwd=cwd, timeout_s=_COLLECT_TIMEOUT_S)
    if spawned.is_err:
        _log.error(
            "collect_python_tests: pytest --collect-only failed to spawn in %s", cwd
        )
        return Err(TestingError.CollectFailed)
    result = spawned.danger_ok
    if result.returncode not in (0, _NO_TESTS_COLLECTED_EXIT):
        _log.error(
            "collect_python_tests: pytest --collect-only exited %d in %s",
            result.returncode,
            cwd,
        )
        return Err(TestingError.CollectFailed)
    return Ok(
        frozenset(
            line.strip()
            for line in result.stdout.splitlines()
            if "::" in line and not line.startswith(" ")
        )
    )


def _reroot_node_ids(node_ids: frozenset[str], cwd_rel: str) -> frozenset[str]:
    """Node ids collected inside a nested `[[test.runner]] cwd` (relative to
    that cwd) rejoined onto `cwd_rel` so they read as the same root-relative
    `path::qualname` symref the graph and `frob:tests` directives use
    (T-0317). `cwd_rel = "."` (the outer collection's own runner) is a
    no-op."""
    if cwd_rel in (".", ""):
        return node_ids
    prefix = cwd_rel.rstrip("/")
    return frozenset(f"{prefix}/{node_id}" for node_id in node_ids)


def _python_runner_cwds(root: Path) -> list[str]:
    """Every distinct nested `cwd` a `language = "python"` `[[test.runner]]`
    entry declares (T-0317): `frob.toml` already tells `run_selected` which
    directory owns which tests (each has its own venv/interpreter/deps, e.g.
    a nested project importing packages the outer repo's `.venv` never
    installs) -- collection must consult the same config, or a nested
    project's node ids are simply never visited and every `frob:tests`
    directive inside it is permanently unresolvable. `cwd = "."` (the outer
    tree itself) is excluded since `collect_python_tests` already covers it
    directly."""
    runners = load_runners(root)
    if runners.is_err:
        _log.warning(
            "collect_python_tests: could not load [[test.runner]] entries, "
            "collecting outer tree only"
        )
        return []
    seen: set[str] = set()
    cwds: list[str] = []
    for spec in runners.danger_ok:
        if not _is_nested_python_runner(spec):
            continue
        if spec.cwd not in seen:
            seen.add(spec.cwd)
            cwds.append(spec.cwd)
    return cwds


def _is_nested_python_runner(spec: RunnerSpec) -> bool:
    """True if `spec` is a `language = "python"` runner scoped to a real
    subdirectory (not the outer tree, `cwd = "."`)."""
    return spec.language == "python" and spec.cwd not in (".", "")


def _collect_nested_python(
    root: Path, cwd_rel: str
) -> Result[frozenset[str], TestingError]:
    """`_run_collect_only` inside `root / cwd_rel`, node ids rerooted onto
    `cwd_rel` (T-0317). A nested project directory that does not exist is
    logged and treated as empty rather than a hard `Err` -- a stale
    `[[test.runner]] cwd` must not take down collection for every OTHER
    project in the repo."""
    nested_root = root / cwd_rel
    if not nested_root.is_dir():
        _log.warning(
            "collect_python_tests: [[test.runner]] cwd %r does not exist under %s",
            cwd_rel,
            root,
        )
        return Ok(frozenset())
    collected = _run_collect_only(nested_root)
    if collected.is_err:
        return collected
    return Ok(_reroot_node_ids(collected.danger_ok, cwd_rel))


# frob:doc docs/modules/testing.md#public-api
def collect_python_tests(root: Path) -> Result[CollectedTests, TestingError]:
    """`uv run pytest --collect-only -q` node ids for the outer tree, UNIONED
    with the same collection run inside every nested `language = "python"`
    `[[test.runner]] cwd` (T-0317) -- each such directory typically has its
    own venv/deps, so a plain outer-tree collection never visits (and can
    never resolve `frob:tests` evidence for) tests living there. Cached on
    the outer tree's test-file content hash UNIONED with a native-build
    fingerprint (T-0333) -- so building or rebuilding a declared `[[native]]`
    extension invalidates the cache automatically (a native's tests are
    `importorskip`-gated: while it is unbuilt they never collect, and that
    stale set must not survive the build). A nested-cwd collection failure
    degrades to a warning plus that project's tests being absent from the
    result, rather than failing the whole call."""
    natives = _load_natives_or_empty(root)
    missing = _missing_natives(natives)
    key = _collection_cache_key(root, natives)
    cache_path = root / _CACHE_REL
    cached = _load_cache(cache_path, key)
    if cached is not None:
        _log.debug("collect_python_tests: cache hit, %d node id(s)", len(cached))
        return Ok(CollectedTests(node_ids=cached, missing_natives=missing))

    collected = _run_collect_only(root)
    if collected.is_err:
        return Err(collected.danger_err)
    node_ids = set(collected.danger_ok)

    for cwd_rel in _python_runner_cwds(root):
        nested = _collect_nested_python(root, cwd_rel)
        if nested.is_err:
            _log.warning(
                "collect_python_tests: nested collection failed for cwd %r (%s); "
                "its tests are absent from this pass' evidence oracle",
                cwd_rel,
                nested.danger_err,
            )
            continue
        node_ids |= nested.danger_ok

    frozen = frozenset(node_ids)
    _store_cache(cache_path, key, frozen)
    _log.info(
        "collect_python_tests: collected %d node id(s), %d declared native(s) missing",
        len(frozen),
        len(missing),
    )
    return Ok(CollectedTests(node_ids=frozen, missing_natives=missing))


def _collection_cache_key(root: Path, natives: tuple[NativeSpec, ...]) -> str:
    """The pytest collection cache key: test-file content hash (`_content_key`)
    unioned with the declared natives' build fingerprint (T-0333). Both must
    invalidate the cache -- edited test files change WHAT collects, a rebuilt
    native changes WHETHER `importorskip`-gated tests collect at all."""
    content = _content_key(root)
    native = _native_fingerprint(natives)
    return hashlib.sha256(f"{content}\n{native}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# Rust: `cargo test -- --list`, one crate directory per discovered Cargo.toml
# ---------------------------------------------------------------------------


def _classify_manifest(manifest_path: Path) -> tuple[bool, bool] | None:
    """`(has_package, has_workspace)` for a `Cargo.toml`, or `None` if it
    cannot be read/parsed (caller falls back to conservative old behavior)."""
    try:
        doc = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("_find_crates: could not parse %s: %s", manifest_path, exc)
        return None
    return ("package" in doc, "workspace" in doc)


def _find_crates(root: Path) -> list[Path]:
    """Directories holding a real crate manifest (`[package]` table),
    exclusions pruned. A cargo VIRTUAL WORKSPACE root (`[workspace]` table,
    no `[package]` table -- e.g. this repo's own top-level `Cargo.toml` is
    not one, but a workspace umbrella like lithos's or feldspar's is) is
    descended into rather than treated as a crate, so member crates under
    it are discovered instead of being collapsed into one bogus root
    "crate". A manifest with both tables is a crate AND a workspace root
    (appended, then descended). A manifest with neither table, or one that
    fails to parse, keeps the old append-and-prune behavior (with a
    warning) so degenerate cases do not regress. Also honors `[graph]
    exclude` (T-0274) -- an excluded directory (e.g. stale agent
    worktrees under `.claude/worktrees/**`) is pruned before its
    `Cargo.toml`, if any, is ever inspected."""
    exclude_globs = load_exclude_globs(root)
    found: list[Path] = []
    # frob:waive WALK001 reason="needs per-directory descend control (stop past a found crate root, _classify_crate_dir's should_prune) that the file-only iter_files/walk_pruned API cannot express; already prunes via _prune_dirnames using frob.excludes primitives"  # noqa: E501
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = _prune_dirnames(Path(dirpath), root, dirnames, exclude_globs)
        if "Cargo.toml" in filenames:
            manifest_dir = Path(dirpath)
            should_append, should_prune = _classify_crate_dir(manifest_dir)
            if should_append:
                found.append(manifest_dir)
            if should_prune:
                dirnames[:] = []
    return sorted(found)


def _classify_crate_dir(manifest_dir: Path) -> tuple[bool, bool]:
    """`(should_append_as_crate, should_prune_children)` for a directory
    holding a `Cargo.toml`, per `_find_crates`'s package/workspace rules."""
    classified = _classify_manifest(manifest_dir / "Cargo.toml")
    if classified is None:
        return True, True
    has_package, has_workspace = classified
    return has_package, not has_workspace


def _rust_content_key(root: Path) -> str:
    """Sha256 over every crate's `(relpath, sha256)` pair -- the cache key."""
    hasher = hashlib.sha256()
    # frob:waive WALK001 reason="bounded to each already-pruned single crate dir from _find_crates, not a repo-wide walk"  # noqa: E501
    all_rs_files = [
        p for crate_dir in _find_crates(root) for p in crate_dir.rglob("*.rs")
    ]
    for path in sorted(all_rs_files):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            _log.warning("collect_rust_tests: could not read %s: %s", path, exc)
            continue
        rel = path.relative_to(root).as_posix()
        hasher.update(f"{rel}:{digest}\n".encode())
    return hasher.hexdigest()


def _module_path_to_symref(root: Path, crate_dir: Path, module_path: str) -> str:
    """A `cargo test --list` module path (`parse::tests::foo`) as the
    `path::qualname` symref convention the graph's comment DSL uses,
    resolving which file the leading module segments bottom out in (`mod
    parse;` in `lib.rs` -> `src/parse.rs`, `mod.rs` for a directory module).
    Segments left over after that file match become the dot-free qualname
    (`tests::foo`), mirroring how an inline `#[cfg(test)] mod tests { ... }`
    in `lib.rs` itself resolves to `lib.rs::tests::foo`."""
    segments = module_path.split("::")
    test_name = segments[-1]
    mod_segments = segments[:-1]
    src_dir = crate_dir / "src"
    for i in range(len(mod_segments), 0, -1):
        prefix = mod_segments[:i]
        file_candidate = src_dir.joinpath(*prefix[:-1]) / f"{prefix[-1]}.rs"
        mod_candidate = src_dir.joinpath(*prefix) / "mod.rs"
        matched = next((c for c in (file_candidate, mod_candidate) if c.exists()), None)
        if matched is not None:
            rest = mod_segments[i:]
            qualname = "::".join([*rest, test_name])
            return f"{matched.relative_to(root).as_posix()}::{qualname}"
    lib_rs = src_dir / "lib.rs"
    qualname = "::".join([*mod_segments, test_name])
    return f"{lib_rs.relative_to(root).as_posix()}::{qualname}"


def _parse_cargo_list(stdout: str) -> list[str]:
    """Every `module::path` a `cargo test -- --list`-style line names."""
    paths: list[str] = []
    for line in stdout.splitlines():
        match = _CARGO_TEST_LINE_RE.match(line.strip())
        if match is not None:
            paths.append(match.group("path"))
    return paths


def _run_cargo_test_list(
    crate_dir: Path, target_argv: list[str]
) -> Result[list[str], TestingError]:
    """Spawn `cargo test <target_argv> -- --list` in one crate, PyO3 env
    resolved first (never silently skipped -- a missing dev environment is
    `Err`, not an empty test list masquerading as "this crate has no
    tests"). `target_argv` selects `--lib` for the crate's unit tests or
    `--test <stem>` for one `tests/<stem>.rs` integration binary."""
    env_result = _cargo_env()
    if env_result.is_err:
        _log.error(
            "collect_rust_tests: PyO3 env unavailable for %s, refusing to run "
            "cargo test --list",
            crate_dir,
        )
        return Err(env_result.danger_err)
    with _env_overlay(env_result.danger_ok):
        spawned = run_argv(
            ["cargo", "test", *target_argv, "--", "--list"],
            cwd=crate_dir,
            timeout_s=_COLLECT_TIMEOUT_S,
        )
    return _cargo_list_result(spawned, crate_dir)


def _cargo_list_result(
    spawned: Result[ProcResult, GitError], crate_dir: Path
) -> Result[list[str], TestingError]:
    """Turn a spawned `cargo test --list` invocation into parsed test paths,
    or `Err` on spawn/exit failure. A crate with no library target (T-0301,
    e.g. a `cargo-fuzz` bin-only harness crate) is a crate SHAPE, not a
    broken build: `cargo test --lib -- --list` exits nonzero for it exactly
    the way a genuine compile error would, so this is detected by cargo's
    own "no library targets found" wording and SKIPPED (an empty test list,
    logged at INFO) rather than failing the whole collection -- a real
    compile error still returns `Err` unchanged."""
    if spawned.is_err:
        _log.error("collect_rust_tests: cargo failed to spawn in %s", crate_dir)
        return Err(TestingError.CollectFailed)
    result = spawned.danger_ok
    if result.returncode != 0:
        if _NO_LIB_TARGET_RE.search(result.stderr):
            _log.info(
                "collect_rust_tests: %s has no library target, skipping (T-0301)",
                crate_dir,
            )
            return Ok([])
        _log.error(
            "collect_rust_tests: cargo test --list exited %d in %s: %s",
            result.returncode,
            crate_dir,
            result.stderr[-500:],
        )
        return Err(TestingError.CollectFailed)
    return Ok(_parse_cargo_list(result.stdout))


def _run_cargo_list(crate_dir: Path) -> Result[list[str], TestingError]:
    """Spawn `cargo test --lib -- --list` in one crate (the crate's own
    unit tests, e.g. `#[cfg(test)] mod tests` blocks under `src/`)."""
    return _run_cargo_test_list(crate_dir, ["--lib"])


def _find_integration_test_files(crate_dir: Path) -> list[Path]:
    """Every `tests/*.rs` integration-test binary file directly under one
    crate, sorted -- `cargo test --lib` never lists these (T-0271), so
    they need their own `cargo test --test <stem>` invocation."""
    tests_dir = crate_dir / "tests"
    if not tests_dir.is_dir():
        return []
    return sorted(tests_dir.glob("*.rs"))


def _integration_module_path_to_symref(
    root: Path, crate_dir: Path, test_file: Path, module_path: str
) -> str:
    """A `cargo test --test <stem> -- --list` module path as a `path::qualname`
    symref against the integration binary's own `tests/<stem>.rs` file.
    Integration binaries are their own crate root, so for the common flat
    case (no submodules under the binary) the whole `module_path` IS the
    qualname against `tests/<stem>.rs` directly. KNOWN APPROXIMATION: a
    `tests/<stem>/` submodule tree (`tests/<stem>/mod.rs` plus siblings) is
    not resolved file-by-file the way `_module_path_to_symref` resolves
    `src/` -- every path from that binary still anchors to
    `tests/<stem>.rs`, with the full module path as qualname."""
    rel = test_file.relative_to(root).as_posix()
    return f"{rel}::{module_path}"


def _collect_rust_uncached(root: Path) -> Result[frozenset[str], TestingError]:
    """`cargo test --lib -- --list` node ids for every crate's unit tests,
    plus `cargo test --test <stem> -- --list` node ids for every crate's
    `tests/*.rs` integration binaries, across every discovered crate."""
    node_ids: set[str] = set()
    for crate_dir in _find_crates(root):
        listed = _run_cargo_list(crate_dir)
        if listed.is_err:
            return Err(listed.danger_err)
        for module_path in listed.danger_ok:
            node_ids.add(_module_path_to_symref(root, crate_dir, module_path))

        for test_file in _find_integration_test_files(crate_dir):
            stem = test_file.stem
            listed_integration = _run_cargo_test_list(crate_dir, ["--test", stem])
            if listed_integration.is_err:
                return Err(listed_integration.danger_err)
            for module_path in listed_integration.danger_ok:
                node_ids.add(
                    _integration_module_path_to_symref(
                        root, crate_dir, test_file, module_path
                    )
                )
    return Ok(frozenset(node_ids))


# frob:doc docs/modules/testing.md#public-api
def collect_rust_tests(root: Path) -> Result[CollectedTests, TestingError]:
    """`cargo test --lib -- --list` node ids (unit tests) plus
    `cargo test --test <stem> -- --list` node ids (`tests/*.rs` integration
    binaries) for every crate under `root` (`Cargo.toml` discovery --
    virtual workspace roots are descended into rather than treated as one
    crate, T-0271 -- cached on rust source content hash); `Err` -- never a
    fabricated empty pass -- when the PyO3 dev environment cannot be
    resolved (T-0092)."""
    key = _rust_content_key(root)
    cache_path = root / _RUST_CACHE_REL
    cached = _load_cache(cache_path, key)
    if cached is not None:
        _log.debug("collect_rust_tests: cache hit, %d node id(s)", len(cached))
        return Ok(CollectedTests(node_ids=cached))

    collected = _collect_rust_uncached(root)
    if collected.is_err:
        return Err(collected.danger_err)
    node_ids = collected.danger_ok
    _store_cache(cache_path, key, node_ids)
    _log.info("collect_rust_tests: collected %d node id(s)", len(node_ids))
    return Ok(CollectedTests(node_ids=node_ids))


# ---------------------------------------------------------------------------
# TypeScript: `npx vitest list --json`, one project directory per discovered
# package.json declaring a `vitest` dependency (T-0587)
# ---------------------------------------------------------------------------

# frob:ticket T-0587
_TS_TEST_NAME_RE = re.compile(r"\.(test|spec)\.(ts|tsx|js|jsx|mts|mjs)$")
# frob:ticket T-0587
_VITEST_DEP_NAME = "vitest"


# frob:ticket T-0587
def _package_json_uses_vitest(pkg_path: Path) -> bool:
    """True if `pkg_path`'s package.json declares `vitest` as a dependency or
    devDependency -- the signal a directory is a real vitest project, not
    just any node package that happens to sit in the tree."""
    try:
        doc = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("_find_vitest_projects: could not parse %s: %s", pkg_path, exc)
        return False
    deps = {**doc.get("dependencies", {}), **doc.get("devDependencies", {})}
    return _VITEST_DEP_NAME in deps


# frob:ticket T-0587
def _find_vitest_projects(root: Path) -> list[Path]:
    """Directories holding a `package.json` that declares `vitest` as a
    dependency, exclusions pruned (mirrors `_find_crates`'s Cargo.toml
    walk). `node_modules` is always pruned -- an installed dependency's own
    package.json must never be mistaken for a project root."""
    exclude_globs = load_exclude_globs(root)
    found: list[Path] = []
    # frob:waive WALK001 reason="needs per-directory node_modules pruning the file-only iter_files/walk_pruned API cannot express; already prunes via _prune_dirnames using frob.excludes primitives"  # noqa: E501
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "node_modules"]
        dirnames[:] = _prune_dirnames(Path(dirpath), root, dirnames, exclude_globs)
        if "package.json" in filenames:
            pkg_dir = Path(dirpath)
            if _package_json_uses_vitest(pkg_dir / "package.json"):
                found.append(pkg_dir)
    return sorted(found)


# frob:ticket T-0587
def _is_ts_test_file(path: Path) -> bool:
    """True if `path`'s name matches vitest's default test-file convention
    (`*.test.{ts,tsx,js,jsx,mts,mjs}` or `*.spec.{...}`)."""
    return bool(_TS_TEST_NAME_RE.search(path.name))


# frob:ticket T-0587
def _find_ts_test_files(project_dir: Path) -> list[Path]:
    """Every vitest-convention test file under `project_dir`, `node_modules`
    and build output dirs pruned."""
    found: list[Path] = []
    # frob:waive WALK001 reason="bounded to one already-discovered vitest project dir, not a repo-wide walk"  # noqa: E501
    for dirpath, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = [
            d for d in dirnames if d not in ("node_modules", "dist", "build")
        ]
        for name in filenames:
            path = Path(dirpath) / name
            if _is_ts_test_file(path):
                found.append(path)
    return sorted(found)


# frob:ticket T-0587
def _ts_content_key(root: Path, projects: list[Path]) -> str:
    """Sha256 over every vitest project's `package.json` plus its test
    files' `(relpath, sha256)` pairs -- the cache key."""
    hasher = hashlib.sha256()
    all_files: list[Path] = []
    for project_dir in projects:
        pkg = project_dir / "package.json"
        if pkg.exists():
            all_files.append(pkg)
        all_files.extend(_find_ts_test_files(project_dir))
    for path in sorted(set(all_files)):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            _log.warning("collect_ts_tests: could not read %s: %s", path, exc)
            continue
        rel = path.relative_to(root).as_posix()
        hasher.update(f"{rel}:{digest}\n".encode())
    return hasher.hexdigest()


# frob:ticket T-0587
def _parse_vitest_json(stdout: str) -> list[tuple[str, str]]:
    """Every `(file, test name)` pair from `vitest list --json`'s output: a
    flat JSON array of objects, each with a `file` (path relative to the
    project's cwd) and a `name` (the full test title, describe blocks
    already joined by vitest itself). Malformed or unparseable entries are
    skipped with a warning rather than failing the whole collection --
    mirroring how a single unreadable test file is skipped, not fatal, in
    `_content_key`."""
    try:
        doc = json.loads(stdout)
    except ValueError as exc:
        _log.warning("collect_ts_tests: unparseable vitest list --json output: %s", exc)
        return []
    if not isinstance(doc, list):
        _log.warning("collect_ts_tests: vitest list --json did not return a JSON array")
        return []
    pairs: list[tuple[str, str]] = []
    for entry in doc:
        if not isinstance(entry, dict):
            _log.warning(
                "collect_ts_tests: skipping non-object vitest entry: %r", entry
            )
            continue
        file = entry.get("file")
        name = entry.get("name")
        if isinstance(file, str) and isinstance(name, str):
            pairs.append((file, name))
        else:
            _log.warning("collect_ts_tests: skipping malformed vitest entry: %r", entry)
    return pairs


# frob:ticket T-0587
def _run_vitest_list(project_dir: Path) -> Result[list[tuple[str, str]], TestingError]:
    """Spawn `npx vitest list --json` in `project_dir`. Degrades to an
    empty, `Ok` result (with a warning, not a hard failure) when `npx` is
    not on PATH -- a repo with no node toolchain installed must not fail
    collection for every OTHER language (T-0587). A genuine vitest failure
    (bad config, nonzero exit) is still a real `Err`, same as a rust
    compile error is for `collect_rust_tests`."""
    if shutil.which("npx") is None:
        _log.warning(
            "collect_ts_tests: npx not found on PATH, skipping %s", project_dir
        )
        return Ok([])
    spawned = run_argv(
        ["npx", "vitest", "list", "--json"],
        cwd=project_dir,
        timeout_s=_COLLECT_TIMEOUT_S,
    )
    if spawned.is_err:
        _log.error("collect_ts_tests: vitest list failed to spawn in %s", project_dir)
        return Err(TestingError.CollectFailed)
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.error(
            "collect_ts_tests: vitest list exited %d in %s: %s",
            result.returncode,
            project_dir,
            result.stderr[-500:],
        )
        return Err(TestingError.CollectFailed)
    return Ok(_parse_vitest_json(result.stdout))


# frob:ticket T-0587
def _vitest_node_id(root: Path, project_dir: Path, file: str, name: str) -> str:
    """A `(file, name)` pair from `_parse_vitest_json` as a `path::qualname`
    symref, `file` resolved relative to `project_dir` (vitest's own
    default) unless it is already absolute."""
    file_path = Path(file)
    if file_path.is_absolute():
        rel_file = file_path.relative_to(root).as_posix()
    else:
        rel_file = (project_dir / file_path).relative_to(root).as_posix()
    return f"{rel_file}::{name}"


# frob:doc docs/modules/testing.md#public-api
# frob:ticket T-0587
def collect_ts_tests(root: Path) -> Result[CollectedTests, TestingError]:
    """`npx vitest list --json` node ids for every discovered vitest project
    (a directory whose `package.json` declares a `vitest` dependency, T-0587),
    mirroring `collect_rust_tests`'s per-crate discovery/cache shape. Cached
    on the projects' `package.json` + test-file content hash. Degrades to an
    empty, `Ok` result (with a warning, never a hard failure) when `npx` is
    not on PATH -- a missing node toolchain must not fail collection for
    every OTHER language."""
    projects = _find_vitest_projects(root)
    key = _ts_content_key(root, projects)
    cache_path = root / _TS_CACHE_REL
    cached = _load_cache(cache_path, key)
    if cached is not None:
        _log.debug("collect_ts_tests: cache hit, %d node id(s)", len(cached))
        return Ok(CollectedTests(node_ids=cached))

    node_ids: set[str] = set()
    for project_dir in projects:
        listed = _run_vitest_list(project_dir)
        if listed.is_err:
            return Err(listed.danger_err)
        for file, name in listed.danger_ok:
            node_ids.add(_vitest_node_id(root, project_dir, file, name))

    frozen = frozenset(node_ids)
    _store_cache(cache_path, key, frozen)
    _log.info("collect_ts_tests: collected %d node id(s)", len(frozen))
    return Ok(CollectedTests(node_ids=frozen))


# ---------------------------------------------------------------------------
# C/C++: `ctest --show-only=json-v1`, one already-configured build directory
# per discovered CMakeLists.txt project (T-0587)
# ---------------------------------------------------------------------------

# frob:ticket T-0587
_CTEST_BUILD_DIRNAME = "build"


# frob:ticket T-0587
def _find_cmake_projects(root: Path) -> list[Path]:
    """Directories holding a `CMakeLists.txt`, exclusions pruned (mirrors
    `_find_crates`'s Cargo.toml walk). A `build/` directory (a previous
    cmake configure's output, which typically nests a COPY of its parent's
    `CMakeLists.txt`) is never descended into as a project root of its own
    -- it is only inspected later, via `_ctest_build_dir`, as the
    conventional build directory belonging to the project that owns it."""
    exclude_globs = load_exclude_globs(root)
    found: list[Path] = []
    # frob:waive WALK001 reason="needs per-directory build/ pruning the file-only iter_files/walk_pruned API cannot express; already prunes via _prune_dirnames using frob.excludes primitives"  # noqa: E501
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = _prune_dirnames(Path(dirpath), root, dirnames, exclude_globs)
        dir_path = Path(dirpath)
        if dir_path.name == _CTEST_BUILD_DIRNAME:
            dirnames[:] = []
            continue
        if "CMakeLists.txt" in filenames:
            found.append(dir_path)
    return sorted(found)


# frob:ticket T-0587
def _ctest_build_dir(project_dir: Path) -> Path | None:
    """The conventional `build/` directory for `project_dir` if it already
    holds a generated `CTestTestfile.cmake`, else `None`. Collection
    deliberately never runs `cmake` itself to configure a fresh build dir
    (too heavy and too project-specific for a collection pass, unlike
    `cargo test --list` which builds implicitly) -- it only lists a build
    that has already been configured (T-0587)."""
    candidate = project_dir / _CTEST_BUILD_DIRNAME / "CTestTestfile.cmake"
    return candidate.parent if candidate.exists() else None


# frob:ticket T-0587
def _find_ctest_dirs(root: Path) -> list[Path]:
    """Every already-configured ctest build directory discovered under `root`."""
    build_dirs: list[Path] = []
    for project_dir in _find_cmake_projects(root):
        build_dir = _ctest_build_dir(project_dir)
        if build_dir is not None:
            build_dirs.append(build_dir)
    return sorted(build_dirs)


# frob:ticket T-0886
# `add_test(<name> "<command>" ...)`, the canonical positional form ctest
# ALWAYS normalizes both the `add_test(NAME ... COMMAND ...)` keyword form
# and the legacy positional form down to in a generated `CTestTestfile.cmake`
# (verified empirically: CMake 3.22 emits this exact shape for both input
# spellings) -- one regex is enough to cover both source conventions.
_ADD_TEST_RE = re.compile(r'add_test\(([^\s()]+)\s+"([^"]+)"')

# frob:ticket T-0886
# `gtest_discover_tests()` (CMake's bundled GoogleTest module) does not
# write its per-case `add_test()` calls into `CTestTestfile.cmake` directly
# -- it writes a small bootstrap that `include()`s a sibling
# `<target>_tests.cmake` file (regenerated by a POST_BUILD custom command
# after the test binary is built), which DOES hold one real
# `add_test(<TestSuite.TestCase> "<path/to/binary>" ...)` line per
# discovered gtest case. Following one level of `include("...")` is enough
# to reach that generated file without hand-rolling a cmake interpreter.
_INCLUDE_RE = re.compile(r'include\("([^"]+)"\)')

# frob:ticket T-0886
# The object-file path convention CMake's Makefiles AND Ninja generators
# both use (`CMakeFiles/<target>.dir/<relative-source-path>.o`), the only
# generators this repo's own build (see `Makefile`'s `make core`) or a
# typical CI runner uses -- present in `compile_commands.json`'s `command`
# field (`output` on newer CMake, not relied upon since it is absent before
# CMake 3.20). An unrecognized generator's differently-shaped object path
# simply never matches, degrading to "no source mapping" for that entry
# rather than a wrong guess.
_OBJECT_TARGET_RE = re.compile(r"CMakeFiles/([^/]+)\.dir/")


# frob:ticket T-0886
def _parse_ctest_command_map(build_dir: Path) -> dict[str, str]:
    """`test name -> raw command path` for every `add_test()` ctest can see
    in `build_dir`, scanning `CTestTestfile.cmake` and any file it
    `include()`s one level deep (the `gtest_discover_tests()` generated-file
    idiom, see `_INCLUDE_RE`). A best-effort regex scan, not a cmake
    interpreter -- returns a partial (or empty) map on anything it cannot
    confidently parse, never raises; callers treat a missing name as "no
    source mapping available for this test", never a hard failure."""
    mapping: dict[str, str] = {}
    testfile = build_dir / "CTestTestfile.cmake"
    try:
        content = testfile.read_text()
    except OSError:
        return mapping
    to_scan = [content]
    for inc in _INCLUDE_RE.findall(content):
        inc_path = Path(inc)
        if not inc_path.is_absolute():
            inc_path = build_dir / inc_path
        try:
            to_scan.append(inc_path.read_text())
        except OSError:
            continue
    for text in to_scan:
        for name, cmd in _ADD_TEST_RE.findall(text):
            mapping.setdefault(name, cmd)
    return mapping


# frob:ticket T-0886
def _cpp_target_sources(root: Path, build_dir: Path) -> dict[str, frozenset[str]]:
    """`cmake target name -> its compiled source file(s)` (root-relative
    posix paths), parsed from `compile_commands.json`
    (`CMAKE_EXPORT_COMPILE_COMMANDS=ON`) if the project was configured with
    it. Empty when the file is missing, unparseable, or the generator's
    object-path convention does not match `_OBJECT_TARGET_RE` -- callers
    treat an empty/absent mapping the same as "cannot be source-accurate
    for this target", never an error (most projects do not turn this cmake
    option on, and that must not fail collection)."""
    cc_path = build_dir / "compile_commands.json"
    try:
        entries = json.loads(cc_path.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(entries, list):
        return {}
    result: dict[str, set[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        file_field = entry.get("file")
        if not isinstance(file_field, str):
            continue
        haystack = entry.get("output")
        if not isinstance(haystack, str):
            haystack = entry.get("command", "")
        if not isinstance(haystack, str):
            continue
        match = _OBJECT_TARGET_RE.search(haystack)
        if match is None:
            continue
        target = match.group(1)
        file_path = Path(file_field)
        if not file_path.is_absolute():
            directory = entry.get("directory", str(build_dir))
            file_path = Path(directory) / file_path
        try:
            rel = file_path.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        result.setdefault(target, set()).add(rel)
    return {target: frozenset(files) for target, files in result.items()}


# frob:ticket T-0886
def _cpp_test_source(
    name: str,
    command_map: dict[str, str],
    target_sources: dict[str, frozenset[str]],
) -> str | None:
    """The single real source file `name` (a ctest test name) can be traced
    to, or `None` when the mapping is missing or ambiguous. Source-accurate
    ONLY when the test's registered executable resolves (by target-name
    stem) to EXACTLY ONE compiled source file -- a binary built from
    multiple `.cpp` files cannot be attributed to one of them without
    per-case symbol/line information this function deliberately does not
    attempt (that would risk a wrong guess; `None` here means the caller
    falls back to the build-dir anchor instead, loudly)."""
    command = command_map.get(name)
    if command is None:
        return None
    target = Path(command).stem
    sources = target_sources.get(target)
    if sources is None or len(sources) != 1:
        return None
    return next(iter(sources))


# frob:ticket T-0886
def _cpp_node_id(source: str, name: str) -> str:
    """`source::name` with `name`'s dots (a gtest `TestSuite.TestCase` name)
    normalized to `::`, mirroring `frob.gates._symref_to_nodeid`'s own
    dot-to-`::` qualname transform on the `frob:tests` directive side --
    without this, a directive written `path::TestSuite::TestCase` could
    never match a collected id that still spelled it `TestSuite.TestCase`."""
    return f"{source}::{name.replace('.', '::')}"


# frob:ticket T-0587
# frob:ticket T-0886
def _ctest_content_key(root: Path, build_dirs: list[Path]) -> str:
    """Sha256 over every discovered build dir's `CTestTestfile.cmake` AND
    `compile_commands.json` content (T-0886 added the latter as a real
    collection input, once the source-accurate mapping started reading it)
    -- hashing both is sufficient to invalidate the cache on any test-set
    OR source-mapping change (a reconfigure, an added/removed `add_test()`,
    a source file added to/removed from a target) without needing to hash
    the whole source tree."""
    hasher = hashlib.sha256()
    testfiles = sorted(
        f
        for d in build_dirs
        for f in (d / "CTestTestfile.cmake", d / "compile_commands.json")
    )
    for path in testfiles:
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            _log.warning("collect_cpp_tests: could not read %s: %s", path, exc)
            continue
        rel = path.relative_to(root).as_posix()
        hasher.update(f"{rel}:{digest}\n".encode())
    return hasher.hexdigest()


# frob:ticket T-0587
def _parse_ctest_json(stdout: str, build_dir: Path) -> Result[list[str], TestingError]:
    """Every registered test `name` from a `ctest --show-only=json-v1`
    payload (the documented CMake json-v1 schema: `{"tests": [{"name":
    ...}, ...]}`). An unparseable payload is a genuine `Err`, not a silent
    empty list -- unlike a missing tool, a malformed payload from an
    installed ctest means something is actually broken."""
    try:
        doc = json.loads(stdout)
    except ValueError as exc:
        _log.error(
            "collect_cpp_tests: unparseable ctest json in %s: %s", build_dir, exc
        )
        return Err(TestingError.CollectFailed)
    names = [t["name"] for t in doc.get("tests", []) if isinstance(t.get("name"), str)]
    return Ok(names)


# frob:ticket T-0587
# frob:waive ARCH103 reason="T-0977: ctest-availability-guarded subprocess wrapper -- \
# the missing-tool degrade-with-warning IS the honest-vacuous- pass behavior T-0587 \
# documents this function for, not a separate concern"
def _run_ctest_list(build_dir: Path) -> Result[list[str], TestingError]:
    """Spawn `ctest --test-dir <build_dir> --show-only=json-v1`. Degrades to
    an empty, `Ok` result (with a warning, not a hard failure) when `ctest`
    is not on PATH -- a repo with no C/C++ toolchain installed must not
    fail collection for every OTHER language (T-0587)."""
    if shutil.which("ctest") is None:
        _log.warning(
            "collect_cpp_tests: ctest not found on PATH, skipping %s", build_dir
        )
        return Ok([])
    spawned = run_argv(
        ["ctest", "--test-dir", str(build_dir), "--show-only=json-v1"],
        cwd=build_dir,
        timeout_s=_COLLECT_TIMEOUT_S,
    )
    if spawned.is_err:
        _log.error("collect_cpp_tests: ctest failed to spawn in %s", build_dir)
        return Err(TestingError.CollectFailed)
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.error(
            "collect_cpp_tests: ctest --show-only exited %d in %s: %s",
            result.returncode,
            build_dir,
            result.stderr[-500:],
        )
        return Err(TestingError.CollectFailed)
    return _parse_ctest_json(result.stdout, build_dir)


def _collect_cpp_build_dir(
    root: Path, build_dir: Path
) -> Result[set[str], TestingError]:
    """One configured build dir's ctest node ids -- source-mapped where
    `_cpp_test_source` resolves an unambiguous compiled source, loudly
    build-dir-anchored otherwise (T-0886; see `collect_cpp_tests`)."""
    listed = _run_ctest_list(build_dir)
    if listed.is_err:
        return Err(listed.danger_err)
    rel_build = build_dir.relative_to(root).as_posix()
    command_map = _parse_ctest_command_map(build_dir)
    target_sources = _cpp_target_sources(root, build_dir)
    node_ids: set[str] = set()
    mapped = 0
    fell_back = 0
    for name in listed.danger_ok:
        source = _cpp_test_source(name, command_map, target_sources)
        if source is not None:
            node_ids.add(_cpp_node_id(source, name))
            mapped += 1
        else:
            node_ids.add(f"{rel_build}::{name}")
            fell_back += 1
    if fell_back:
        _log.warning(
            "collect_cpp_tests: FALLBACK -- %d/%d test(s) in %s could not "
            "be source-mapped (no unambiguous compiled source found via "
            "compile_commands.json), anchored to the build dir instead of "
            "a real source file",
            fell_back,
            mapped + fell_back,
            build_dir,
        )
    return Ok(node_ids)


# frob:doc docs/modules/testing.md#public-api
# frob:ticket T-0587
def collect_cpp_tests(root: Path) -> Result[CollectedTests, TestingError]:
    """`ctest --test-dir <dir> --show-only=json-v1` node ids for every
    already-configured CMake build directory under `root` (one holding a
    generated `CTestTestfile.cmake`, discovered from a `CMakeLists.txt`
    project root's conventional `build/` subdirectory, T-0587). Collection
    never invokes `cmake` itself to configure a fresh build -- only an
    already-configured one is listed, mirroring `collect_rust_tests`'s
    per-crate shape as closely as ctest's own model allows.

    SOURCE-ACCURATE where it can be, honestly degraded where it cannot
    (T-0886): investigation found `ctest --show-only=json-v1`'s own
    `backtrace` field anchors to the CMake SCRIPT location of the
    `add_test()` call (almost always `CMakeLists.txt` itself, or a
    `gtest_discover_tests()` call site) -- never the real test source file
    -- so it cannot answer the source-accuracy question at all, on any
    CMake version. What DOES work: `CTestTestfile.cmake` (and any
    `gtest_discover_tests()`-generated file it `include()`s, T-0886)
    literally spells out each test's executable path via `add_test(<name>
    "<path>")`; cross-referencing that executable's cmake TARGET NAME
    against `compile_commands.json` (`_cpp_target_sources`) gives the
    target's real compiled source file(s) whenever the project was
    configured with `CMAKE_EXPORT_COMPILE_COMMANDS=ON`. When a target
    compiles from exactly ONE source file -- the common shape for a
    dedicated test binary, including every gtest case
    `gtest_discover_tests()` registers against it -- that source file IS
    the test's real location, and the node id anchors there
    (`_cpp_node_id`) exactly like the python/rust/ts collectors already do
    for their own languages. A test whose executable cannot be resolved to
    exactly one compiled source (no `compile_commands.json`, an unmatched
    generator, or a multi-source binary that would be a guess) falls back
    to the old build-dir anchor (`<build_dir>::<test name>`) -- loudly: one
    `collect_cpp_tests: FALLBACK` warning per build dir naming how many of
    its tests could not be source-mapped, never a silent downgrade. Cached
    on every discovered `CTestTestfile.cmake` + `compile_commands.json`
    content hash. Degrades to an empty, `Ok` result (with a warning, never
    a hard failure) when `ctest` is not on PATH."""
    build_dirs = _find_ctest_dirs(root)
    key = _ctest_content_key(root, build_dirs)
    cache_path = root / _CTEST_CACHE_REL
    cached = _load_cache(cache_path, key)
    if cached is not None:
        _log.debug("collect_cpp_tests: cache hit, %d node id(s)", len(cached))
        return Ok(CollectedTests(node_ids=cached))

    node_ids: set[str] = set()
    for build_dir in build_dirs:
        collected = _collect_cpp_build_dir(root, build_dir)
        if collected.is_err:
            return Err(collected.danger_err)
        node_ids |= collected.danger_ok

    frozen = frozenset(node_ids)
    _store_cache(cache_path, key, frozen)
    _log.info("collect_cpp_tests: collected %d node id(s)", len(frozen))
    return Ok(CollectedTests(node_ids=frozen))


__all__ = [
    "collect_cpp_tests",
    "collect_python_tests",
    "collect_rust_tests",
    "collect_ts_tests",
]
