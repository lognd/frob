"""`pytest --collect-only` python test collection, cached by source content
hash under `.frob/`. The rust/TS/C++ collectors (`cargo test -- --list`,
`vitest list --json`, `ctest --show-only=json-v1`) live in their own
`frob.testing._collect_rust`/`_collect_ts`/`_collect_cpp` sibling modules
(T-1074 split -- this module used to hold all four; every name those
modules define is re-imported here so `from frob.testing._collect import
...` call sites keep resolving unchanged, matching this repo's existing
`tickets/_evidence.py`-style split precedent). Cache-file and directory-walk
primitives shared across all four languages live in
`frob.testing._collect_shared`. T-4409: the python collector's own cache
key / native-build-fingerprint / cross-call state helpers (content hash,
`[[native]]` fingerprinting, `python_collection_failure_detail` and its
siblings, `drop_collection_cache`) live in `frob.testing._collect_python_
cache`, split out to keep this module under LARGE001's 800-line threshold
-- the `pytest --collect-only` invocation/parsing itself (spawning the
collector, parsing node ids, unioning nested `[[test.runner]] cwd`
projects) stays here. Every name that module defines is re-imported here
too, for the same call-site-stability reason as the T-1074 split."""
# frob:waive ARCH102 reason="T-1161 added python_collection_failure_detail, one more \
# read accessor over this module's existing collect_python_tests/_run_collect_only \
# outer-collection pair (it reads the exact module-level detail those two functions \
# populate on failure) -- the naming/usage clustering heuristic cannot see that \
# state-sharing coupling since it groups by name-prefix/direct-call edges, not by \
# shared module-level state; splitting this one read accessor into its own module \
# would separate it from the state it exists to read"

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.gitio import excerpt, run_argv
from frob.logging import get_logger
from frob.process._pytest_spawn import pytest_importable, resolve_pytest_argv

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
from frob.testing._collect_kotlin import (  # noqa: F401
    _find_junit_report_dirs,
    _find_kotlin_gradle_projects,
    _find_kotlin_source,
    _gradle_build_uses_kotlin,
    _junit_report_dir,
    _kotlin_content_key,
    _kotlin_node_id,
    _parse_junit_xml,
    collect_kotlin_tests,
)
from frob.testing._collect_python_cache import (  # noqa: F401
    _add_collection_platform_skipped,
    _autorebuild_missing_natives,
    _collection_cache_key,
    _compiled_artifacts,
    _content_key,
    _find_test_files,
    _is_nested_python_runner,
    _load_natives_or_empty,
    _missing_natives,
    _native_artifact_digest,
    _native_fingerprint,
    _parse_platform_skipped,
    _platform_skipped_test_modules,
    _python_runner_cwds,
    _set_collection_failure_detail,
    _set_collection_missing_natives,
    _set_collection_platform_skipped,
    _walk_test_files,
    drop_collection_cache,
    python_collection_failure_detail,
    python_collection_missing_natives,
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
    _KOTLIN_CACHE_REL,
    _RUST_CACHE_REL,
    _TS_CACHE_REL,
    _load_cache,
    _load_cache_extra,
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
from frob.testing._models import CollectedTests
from frob.testing._runners import TestingError
from frob.tickets._worktree_guard import apply_agent_env, warn_if_xdist_bound_missing

_log = get_logger(__name__)

_NO_TESTS_COLLECTED_EXIT = 5


# frob:ticket T-4349
# frob:tests \
# tests/test_testing_collect.py::TestCollectorPython.test_prefers_cwds_own_venv_when_py\
# test_importable
# frob:tests \
# tests/test_testing_collect.py::TestCollectorPython.test_falls_back_to_sys_executable_\
# with_no_venv
# frob:tests \
# tests/test_testing_collect.py::TestCollectorPython.test_falls_back_to_sys_executable_\
# when_venv_pytest_unimportable
def _collector_python(cwd: Path) -> str:
    """T-4349: the interpreter `_run_collect_only` should collect `cwd`
    with -- `cwd`'s own `.venv/bin/python` when it exists AND has `pytest`
    importable through it, else `sys.executable` (T-4327's fallback,
    unchanged).

    T-4327 made `sys.executable` the ONE spawn convention so a THROWAWAY
    fixture with no environment of its own (no `.venv`, nothing for `uv`
    to sync) never routes through `uv run pytest`'s VIRTUAL_ENV-fallback
    footgun -- that fix stays exactly as it was for exactly that case.
    But `cwd` is not always a throwaway fixture: a freshly scaffolded
    project (`tests/system/test_scaffold_dx.py`) runs a real `uv sync`
    before `frob check`, giving it a real `.venv` with its own `pytest`
    and its own dependencies installed -- collecting THAT with `sys.
    executable` uses the calling frob process's OWN interpreter (the
    globally-installed `uv tool`'s venv, or this repo's dev venv), which
    has neither the scaffolded project's dependencies nor any reason to
    import them, and fails with e.g. `ModuleNotFoundError: No module
    named 'demo'` on every test module that imports the project's own
    package. Preferring `cwd`'s own venv when it is actually usable
    (`pytest` importable through it, mirroring `_python_for_tree`'s
    `frob`-importability probe in `frob.app.ticket_runner._verify`, T-3305's
    same probe-don't-assume principle applied to a different importable)
    fixes that without reintroducing any `uv` dependency: this never
    shells out through `uv`, it only chooses WHICH already-built
    interpreter's `-m pytest` to invoke. A `cwd` with no `.venv`, or one
    whose `pytest` is not importable (T-4327's original throwaway-fixture
    case), falls straight through to `sys.executable` exactly as before."""
    venv_python = cwd / ".venv" / "bin" / "python"
    if venv_python.is_file() and pytest_importable(str(venv_python)):
        return str(venv_python)
    return sys.executable


# frob:ticket T-4349
def _run_collect_only(cwd: Path) -> Result[frozenset[str], TestingError]:
    """Spawn `pytest --collect-only -q` in `cwd` and parse its stdout into
    node ids relative to `cwd` (the caller reroots them if `cwd` is not the
    repo root, T-0317). T-1161: on failure, also records a human-readable
    detail (argv/exit code/stderr tail) via `_set_collection_failure_detail`
    for `python_collection_failure_detail`'s later read -- the `Result`
    contract itself is unchanged, every existing caller keeps working
    exactly as before.

    T-4327 root cause fix: `cwd` is frequently a THROWAWAY fixture project
    with no environment of its own (a `tests/` fixture, a `[[test.runner]]
    cwd` nested project), never a real sibling checkout of THIS repo -- so
    spawning `uv run pytest` here was always relying on `uv`'s "fall back to
    an already-active, compatible VIRTUAL_ENV" behavior to find `pytest` at
    all, rather than ever syncing/installing it into `cwd` itself. T-4308
    made that ambient `VIRTUAL_ENV` reliably set; the CI run that followed
    (macOS leg) then MEASURED that a newer `uv` (0.12.10, installed fresh
    because that leg's `setup-uv` cache key -- keyed by system-python-version,
    `aarch64-apple-darwin-3.14.7` -- had never been populated before, versus
    ubuntu's leg restoring a `uv` binary a stale cache had kept around;
    neither leg pins a `uv` version) validates that fallback by PATH: it
    compares
    `VIRTUAL_ENV` against `cwd`'s own discovered project's configured `.venv`
    path, and when they disagree (they always do -- `VIRTUAL_ENV` points at
    THIS repo's own venv, never a fixture's) it warns and ignores the
    variable, builds a brand-new empty venv at `cwd`, defaults its Python
    version (the fixture declares no `requires-python`, so whatever
    interpreter `uv` happens to discover next), and fails to find `pytest`
    inside it -- unrelated to `sys.platform`, and just as reachable on any
    leg whose `uv` cache happens to miss.

    The fix is not `--active` (still a `uv`-version-and-cache-dependent
    fallback path, still capable of drifting again on the next `uv`
    release) and not skipping venv creation alone (still resolves `pytest`
    through `uv`/PATH, still exposed to the identical path-mismatch check).
    Routing through `resolve_pytest_argv` (T-3311, already the ONE
    pytest-spawn convention this codebase adopted for exactly this
    situation) instead runs `pytest` as a module of THIS interpreter
    (`sys.executable`, the interpreter `frob` itself is already running
    under) -- `uv` is never invoked for this spawn at all, so there is no
    project/venv to discover, no version to default, and no cache-driven
    `uv` version skew to be exposed to."""
    # -o addopts= neutralizes the project's own addopts: a configured -q
    # would stack with ours into -qq, which switches --collect-only from
    # node ids to per-file counts (and -n auto adds xdist noise) -- the
    # evidence oracle would silently see an empty set (observed: INV001
    # false positives on every invariant).
    collector_python = _collector_python(cwd)
    resolved_argv = resolve_pytest_argv(
        # T-4382: -rs reports skip reasons in pytest's summary output --
        # the ONLY way a --collect-only run can produce a SKIPPED line at
        # all is a module-level `pytest.skip(allow_module_level=True)`
        # (per-test skipif decorators are evaluated at setup time, never
        # during collection), so this is a cheap, precise signal for
        # platform-excluded test modules with no risk of colliding with
        # the existing "::"-containing node-id line filter below.
        "--collect-only",
        "-q",
        "-rs",
        "-o",
        "addopts=",
        python=collector_python,
    )
    if resolved_argv.is_err:
        _log.error(
            "collect_python_tests: pytest is not importable through %s -- "
            "cannot collect in %s",
            collector_python,
            cwd,
        )
        _set_collection_failure_detail(
            f"pytest not importable through {collector_python} "
            f"(cwd={cwd}): {resolved_argv.danger_err}"
        )
        return Err(TestingError.CollectFailed)
    argv = tuple(resolved_argv.danger_ok)
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
        # T-4349: pytest writes its own collection errors (ImportError
        # tracebacks, "N errors during collection") to STDOUT, not
        # stderr -- a genuinely empty stderr here is normal pytest
        # behavior, not a diagnostic failure, and reporting only "stderr
        # tail: <nothing>" leaves the actual cause unquoted (measured:
        # COV003's empty stderr tail on the scaffold-check regression).
        # Fall back to the stdout tail whenever stderr has nothing to
        # say, so the detail always quotes SOME real output when pytest
        # produced any.
        stream_label, stream_text = (
            ("stderr", result.stderr)
            if result.stderr.strip()
            else ("stdout (stderr was empty)", result.stdout)
        )
        _set_collection_failure_detail(
            f"{' '.join(argv)} (cwd={cwd}) exited {result.returncode}\n"
            f"{stream_label} tail:\n{excerpt(stream_text)}"
        )
        return Err(TestingError.CollectFailed)
    _add_collection_platform_skipped(_parse_platform_skipped(result.stdout))
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
# frob:ticket T-3099
# frob:tests tests/unit/test_pytest_spawn_env_wiring.py::TestCollectPythonTestsWiring.test_must_fire_applies_and_warns_before_collection  # noqa: E501
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
    # T-3099: apply the T-3094 fleet-aware xdist bound in-process before
    # this function's own `uv run pytest --collect-only ...` spawns (below,
    # via `_run_collect_only`/`_collect_nested_python`) so those children
    # inherit it with no shell `eval` hop; warn loudly if a fleet context
    # exists but the bound still did not make it into this process's env.
    apply_agent_env(root)
    warn_if_xdist_bound_missing(root)
    natives = _load_natives_or_empty(root)
    missing = _missing_natives(natives)
    if missing:
        missing = _autorebuild_missing_natives(root, natives, missing)
    _set_collection_missing_natives(missing)
    # T-4382/T-4390: reset (not accumulate) here -- this is the ONE point
    # in collect_python_tests every return path passes through before any
    # _run_collect_only call, mirroring missing_natives' single-reset
    # discipline above. A cache HIT below used to return without ever
    # calling _run_collect_only, so this read back () even when
    # platform-skipped modules exist (T-4382's own documented gap,
    # measured live on Windows CI: COV003 kept erroring on the SAME
    # platform-skipped evidence T-4382 fixed, because the SAME job runs
    # an earlier `frob test`/`frob check` pass that warms this cache
    # before COV003's own collection call hits it) -- T-4390 closes it by
    # round-tripping platform_skipped through the cache's own `extra`
    # payload (_load_cache_extra/_store_cache), below.
    _set_collection_platform_skipped(())
    key = _collection_cache_key(root, natives)
    cache_path = root / _CACHE_REL
    cached = _load_cache(cache_path, key)
    if cached is not None:
        cached_extra = _load_cache_extra(cache_path, key)
        cached_skipped = tuple(
            (str(f), str(r)) for f, r in cached_extra.get("platform_skipped", [])
        )
        _set_collection_platform_skipped(cached_skipped)
        _log.debug(
            "collect_python_tests: cache hit, %d node id(s), %d platform-skipped "
            "module(s)",
            len(cached),
            len(cached_skipped),
        )
        _set_collection_failure_detail(None)
        return Ok(
            CollectedTests(
                node_ids=cached,
                missing_natives=missing,
                platform_skipped=cached_skipped,
            )
        )

    collected = _run_collect_only(root)
    if collected.is_err:
        if missing:
            # T-2090: collection failed AND at least one declared native is
            # still missing after the autorebuild attempt above -- name it
            # and its build_cmd explicitly rather than letting the raw
            # `pytest --collect-only exited N` detail (still recorded by
            # `_run_collect_only`) stand alone; that raw detail says nothing
            # about the actual, already-known cause.
            remedy = ", ".join(
                f"{spec.name} (run: {spec.build_cmd})" for spec in missing
            )
            # `_run_collect_only` (called just above) always sets a detail
            # before returning its own Err, so `python_collection_failure_
            # detail()` is never None here -- no `or ''` fallback needed.
            _set_collection_failure_detail(
                f"{python_collection_failure_detail()}\n"
                f"declared native extension(s) not built: {remedy} -- build "
                f"it, then re-run"
            )
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
    platform_skipped = _platform_skipped_test_modules()
    _store_cache(
        cache_path,
        key,
        frozen,
        extra={"platform_skipped": [list(pair) for pair in platform_skipped]}
        if platform_skipped
        else None,
    )
    _log.info(
        "collect_python_tests: collected %d node id(s), %d declared native(s) missing",
        len(frozen),
        len(missing),
    )
    return Ok(
        CollectedTests(
            node_ids=frozen,
            missing_natives=missing,
            platform_skipped=platform_skipped,
        )
    )


# frob:ticket T-3847
# frob:waive COV001 reason="a frob:doc anchor here would live in \
# docs/modules/testing.md, whose own SCOPE002 closure (every OTHER symbol that shared \
# doc file describes) is out of proportion to pull into T-3847's narrow \
# evidence-verification-wiring scope -- same doc-anchor scope-closure tension \
# src/frob/gates/_rule_id_scan.py's SCANNED_BASES/RETIRED_RULE_IDS waivers already \
# document (T-1010/ T-1937); this dict's own docstring below is the authoritative \
# description"
LANGUAGE_COLLECTORS: dict[
    str, Callable[[Path], Result[CollectedTests, TestingError]]
] = {
    "python": collect_python_tests,
    "rust": collect_rust_tests,
    "cpp": collect_cpp_tests,
    "kotlin": collect_kotlin_tests,
    "ts": collect_ts_tests,
}
"""T-3847: the ONE registry of every language this repo can collect test
node ids for, keyed by the same language name a `[[test.runner]]` entry's
`language=` field uses. `frob.app.ticket_runner._verify._verify_ids_passing`
derives its evidence-verification bucket set by iterating this dict rather
than a hand-written per-language dict -- adding a new collector here wires
it into verification automatically, closing the exact gap T-3847 measured
(cpp/kotlin/ts collectors existed and were simply never consulted).
catch2 and doctest tests registered via CMake's `catch_discover_tests()`/
`doctest_discover_tests()` are ALREADY reachable through `collect_cpp_tests`
(it reads `ctest --show-only=json-v1`, which is framework-agnostic --
any `add_test()` entry a CMake test-discovery macro generates is
collected, regardless of which C++ test framework produced it), so no
separate catch2/doctest entry exists or is needed here. `cargo nextest`
is likewise IN with no separate entry: nextest re-executes the SAME
compiled test binaries `cargo test` does and reports the SAME
`module::path::test_name` ids (it changes the harness/output format, not
the test identity), so an id `collect_rust_tests` already collects binds
correctly whether the evidence was run via `cargo test` or `cargo
nextest run`. jest is OUT for now: unlike catch2/doctest/nextest, it is
NOT a drop-in alternate frontend over an already-collected id space --
it is a distinct JS/TS runner with its own CLI, JSON reporter shape, and
node-id spelling, so supporting it is genuine new collector work, not a
generalization of `collect_ts_tests`'s existing vitest path. Filed as
T-3921 rather than folded into this ticket."""


__all__ = [
    "LANGUAGE_COLLECTORS",
    "collect_cpp_tests",
    "collect_kotlin_tests",
    "collect_python_tests",
    "collect_rust_tests",
    "collect_ts_tests",
    "python_collection_failure_detail",
]
