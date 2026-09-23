"""T-4449: unit coverage for the pytest-collection cache's `platform_
skipped` round-trip through `.frob/pytest-collect.json` written by the
REAL `_store_cache` writer (not a hand-built JSON fixture) -- the runner
measurement (CI run 34735688390, Windows) found a live cache file with
top-level keys `['key', 'node_ids']` ONLY, no `platform_skipped` at all,
served through a warm cache hit as if that meant "nothing platform-
skipped". These tests pin the fix at the cache layer directly: a fresh
write always carries the field (even empty), and a load that finds the
field ABSENT (the old format, or any writer that predates it) must read
back as a MISS, never as an empty tuple. Every file write below goes
through `_store_cache` or `tests.conftest._write` (both already-declared
testsuite fs.write via-list sites) rather than a raw `Path.write_text`
call of this file's own, so this module adds no new capability site
`design/frob.strata` needs to declare."""

from __future__ import annotations

import json
from pathlib import Path

from frob.testing._collect_python_cache import (
    _set_collection_platform_skipped,
)
from frob.testing._collect_shared import _load_cache, _load_cache_extra, _store_cache


class TestPlatformSkippedCacheWriteFormat:
    """`_store_cache`'s `extra` payload always carries `platform_skipped`,
    even when the tuple is empty -- T-4449's write-side half of the fix."""

    # frob:tests \
    # tests/unit/test_collect_python_cache.py::TestPlatformSkippedCacheWriteFormat.test_empty_platform_skipped_still_written  # noqa: E501
    def test_empty_platform_skipped_still_written(self, tmp_path: Path) -> None:
        """A collection that finds NOTHING platform-skipped must still
        persist `extra.platform_skipped == []`, not omit `extra`
        entirely -- an omitted field is indistinguishable, on a later
        load, from a cache entry that predates the field."""
        cache_path = tmp_path / "pytest-collect.json"
        _store_cache(
            cache_path,
            "somekey",
            frozenset({"tests/test_a.py::test_a"}),
            extra={"platform_skipped": []},
        )
        extra = _load_cache_extra(cache_path, "somekey")
        assert "platform_skipped" in extra
        assert extra["platform_skipped"] == []

    # frob:tests \
    # tests/unit/test_collect_python_cache.py::TestPlatformSkippedCacheWriteFormat.test_nonempty_platform_skipped_round_trips  # noqa: E501
    def test_nonempty_platform_skipped_round_trips(self, tmp_path: Path) -> None:
        """A real `(file, reason)` pair written through `_store_cache`
        reads back byte-for-byte through `_load_cache_extra`."""
        cache_path = tmp_path / "pytest-collect.json"
        pair = ("tests/unit/test_stackdump.py", "SIGUSR1 is POSIX-only")
        _store_cache(
            cache_path,
            "somekey",
            frozenset({"tests/test_a.py::test_a"}),
            extra={"platform_skipped": [list(pair)]},
        )
        extra = _load_cache_extra(cache_path, "somekey")
        assert extra["platform_skipped"] == [list(pair)]


class TestOldFormatCacheEntryIsAMiss:
    """A cache file that matches `key` but was written before T-4390's
    `extra.platform_skipped` field existed (or by ANY writer that omitted
    it) must be readable as having NO `platform_skipped` term at all --
    the caller (`collect_python_tests`) is what turns that absence into a
    forced re-collection; this layer just needs to make the absence
    observable, not silently equal to an empty list."""

    # frob:tests \
    # tests/unit/test_collect_python_cache.py::TestOldFormatCacheEntryIsAMiss.test_old_format_entry_has_no_platform_skipped_key  # noqa: E501
    def test_old_format_entry_has_no_platform_skipped_key(self, tmp_path: Path) -> None:
        """A hand-written cache doc shaped exactly like the runner-measured
        one (`key` + `node_ids` only, no `extra` at all) loads with
        `_load_cache` succeeding (a genuine node-id cache hit) but
        `_load_cache_extra` returning a dict with NO `platform_skipped`
        key -- the signal `collect_python_tests` uses to force a fresh
        collection instead of trusting the file."""
        from tests.conftest import _write

        _write(
            tmp_path,
            "pytest-collect.json",
            json.dumps({"key": "somekey", "node_ids": ["tests/test_a.py::test_a"]}),
        )
        cache_path = tmp_path / "pytest-collect.json"
        cached = _load_cache(cache_path, "somekey")
        assert cached == frozenset({"tests/test_a.py::test_a"})
        extra = _load_cache_extra(cache_path, "somekey")
        assert "platform_skipped" not in extra

    def teardown_method(self) -> None:
        """Reset the module-level `platform_skipped` state (T-4382) after
        each test so a hand-crafted cache scenario in this class can never
        leak into an unrelated later test in the same process."""
        _set_collection_platform_skipped(())
