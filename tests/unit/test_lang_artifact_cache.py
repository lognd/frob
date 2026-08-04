"""Tests for `frob.lang`'s persistent parse-artifact cache (T-1464).

Covers `_parse_file_with_artifact_cache`: a transparent passthrough when
`PARSE_ARTIFACT_CACHE_ENV` is unset (the common single-process case), and
a real hit/miss round trip through `.frob/cache.db` when it is set --
the mechanism `frob.gates._stamp_worker_parse_artifact_cache_env` wires
into every `ProcessPoolExecutor` gate worker.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import frob.lang as lang_mod
from frob.graph import cache as graph_cache


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


# frob:ticket T-1464
class TestParseFileArtifactCache:
    """`_parse_file_with_artifact_cache`'s cache-consult behavior."""

    def test_no_env_is_a_transparent_passthrough(self, tmp_path: Path) -> None:
        """With `PARSE_ARTIFACT_CACHE_ENV` unset, behavior is identical to
        calling `_parse_file_uncached` directly."""
        path = _write(tmp_path, "a.py", "def f():\n    return 1\n")
        with patch.dict("os.environ", {}, clear=False):
            lang_mod.os.environ.pop(lang_mod.PARSE_ARTIFACT_CACHE_ENV, None)
            result = lang_mod._parse_file_with_artifact_cache(path)
        assert result.is_ok
        assert result.danger_ok.symbols[0].qualname == "f"

    def test_miss_populates_cache(self, tmp_path: Path) -> None:
        """A first call with no matching row parses normally and stores
        its result under `(content_hash, fingerprint)`."""
        cache_db = tmp_path / ".frob" / "cache.db"
        graph_cache.connect(cache_db).close()
        path = _write(tmp_path, "b.py", "def g():\n    return 2\n")
        lang_mod._artifact_conn = None
        lang_mod._artifact_conn_path = None
        with patch.dict(
            "os.environ", {lang_mod.PARSE_ARTIFACT_CACHE_ENV: str(cache_db)}
        ):
            result = lang_mod._parse_file_with_artifact_cache(path)
            assert result.is_ok
            conn = lang_mod._artifact_cache_connection()
            fingerprint = lang_mod._artifact_fingerprint()
            content_hash = result.danger_ok.content_hash
            stored = graph_cache.load_parsed_artifact(
                conn, content_hash=content_hash, fingerprint=fingerprint
            )
            assert stored is not None
        lang_mod._artifact_conn = None
        lang_mod._artifact_conn_path = None

    def test_hit_skips_extract(self, tmp_path: Path) -> None:
        """A second call for the same content hash rebuilds `ParsedFile`
        from the stored payload instead of calling `_parse_file_uncached`
        again, and rebinds `.path` to the calling path."""
        cache_db = tmp_path / ".frob" / "cache.db"
        graph_cache.connect(cache_db).close()
        path = _write(tmp_path, "c.py", "def h():\n    return 3\n")
        lang_mod._artifact_conn = None
        lang_mod._artifact_conn_path = None
        with patch.dict(
            "os.environ", {lang_mod.PARSE_ARTIFACT_CACHE_ENV: str(cache_db)}
        ):
            first = lang_mod._parse_file_with_artifact_cache(path)
            assert first.is_ok
            with patch.object(
                lang_mod, "_parse_file_uncached", side_effect=AssertionError("miss")
            ):
                second = lang_mod._parse_file_with_artifact_cache(path)
        assert second.is_ok
        assert second.danger_ok.symbols[0].qualname == "h"
        assert second.danger_ok.path == lang_mod._display_path(path)
        lang_mod._artifact_conn = None
        lang_mod._artifact_conn_path = None


# frob:ticket T-1464
class TestArtifactCacheLockDegradesGracefully:
    """T-1464 incident regression: a `CacheLocked`/`OperationalError` past
    the retry budget must degrade to a cache miss (or a skipped write),
    never escape and crash the whole `_parse_file_with_artifact_cache`
    call -- a real parse is always a safe fallback."""

    def test_load_locked_is_treated_as_a_miss(self, tmp_path: Path) -> None:
        """A `CacheLocked` read is swallowed and reported as `None`."""
        from frob.graph.cache import CacheLocked

        conn = graph_cache.connect(tmp_path / "cache.db")
        with patch(
            "frob.graph.cache.load_parsed_artifact", side_effect=CacheLocked("busy")
        ):
            result = lang_mod._load_cached_artifact_payload(conn, "h", "f")
        assert result is None

    def test_store_locked_does_not_raise(self, tmp_path: Path) -> None:
        """A `CacheLocked` write is swallowed; the parsed result still
        comes back `Ok`."""
        from frob.graph.cache import CacheLocked

        conn = graph_cache.connect(tmp_path / "cache.db")
        path = _write(tmp_path, "z.py", "def zz():\n    return 0\n")
        with patch(
            "frob.graph.cache.store_parsed_artifact", side_effect=CacheLocked("busy")
        ):
            result = lang_mod._parse_and_populate_artifact_cache(path, conn, "h", "f")
        assert result.is_ok
        assert result.danger_ok.symbols[0].qualname == "zz"
