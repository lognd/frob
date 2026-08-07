"""`cargo test -- --list` collection, one crate directory per discovered
`Cargo.toml` -- split out of `frob.testing._collect` (T-1074) as its own
self-contained per-language collector; `_collect.py` re-imports every name
here so `from frob.testing._collect import ...` call sites (tests,
`frob.testing.__init__`) keep resolving unchanged."""
# frob:ticket T-1074

from __future__ import annotations

import hashlib
import os
import re
import tomllib
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.excludes import load_exclude_globs
from frob.gitio import GitError, ProcResult, run_argv
from frob.logging import get_logger
from frob.testing._collect_shared import (
    _COLLECT_TIMEOUT_S,
    _RUST_CACHE_REL,
    _load_cache,
    _prune_dirnames,
    _store_cache,
)
from frob.testing._models import CollectedTests
from frob.testing._runners import TestingError, _cargo_env, _env_overlay

_log = get_logger(__name__)

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


__all__ = [
    "collect_rust_tests",
]
