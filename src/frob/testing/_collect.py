"""`pytest --collect-only` and `cargo test -- --list`, each cached by source
content hash under `.frob/`."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.testing._models import CollectedTests
from frob.testing._runners import TestingError, _cargo_env, _env_overlay

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "pytest-collect.json"
_RUST_CACHE_REL = Path(".frob") / "cargo-collect.json"
_EXCLUDED_DIRS = frozenset(
    {".git", ".venv", "node_modules", "target", "build", "dist", ".frob"}
)
_COLLECT_TIMEOUT_S = 300.0
_NO_TESTS_COLLECTED_EXIT = 5
_CARGO_TEST_LINE_RE = re.compile(r"^(?P<path>[\w:]+): test$")


def _walk_test_files(root: Path) -> list[Path]:
    """Unordered `test_*.py` / `*_test.py` files under `root`, exclusions pruned."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
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
    """Sha256 over every test file's `(relpath, sha256)` pair -- the cache key."""
    hasher = hashlib.sha256()
    for path in _find_test_files(root):
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


def _run_collect_only(root: Path) -> Result[frozenset[str], TestingError]:
    """Spawn `pytest --collect-only -q` and parse its stdout into node ids."""
    # -o addopts= neutralizes the project's own addopts: a configured -q
    # would stack with ours into -qq, which switches --collect-only from
    # node ids to per-file counts (and -n auto adds xdist noise) -- the
    # evidence oracle would silently see an empty set (observed: INV001
    # false positives on every invariant).
    argv = ("uv", "run", "pytest", "--collect-only", "-q", "-o", "addopts=")
    spawned = run_argv(argv, cwd=root, timeout_s=_COLLECT_TIMEOUT_S)
    if spawned.is_err:
        _log.error("collect_python_tests: pytest --collect-only failed to spawn")
        return Err(TestingError.CollectFailed)
    result = spawned.danger_ok
    if result.returncode not in (0, _NO_TESTS_COLLECTED_EXIT):
        _log.error(
            "collect_python_tests: pytest --collect-only exited %d", result.returncode
        )
        return Err(TestingError.CollectFailed)
    return Ok(
        frozenset(
            line.strip()
            for line in result.stdout.splitlines()
            if "::" in line and not line.startswith(" ")
        )
    )


# frob:doc docs/modules/testing.md#public-api
def collect_python_tests(root: Path) -> Result[CollectedTests, TestingError]:
    """`uv run pytest --collect-only -q` node ids, cached on test-file content hash."""
    key = _content_key(root)
    cache_path = root / _CACHE_REL
    cached = _load_cache(cache_path, key)
    if cached is not None:
        _log.debug("collect_python_tests: cache hit, %d node id(s)", len(cached))
        return Ok(CollectedTests(node_ids=cached))

    collected = _run_collect_only(root)
    if collected.is_err:
        return Err(collected.danger_err)
    node_ids = collected.danger_ok
    _store_cache(cache_path, key, node_ids)
    _log.info("collect_python_tests: collected %d node id(s)", len(node_ids))
    return Ok(CollectedTests(node_ids=node_ids))


# ---------------------------------------------------------------------------
# Rust: `cargo test -- --list`, one crate directory per discovered Cargo.toml
# ---------------------------------------------------------------------------


def _find_crates(root: Path) -> list[Path]:
    """Directories holding a `Cargo.toml`, exclusions pruned, not descending
    into a found crate's own subtree (no nested-manifest workspaces here)."""
    # frob:waive PERF004 reason="one sort of the final result list, not per-iteration"
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
        if "Cargo.toml" in filenames:
            found.append(Path(dirpath))
            dirnames[:] = []
    return sorted(found)


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


def _run_cargo_list(crate_dir: Path) -> Result[list[str], TestingError]:
    """Spawn `cargo test --lib -- --list` in one crate, PyO3 env resolved first
    (never silently skipped -- a missing dev environment is `Err`, not an
    empty test list masquerading as "this crate has no tests")."""
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
            ["cargo", "test", "--lib", "--", "--list"],
            cwd=crate_dir,
            timeout_s=_COLLECT_TIMEOUT_S,
        )
    if spawned.is_err:
        _log.error("collect_rust_tests: cargo failed to spawn in %s", crate_dir)
        return Err(TestingError.CollectFailed)
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.error(
            "collect_rust_tests: cargo test --list exited %d in %s: %s",
            result.returncode,
            crate_dir,
            result.stderr[-500:],
        )
        return Err(TestingError.CollectFailed)
    return Ok(_parse_cargo_list(result.stdout))


def _collect_rust_uncached(root: Path) -> Result[frozenset[str], TestingError]:
    """`cargo test --lib -- --list` node ids across every discovered crate."""
    node_ids: set[str] = set()
    for crate_dir in _find_crates(root):
        listed = _run_cargo_list(crate_dir)
        if listed.is_err:
            return Err(listed.danger_err)
        for module_path in listed.danger_ok:
            node_ids.add(_module_path_to_symref(root, crate_dir, module_path))
    return Ok(frozenset(node_ids))


# frob:doc docs/modules/testing.md#public-api
def collect_rust_tests(root: Path) -> Result[CollectedTests, TestingError]:
    """`cargo test --lib -- --list` node ids for every crate under `root`
    (`Cargo.toml` discovery, cached on rust source content hash); `Err` --
    never a fabricated empty pass -- when the PyO3 dev environment cannot be
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
