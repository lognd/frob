"""OSV.dev in-process advisory adapter (docs/modules/vet.md "External tool
adapters" -- VET005; T-5138).

Queries https://api.osv.dev directly over HTTPS (POST `/v1/querybatch` for
every dependency, then GET `/v1/vulns/{id}` for each hit's full record) --
no external binary. OSV.dev aggregates GitHub Advisory DB (GHSA), PyPA,
RustSec, npm, Go, and NVD-derived CVE aliases under one package-keyed
schema, so osv-scanner/pip-audit/cargo-audit add nothing when absent and
are not wired in here (no duplication, ticket T-5138 DESIGN item 1).

Cache-first in `.frob/vet.db` (`_cache.py`'s TTL helpers, `osv_cache`
table), keyed per (ecosystem, name, version): a fresh (< 24h) entry serves
with zero network calls; an expired entry triggers one refetch attempt
UNLESS `fetch=False`. On a failed/disabled fetch the STALE cached value is
still served as long as it is younger than `max_age_days`
(`[vet].advisory_max_age_days`, default 7) -- older than that, or no cache
at all, degrades to `Err(OsvQueryError.Unavailable)` (VET012), never a
silent "no advisories" pass (silent-zero doctrine).

T-0822 posture reused: every network call is gated by
`frob.process.net_enabled()` (the `FROB_DISABLE_NET` kill switch) before
the socket ever opens -- a disabled switch degrades exactly like a network
failure.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from typani import Err, Ok
from typani.error_set import ErrorSet
from typani.result import Result

from frob.logging import get_logger
from frob.process import NET_KILL_SWITCH_ENV, net_enabled
from frob.vet._cache import ttl_cache_set
from frob.vet._models import Dependency

_log = get_logger(__name__)

#: sqlite table name for this module's TTL cache (shared `.frob/vet.db`,
#: same "one table per key-space/TTL" convention as `_nvd.py`/`_registry.py`).
_CACHE_TABLE = "osv_cache"

_TIMEOUT_S = 10.0
#: Freshness target: a cache entry younger than this serves with no network
#: call at all (docs/modules/vet.md "Advisories (VET005)").
_CACHE_TTL_S = 24 * 60 * 60

_QUERYBATCH_URL = "https://api.osv.dev/v1/querybatch"
_VULN_URL = "https://api.osv.dev/v1/vulns/{id}"

#: frob ecosystem strings (`_lockfile.py::Dependency.ecosystem`) -> OSV.dev
#: ecosystem names (https://ossf.github.io/osv-schema/#affectedpackage-field).
#: A dependency whose ecosystem is not in this map is honestly skipped
#: (OSV has no data to query for it), never silently treated as clean.
_OSV_ECOSYSTEM = {
    "pypi": "PyPI",
    "npm": "npm",
    "cargo": "crates.io",
}

#: An OSV advisory id (or one of its `aliases`) is a CVE id when it matches
#: this shape (docs/strata/threat.md "CVE: threat intelligence joined to
#: the proof") -- GHSA/PYSEC/RUSTSEC-only advisories with no CVE alias are
#: honestly out of the T-0110 join (see `_containment.py` module docstring).
_CVE_RE = re.compile(r"^CVE-\d{4}-\d+$")


# frob:doc docs/modules/vet.md#public-api
# frob:tests tests/vet_suite/test_advisories.py::TestOsvAdapter.test_query_advisories_no_cache_no_network_is_unavailable  # noqa: E501
class OsvQueryError(ErrorSet):
    """Fallible outcomes of an OSV.dev advisory query."""

    Unavailable = (
        "advisory data unavailable: no cache and no network "
        "(or cache older than [vet].advisory_max_age_days) -- VET012"
    )
    #: T-5139 acceptance [2]: OSV.dev was REACHED but answered with a body
    #: that does not parse as its own documented schema -- a distinct,
    #: more actionable failure than `Unavailable` (which means "never
    #: answered at all"). Reported as VET005 UNRESOLVED, never a silent
    #: clean pass (`OsvQueryFailure.detail` below carries the response tail).
    UnparseableResponse = (
        "advisory query reached OSV.dev but its response did not parse"
    )


# frob:doc docs/modules/vet.md#public-api
# frob:tests tests/vet_suite/test_advisories.py::TestOsvAdapter.test_query_advisories_unparseable_response_is_distinct_from_unavailable  # noqa: E501
class OsvQueryFailure:
    """`query_advisories`'s error value: `kind` (`OsvQueryError`) plus an
    optional `detail` -- the raw response tail for `UnparseableResponse`,
    empty for every other kind (T-5139 acceptance [2])."""

    __slots__ = ("kind", "detail")

    def __init__(self, kind: OsvQueryError, detail: str = "") -> None:
        self.kind = kind
        self.detail = detail

    def __eq__(self, other: object) -> bool:
        """Structural equality on (kind, detail) -- lets tests assert
        `result.danger_err == OsvQueryFailure(OsvQueryError.X)` directly."""
        if not isinstance(other, OsvQueryFailure):
            return NotImplemented
        return self.kind == other.kind and self.detail == other.detail


# frob:doc docs/modules/vet.md#public-api
class OsvAdvisory:
    """One advisory finding: id + affected package + fixed version (if
    known) + severity string (raw OSV `severity[].score`, vector or word --
    see module docstring's CVSS disclosure) + any `aliases` OSV reports
    (GHSA<->CVE cross-references)."""

    __slots__ = (
        "advisory_id",
        "package",
        "version",
        "fixed_version",
        "aliases",
        "severity",
        "summary",
    )

    def __init__(
        self,
        advisory_id: str,
        package: str,
        version: str,
        fixed_version: str | None,
        aliases: tuple[str, ...] = (),
        severity: str | None = None,
        summary: str = "",
    ) -> None:
        self.advisory_id = advisory_id
        self.package = package
        self.version = version
        self.fixed_version = fixed_version
        self.aliases = aliases
        self.severity = severity
        self.summary = summary


# frob:doc docs/modules/vet.md#public-api
def cve_ids(advisory: OsvAdvisory) -> tuple[str, ...]:
    """The CVE-shaped ids naming `advisory`: its own `advisory_id` plus any
    `aliases` matching `CVE-\\d{4}-\\d+` (docs/strata/threat.md "CVE: threat
    intelligence joined to the proof") -- a GHSA/PYSEC/RUSTSEC-only advisory
    with no CVE alias yields an empty tuple, honestly, rather than a guess."""
    candidates = (advisory.advisory_id, *advisory.aliases)
    seen: list[str] = []
    for candidate in candidates:
        if _CVE_RE.match(candidate) and candidate not in seen:
            seen.append(candidate)
    return tuple(seen)


def _cache_key(ecosystem: str, name: str, version: str) -> str:
    """The `.frob/vet.db` `osv_cache` key for one (ecosystem, name,
    version)'s advisory list."""
    return f"osv:{ecosystem}:{name}:{version}"


def _osv_ecosystem(dep: Dependency) -> str | None:
    """`dep`'s OSV.dev ecosystem name, or `None` when frob has no mapping
    for it yet (honestly skipped, not queried as if it were pypi)."""
    return _OSV_ECOSYSTEM.get(dep.ecosystem)


def _severity_of(vuln: dict) -> str | None:
    """The first `severity[].score` OSV reports for `vuln` (a CVSS vector
    string, e.g. `"CVSS:3.1/AV:N/..."`, or a bare word for non-CVSS
    schemes) -- raw, not parsed to a numeric score: a full CVSS-vector
    parser is out of this ticket's scope, disclosed here rather than
    silently faked with a wrong number."""
    for entry in vuln.get("severity", []):
        score = entry.get("score")
        if score:
            return str(score)
    database_specific = vuln.get("database_specific", {})
    if isinstance(database_specific, dict) and database_specific.get("severity"):
        return str(database_specific["severity"])
    return None


def _fixed_version(vuln: dict) -> str | None:
    """The last-declared `fixed` event across a vuln's affected ranges, if any."""
    fixed: str | None = None
    for affected in vuln.get("affected", []):
        for rng in affected.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event:
                    fixed = event["fixed"]
    return fixed


def _advisory_from_vuln(dep: Dependency, vuln: dict) -> OsvAdvisory:
    """One `GET /v1/vulns/{id}` body -> `OsvAdvisory` for `dep`."""
    return OsvAdvisory(
        advisory_id=vuln.get("id", "unknown"),
        package=dep.name,
        version=dep.version,
        fixed_version=_fixed_version(vuln),
        aliases=tuple(vuln.get("aliases", [])),
        severity=_severity_of(vuln),
        summary=str(vuln.get("summary", "")),
    )


def _querybatch_body(deps: tuple[Dependency, ...]) -> tuple[bytes, list[Dependency]]:
    """The JSON POST body for `/v1/querybatch` naming every queryable `dep`
    (OSV has no ecosystem mapping for the rest -- see `_osv_ecosystem`),
    plus the parallel list of deps actually included (same order as
    `queries[]`, so the response can be zipped back against it)."""
    queryable = [d for d in deps if _osv_ecosystem(d) is not None]
    queries = [
        {
            "package": {"name": d.name, "ecosystem": _osv_ecosystem(d)},
            "version": d.version,
        }
        for d in queryable
    ]
    return json.dumps({"queries": queries}).encode("utf-8"), queryable


def _http_post_json(url: str, body: bytes, timeout_s: float) -> str | None:
    """POST `body` as JSON to `url`; `None` on any network/HTTP failure."""
    req = urllib.request.Request(  # noqa: S310
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _log.warning("vet: osv query POST %s failed: %s", url, exc)
        return None


def _http_get_json(url: str, timeout_s: float) -> str | None:
    """GET `url`; `None` on any network/HTTP failure."""
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:  # noqa: S310
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _log.warning("vet: osv query GET %s failed: %s", url, exc)
        return None


def _fetch_advisory_ids(
    deps: tuple[Dependency, ...], base_url: str | None, timeout_s: float
) -> Result[dict[Dependency, tuple[str, ...]], str]:
    """`/v1/querybatch` ids-only lookup for every queryable dep in `deps`.

    T-5139: distinguishes a network failure (`Err("network")` -- caller
    degrades to cache/VET012-shaped Unavailable) from a REACHED-but-
    unparseable response (`Err("unparseable:<raw response tail>")` --
    caller reports the specific UnparseableResponse failure kind, T-5139
    acceptance [2]: a tool that answered with garbage is a DIFFERENT,
    more actionable failure than one that never answered at all)."""
    body, queryable = _querybatch_body(deps)
    if not queryable:
        return Ok({})
    url = base_url if base_url else _QUERYBATCH_URL
    raw = _http_post_json(url, body, timeout_s)
    if raw is None:
        return Err("network")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        _log.warning("vet: osv querybatch response unparseable: %s", exc)
        return Err(f"unparseable:{raw[-200:]}")
    results = data.get("results", [])
    out: dict[Dependency, tuple[str, ...]] = {}
    for dep, result_entry in zip(queryable, results, strict=False):
        ids = tuple(
            v.get("id", "") for v in result_entry.get("vulns", []) if v.get("id")
        )
        out[dep] = ids
    return Ok(out)


def _fetch_vuln(vuln_id: str, base_url: str | None, timeout_s: float) -> dict | None:
    """`GET /v1/vulns/{id}` full record for one advisory id; `None` on
    failure/unparseable body."""
    url = (base_url if base_url else _VULN_URL).format(id=vuln_id)
    raw = _http_get_json(url, timeout_s)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        _log.warning("vet: osv vuln %s response unparseable: %s", vuln_id, exc)
        return None


def _fetch_from_network(
    deps: tuple[Dependency, ...],
    cache_path: Path,
    *,
    base_url: str | None,
    timeout_s: float,
) -> Result[dict[Dependency, tuple[OsvAdvisory, ...]], str]:
    """Query OSV.dev for every dep in `deps`, cache each dep's result, and
    return the full per-dep advisory map; `Err("network")` /
    `Err("unparseable:...")` if the batch call itself fails (a per-vuln
    detail-fetch failure degrades that ONE advisory's record to a minimal
    stub instead of dropping the whole batch -- an id-only hit is still a
    real finding, just less detailed)."""
    ids_result = _fetch_advisory_ids(deps, base_url, timeout_s)
    if ids_result.is_err:
        return Err(ids_result.danger_err)
    ids_by_dep = ids_result.danger_ok

    vuln_cache: dict[str, dict] = {}
    out: dict[Dependency, tuple[OsvAdvisory, ...]] = {}
    for dep, ids in ids_by_dep.items():
        advisories: list[OsvAdvisory] = []
        for vuln_id in ids:
            vuln = vuln_cache.get(vuln_id)
            if vuln is None:
                vuln = _fetch_vuln(vuln_id, None, timeout_s)
                if vuln is None:
                    vuln = {"id": vuln_id}  # id-only stub, never dropped
                vuln_cache[vuln_id] = vuln
            advisories.append(_advisory_from_vuln(dep, vuln))
        out[dep] = tuple(advisories)
        ttl_cache_set(
            cache_path,
            _CACHE_TABLE,
            _cache_key(dep.ecosystem, dep.name, dep.version),
            json.dumps([_advisory_to_dict(a) for a in advisories]),
        )
    _log.info(
        "vet: osv queried %d dependency(ies), %d had advisories",
        len(deps),
        sum(1 for advs in out.values() if advs),
    )
    return Ok(out)


def _advisory_to_dict(advisory: OsvAdvisory) -> dict:
    """`OsvAdvisory` -> the JSON-serializable shape stored in the cache."""
    return {
        "advisory_id": advisory.advisory_id,
        "package": advisory.package,
        "version": advisory.version,
        "fixed_version": advisory.fixed_version,
        "aliases": list(advisory.aliases),
        "severity": advisory.severity,
        "summary": advisory.summary,
    }


def _advisory_from_dict(data: dict) -> OsvAdvisory:
    """The inverse of `_advisory_to_dict` (cache read path)."""
    return OsvAdvisory(
        advisory_id=data["advisory_id"],
        package=data["package"],
        version=data["version"],
        fixed_version=data.get("fixed_version"),
        aliases=tuple(data.get("aliases", [])),
        severity=data.get("severity"),
        summary=data.get("summary", ""),
    )


def _cached_advisories_and_age(
    cache_path: Path, dep: Dependency
) -> tuple[tuple[OsvAdvisory, ...] | None, float | None]:
    """The cached advisory list for `dep` (any age -- staleness is the
    caller's decision) and how many seconds old the entry is; `(None,
    None)` on a cold cache."""
    import sqlite3

    key = _cache_key(dep.ecosystem, dep.name, dep.version)
    if not cache_path.exists():
        return None, None
    try:
        conn = sqlite3.connect(str(cache_path))
        try:
            row = conn.execute(
                f"SELECT value, fetched_at FROM {_CACHE_TABLE} WHERE key = ?",  # noqa: S608
                (key,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        _log.warning("vet: osv cache read failed for %s: %s", key, exc)
        return None, None
    if row is None:
        return None, None
    value, fetched_at = row
    try:
        advisories = tuple(_advisory_from_dict(d) for d in json.loads(value))
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        _log.warning("vet: osv cache entry for %s unparseable: %s", key, exc)
        return None, None
    return advisories, time.time() - fetched_at


# frob:doc docs/modules/vet.md#public-api
# frob:enforces SC-DEFENSE-OSV
# frob:ticket T-5138
# frob:tests tests/vet_suite/test_advisories.py::TestOsvAdapter.test_query_advisories_positive_control_fires_a_known_advisory  # noqa: E501
# frob:tests tests/vet_suite/test_advisories.py::TestOsvAdapter.test_query_advisories_serves_fresh_cache_with_no_network_call  # noqa: E501
# frob:tests tests/vet_suite/test_advisories.py::TestOsvAdapter.test_query_advisories_no_cache_no_network_is_unavailable  # noqa: E501
def query_advisories(
    deps: tuple[Dependency, ...],
    *,
    cache_path: Path,
    base_url: str | None = None,
    timeout_s: float = _TIMEOUT_S,
    fetch: bool = True,
    max_age_days: float = 7.0,
) -> Result[dict[Dependency, tuple[OsvAdvisory, ...]], OsvQueryFailure]:
    """Advisories for every dep in `deps`, batched through OSV.dev's
    `querybatch` API (docs/modules/vet.md "Advisories (VET005)").

    Cache-first per dep (fresh < 24h TTL serves with zero network calls).
    A stale-cache-or-miss dep triggers one network attempt UNLESS
    `fetch=False`. A dep whose cache is unusable (miss, or older than
    `max_age_days`) AND could not be freshly fetched makes the WHOLE call
    `Err(OsvQueryFailure(Unavailable))` (VET012) -- never a partial silent
    drop of that one dependency's advisories. T-5139: OSV.dev REACHED but
    answering with an unparseable body is instead
    `Err(OsvQueryFailure(UnparseableResponse, detail=<response tail>))`,
    a distinct, more actionable failure (acceptance [2]).
    """
    fresh, need_fetch, stale_fallback, unusable = _classify_deps(
        deps, cache_path, max_age_days
    )
    fetch_result = _fetch_if_needed(need_fetch, fetch, cache_path, base_url, timeout_s)
    if fetch_result is not None and fetch_result.is_err:
        detail = fetch_result.danger_err
        if detail.startswith("unparseable:"):
            _log.warning("vet: osv response unparseable: %s", detail)
            return Err(
                OsvQueryFailure(
                    OsvQueryError.UnparseableResponse, detail[len("unparseable:") :]
                )
            )
    fresh, unusable = _merge_fetch_outcome(
        fresh, stale_fallback, unusable, need_fetch, fetch_result
    )

    if unusable:
        _log.warning(
            "vet: osv advisory data unavailable for %d dep(s) (no fresh cache, "
            "no network, or cache older than %.0fd)",
            len(unusable),
            max_age_days,
        )
        return Err(OsvQueryFailure(OsvQueryError.Unavailable))

    return Ok(fresh)


def _classify_deps(
    deps: tuple[Dependency, ...], cache_path: Path, max_age_days: float
) -> tuple[
    dict[Dependency, tuple[OsvAdvisory, ...]],
    list[Dependency],
    dict[Dependency, tuple[OsvAdvisory, ...]],
    list[Dependency],
]:
    """Bucket each dep in `deps` by cache state: `fresh` (serve as-is, no
    fetch needed -- includes ecosystems OSV has no data for at all),
    `need_fetch` (a network attempt is worth making), `stale_fallback` (a
    usable-if-fetch-fails backstop), `unusable` (nothing to fall back to
    if the fetch does not happen/succeed)."""
    fresh: dict[Dependency, tuple[OsvAdvisory, ...]] = {}
    need_fetch: list[Dependency] = []
    stale_fallback: dict[Dependency, tuple[OsvAdvisory, ...]] = {}
    unusable: list[Dependency] = []

    for dep in deps:
        cached, age_s = _cached_advisories_and_age(cache_path, dep)
        if cached is not None and age_s is not None and age_s <= _CACHE_TTL_S:
            fresh[dep] = cached
            continue
        need_fetch.append(dep)
        if cached is not None and age_s is not None and age_s <= max_age_days * 86400:
            stale_fallback[dep] = cached
        elif cached is None and _osv_ecosystem(dep) is None:
            # No OSV coverage for this ecosystem at all -- honestly "no
            # advisories to report" rather than an unreachable-network verdict.
            fresh[dep] = ()
            need_fetch.remove(dep)
        else:
            unusable.append(dep)
    return fresh, need_fetch, stale_fallback, unusable


def _fetch_if_needed(
    need_fetch: list[Dependency],
    fetch: bool,
    cache_path: Path,
    base_url: str | None,
    timeout_s: float,
) -> Result[dict[Dependency, tuple[OsvAdvisory, ...]], str] | None:
    """One network attempt for `need_fetch`, or `None` if skipped
    (`fetch=False`, net disabled, or nothing to fetch); a made attempt
    always returns a `Result` (T-5139: distinguishes a plain network
    failure from a reached-but-unparseable response, see
    `_fetch_advisory_ids`)."""
    if not need_fetch or not fetch:
        return None
    if not net_enabled():
        _log.warning(
            "vet: osv query for %d dep(s) skipped (net disabled via %s)",
            len(need_fetch),
            NET_KILL_SWITCH_ENV,
        )
        return None
    return _fetch_from_network(
        tuple(need_fetch), cache_path, base_url=base_url, timeout_s=timeout_s
    )


def _merge_fetch_outcome(
    fresh: dict[Dependency, tuple[OsvAdvisory, ...]],
    stale_fallback: dict[Dependency, tuple[OsvAdvisory, ...]],
    unusable: list[Dependency],
    need_fetch: list[Dependency],
    fetch_result: Result[dict[Dependency, tuple[OsvAdvisory, ...]], str] | None,
) -> tuple[dict[Dependency, tuple[OsvAdvisory, ...]], list[Dependency]]:
    """Fold a (possibly-skipped/failed) fetch attempt's outcome into
    `fresh`/`unusable`: a successful fetch resolves every dep it covers
    (clearing it from `unusable`); a skipped/failed one falls back to
    `stale_fallback`, leaving only the truly unusable deps."""
    fetched = (
        fetch_result.danger_ok
        if fetch_result is not None and fetch_result.is_ok
        else None
    )
    if fetched is not None:
        fresh = {**fresh, **fetched}
        unusable = [d for d in unusable if d not in fetched]
    else:
        fresh = {**fresh, **stale_fallback}
        unusable = [d for d in need_fetch if d not in stale_fallback]
    return fresh, unusable


__all__ = [
    "OsvAdvisory",
    "OsvQueryError",
    "OsvQueryFailure",
    "cve_ids",
    "query_advisories",
]
