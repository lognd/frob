"""`pytest --collect-only` and `cargo test -- --list`, each cached by source
content hash under `.frob/`."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tomllib
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs
from frob.gitio import GitError, ProcResult, run_argv
from frob.logging import get_logger
from frob.testing._models import CollectedTests, RunnerSpec
from frob.testing._runners import TestingError, _cargo_env, _env_overlay, load_runners

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "pytest-collect.json"
_RUST_CACHE_REL = Path(".frob") / "cargo-collect.json"
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
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = _prune_dirnames(Path(dirpath), root, dirnames, exclude_globs)
        for name in filenames:
            if name.startswith("test_") and name.endswith(".py"):
                found.append(Path(dirpath) / name)
            elif name.endswith("_test.py"):
                found.append(Path(dirpath) / name)
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
    the outer tree's test-file content hash; a nested-cwd collection failure
    degrades to a warning plus that project's tests being absent from the
    result, rather than failing the whole call."""
    key = _content_key(root)
    cache_path = root / _CACHE_REL
    cached = _load_cache(cache_path, key)
    if cached is not None:
        _log.debug("collect_python_tests: cache hit, %d node id(s)", len(cached))
        return Ok(CollectedTests(node_ids=cached))

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
    _log.info("collect_python_tests: collected %d node id(s)", len(frozen))
    return Ok(CollectedTests(node_ids=frozen))


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
    # frob:waive PERF004 reason="one sort of the final result list, not per-iteration"
    exclude_globs = load_exclude_globs(root)
    found: list[Path] = []
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


__all__ = ["collect_python_tests", "collect_rust_tests"]
