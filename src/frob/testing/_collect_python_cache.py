"""T-4409: python test-collection cache/state helpers, split out of
`_collect.py` to keep that module under LARGE001's 800-line threshold. No
behavior change from the code this replaces -- covers the collection
content-hash/native-build-fingerprint cache key, the module-level state
`collect_python_tests` (in `_collect.py`) exposes through `python_collection_
failure_detail`/`python_collection_missing_natives`/`_platform_skipped_test_
modules`, and `drop_collection_cache`'s cache-file escape hatch. The
`pytest --collect-only` invocation/parsing itself (spawning the collector,
parsing node ids, unioning nested `[[test.runner]] cwd` projects) stays in
`_collect.py`; every name here is re-imported there so `from frob.testing.
_collect import ...` call sites keep resolving unchanged (T-1074's existing
split precedent, applied again).
"""
# frob:waive ARCH102 reason="the naming/usage clustering heuristic sees 3 unrelated \
# clusters (the failure-detail/missing-natives/platform-skipped module-state \
# read/write triples, the native-build fingerprint chain, and the \
# content-hash/cache-key pair), but this module's own docstring names the ONE concern \
# all three are facets of: everything the python collection cache key is built from, \
# and everything collect_python_tests's outer call needs to read back across a call. \
# The heuristic groups by name-prefix/ direct-call edges, not by shared module purpose \
# -- same T-1651-grade shape as this repo's other LARGE001-split-module ARCH102 \
# waivers (e.g. frob.gates._coverage, frob.gates._waive)"

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import re
from pathlib import Path

from frob.excludes import load_exclude_globs, walk_pruned
from frob.logging import get_logger
from frob.testing._collect_shared import _CACHE_REL
from frob.testing._models import NativeSpec, RunnerSpec
from frob.testing._runners import load_natives, load_runners

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
# frob:tests \
# tests/test_testing_collect.py::TestPythonCollectionFailureDetail.test_none_before_any\
# _call
def python_collection_failure_detail() -> str | None:
    """The most recent OUTER `collect_python_tests` failure's detail
    string (argv + exit code + stderr tail, T-1161), or `None` if the last
    collection attempt succeeded (or none has run yet in this process).
    Read by `frob.gates.coverage_gate`'s COV003 wiring immediately after
    observing `collect_python_tests(...).is_err` to build one honest
    finding instead of treating every archived evidence id as
    independently unresolved."""
    return _last_python_collection_failure_detail


def _set_collection_failure_detail(detail: str | None) -> None:
    """T-1161: record (or clear, `detail=None`) `_last_python_collection_
    failure_detail` -- the single write point both `_run_collect_only`
    (on failure) and `collect_python_tests` (on any success/cache-hit
    path, so a stale failure detail can never outlive the run that
    produced it) go through."""
    global _last_python_collection_failure_detail
    _last_python_collection_failure_detail = detail


# frob:ticket T-2090
#: T-2090: the most recent `collect_python_tests` call's `missing_natives`
#: (post-autorebuild-attempt), mirroring `_last_python_collection_failure_
#: detail`'s module-state pattern above. Lets a caller that only has a
#: pytest node-id frozenset in hand (`add_evidence`'s `collected` param
#: predates `CollectedTests` and cannot be widened without breaking every
#: existing caller) still ask "was an unresolved id's absence explained by
#: a still-missing native, or is the test genuinely gone" -- the
#: distinction `_check_evidence_resolution` needs to stop advising a cache
#: deletion for a case the cache was never responsible for.
_last_missing_natives: tuple[NativeSpec, ...] = ()


# frob:doc docs/modules/testing.md#public-api
# frob:tests \
# tests/test_testing.py::TestCollectPythonTests.test_python_collection_missing_natives_\
# reflects_last_call
def python_collection_missing_natives() -> tuple[NativeSpec, ...]:
    """The most recent `collect_python_tests` call's `missing_natives`,
    AFTER its own autorebuild attempt (T-2090) -- `()` if every declared
    native was already built, or if none has run yet in this process.
    Read by evidence-resolution wiring right after an unresolved id to
    tell "a native is still missing, name it" apart from "this test
    genuinely does not exist", which look identical from a bare node-id
    frozenset alone."""
    return _last_missing_natives


def _set_collection_missing_natives(missing: tuple[NativeSpec, ...]) -> None:
    """T-2090: record `missing` as the current `python_collection_missing_
    natives()` value -- the single write point `collect_python_tests`
    goes through on every return path (cache hit, fresh collection success,
    and collection failure alike), mirroring `_set_collection_failure_
    detail`'s existing single-write-point discipline so this value can
    never linger stale across two different calls."""
    global _last_missing_natives
    _last_missing_natives = missing


# frob:ticket T-4382
#: T-4382: the most recent `collect_python_tests` call's `platform_
#: skipped` (file, reason) pairs, mirroring `_last_missing_natives`'
#: module-state pattern -- the same "bare frozenset caller" gap
#: `_last_missing_natives` documents applies here: a caller that only
#: has a pytest node-id frozenset in hand cannot ask "was this file
#: excluded at collection time for a platform reason" without a
#: side channel.
_last_platform_skipped: tuple[tuple[str, str], ...] = ()


def _platform_skipped_test_modules() -> tuple[tuple[str, str], ...]:
    """The most recent `collect_python_tests` call's `platform_skipped`
    `(file, reason)` pairs, `()` if none or if collection has not run yet
    in this process. Mirrors `python_collection_missing_natives`'s
    module-state read for the analogous platform-exclusion cause."""
    return _last_platform_skipped


def _set_collection_platform_skipped(skipped: tuple[tuple[str, str], ...]) -> None:
    """T-4382: reset `_platform_skipped_test_modules()` to `skipped` --
    called once at the top of `collect_python_tests`, mirroring
    `_set_collection_missing_natives`'s single-reset-point discipline, so
    a stale value from a PRIOR call can never leak into this one."""
    global _last_platform_skipped
    _last_platform_skipped = skipped


def _add_collection_platform_skipped(skipped: tuple[tuple[str, str], ...]) -> None:
    """T-4382: union `skipped` into the current `platform_skipped_test_
    modules()` value -- `_run_collect_only` calls this once per outer OR
    nested-`[[test.runner]] cwd` collection pass within a single
    `collect_python_tests` call, so accumulation (not overwrite) is
    correct here; `_set_collection_platform_skipped` resets to `()` once
    at the top of `collect_python_tests` before any of these adds run."""
    global _last_platform_skipped
    _last_platform_skipped = _last_platform_skipped + skipped


_SKIPPED_MODULE_LEVEL_RE = re.compile(r"^SKIPPED \[\d+\] ([^:]+):(\d+): (.+)$")


# frob:ticket T-4408
# frob:tests tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape
def _parse_platform_skipped(stdout: str) -> tuple[tuple[str, str], ...]:
    """T-4382: parse `pytest --collect-only -rs`'s stdout for module-level
    skip lines (`SKIPPED [N] <file>:<line>: <reason>`) -- the ONLY shape
    `--collect-only` can produce a SKIPPED summary line for, since it
    never runs a test's body (where a per-test `skipif` decorator would
    normally be evaluated): these lines come exclusively from a module
    calling `pytest.skip(..., allow_module_level=True)` at import time,
    which is exactly the "excluded from collection on this platform"
    shape COV003 needs to distinguish from a genuinely missing test.

    T-4408: pytest reports the file with the platform's native path
    separator, so on Windows this is a backslash path
    (`tests\\unit\\test_stackdump.py`) while every consumer (ticket
    evidence ids, `frob:tests` symrefs) is always POSIX-style
    (forward-slash) by repo convention -- `_evidence_platform_skip_reason`
    and `_edges_platform_skip_reason` both compare these paths with plain
    `==`, so an unnormalized backslash path silently never matches on
    Windows and every platform-skipped POSIX-only test module floods
    COV003/TEST002 instead of being attributed. Normalize to
    forward-slash here, once, at the source, so every downstream
    comparison sees the same shape regardless of platform."""
    found: list[tuple[str, str]] = []
    for line in stdout.splitlines():
        match = _SKIPPED_MODULE_LEVEL_RE.match(line.strip())
        if match is not None:
            found.append((match.group(1).replace("\\", "/"), match.group(3)))
    return tuple(found)


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
        # frob:waive WALK001 reason="bounded to a single already-resolved \
        # package dir's own compiled-artifact siblings, not a repo-wide \
        # walk"  # noqa: E501
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
        except Exception:
            # A `find_spec` surprise is still "cannot resolve this native"
            # (this function's own docstring), the same `None` outcome as
            # the two named exceptions, not a crash of the whole missing-
            # natives scan (EXHAUST001, T-1371).
            found = None
        if found is None or not _compiled_artifacts(found):
            missing.append(spec)
    return tuple(missing)


def _autorebuild_missing_natives(
    root: Path, natives: tuple[NativeSpec, ...], missing: tuple[NativeSpec, ...]
) -> tuple[NativeSpec, ...]:
    """T-2090: when `missing` (from `_missing_natives`) is non-empty, attempt
    `_maybe_autorebuild_natives(root)` and re-scan -- so a fresh worktree's
    FIRST collection call builds the natives itself instead of failing with
    an opaque `pytest --collect-only exited 2` that sent an agent chasing
    the collection cache instead of the actual missing artifact (T-2090's
    root cause). Called ONLY when `missing` is already non-empty (never on
    the common already-built path), matching this ticket's acceptance
    criterion that a rebuild is never triggered speculatively -- a native
    build is slow and land cost is already the fleet's throughput ceiling.
    Deferred import: `frob.gates` imports this module at ITS OWN top level,
    so importing it back here at module scope would cycle; mirrors
    `_maybe_autorebuild_natives`'s own documented precedent for the same
    hazard against `frob.strata`/`frob.natives`."""
    from frob.gates import _maybe_autorebuild_natives

    _log.warning(
        "collect_python_tests: %d declared native(s) missing (%s), attempting "
        "autorebuild before collection",
        len(missing),
        sorted(spec.name for spec in missing),
    )
    _maybe_autorebuild_natives(root)
    return _missing_natives(natives)


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


def _collection_cache_key(root: Path, natives: tuple[NativeSpec, ...]) -> str:
    """The pytest collection cache key: test-file content hash (`_content_key`)
    unioned with the declared natives' build fingerprint (T-0333). Both must
    invalidate the cache -- edited test files change WHAT collects, a rebuilt
    native changes WHETHER `importorskip`-gated tests collect at all."""
    content = _content_key(root)
    native = _native_fingerprint(natives)
    return hashlib.sha256(f"{content}\n{native}".encode()).hexdigest()


# frob:doc docs/modules/testing.md#public-api
# frob:tests \
# tests/test_testing.py::TestNativeFingerprint.test_drop_collection_cache_removes_file
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
