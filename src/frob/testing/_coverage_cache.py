"""Per-file content-hash keyed incremental coverage cache (T-1517).

T-1205 acceptance[2]: an unchanged file's coverage must never be
recomputed, even across separate touched-set runs. T-0484's
`python_coverage_targets` already narrows WHICH tests a touched-set
`pytest --cov-append` run executes, and the Makefile `coverage-fast`
recipe (T-1397) already restricts execution to that selection -- but
neither one persists a durable, content-hash-keyed record of every OTHER
file's last-known coverage, so a touched-set run's own `coverage.xml`
structurally only ever contains data for files pytest actually
re-executed this time, and any file untouched this run but never
verified against a stable, addressable cache is at risk of silently
dropping out of the merged picture the next time something reads
`coverage.xml` in isolation.

This module is the missing persistence layer: `.frob/coverage-file-
cache.json` maps a `path -> {content_hash, line_pct}` record, mirroring
`frob.graph.cache`'s own "cache derived data, key it by content hash,
treat a hash mismatch as a plain cache miss" pattern (T-1464's
`parsed_artifacts` table is the closest sibling, though this cache is a
single small JSON document rather than a sqlite table -- coverage
percentages are a few hundred small floats, not whole parsed-file
payloads, so sqlite's concurrency machinery is not worth the added
surface here). `fill_from_cache` backfills any file missing from a
freshly loaded `CoverageData.module_line` whose current content hash
still matches what the cache last recorded, so a touched-set run's
narrower `coverage.xml` still reports every unchanged file's real,
previously-measured percentage instead of silently omitting it.
`update_file_cache` is the write side, called after a successful stamp so
the cache always reflects the most recent measurement for every file
`coverage.xml` actually covered.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from frob.logging import get_logger

if TYPE_CHECKING:
    # frob:ticket T-1517
    # Import deferred to type-checking only: `frob.gates._coverage` (the
    # only real caller) imports THIS module, so a runtime import of
    # `frob.gates._models` here would close a cycle back through
    # `frob.gates.__init__` -> `frob.gates._coverage` -> `frob.testing` ->
    # this module. `CoverageData` is only ever used in type positions
    # below (`from __future__ import annotations` already makes every
    # annotation a lazily-evaluated string), so no runtime import is
    # needed at all.
    from frob.gates._models import CoverageData

_log = get_logger(__name__)

#: Gitignored, like every other `.frob/` derived artifact (docs/modules/
#: graph.md#cache) -- safe to delete at any time, rebuilt from
#: `coverage.xml` + the live file hashes on the next stamp.
# frob:ticket T-1516
_CACHE_REL = Path(".frob") / "coverage-file-cache.json"


# frob:ticket T-1517
# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_coverage.py::TestCoverageFileCache.test_load_missing_returns_empty  # noqa: E501
def load_file_cache(root: Path) -> dict[str, dict[str, object]]:
    """The persisted `path -> {content_hash, line_pct}` cache, or `{}` if
    missing/unreadable (T-1517) -- a missing cache is a cold start, not an
    error; every caller treats it identically to an empty dict."""
    cache_path = root / _CACHE_REL
    if not cache_path.exists():
        return {}
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("load_file_cache: %s unreadable: %s", cache_path, exc)
        return {}
    if not isinstance(raw, dict):
        _log.warning("load_file_cache: %s is not a JSON object, ignoring", cache_path)
        return {}
    return raw


# frob:ticket T-1516
def _save_file_cache(root: Path, cache: Mapping[str, dict[str, object]]) -> None:
    """Write `cache` back to `_CACHE_REL`, best-effort (T-1517).

    Mirrors `write_coverage_lock`'s own best-effort-write shape: a failure
    to persist the cache degrades the NEXT run back to full recomputation
    for whatever did not get saved, never a crash for the current one."""
    cache_path = root / _CACHE_REL
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        _log.warning("update_file_cache: could not write %s: %s", cache_path, exc)


# frob:ticket T-1517
# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_coverage.py::TestCoverageFileCache.test_fill_from_cache_backfills_unchanged_file  # noqa: E501
# frob:tests tests/test_coverage.py::TestCoverageFileCache.test_fill_from_cache_ignores_stale_hash  # noqa: E501
# frob:tests tests/test_coverage.py::TestCoverageFileCache.test_fill_from_cache_never_overwrites_fresh_data  # noqa: E501
def fill_from_cache(
    data: CoverageData,
    *,
    file_hashes: Mapping[str, str],
    cache: Mapping[str, dict[str, object]],
) -> CoverageData:
    """Backfill `data.module_line` from `cache` for every known file that
    `data` did not itself measure this run (T-1517).

    A file is backfilled only when BOTH: (1) it is absent from `data.
    module_line` (never overwrites a value this run actually measured --
    fresh data always wins), and (2) its current `file_hashes` entry
    matches the cached `content_hash` exactly (a changed file has no
    trustworthy cached percentage, so it is left for the caller's own
    "no data this run" handling, same as before this cache existed).
    Returns a new `CoverageData` (frozen model) rather than mutating
    `data` in place.
    """
    merged = dict(data.module_line)
    backfilled = 0
    for path, current_hash in file_hashes.items():
        if path in merged:
            continue
        entry = cache.get(path)
        if entry is None:
            continue
        if entry.get("content_hash") != current_hash:
            continue
        pct = entry.get("line_pct")
        if not isinstance(pct, int | float):
            continue
        merged[path] = float(pct)
        backfilled += 1
    if backfilled:
        _log.info(
            "fill_from_cache: backfilled %d unchanged file(s) from %s",
            backfilled,
            _CACHE_REL,
        )
    return data.model_copy(update={"module_line": merged})


# frob:ticket T-1517
# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_coverage.py::TestCoverageFileCache.test_update_file_cache_persists_measured_files  # noqa: E501
# frob:tests tests/test_coverage.py::TestCoverageFileCache.test_update_file_cache_roundtrips_through_fill_from_cache  # noqa: E501
def update_file_cache(
    root: Path, data: CoverageData, *, file_hashes: Mapping[str, str]
) -> dict[str, dict[str, object]]:
    """Persist every `(path, content_hash) -> line_pct` this `data` knows
    about into `_CACHE_REL`, merged with whatever was already cached
    (T-1517), and return the merged cache.

    Only files with a known current content hash are written (a file
    `data.module_line` mentions but that no longer exists / is untracked
    has no hash to key on, so it is skipped rather than cached under a
    stale or missing key). Existing entries for files NOT in `data.
    module_line` this run are kept as-is -- this is a merge, not a
    replace, so a touched-set run's narrower `coverage.xml` never evicts
    an unrelated file's still-valid cached percentage.
    """
    cache = load_file_cache(root)
    updated = 0
    for path, pct in data.module_line.items():
        content_hash = file_hashes.get(path)
        if content_hash is None:
            continue
        cache[path] = {"content_hash": content_hash, "line_pct": pct}
        updated += 1
    _save_file_cache(root, cache)
    _log.info(
        "update_file_cache: wrote %d file entr(y/ies) to %s (%d total cached)",
        updated,
        _CACHE_REL,
        len(cache),
    )
    return cache


__all__ = [
    "fill_from_cache",
    "load_file_cache",
    "update_file_cache",
]
