"""Containment report: joins `frob vet`'s OSV/CVE findings against strata's
CWE obligation model (docs/strata/threat.md "CVE: threat intelligence
joined to the proof" -- phase D, T-0110).

A CVE against a locked dependency maps (via NVD, `_nvd.py`) to one or more
CWE ids. For each mapped CWE that is also in `frob.strata`'s catalog, this
module asks: which node's `code=` glob covers the file(s) that import this
dependency (`frob.strata.bind_code`), and is THAT node's obligation for
this CWE discharged (`frob.strata.check_discharge_completeness`)? A live
CVE whose obligation is undischarged is reported `state="live"`
(high-severity: the design offers no proof this weakness class is
mitigated where the vulnerable code actually runs); one whose obligation
is discharged is `state="contained"` (defense-in-depth). A dependency the
model does not bind to any node, or a CWE the catalog does not classify,
is reported `state="unmodeled"` (genuine no-coverage -- there is nothing
to check, not that a check failed). A CVE whose NVD lookup itself could
not be completed (network failure, cache miss under `fetch=False`,
unparseable response) is reported `state="unverified"` -- DISTINCT from
`"unmodeled"`: an NVD outage means "we do not know", never "there is
nothing here", and a triage consumer scanning for the worst finding must
never read a data-source outage as a benign no-coverage result. Nothing
here is silently dropped and nothing is conflated with "contained"
(charter law 2: deny-by-default, no vacuous pass).

Import-only consumer of `frob.strata`'s public API (`bind_code`, `FOREIGN`,
`CWE_CATALOG`, `check_discharge_completeness`) -- this module adds no new
strata primitive and does not touch `frob/strata/**` internals.

Honest scope cut: CVE ingestion only resolves advisory ids/aliases already
shaped like `CVE-\\d{4}-\\d+` (`_osv.py::cve_ids`) -- a GHSA/PYSEC/RUSTSEC
advisory with no CVE alias is out of this join, same as `_osv.py`'s own
module docstring discloses for osv-scanner absence; it is not silently
treated as "no CVE", it simply never enters `build_containment_report`'s
input in the first place (the caller filters via `cve_ids` before calling).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._nvd import fetch_cwe_for_cve
from ._osv import OsvAdvisory, cve_ids

if TYPE_CHECKING:
    # `frob.strata` imports `frob.vet._capability` at its own module top
    # level (the tree-sitter query infra `_effects.py` shares with
    # `frob.policy`), so a MODULE-LEVEL `from frob.strata import ...` here
    # would close a circular import: loading `frob.vet` triggers this
    # module, which would try to finish loading `frob.strata` before
    # `frob.strata` has finished loading `frob.vet`. Type-only here;
    # runtime call sites import lazily instead (see `_strata()` below).
    from frob.strata import CodeBinding, KernelModel, WeaknessEntry

_log = get_logger(__name__)

#: `state` values a `ContainmentFinding` may carry -- deliberately not an
#: enum so a new value never silently fails a `match`; every consumer
#: switches on the string and each arm is exercised by a test. `UNVERIFIED`
#: (an NVD lookup could not be completed) is intentionally distinct from
#: `UNMODELED` (no coverage to check in the first place) -- collapsing the
#: two would let a data-source outage silently read as "nothing here",
#: exactly the vacuous pass charter law 2 forbids.
# frob:doc docs/modules/vet.md#public-api
LIVE = "live"
# frob:doc docs/modules/vet.md#public-api
UNVERIFIED = "unverified"
# frob:doc docs/modules/vet.md#public-api
CONTAINED = "contained"
# frob:doc docs/modules/vet.md#public-api
UNMODELED = "unmodeled"


# frob:doc docs/modules/vet.md#public-api
class ContainmentFinding(BaseModel):
    """One CVE, joined against the strata obligation model for the node
    whose code binding covers the vulnerable dependency's import surface
    (docs/strata/threat.md "CVE: threat intelligence joined to the proof").
    `node_id` is `None` when no node's `code=` glob imports `package`
    (`UNMODELED`) or when the NVD lookup itself failed (`UNVERIFIED`) --
    either is itself the finding, not an absence of one."""

    model_config = ConfigDict(frozen=True)

    cve_id: str
    package: str
    version: str
    fixed_version: str | None = None
    cwe_ids: tuple[str, ...] = ()
    node_id: str | None = None
    state: str = UNMODELED
    detail: str = ""


# frob:doc docs/modules/vet.md#public-api
class ContainmentReport(BaseModel):
    """Every `ContainmentFinding` from one `build_containment_report` pass,
    in cve-then-package order (deterministic diffing)."""

    model_config = ConfigDict(frozen=True)

    findings: tuple[ContainmentFinding, ...] = ()


def _strata():
    """Lazy `frob.strata` import (see the `TYPE_CHECKING` note above) --
    imported on first call, not at module load, to avoid the circular
    import `frob.strata._effects` -> `frob.vet._capability` -> `frob.vet`
    (this package's `__init__.py`) -> this module -> `frob.strata` would
    otherwise close."""
    import frob.strata as strata

    return strata


def _module_name(package: str) -> str:
    """The likely top-level python import name for a PyPI dist name
    (`"foo-bar"` -> `"foo_bar"`) -- a heuristic, not a resolver; a
    dependency whose import name diverges further (e.g. `pyyaml` ->
    `yaml`) is honestly `UNMODELED` rather than guessed at."""
    return package.replace("-", "_")


def _imported_names(path: Path) -> frozenset[str]:
    """Top-level module names one python file imports, best-effort -- a
    parse failure yields an empty set (never raises; this is a heuristic
    signal, not a gate)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError) as exc:
        _log.debug("containment: could not parse %s: %s", path, exc)
        return frozenset()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".", 1)[0])
    return frozenset(names)


# frob:doc docs/modules/vet.md#public-api
def find_importing_nodes(
    binding: CodeBinding, root: Path, package: str
) -> frozenset[str]:
    """Node ids whose bound files import `package` (by its likely top-level
    module name, `_module_name`) -- the "component whose code binding
    covers the dependent import surface" strata.md's phase D asks for.
    `FOREIGN`-owned files are excluded (no node claims them, so they can
    never anchor a discharge check)."""
    module = _module_name(package)
    foreign = _strata().FOREIGN
    owners: set[str] = set()
    for rel, owner in binding.owner.items():
        if owner == foreign:
            continue
        if module in _imported_names(root / rel):
            owners.add(owner)
    return frozenset(owners)


def _catalog_by_id(
    catalog: tuple[WeaknessEntry, ...],
) -> dict[str, WeaknessEntry]:
    """CWE id -> catalog entry, for the O(1) join `_finding_for_cve` needs."""
    return {entry.id: entry for entry in catalog}


def _undischarged_pairs(
    model: KernelModel,
    catalog: tuple[WeaknessEntry, ...],
    binding: CodeBinding,
    root: Path,
) -> frozenset[tuple[str, str]]:
    """`(node_id, cwe_id)` pairs THREAT003 reports as undischarged --
    `check_discharge_completeness` is the ONE home for firing + discharge
    logic (charter: no duplication); this just re-shapes its result for a
    fast membership test. T-0630: `binding`/`root` are threaded through so
    the G1 code-bound-predicate join actually runs here -- `build_
    containment_report` (this module's one caller) already has both in
    hand for `find_importing_nodes`, so omitting them from this join was
    the catalogued-is-not-enforced gap this ticket closes, not a genuine
    design-level-only caller."""
    result = _strata().check_discharge_completeness(model, catalog, binding, root)
    if result.is_err:
        _log.warning("containment: THREAT003 evaluation failed: %s", result.danger_err)
        return frozenset()
    return frozenset(
        (v.node, v.cwe) for v in result.danger_ok if v.rule == "THREAT003" and v.node
    )


def _first_live_pair(
    ordered_nodes: list[str],
    known_cwes: tuple[str, ...],
    undischarged: frozenset[tuple[str, str]],
) -> tuple[str, str] | None:
    """The first `(node_id, cwe)` pair (in `ordered_nodes`/`known_cwes`
    order) present in `undischarged`, or None if none is."""
    for node_id in ordered_nodes:
        for cwe in known_cwes:
            if (node_id, cwe) in undischarged:
                return (node_id, cwe)
    return None


def _unmodeled_finding(
    advisory: OsvAdvisory,
    cve_id: str,
    cwe_ids_for_cve: tuple[str, ...],
    node_ids: frozenset[str],
) -> ContainmentFinding:
    """The UNMODELED `ContainmentFinding` for a CVE with no importing node
    or no catalog-recognized CWE."""
    detail = (
        "no bound node imports this dependency"
        if not node_ids
        else f"no catalog entry for {cwe_ids_for_cve}"
    )
    return ContainmentFinding(
        cve_id=cve_id,
        package=advisory.package,
        version=advisory.version,
        fixed_version=advisory.fixed_version,
        cwe_ids=cwe_ids_for_cve,
        state=UNMODELED,
        detail=detail,
    )


def _finding_for_pair(
    advisory: OsvAdvisory,
    cve_id: str,
    cwe_ids_for_cve: tuple[str, ...],
    node_ids: frozenset[str],
    catalog_by_id: dict[str, WeaknessEntry],
    undischarged: frozenset[tuple[str, str]],
) -> ContainmentFinding:
    """One `ContainmentFinding` for `cve_id` against `advisory`'s package,
    classifying `state` from the joined node set and THREAT003 result."""
    known_cwes = tuple(cwe for cwe in cwe_ids_for_cve if cwe in catalog_by_id)
    if not node_ids or not known_cwes:
        return _unmodeled_finding(advisory, cve_id, cwe_ids_for_cve, node_ids)

    # Deterministic: sorted node/cwe pair order, first LIVE pair wins (a
    # live exposure on ANY covering node is reported, never averaged away).
    ordered_nodes = sorted(node_ids)
    live_pair = _first_live_pair(ordered_nodes, known_cwes, undischarged)

    if live_pair is not None:
        return _live_finding(advisory, cve_id, known_cwes, live_pair)
    return _contained_finding(advisory, cve_id, known_cwes, ordered_nodes[0])


def _live_finding(
    advisory: OsvAdvisory,
    cve_id: str,
    known_cwes: tuple[str, ...],
    live_pair: tuple[str, str],
) -> ContainmentFinding:
    """The LIVE `ContainmentFinding` for an undischarged `(node_id, cwe)` pair."""
    node_id, cwe = live_pair
    return ContainmentFinding(
        cve_id=cve_id,
        package=advisory.package,
        version=advisory.version,
        fixed_version=advisory.fixed_version,
        cwe_ids=known_cwes,
        node_id=node_id,
        state=LIVE,
        detail=f"{cwe} obligation on {node_id} is undischarged",
    )


def _contained_finding(
    advisory: OsvAdvisory, cve_id: str, known_cwes: tuple[str, ...], node_id: str
) -> ContainmentFinding:
    """The CONTAINED `ContainmentFinding` when every covering node
    discharges its obligations."""
    return ContainmentFinding(
        cve_id=cve_id,
        package=advisory.package,
        version=advisory.version,
        fixed_version=advisory.fixed_version,
        cwe_ids=known_cwes,
        node_id=node_id,
        state=CONTAINED,
        detail=f"{', '.join(known_cwes)} obligation(s) discharged on {node_id}",
    )


def _findings_for_advisory(
    advisory: OsvAdvisory,
    node_ids: frozenset[str],
    catalog_by_id: dict[str, WeaknessEntry],
    undischarged: frozenset[tuple[str, str]],
    cache_path: Path,
    base_url: str | None,
    fetch: bool,
) -> list[ContainmentFinding]:
    """One `ContainmentFinding` per CVE id on `advisory`'s package: UNVERIFIED
    if the CVE->CWE lookup fails, else `_finding_for_pair`'s join result."""
    findings: list[ContainmentFinding] = []
    for cve_id in cve_ids(advisory):
        lookup = fetch_cwe_for_cve(
            cve_id,
            cache_path=cache_path,
            base_url=base_url,
            fetch=fetch,
        )
        if not lookup.ok:
            findings.append(
                ContainmentFinding(
                    cve_id=cve_id,
                    package=advisory.package,
                    version=advisory.version,
                    fixed_version=advisory.fixed_version,
                    state=UNVERIFIED,
                    detail=lookup.note or "CWE mapping could not be verified",
                )
            )
            continue
        findings.append(
            _finding_for_pair(
                advisory, cve_id, lookup.cwe_ids, node_ids, catalog_by_id, undischarged
            )
        )
    return findings


# `fetch=False` restricts lookups to `.frob/vet.db`'s existing cache
# (offline CI / tests) -- a cache miss under `fetch=False`, a network
# failure, or an unparseable NVD response degrades to `UNVERIFIED` for
# that CVE rather than blocking or silently reading as `UNMODELED` ("we
# could not check" must never be read as "there is nothing here"), same
# offline-first posture as every other vet network adapter
# (docs/modules/vet.md VET011).
# frob:doc docs/modules/vet.md#public-api
def build_containment_report(
    advisories: tuple[OsvAdvisory, ...],
    model: KernelModel,
    binding: CodeBinding,
    root: Path,
    *,
    cache_path: Path,
    catalog: tuple[WeaknessEntry, ...] | None = None,
    fetch: bool = True,
    base_url: str | None = None,
) -> ContainmentReport:
    """Join `advisories` (an osv-scanner pass, `_osv.py::_run_osv_scan`)
    against `model`'s CWE obligations via NVD CVE->CWE data
    (docs/strata/threat.md "CVE: threat intelligence joined to the proof").
    `catalog` defaults to `frob.strata.CWE_CATALOG` (resolved lazily, see
    `_strata()`) when omitted."""
    if catalog is None:
        catalog = _strata().CWE_CATALOG
    catalog_by_id = _catalog_by_id(catalog)
    undischarged = _undischarged_pairs(model, catalog, binding, root)
    findings: list[ContainmentFinding] = []

    for advisory in advisories:
        node_ids = find_importing_nodes(binding, root, advisory.package)
        findings.extend(
            _findings_for_advisory(
                advisory,
                node_ids,
                catalog_by_id,
                undischarged,
                cache_path,
                base_url,
                fetch,
            )
        )

    findings.sort(key=lambda f: (f.cve_id, f.package))
    return ContainmentReport(findings=tuple(findings))


#: `state` -> the one-line severity tag `render_containment_report` prints
#: (docs/modules/vet.md "Public API"); order is LIVE, then UNVERIFIED,
#: then CONTAINED, then UNMODELED -- `UNVERIFIED` sorts directly after
#: `LIVE` and strictly before `CONTAINED`/`UNMODELED` because "we could
#: not check this CVE" is a MORE urgent triage signal than either a
#: verified-safe or a verified-not-applicable result: a triage consumer
#: scanning top-to-bottom must hit every unresolved data-source outage
#: before it hits anything the join actually resolved, so an outage can
#: never be silently skipped past as if it were routine no-coverage.
_STATE_LABEL = {
    LIVE: "LIVE",
    UNVERIFIED: "UNVERIFIED",
    CONTAINED: "contained",
    UNMODELED: "unmodeled",
}
_STATE_ORDER = {LIVE: 0, UNVERIFIED: 1, CONTAINED: 2, UNMODELED: 3}


# frob:doc docs/modules/vet.md#public-api
def render_containment_report(report: ContainmentReport) -> str:
    """Human-readable text rendering of `report`, ordered LIVE, then
    UNVERIFIED, then CONTAINED, then UNMODELED (the `frob vet` CLI surface
    for phase D, docs/strata/threat.md "CVE: threat intelligence joined to
    the proof") -- one line per finding, empty report renders as an
    explicit "no CVE findings" line rather than silence, matching every
    other vet skipped-note convention."""
    if not report.findings:
        return "containment: no CVE findings"
    ordered = sorted(
        report.findings, key=lambda f: (_STATE_ORDER[f.state], f.cve_id, f.package)
    )
    lines = []
    for finding in ordered:
        label = _STATE_LABEL[finding.state]
        cwe = ",".join(finding.cwe_ids) if finding.cwe_ids else "-"
        node = finding.node_id or "-"
        lines.append(
            f"{label:>10}  {finding.cve_id}  {finding.package}@{finding.version}  "
            f"cwe={cwe}  node={node}  {finding.detail}"
        )
    return "\n".join(lines)


__all__ = [
    "CONTAINED",
    "LIVE",
    "UNMODELED",
    "UNVERIFIED",
    "ContainmentFinding",
    "ContainmentReport",
    "build_containment_report",
    "find_importing_nodes",
    "render_containment_report",
]
