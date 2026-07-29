"""`npx vitest list --json` collection, one project directory per discovered
`package.json` declaring a `vitest` dependency (T-0587) -- split out of
`frob.testing._collect` (T-1074) as its own self-contained per-language
collector; `_collect.py` re-imports every name here so `from
frob.testing._collect import ...` call sites (tests, `frob.testing.__init__`)
keep resolving unchanged."""
# frob:ticket T-1074
# frob:ticket T-0587
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's exclusivity- \
# vocabulary hit is source-level design-rationale/scope-cut prose (a docstring \
# describing already-implemented internal behavior, verifiable by reading the code it \
# annotates) rather than a separate cross-module contract needing its own tracked \
# invariant; carried verbatim from the pre-split src/frob/testing/_collect.py waiver \
# (T-1074) rather than re-derived"

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.excludes import load_exclude_globs
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.testing._collect_shared import (
    _COLLECT_TIMEOUT_S,
    _TS_CACHE_REL,
    _load_cache,
    _prune_dirnames,
    _store_cache,
)
from frob.testing._models import CollectedTests
from frob.testing._runners import TestingError

_log = get_logger(__name__)

_TS_TEST_NAME_RE = re.compile(r"\.(test|spec)\.(ts|tsx|js|jsx|mts|mjs)$")
_VITEST_DEP_NAME = "vitest"


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


def _find_vitest_projects(root: Path) -> list[Path]:
    """Directories holding a `package.json` that declares `vitest` as a
    dependency, exclusions pruned (mirrors `frob.testing._collect_rust.
    _find_crates`'s Cargo.toml walk). `node_modules` is always pruned -- an
    installed dependency's own package.json must never be mistaken for a
    project root."""
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


def _is_ts_test_file(path: Path) -> bool:
    """True if `path`'s name matches vitest's default test-file convention
    (`*.test.{ts,tsx,js,jsx,mts,mjs}` or `*.spec.{...}`)."""
    return bool(_TS_TEST_NAME_RE.search(path.name))


# frob:waive DUP001 reason="T-1074 split: this function moved here verbatim from \
# frob.testing._collect (unchanged content, same pre-existing 95%-similarity to \
# frob.strata._selfconform._repo_files_excluding_skip_dirs it always had) -- the \
# duplicate is pre-existing debt surfaced by the file becoming touched, not introduced \
# by this split; a real extraction is a separate, deliberate ticket"
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


__all__ = [
    "collect_ts_tests",
]
