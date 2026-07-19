"""Match project dependencies against a local cvelistV5 mirror and link
each hit's CWE ids into the strata threat catalog (docs/modules/vet.md
"CVE mirror matching (T-0147)"; builds on `frob.cve` (T-0146), which is
parser/models only and deliberately does not do this matching itself).

No network anywhere: `frob.cve.iter_mirror` walks a local mirror clone
only, and this module never fetches. Vacuous-pass doctrine throughout: an
installed version whose range membership cannot be determined (an
uncomparable `versionType`, or no explicit range plus an unknown
`defaultStatus`) is reported `INDETERMINATE` with a specific reason, never
silently folded into `UNAFFECTED`. A CWE id with no catalog or
out-of-scope entry is reported `UNMAPPED`, never dropped.
"""

# frob:ticket T-0147
from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from packaging.version import InvalidVersion
from packaging.version import Version as PkgVersion
from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.result import Result

from frob.cve import Affected, CveRecord, CveState, Version, iter_mirror
from frob.cve._models import CveError
from frob.logging import get_logger
from frob.vet._models import Dependency, VetError

_log = get_logger(__name__)

#: `versionType` values this module can order/compare -- PEP440 covers
#: `packaging.version.Version`'s own dialect, "semver"/"python" are the
#: two most common upstream spellings for the same comparable shape, and
#: "" is the (common) unset case treated as PEP440-ish best-effort. Any
#: other value (git commit hashes, "custom", "rpm", "unspecified", ...)
#: is NOT comparable and yields `INDETERMINATE`, never a guessed order.
_COMPARABLE_VERSION_TYPES: frozenset[str] = frozenset(
    {"", "semver", "python", "pep440"}
)


# frob:doc docs/modules/vet.md#public-api
class MatchStatus(StrEnum):
    """One dependency-vs-CVE verdict: `AFFECTED`/`UNAFFECTED` are
    determinate; `INDETERMINATE` means the range membership could not be
    established (uncomparable `versionType`, unparseable version string,
    or no explicit range plus `defaultStatus="unknown"`) -- reported
    loudly with a reason, never silently downgraded to `UNAFFECTED`
    (vacuous-pass doctrine)."""

    AFFECTED = "affected"
    UNAFFECTED = "unaffected"
    INDETERMINATE = "indeterminate"


# frob:doc docs/modules/vet.md#public-api
class CweDisposition(StrEnum):
    """Where a matched CVE's CWE id landed against the strata threat
    catalog: cataloged (named entry + mitigation), explicitly out-of-scope
    (named reason), or unmapped (neither -- the id is simply not covered
    yet)."""

    CATALOG = "catalog"
    OUT_OF_SCOPE = "out_of_scope"
    UNMAPPED = "unmapped"


# frob:doc docs/modules/vet.md#public-api
class CweLink(BaseModel):
    """One CVE `problemTypes[].descriptions[].cweId` cross-referenced
    against `CWE_CATALOG`/`CWE_TOP_25_CATALOG` (catalog hit: `title`/
    `mitigation` populated) or `CWE_TOP_25_OUT_OF_SCOPE`/
    `QUALITY_OUT_OF_SCOPE` (out-of-scope hit: `reason` populated) --
    `UNMAPPED` when neither table names the id."""

    model_config = ConfigDict(frozen=True)

    cwe_id: str
    disposition: CweDisposition
    title: str = ""
    mitigation: str = ""
    reason: str = ""


# frob:doc docs/modules/vet.md#public-api
class CveMatch(BaseModel):
    """One (CVE, dependency) hit: the version-range verdict plus CVSS
    (v4.0 preferred over v3.1), a description summary, and every matched
    CWE's catalog linkage."""

    model_config = ConfigDict(frozen=True)

    cve_id: str
    dependency: str
    version: str
    ecosystem: str
    status: MatchStatus
    reason: str
    cvss_score: float | None = None
    cvss_severity: str | None = None
    summary: str = ""
    cwe_links: tuple[CweLink, ...] = ()


def _cwe_catalog_index() -> dict[str, tuple[str, str]]:
    """`{cwe_id: (title, mitigation)}` over `CWE_CATALOG + CWE_TOP_25_CATALOG`.

    Imports `frob.strata._threat` lazily (call time, not module load time):
    `frob.strata` imports `frob.vet` (capability scanning feeds strata's
    effects model), so a module-level import here would be a circular
    import -- `frob.vet` must finish initializing before `frob.strata` is
    safe to import from.
    """
    from frob.strata._threat import CWE_CATALOG, CWE_TOP_25_CATALOG

    return {
        entry.id: (entry.title, entry.mitigation)
        for entry in (*CWE_CATALOG, *CWE_TOP_25_CATALOG)
    }


def _cwe_out_of_scope_index() -> dict[str, str]:
    """`{cwe_id: reason}` over the two out-of-scope tables named in
    `docs/strata/threat.md` (`CWE_TOP_25_OUT_OF_SCOPE`, `QUALITY_OUT_OF_SCOPE`)
    -- lazy import for the same circular-import reason as `_cwe_catalog_index`."""
    from frob.strata._threat import CWE_TOP_25_OUT_OF_SCOPE, QUALITY_OUT_OF_SCOPE

    return {
        entry.id: entry.reason
        for entry in (*CWE_TOP_25_OUT_OF_SCOPE, *QUALITY_OUT_OF_SCOPE)
    }


# frob:doc docs/modules/vet.md#public-api
def link_cwe_ids(cwe_ids: tuple[str, ...]) -> tuple[CweLink, ...]:
    """Cross-reference `cwe_ids` against the strata threat catalog: a
    catalog hit names its entry's title/mitigation, an out-of-scope hit
    names its reason, and anything else is `UNMAPPED` (logged, never
    dropped) -- order-stable over `cwe_ids`."""
    catalog = _cwe_catalog_index()
    out_of_scope = _cwe_out_of_scope_index()
    return tuple(_link_one_cwe(cwe_id, catalog, out_of_scope) for cwe_id in cwe_ids)


def _link_one_cwe(
    cwe_id: str, catalog: dict[str, tuple[str, str]], out_of_scope: dict[str, str]
) -> CweLink:
    """One `CweLink` for `cwe_id`: CATALOG hit, OUT_OF_SCOPE hit, or
    UNMAPPED (logged) if neither table names it."""
    catalog_hit = catalog.get(cwe_id)
    if catalog_hit is not None:
        title, mitigation = catalog_hit
        return CweLink(
            cwe_id=cwe_id,
            disposition=CweDisposition.CATALOG,
            title=title,
            mitigation=mitigation,
        )
    oos_reason = out_of_scope.get(cwe_id)
    if oos_reason is not None:
        return CweLink(
            cwe_id=cwe_id, disposition=CweDisposition.OUT_OF_SCOPE, reason=oos_reason
        )
    _log.info(
        "vet: cve: %s is not in the threat catalog or out-of-scope tables; unmapped",
        cwe_id,
    )
    return CweLink(cwe_id=cwe_id, disposition=CweDisposition.UNMAPPED)


def _parse_comparable(value: str) -> PkgVersion | None:
    """`value` as a `packaging.version.Version`, or `None` if it does not
    parse as PEP440/semver-ish (the ONLY failure mode this function has;
    callers turn a `None` into `INDETERMINATE`, never a comparison)."""
    try:
        return PkgVersion(value)
    except InvalidVersion:
        return None


def _evaluate_entry(dep_version: str, entry: Version) -> tuple[str, str]:
    """One `versions[]` entry against `dep_version`: `("match"|"no-match"
    |"indeterminate", reason)`. `entry.version` of `""`/`"0"` is the
    schema's own "no lower bound" convention; a missing `lessThan`/
    `lessThanOrEqual` with a real lower bound is a single-version point
    match."""
    version_type = (entry.versionType or "").strip().lower()
    if version_type not in _COMPARABLE_VERSION_TYPES:
        return (
            "indeterminate",
            f"versionType={entry.versionType!r} is not comparable (semver/PEP440 only)",
        )

    dep_v = _parse_comparable(dep_version)
    if dep_v is None:
        return (
            "indeterminate",
            f"installed version {dep_version!r} does not parse as semver/PEP440",
        )

    lower: PkgVersion | None = None
    if entry.version not in ("", "0"):
        lower = _parse_comparable(entry.version)
        if lower is None:
            return (
                "indeterminate",
                f"range lower bound {entry.version!r} does not parse",
            )

    return _range_match_outcome(dep_v, lower, entry)


def _range_match_outcome(
    dep_v: PkgVersion, lower: PkgVersion | None, entry: Version
) -> tuple[str, str]:
    """The `("match"|"no-match"|"indeterminate", reason)` outcome once
    `dep_v`/`lower` have parsed, from `entry`'s upper-bound fields."""
    if entry.lessThan is not None:
        upper = _parse_comparable(entry.lessThan)
        if upper is None:
            return "indeterminate", f"lessThan {entry.lessThan!r} does not parse"
        in_range = (lower is None or dep_v >= lower) and dep_v < upper
    elif entry.lessThanOrEqual is not None:
        upper = _parse_comparable(entry.lessThanOrEqual)
        if upper is None:
            return (
                "indeterminate",
                f"lessThanOrEqual {entry.lessThanOrEqual!r} does not parse",
            )
        in_range = (lower is None or dep_v >= lower) and dep_v <= upper
    elif lower is None:
        # version in {"", "0"} with no upper bound at all: the schema has
        # no way to express this except "every version", honored literally.
        in_range = True
    else:
        in_range = dep_v == lower

    return ("match" if in_range else "no-match"), ""


def _status_for_affected(
    dep_version: str, affected: Affected
) -> tuple[MatchStatus, str]:
    """`dep_version` against one `affected[]` product entry's `versions[]`
    list plus `defaultStatus` fallback. The LAST matching explicit range
    wins (the schema's own override-by-order convention); any uncomparable
    range that could not be ruled out demotes a would-be `UNAFFECTED` to
    `INDETERMINATE` rather than silently clearing it."""
    matched_status: str | None = None
    matched_reason = ""
    indeterminate_reasons: list[str] = []
    for entry in affected.versions:
        outcome, reason = _evaluate_entry(dep_version, entry)
        if outcome == "indeterminate":
            indeterminate_reasons.append(reason)
            continue
        if outcome == "match":
            matched_status = entry.status
            matched_reason = (
                f"matches range starting at {entry.version!r} (status={entry.status!r})"
            )

    if matched_status is not None:
        return _status_from_matched(matched_status, matched_reason)

    if indeterminate_reasons:
        return MatchStatus.INDETERMINATE, "; ".join(indeterminate_reasons)

    return _status_from_default(affected.defaultStatus)


def _status_from_matched(
    matched_status: str, matched_reason: str
) -> tuple[MatchStatus, str]:
    """The `(MatchStatus, reason)` for an explicit matched range's status string."""
    if matched_status == "affected":
        return MatchStatus.AFFECTED, matched_reason
    if matched_status == "unaffected":
        return MatchStatus.UNAFFECTED, matched_reason
    return (
        MatchStatus.INDETERMINATE,
        f"matched range status={matched_status!r} is neither affected nor unaffected",
    )


def _status_from_default(default: str | None) -> tuple[MatchStatus, str]:
    """The `(MatchStatus, reason)` fallback when no explicit range covers
    the installed version, from `affected.defaultStatus`."""
    if default == "affected":
        return (
            MatchStatus.AFFECTED,
            "no explicit range covers installed version; defaultStatus=affected",
        )
    if default == "unaffected":
        return (
            MatchStatus.UNAFFECTED,
            "no explicit range covers installed version; defaultStatus=unaffected",
        )
    return (
        MatchStatus.INDETERMINATE,
        "no explicit range covers installed version; defaultStatus is unknown",
    )


def _product_matches(dep_name: str, affected: Affected) -> bool:
    """Case-insensitive exact match of `dep_name` against `affected.product`.

    Honest limitation: real CVE records name products in vendor-chosen
    prose ("Apache Log4j2") that frequently differs from the package's
    registry name ("log4j-core") -- a real CPE-dictionary join is out of
    scope here (not yet built, noted rather than faked); this exact match
    only fires when the two strings agree, which undercounts real hits
    rather than overclaiming them."""
    return affected.product.strip().lower() == dep_name.strip().lower()


def _cwe_ids_of(record: CveRecord) -> tuple[str, ...]:
    """Every `cweId` across `record`'s CNA and ADP `problemTypes[]`,
    order-stable and deduped."""
    seen: list[str] = []
    for container in (record.containers.cna, *record.containers.adp):
        for problem_type in container.problemTypes:
            for desc in problem_type.descriptions:
                if desc.cweId and desc.cweId not in seen:
                    seen.append(desc.cweId)
    return tuple(seen)


def _best_cvss(record: CveRecord) -> tuple[float | None, str | None]:
    """`(baseScore, baseSeverity)` from the first `cvssV4_0` metric found
    across CNA/ADP containers, falling back to the first `cvssV3_1`
    (v4.0 preferred per docs/modules/vet.md "CVE mirror matching")."""
    v4: object = None
    v31: object = None
    for container in (record.containers.cna, *record.containers.adp):
        for metric in container.metrics:
            if metric.cvssV4_0 is not None and v4 is None:
                v4 = metric.cvssV4_0
            if metric.cvssV3_1 is not None and v31 is None:
                v31 = metric.cvssV3_1
    chosen = v4 or v31
    if chosen is None:
        return None, None
    return chosen.baseScore, chosen.baseSeverity  # type: ignore[attr-defined]


def _description_summary(record: CveRecord, *, max_len: int = 240) -> str:
    """The first English description across CNA/ADP containers, truncated
    to `max_len` chars; empty string when the record carries none."""
    # frob:waive PERF003 reason="flat walk over few containers x descriptions"
    for container in (record.containers.cna, *record.containers.adp):
        for desc in container.descriptions:
            if desc.lang == "en" and desc.value:
                text = desc.value.strip()
                return text if len(text) <= max_len else text[: max_len - 3] + "..."
    return ""


def _scan_containers_for_dependency(
    record: CveRecord, dep: Dependency
) -> tuple[bool, bool, bool, list[str]]:
    """Scan every CNA/ADP container's `affected[]` for a product-name match
    against `dep`; returns `(any_affected, any_indeterminate,
    matched_product, reasons)`."""
    any_affected = False
    any_indeterminate = False
    matched_product = False
    reasons: list[str] = []
    for container in (record.containers.cna, *record.containers.adp):
        for affected in container.affected:
            if not _product_matches(dep.name, affected):
                continue
            matched_product = True
            status, reason = _status_for_affected(dep.version, affected)
            reasons.append(reason)
            if status is MatchStatus.AFFECTED:
                any_affected = True
            elif status is MatchStatus.INDETERMINATE:
                any_indeterminate = True
    return any_affected, any_indeterminate, matched_product, reasons


def _match_record_dependency(
    record: CveRecord, dep: Dependency
) -> tuple[MatchStatus, str] | None:
    """`dep` against every `affected[]` entry (CNA + ADP) whose product
    name matches; `None` when no entry names this dependency at all. Any
    matching entry saying `AFFECTED` wins outright; failing that, any
    `INDETERMINATE` wins over a clean `UNAFFECTED` -- never silently
    downgraded (vacuous-pass doctrine)."""
    any_affected, any_indeterminate, matched_product, reasons = (
        _scan_containers_for_dependency(record, dep)
    )

    if not matched_product:
        return None
    if any_affected:
        return MatchStatus.AFFECTED, "; ".join(reasons)
    if any_indeterminate:
        return MatchStatus.INDETERMINATE, "; ".join(reasons)
    return MatchStatus.UNAFFECTED, "; ".join(reasons)


def _matches_for_record(
    record: CveRecord, deps: tuple[Dependency, ...]
) -> list[CveMatch]:
    """One `CveMatch` per `deps` entry `record` names as affected/unaffected/
    indeterminate."""
    matches: list[CveMatch] = []
    for dep in deps:
        outcome = _match_record_dependency(record, dep)
        if outcome is None:
            continue
        status, reason = outcome
        score, severity = _best_cvss(record)
        match = CveMatch(
            cve_id=record.cveMetadata.cveId,
            dependency=dep.name,
            version=dep.version,
            ecosystem=dep.ecosystem,
            status=status,
            reason=reason,
            cvss_score=score,
            cvss_severity=severity,
            summary=_description_summary(record),
            cwe_links=link_cwe_ids(_cwe_ids_of(record)),
        )
        matches.append(match)
        _log.info(
            "vet: cve: %s vs %s@%s -> %s",
            record.cveMetadata.cveId,
            dep.name,
            dep.version,
            status,
        )
    return matches


def _usable_mirror_record(
    path: Path, result: Result[CveRecord, CveError], mirror_root: Path
) -> Result[CveRecord | None, VetError]:
    """One `iter_mirror` entry's usable record, or `None` to skip (a parse
    failure or a REJECTED record); `Err` only for an invalid mirror path."""
    if result.is_err:
        if result.danger_err is CveError.MirrorPathInvalid:
            _log.error("vet: cve: mirror path configured but invalid: %s", mirror_root)
            return Err(VetError.CveMirrorInvalid)
        _log.warning("vet: cve: record %s failed to parse: %s", path, result.danger_err)
        return Ok(None)

    record = result.danger_ok
    if record.cveMetadata.state is CveState.REJECTED:
        _log.info("vet: cve: skipping REJECTED record %s", record.cveMetadata.cveId)
        return Ok(None)
    return Ok(record)


# A configured-but-missing/unreadable mirror is a loud `Err
# (VetError.CveMirrorInvalid)` -- vacuous-pass doctrine: this function is
# only ever called when a mirror IS configured, so failing to read it
# must never look like "zero CVEs found".
# frob:doc docs/modules/vet.md#public-api
# frob:waive TEST005 reason="match_deps_against_mirror 88.9% branch cover, debt T-0160"
def match_dependencies_against_mirror(
    deps: tuple[Dependency, ...], mirror_root: Path
) -> Result[tuple[CveMatch, ...], VetError]:
    """Walk `mirror_root` (a local cvelistV5 clone, `frob.cve.iter_mirror`
    layout) and match every `deps` entry against every `PUBLISHED` record's
    `affected[]` products. `REJECTED` records are skipped with a log line."""
    matches: list[CveMatch] = []
    try:
        for path, result in iter_mirror(mirror_root):
            record_result = _usable_mirror_record(path, result, mirror_root)
            if record_result.is_err:
                return Err(record_result.danger_err)
            record = record_result.danger_ok
            if record is None:
                continue
            matches.extend(_matches_for_record(record, deps))
    except OSError as exc:
        _log.error("vet: cve: mirror %s unreadable: %s", mirror_root, exc)
        return Err(VetError.CveMirrorInvalid)

    _log.info(
        "vet: cve: matched %d dependency/CVE pair(s) against mirror %s",
        len(matches),
        mirror_root,
    )
    return Ok(tuple(matches))


__all__ = [
    "CveMatch",
    "CweDisposition",
    "CweLink",
    "MatchStatus",
    "link_cwe_ids",
    "match_dependencies_against_mirror",
]
