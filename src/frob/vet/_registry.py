"""Registry publish-date lookups (VET011 cooldown) with a 24h sqlite cache.

Network calls: 5s timeout, degrade to a WARN on any failure (offline must
never hard-block -- docs/modules/vet.md VET011). `[vet].registry_base_url` swaps the
host for tests; the path suffix per ecosystem is identical to the real
registry so parsing logic is shared between real and fake responses.
"""

# frob:waive TEST005 reason="module line coverage 39.5%, debt T-0160"

from __future__ import annotations

import json
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

_log = get_logger(__name__)

_TIMEOUT_S = 5.0
_CACHE_TTL_S = 24 * 60 * 60

_PYPI_HOST = "https://pypi.org"
_NPM_HOST = "https://registry.npmjs.org"
_CRATES_HOST = "https://crates.io"


# frob:doc docs/modules/vet.md#public-api
class _RegistryResult(BaseModel):
    """Outcome of a publish-date lookup: `ok=False` means "could not verify"."""

    model_config = ConfigDict(frozen=True)

    ok: bool
    published_at: datetime | None = None
    resolved_version: str | None = None
    note: str = ""


def _cache_key(ecosystem: str, name: str, version: str) -> str:
    return f"{ecosystem}:{name}:{version}"


# frob:waive DUP001 reason="documented deliberate split: same shape as \
# _nvd.py::_cache_get, kept separate since the two caches key different \
# id spaces and expire on different TTLs (see _nvd.py's docstring)"
def _cache_get(db_path: Path, key: str) -> str | None:
    """Cached JSON body for `key`, or `None` on miss/expiry/unreadable db."""
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT value, fetched_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        _log.warning("vet: cache read failed for %s: %s", db_path, exc)
        return None
    if row is None:
        return None
    value, fetched_at = row
    if time.time() - fetched_at > _CACHE_TTL_S:
        _log.debug("vet: cache entry for %s expired", key)
        return None
    _log.debug("vet: cache hit for %s", key)
    return value


# frob:waive DUP001 reason="mirrors _nvd.py::_cache_set; the two caches \
# are independent artifacts with different TTLs, not worth forcing into \
# one abstraction"
def _cache_set(db_path: Path, key: str, value: str) -> None:
    """Best-effort cache write; failures are logged, never raised."""
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cache "
                "(key TEXT PRIMARY KEY, value TEXT, fetched_at REAL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, fetched_at) "
                "VALUES (?, ?, ?)",
                (key, value, time.time()),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        _log.warning("vet: cache write failed for %s: %s", db_path, exc)


_LATEST = "latest"


def _url_for(ecosystem: str, name: str, version: str, base_url: str | None) -> str:
    """Build the lookup URL; `base_url` (test override) keeps the real path suffix."""
    if ecosystem == "pypi":
        host = base_url + "/pypi" if base_url else _PYPI_HOST + "/pypi"
        if version == _LATEST:
            return f"{host}/{name}/json"
        return f"{host}/{name}/{version}/json"
    if ecosystem == "npm":
        host = base_url + "/npm" if base_url else _NPM_HOST
        return f"{host}/{name}"
    if ecosystem == "cargo":
        host = base_url + "/crates" if base_url else _CRATES_HOST + "/api/v1/crates"
        return f"{host}/{name}/versions"
    raise ValueError(f"unsupported ecosystem: {ecosystem}")


def _parse_published(
    ecosystem: str, name: str, version: str, body: str
) -> tuple[str | None, datetime | None]:
    """Extract `(resolved_version, publish_timestamp)` from a registry JSON body.
    `version == "latest"` resolves the registry's current release."""
    data = json.loads(body)
    if ecosystem == "pypi":
        if version == _LATEST:
            resolved = data.get("info", {}).get("version")
        else:
            resolved = version
        releases = data.get("releases", {}).get(resolved, []) if resolved else []
        if not releases:
            return resolved, None
        ts = releases[0].get("upload_time_iso_8601")
        return resolved, (datetime.fromisoformat(ts) if ts else None)
    if ecosystem == "npm":
        resolved = version
        if version == _LATEST:
            resolved = data.get("dist-tags", {}).get("latest")
        ts = data.get("time", {}).get(resolved) if resolved else None
        return resolved, (datetime.fromisoformat(ts) if ts else None)
    if ecosystem == "cargo":
        versions = data.get("versions", [])
        if version == _LATEST:
            entry = versions[0] if versions else None
        else:
            entry = next((e for e in versions if e.get("num") == version), None)
        if entry is None:
            return None, None
        ts = entry.get("created_at")
        return entry.get("num"), (datetime.fromisoformat(ts) if ts else None)
    return None, None


def _result_from_cached(
    ecosystem: str, name: str, version: str, key: str, cached: str
) -> _RegistryResult:
    """Build a `_RegistryResult` from an already-cached registry JSON body."""
    try:
        resolved, published = _parse_published(ecosystem, name, version, cached)
    except (json.JSONDecodeError, ValueError) as exc:
        _log.warning("vet: cached body for %s unparseable: %s", key, exc)
        return _RegistryResult(ok=False, note="cached response unparseable")
    _log.info("vet: %s publish date from cache: %s", key, published)
    return _RegistryResult(ok=True, published_at=published, resolved_version=resolved)


# frob:boundary b_vet_endorse
# This is the endorsement site for design/frob.strata's
# `boundary b_vet_endorse endorse f_registry_fetch : foreign -> trusted`:
# a raw network response is parsed/validated into a `_RegistryResult` here,
# and nothing downstream re-validates it -- delete this validation and the
# model's `c_no_registry_ledger` noflow claim would (correctly) refute.
def _result_from_network(
    ecosystem: str,
    name: str,
    version: str,
    key: str,
    url: str,
    cache_path: Path,
    timeout_s: float,
) -> _RegistryResult:
    """Fetch, parse, and (for pinned versions) cache a registry publish date."""
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _log.warning("vet: registry query failed for %s: %s", key, exc)
        return _RegistryResult(ok=False, note=f"could not verify publish date: {exc}")

    try:
        resolved, published = _parse_published(ecosystem, name, version, body)
    except (json.JSONDecodeError, ValueError) as exc:
        _log.warning("vet: response for %s unparseable: %s", key, exc)
        return _RegistryResult(ok=False, note="could not verify publish date")

    if version != _LATEST:
        _cache_set(cache_path, key, body)
    _log.info("vet: %s publish date: %s (resolved=%s)", key, published, resolved)
    return _RegistryResult(ok=True, published_at=published, resolved_version=resolved)


# frob:doc docs/modules/vet.md#public-api
# frob:waive TEST005 reason="_fetch_publish_date 87.5% branch cover, debt T-0160"
def _fetch_publish_date(
    ecosystem: str,
    name: str,
    version: str,
    *,
    cache_path: Path,
    base_url: str | None = None,
    timeout_s: float = _TIMEOUT_S,
) -> _RegistryResult:
    """The publish timestamp for `name@version`; `ok=False` on any lookup failure."""
    key = _cache_key(ecosystem, name, version)
    cached = None if version == _LATEST else _cache_get(cache_path, key)
    if cached is not None:
        return _result_from_cached(ecosystem, name, version, key, cached)

    url = _url_for(ecosystem, name, version, base_url)
    _log.info("vet: querying registry for %s: %s", key, url)
    return _result_from_network(
        ecosystem, name, version, key, url, cache_path, timeout_s
    )


# frob:doc docs/modules/vet.md#public-api
LATEST_VERSION = _LATEST

__all__ = ["LATEST_VERSION", "_RegistryResult", "_fetch_publish_date"]
