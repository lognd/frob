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
_KOTLIN_CACHE_REL = Path(".frob") / "kotlin-junit-collect.json"
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


# frob:invariant INV-050
# invariant spec: [INV-050](invariants/INV-050.md)
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


# frob:ticket T-4390
def _load_cache_extra(cache_path: Path, key: str) -> dict:
    """T-4390: the `extra` JSON payload stored alongside `key`'s node ids
    (e.g. Python's platform-skip `(file, reason)` pairs), `{}` if the
    cache is absent/unreadable/stale or carries no `extra` at all -- a
    cache HIT that predates this field (or a collector that never passes
    `extra` to `_store_cache`) degrades to the same `{}` a miss returns,
    never a crash. Split from `_load_cache`'s frozenset-only return so
    every OTHER collector (rust/ts/ctest/kotlin) stays untouched by this
    Python-only need."""
    if not cache_path.exists():
        return {}
    try:
        doc = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("collect: unreadable cache %s: %s", cache_path, exc)
        return {}
    if doc.get("key") != key:
        return {}
    extra = doc.get("extra")
    return extra if isinstance(extra, dict) else {}


# frob:ticket T-4390
def _store_cache(
    cache_path: Path,
    key: str,
    node_ids: frozenset[str],
    extra: dict | None = None,
) -> None:
    """Persist `node_ids` keyed by `key` to `cache_path`. `extra` (T-4390,
    optional, default `None`/omitted) is an opaque JSON-serializable
    payload a collector can round-trip through a cache HIT via
    `_load_cache_extra` -- Python's own use is `platform_skipped`
    `(file, reason)` pairs, which `_load_cache`'s plain node-id set
    cannot carry, so a warm cache previously read back as "nothing
    platform-skipped" even when the fresh collection that built the
    cache found some (T-4382's own documented gap)."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    doc: dict = {"key": key, "node_ids": sorted(node_ids)}
    if extra:
        doc["extra"] = extra
    cache_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
