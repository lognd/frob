"""`pytest --collect-only` python test collection, cached by source content
hash under `.frob/`. The rust/TS/C++ collectors (`cargo test -- --list`,
`vitest list --json`, `ctest --show-only=json-v1`) live in their own
`frob.testing._collect_rust`/`_collect_ts`/`_collect_cpp` sibling modules
(T-1074 split -- this module used to hold all four; every name those
modules define is re-imported here so `from frob.testing._collect import
...` call sites keep resolving unchanged, matching this repo's existing
`tickets/_evidence.py`-style split precedent). Cache-file and directory-walk
primitives shared across all four languages live in
`frob.testing._collect_shared`."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/testing/_collect.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"
# frob:waive ARCH102 reason="T-1161 added python_collection_failure_detail, one more \
# read accessor over this module's existing collect_python_tests/_run_collect_only \
# outer-collection pair (it reads the exact module-level detail those two functions \
# populate on failure) -- the naming/usage clustering heuristic cannot see that \
# state-sharing coupling since it groups by name-prefix/direct-call edges, not by \
# shared module-level state; splitting this one read accessor into its own module \
# would separate it from the state it exists to read"

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.excludes import load_exclude_globs, walk_pruned
from frob.gitio import excerpt, run_argv
from frob.logging import get_logger

# T-1074: the rust/ts/cpp collector bodies now live in the sibling
# `_collect_rust`/`_collect_ts`/`_collect_cpp` modules; every name is
# re-imported here (unused within this module, lint-waived below) purely so
# `from frob.testing._collect import <name>` call sites (existing tests,
# `frob.testing.__init__`) keep resolving unchanged after the split.
from frob.testing._collect_cpp import (  # noqa: F401
    _ADD_TEST_RE,
    _CTEST_BUILD_DIRNAME,
    _INCLUDE_RE,
    _OBJECT_TARGET_RE,
    _collect_cpp_build_dir,
    _cpp_node_id,
    _cpp_target_sources,
    _cpp_test_source,
    _ctest_build_dir,
    _ctest_content_key,
    _find_cmake_projects,
    _find_ctest_dirs,
    _parse_ctest_command_map,
    _parse_ctest_json,
    _run_ctest_list,
    collect_cpp_tests,
)
from frob.testing._collect_rust import (  # noqa: F401
    _CARGO_TEST_LINE_RE,
    _NO_LIB_TARGET_RE,
    _cargo_list_result,
    _classify_crate_dir,
    _classify_manifest,
    _collect_rust_uncached,
    _find_crates,
    _find_integration_test_files,
    _integration_module_path_to_symref,
    _module_path_to_symref,
    _parse_cargo_list,
    _run_cargo_list,
    _run_cargo_test_list,
    _rust_content_key,
    collect_rust_tests,
)
from frob.testing._collect_shared import (  # noqa: F401
    _CACHE_REL,
    _COLLECT_TIMEOUT_S,
    _CTEST_CACHE_REL,
    _RUST_CACHE_REL,
    _TS_CACHE_REL,
    _load_cache,
    _prune_dirnames,
    _store_cache,
)
from frob.testing._collect_ts import (  # noqa: F401
    _TS_TEST_NAME_RE,
    _VITEST_DEP_NAME,
    _find_ts_test_files,
    _find_vitest_projects,
    _is_ts_test_file,
    _package_json_uses_vitest,
    _parse_vitest_json,
    _run_vitest_list,
    _ts_content_key,
    _vitest_node_id,
    collect_ts_tests,
)
from frob.testing._models import CollectedTests, NativeSpec, RunnerSpec
from frob.testing._runners import (
    TestingError,
    load_natives,
    load_runners,
)

_log = get_logger(__name__)

# frob:ticket T-1161
#: T-1161: human-readable detail (argv, exit code, stderr tail) for the most
#: recent OUTER `collect_python_tests` collection failure, or `None` after a
#: successful collection (or before any call). `collect_python_tests` keeps
#: returning the same `Err(TestingError.CollectFailed)` its `Result` contract
#: already promises (every existing caller's `.is_err` handling is
#: unaffected) -- this module-level detail is a SEPARATE, additive read
#: `frob.gates.coverage_gate`'s wiring consults right after seeing that Err,
#: so it can report ONE honest `COV003`-adjacent finding naming the real
#: collection failure instead of degrading into a flood of per-evidence
#: `COV003`s (the 2026-07-28 incident this ticket fixes: a corrupted venv
#: shim broke `uv run pytest` outright, and 6219 archived evidence ids each
#: independently "failed to resolve" with no hint at the shared root cause).
_last_python_collection_failure_detail: str | None = None


# frob:doc docs/modules/testing.md#public-api
def python_collection_failure_detail() -> str | None:
    """The most recent OUTER `collect_python_tests` failure's detail
    string (argv + exit code + stderr tail, T-1161), or `None` if the last
    collection attempt succeeded (or none has run yet in this process).
    Read by `frob.gates.coverage_gate`'s COV003 wiring immediately after
    observing `collect_python_tests(...).is_err` to build one honest
    finding instead of treating every archived evidence id as
    independently unresolved."""
    return _last_python_collection_failure_detail


_NO_TESTS_COLLECTED_EXIT = 5


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


def _set_collection_failure_detail(detail: str | None) -> None:
    """T-1161: record (or clear, `detail=None`) `_last_python_collection_
    failure_detail` -- the single write point both `_run_collect_only`
    (on failure) and `collect_python_tests` (on any success/cache-hit
    path, so a stale failure detail can never outlive the run that
    produced it) go through."""
    global _last_python_collection_failure_detail
    _last_python_collection_failure_detail = detail


def _run_collect_only(cwd: Path) -> Result[frozenset[str], TestingError]:
    """Spawn `pytest --collect-only -q` in `cwd` and parse its stdout into
    node ids relative to `cwd` (the caller reroots them if `cwd` is not the
    repo root, T-0317). T-1161: on failure, also records a human-readable
    detail (argv/exit code/stderr tail) via `_set_collection_failure_detail`
    for `python_collection_failure_detail`'s later read -- the `Result`
    contract itself is unchanged, every existing caller keeps working
    exactly as before."""
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
        _set_collection_failure_detail(
            f"{' '.join(argv)} (cwd={cwd}) failed to spawn: {spawned.danger_err}"
        )
        return Err(TestingError.CollectFailed)
    result = spawned.danger_ok
    if result.returncode not in (0, _NO_TESTS_COLLECTED_EXIT):
        _log.error(
            "collect_python_tests: pytest --collect-only exited %d in %s",
            result.returncode,
            cwd,
        )
        _set_collection_failure_detail(
            f"{' '.join(argv)} (cwd={cwd}) exited {result.returncode}\n"
            f"stderr tail:\n{excerpt(result.stderr)}"
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
        _set_collection_failure_detail(None)
        return Ok(CollectedTests(node_ids=cached, missing_natives=missing))

    collected = _run_collect_only(root)
    if collected.is_err:
        return Err(collected.danger_err)
    _set_collection_failure_detail(None)
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


__all__ = [
    "collect_cpp_tests",
    "collect_python_tests",
    "collect_rust_tests",
    "collect_ts_tests",
    "python_collection_failure_detail",
]
