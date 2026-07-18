"""`pytest --collect-only`, cached by test-file content hash under `.frob/`."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.testing._models import CollectedTests
from frob.testing._runners import TestingError

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "pytest-collect.json"
_EXCLUDED_DIRS = frozenset(
    {".git", ".venv", "node_modules", "target", "build", "dist", ".frob"}
)
_COLLECT_TIMEOUT_S = 300.0
_NO_TESTS_COLLECTED_EXIT = 5


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


__all__ = ["collect_python_tests"]
