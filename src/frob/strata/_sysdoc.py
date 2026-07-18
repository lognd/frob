"""`frob sys doc` audit matrix rendering + DOC003 claims audit (T-0085,
docs/strata/threat.md#the-exhaustiveness-proof-the-point).

Two responsibilities, both pure (no I/O -- mirrors `_report.py::render_
report`'s split from its CLI caller):

1. `render_audit_matrix` -- the human-facing matrix the charter names:
   "applicable weakness -> precondition present? -> mitigation -> evidence
   rung -> citation", grouped by `WeaknessEntry.family` (docs/strata/
   threat.md: "the exhaustiveness proof is computed PER FAMILY against a
   cited baseline"). `frob.app.sys_runner` is the CLI wrapper.
2. `audit_claim` -- the model-side half of DOC003 (a doc's `frob:claims
   <view>` marker resolving to PROVED or not); `frob.gates.sys_gate` does
   the doc-scanning I/O and turns a non-proved result into a `Violation`.

T-0085 scope note: this module imports `frob.strata._threat`'s PUBLIC
surface only (`evaluate_threats`, `check_catalog_completeness`, `check_
discharge_completeness`, `CWE_CATALOG`, `VIEWS`, the catalog models) --
`_threat.py`'s catalog internals (`_entries_by_capability_kind`, `_fired_
obligations`, ...) are never touched or imported here, since T-0116
extends that catalog concurrently. `_may_kind` is imported from
`._effects` the SAME way `_threat.py` itself already does (established
cross-module precedent, not a new one) -- there is no public capability-
kind-extraction helper anywhere in `frob.strata` today.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._effects import _may_kind
from ._errors import StrataError
from ._models import KernelModel
from ._threat import (
    CWE_CATALOG,
    DEFAULT_BENIGN_CAPABILITIES,
    VIEWS,
    BenignCapability,
    OutOfScopeEntry,
    ThreatViolation,
    WeaknessEntry,
    check_catalog_completeness,
    check_discharge_completeness,
    evaluate_threats,
)

_log = get_logger(__name__)


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:tests tests/unit/strata/test_sysdoc.py::TestMergeModels.test_concat_fields
# frob:tests tests/unit/strata/test_sysdoc.py::TestMergeModels.test_empty_tuple
def merge_models(models: tuple[KernelModel, ...]) -> KernelModel:
    """Concatenate every loaded design file's facts into one `KernelModel`
    so a multi-file design is audited as a single obligation surface.

    Public (unlike `frob.app.sys_runner`'s private, unrelated `_merge_
    models` helper for `frob sys plan`) because DOC003's gate
    (`frob.gates.sys_gate`) needs the exact same merge and lives in a
    different package -- `frob.gates` must not import `frob.app` (wrong
    direction), so this is the one shared home (charter: no
    duplication)."""
    return KernelModel(
        nodes=tuple(n for m in models for n in m.nodes),
        flows=tuple(f for m in models for f in m.flows),
        boundaries=tuple(b for m in models for b in m.boundaries),
        claims=tuple(c for m in models for c in m.claims),
        scenarios=tuple(s for m in models for s in m.scenarios),
    )


def _declared_capability_kinds(model: KernelModel) -> frozenset[str]:
    """Every capability KIND declared by ANY node's `may` atoms in `model`
    -- the model-wide "is this precondition present at all" join the
    matrix needs. Per-entry, not per-node: the charter names the matrix
    row unit as "applicable weakness", not "weakness x node"."""
    kinds: set[str] = set()
    for node in model.nodes:
        kinds.update(_may_kind(atom) for atom in node.may)
    return frozenset(kinds)


def _row(
    entry: WeaknessEntry,
    *,
    declared: frozenset[str],
    discharge_violations: dict[str, list[ThreatViolation]],
) -> tuple[str, str, str, str, str, str]:
    """One matrix row: (id, title, precondition-present?, mitigation,
    status/evidence-rung, citation) -- the exact five-column shape the
    charter names, plus the id/title lead columns a human-readable table
    needs."""
    if entry.capability_kind is None:
        precondition = "n/a (design-level)"
        status = "not evaluated (no precondition detector yet, phase A)"
    elif entry.capability_kind in declared:
        precondition = "present"
        violations = discharge_violations.get(entry.id, [])
        if violations:
            status = "FAILING: " + "; ".join(v.detail for v in violations)
        else:
            status = f"PROVED ({entry.rung.value})"
    else:
        precondition = "absent"
        status = "not applicable"

    return (entry.id, entry.title, precondition, entry.mitigation, status, entry.cite)


def _md_row(cells: tuple[str, ...]) -> str:
    """One markdown table row, pipe-escaped (a `|` inside a cell would
    otherwise split the table -- catalog `detail` text can legitimately
    contain one, e.g. quoting a claim id)."""
    escaped = (cell.replace("|", "\\|") for cell in cells)
    return "| " + " | ".join(escaped) + " |"


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:ticket T-0148
# frob:waive TEST005 reason="render_audit_matrix 85.7% branch cover, debt T-0160"
def render_audit_matrix(
    model: KernelModel,
    view: str,
    *,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    out_of_scope: tuple[OutOfScopeEntry, ...] = (),
    benign: tuple[BenignCapability, ...] = (),
    views: dict[str, frozenset[str]] | None = None,
) -> Result[str, StrataError]:
    """Render the deterministic per-family audit matrix for `view` against
    `model`: applicable weakness -> precondition present? -> mitigation ->
    evidence rung/status -> citation (docs/strata/threat.md#the-
    exhaustiveness-proof-the-point). `Err(StrataError.UnknownReference)`
    on an unrecognized `view`, matching `check_catalog_completeness`'s
    fail-closed posture on a typo'd view name."""
    view_table = views if views is not None else VIEWS
    members = view_table.get(view)
    if members is None:
        _log.error("sysdoc: unknown baseline view %r", view)
        return Err(StrataError.UnknownReference)

    catalog_gaps = check_catalog_completeness(view, catalog, out_of_scope, views)
    if catalog_gaps.is_err:
        return Err(catalog_gaps.danger_err)
    discharge = check_discharge_completeness(model, catalog)
    if discharge.is_err:
        return Err(discharge.danger_err)

    declared = _declared_capability_kinds(model)
    by_cwe: dict[str, list[ThreatViolation]] = {}
    for violation in discharge.danger_ok:
        by_cwe.setdefault(violation.cwe, []).append(violation)

    # frob:waive PERF004 reason="sorts once per call, not per loop iteration"
    entries = sorted(
        (e for e in catalog if e.id in members), key=lambda e: (e.family, e.id)
    )
    excused = sorted((e for e in out_of_scope if e.id in members), key=lambda e: e.id)

    lines: list[str] = [f"# Audit matrix -- view {view!r}", ""]

    entries_by_family: dict[str, list[WeaknessEntry]] = {}
    for entry in entries:
        entries_by_family.setdefault(entry.family, []).append(entry)
    families = sorted(entries_by_family)
    for family in families:
        lines.append(f"## {family}")
        lines.append("")
        header = ("CWE", "title", "precondition", "mitigation", "status", "citation")
        lines.append(_md_row(header))
        lines.append(_md_row(("---", "---", "---", "---", "---", "---")))
        for entry in entries_by_family[family]:
            row = _row(entry, declared=declared, discharge_violations=by_cwe)
            lines.append(_md_row(row))
        lines.append("")

    if excused:
        lines.append("## out-of-scope")
        lines.append("")
        lines.append(_md_row(("CWE", "reason")))
        lines.append(_md_row(("---", "---")))
        for entry in excused:
            lines.append(_md_row((entry.id, entry.reason)))
        lines.append("")

    if catalog_gaps.danger_ok:
        lines.append("## catalog gaps (THREAT001)")
        lines.append("")
        for gap in sorted(catalog_gaps.danger_ok, key=lambda v: v.cwe):
            lines.append(f"- {gap.cwe}: {gap.detail}")
        lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    _log.info(
        "sysdoc: rendered matrix view=%r entries=%d families=%d gaps=%d",
        view,
        len(entries),
        len(families),
        len(catalog_gaps.danger_ok),
    )
    return Ok(text)


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class ClaimAuditResult(BaseModel):
    """One `frob:claims <view>` doc marker's audit outcome -- PROVED (zero
    THREAT001/THREAT002/THREAT003 violations for `view` against the
    current model) or the named failing obligations. The DOC003 gate
    (`frob.gates.sys_gate`) turns a non-proved result into a `Violation`
    verbatim."""

    model_config = ConfigDict(frozen=True)

    view: str
    proved: bool
    violations: tuple[ThreatViolation, ...] = ()


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
def audit_claim(
    model: KernelModel,
    view: str,
    *,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    out_of_scope: tuple[OutOfScopeEntry, ...] = (),
    benign: tuple[BenignCapability, ...] = DEFAULT_BENIGN_CAPABILITIES,
) -> Result[ClaimAuditResult, StrataError]:
    """DOC003's model-side half: is `view`'s exhaustiveness claim PROVED
    against `model` -- or which obligations are failing, named (docs/
    strata/threat.md: "a README claiming 'protected against the OWASP Top
    10' must cite a PROVED exhaustiveness result or it fails CI"). Reuses
    `evaluate_threats` exactly as `frob sys doc`'s matrix would; a claim
    is PROVED iff the SAME conjunction the matrix reports has zero
    violations -- the two can never honestly disagree (charter: no
    duplication). `benign` defaults to `DEFAULT_BENIGN_CAPABILITIES`
    (T-0150), matching `evaluate_exhaustiveness`'s default, so DOC003 (the
    ONLY caller that reaches `design/frob.strata`'s own `frob:claims`
    marker, `src/frob/gates/__init__.py::_doc003_one_marker`) does not
    fail on tier-2 `may` kinds with no CWE-catalog analog by default; a
    caller wanting the pre-T-0150 strict behavior passes `benign=()`."""
    report = evaluate_threats(model, view, catalog, out_of_scope, benign)
    if report.is_err:
        return Err(report.danger_err)
    violations = report.danger_ok.violations
    _log.info(
        "sysdoc: claim view=%r proved=%s violations=%d",
        view,
        not violations,
        len(violations),
    )
    return Ok(ClaimAuditResult(view=view, proved=not violations, violations=violations))


__all__ = [
    "ClaimAuditResult",
    "audit_claim",
    "merge_models",
    "render_audit_matrix",
]
