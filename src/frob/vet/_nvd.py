"""NVD CVE->CWE lookups (docs/strata/threat.md "CVE: threat intelligence
joined to the proof" -- phase D, T-0110) with a 7d sqlite cache in the
same `.frob/vet.db` `_registry.py` already writes to.

Network calls: 5s timeout, degrade to `ok=False` on any failure -- the
SAME offline-first posture `_registry.py::_fetch_publish_date` establishes
for VET011 (docs/modules/vet.md VET011): an unreachable/unparseable NVD
response is reported as "could not verify", never treated as "no CWEs",
so a live CVE can never silently read as contained for lack of a network
call. `[vet].registry_base_url`-style host override is `base_url` here too,
for the same reason (tests never touch the real NVD API).

T-0822: `_fetch_from_network` is gated by `frob.process.net_enabled()` (the
`FROB_DISABLE_NET` kill switch, T-0200) before the socket is opened -- a
disabled switch degrades exactly like a network failure (`ok=False`), the
same offline-must-never-hard-block posture as `_registry.py`.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger
from frob.process import NET_KILL_SWITCH_ENV, net_enabled
from frob.vet._cache import ttl_cache_get, ttl_cache_set

#: sqlite table name for this module's TTL cache (T-1067, shared helper
#: home in `frob.vet._cache`; kept distinct from `_registry.py`'s `cache`
#: table since the two key different id spaces and expire on different
#: TTLs).
_CACHE_TABLE = "nvd_cache"

_log = get_logger(__name__)

_TIMEOUT_S = 5.0
_CACHE_TTL_S = 7 * 24 * 60 * 60  # CWE mappings on a published CVE are stable;
# 7d (vs. the registry lookup's 24h) trades a little staleness for far fewer
# calls against a rate-limited public API.

_NVD_HOST = "https://services.nvd.nist.gov/rest/json/cves/2.0"

#: docs/strata/threat.md#the-catalog-stdcwe ids are always this shape;
#: NVD's own weakness descriptions occasionally carry "NVD-CWE-Other" or
#: "NVD-CWE-noinfo" placeholders that name no real weakness -- filtered out
#: below rather than joined against the catalog as if they were real CWEs.
_CWE_RE = re.compile(r"^CWE-\d+$")


# frob:doc docs/modules/vet.md#public-api
class NvdResult(BaseModel):
    """Outcome of a CVE->CWE lookup: `ok=False` means "could not verify",
    never "no weaknesses" -- callers must not treat `ok=False` as a clean
    result (docs/strata/threat.md "CVE: threat intelligence joined to the
    proof")."""

    model_config = ConfigDict(frozen=True)

    ok: bool
    cwe_ids: tuple[str, ...] = ()
    note: str = ""


def _cache_key(cve_id: str) -> str:
    """The `.frob/vet.db` cache key for one CVE's NVD lookup."""
    return f"nvd:{cve_id}"


def _cwe_ids_from_body(body: str) -> tuple[str, ...]:
    """Every real `CWE-\\d+` id in an NVD `cves/2.0` JSON body's
    `weaknesses[].description[].value` fields, order-stable and deduped;
    `NVD-CWE-Other`/`NVD-CWE-noinfo` placeholders are dropped (see `_CWE_RE`
    docstring above)."""
    data = json.loads(body)
    vulns = data.get("vulnerabilities", [])
    if not vulns:
        return ()
    cve = vulns[0].get("cve", {})
    found: list[str] = []
    for weakness in cve.get("weaknesses", []):
        for desc in weakness.get("description", []):
            value = desc.get("value", "")
            if desc.get("lang", "en") == "en" and _CWE_RE.match(value):
                if value not in found:
                    found.append(value)
    return tuple(found)


def _url_for(cve_id: str, base_url: str | None) -> str:
    """Build the NVD lookup URL; `base_url` (test override) keeps the real
    query-param shape."""
    host = base_url if base_url else _NVD_HOST
    return f"{host}?cveId={cve_id}"


def _result_from_body(cve_id: str, body: str) -> NvdResult:
    """Parse a (fetched or cached) NVD response body into an `NvdResult`."""
    try:
        cwe_ids = _cwe_ids_from_body(body)
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        _log.warning("vet: nvd response for %s unparseable: %s", cve_id, exc)
        return NvdResult(ok=False, note=f"could not verify CWE mapping: {exc}")
    _log.info("vet: %s maps to CWEs %s", cve_id, cwe_ids)
    return NvdResult(ok=True, cwe_ids=cwe_ids)


# frob:ticket T-0822
def _fetch_from_network(
    cve_id: str, url: str, cache_path: Path, timeout_s: float
) -> NvdResult:
    """Fetch, parse, and cache one CVE's NVD weakness mapping."""
    if not net_enabled():
        _log.warning(
            "vet: nvd query for %s skipped (net disabled via %s)",
            cve_id,
            NET_KILL_SWITCH_ENV,
        )
        return NvdResult(ok=False, note="could not verify CWE mapping: net disabled")
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _log.warning("vet: nvd query failed for %s: %s", cve_id, exc)
        return NvdResult(ok=False, note=f"could not verify CWE mapping: {exc}")

    result = _result_from_body(cve_id, body)
    if result.ok:
        ttl_cache_set(cache_path, _CACHE_TABLE, _cache_key(cve_id), body)
    return result


# frob:doc docs/modules/vet.md#public-api
def fetch_cwe_for_cve(
    cve_id: str,
    *,
    cache_path: Path,
    base_url: str | None = None,
    timeout_s: float = _TIMEOUT_S,
    fetch: bool = True,
) -> NvdResult:
    """The CWE ids NVD lists for `cve_id`; `ok=False` on any lookup failure
    (docs/strata/threat.md "CVE: threat intelligence joined to the proof").
    Cache-first (7d TTL); a cache miss or expiry triggers one network call
    UNLESS `fetch=False` (offline CI / tests -- mirrors `_scan.py::scan_tree`'s
    `fetch` parameter), in which case a miss degrades to `ok=False` directly,
    never a silent network attempt and never a vacuous "no CWEs" pass."""
    key = _cache_key(cve_id)
    cached = ttl_cache_get(cache_path, _CACHE_TABLE, key, ttl_s=_CACHE_TTL_S)
    if cached is not None:
        return _result_from_body(cve_id, cached)

    if not fetch:
        _log.info("vet: nvd lookup for %s skipped (fetch=False, no cache)", cve_id)
        return NvdResult(ok=False, note="fetch disabled and no cache entry")

    url = _url_for(cve_id, base_url)
    _log.info("vet: querying NVD for %s: %s", cve_id, url)
    return _fetch_from_network(cve_id, url, cache_path, timeout_s)


__all__ = ["NvdResult", "fetch_cwe_for_cve"]
