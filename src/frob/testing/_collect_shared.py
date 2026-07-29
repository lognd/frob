"""Cache-file and directory-walk primitives every per-language collector in
`frob.testing._collect*` shares -- split out (T-1074) so `_prune_dirnames`/
`_load_cache`/`_store_cache` have exactly one home instead of being
re-derived per language module."""
# frob:ticket T-1074

from __future__ import annotations

import json
from pathlib import Path

from frob.excludes import is_excluded, is_skipped_dir
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "pytest-collect.json"
_RUST_CACHE_REL = Path(".frob") / "cargo-collect.json"
_TS_CACHE_REL = Path(".frob") / "vitest-collect.json"
_CTEST_CACHE_REL = Path(".frob") / "ctest-collect.json"
_COLLECT_TIMEOUT_S = 300.0


def _prune_dirnames(
    dirpath: Path, root: Path, dirnames: list[str], exclude_globs: tuple[str, ...]
) -> list[str]:
    """`dirnames` filtered to drop built-in-skipped names AND any child
    whose root-relative POSIX path matches `[graph].exclude` (T-0274: a
    file-walking surface that does not consult frob.excludes is exactly
    the desync that module exists to prevent -- docs/strata/surface.md).
    Shared by every `os.walk`-based collector across `frob.testing._collect*`
    so the rule lives once."""
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


def _load_cache(cache_path: Path, key: str) -> frozenset[str] | None:
    """The cached node id set if `cache_path` exists and matches `key`, else `None`."""
    if not cache_path.exists():
        return None
    try:
        doc = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("collect: unreadable cache %s: %s", cache_path, exc)
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
