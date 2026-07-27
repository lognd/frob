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
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/strata/_sysdoc.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"
# frob:waive ARCH102 reason="11 of 13 exports form one connected matrix- rendering \
# cluster around render_audit_matrix (the module's first documented responsibility); \
# the 2 outliers (merge_models, audit_claim) are the module's own documented SECOND \
# responsibility (audit_claim, the DOC003 half) plus a small WeaknessEntry-merge \
# helper the first responsibility's matrix consumes -- this module's docstring already \
# discloses it deliberately holds exactly two related pure responsibilities in one \
# file (mirroring the _report.py precedent it names), so the 3-cluster count matches a \
# documented, deliberate design rather than an accidental one"

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import CodeBinding, bind_code
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


def _assumed_cwes(model: KernelModel) -> frozenset[str]:
    """CWE ids with at least one `assumed` discharging claim (naming
    convention `weakness:<cwe-id>:<node-id>`, docs/strata/threat.md#the-
    core-reframe) -- the matrix (T-0224) must never print PROVED for these:
    an assume is a human-owned TCB entry `_claims.py::evaluate_claims`
    short-circuits to the `ASSUMED` verdict without ever running it through
    the closure, so a row backed only by an assume carries weaker assurance
    than one the closure actually proved and must say so distinctly."""
    cwes: set[str] = set()
    for claim in model.claims:
        if not claim.assumed:
            continue
        parts = claim.id.split(":")
        if len(parts) >= 3 and parts[0] == "weakness":
            cwes.add(parts[1])
    return frozenset(cwes)


def _row(
    entry: WeaknessEntry,
    *,
    declared: frozenset[str],
    discharge_violations: dict[str, list[ThreatViolation]],
    assumed: frozenset[str],
) -> tuple[str, str, str, str, str, str]:
    """One matrix row: (id, title, precondition-present?, mitigation,
    status/evidence-rung, citation) -- the exact five-column shape the
    charter names, plus the id/title lead columns a human-readable table
    needs. `assumed` (T-0224) forces a distinct ASSUMED status whenever the
    discharging claim is a human-owned assume rather than a closure-proved
    result -- PROVED must never overstate an assume's assurance."""
    if entry.capability_kind is None:
        precondition = "n/a (design-level)"
        status = "not evaluated (no precondition detector yet, phase A)"
    elif entry.capability_kind in declared:
        precondition = "present"
        violations = discharge_violations.get(entry.id, [])
        if violations:
            status = "FAILING: " + "; ".join(v.detail for v in violations)
        elif entry.id in assumed:
            status = f"ASSUMED ({entry.rung.value})"
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
    root: Path | None = None,
) -> Result[str, StrataError]:
    """Render the deterministic per-family audit matrix for `view` against
    `model`: applicable weakness -> precondition present? -> mitigation ->
    evidence rung/status -> citation (docs/strata/threat.md#the-
    exhaustiveness-proof-the-point). `Err(StrataError.UnknownReference)`
    on an unrecognized `view`, matching `check_catalog_completeness`'s
    fail-closed posture on a typo'd view name.

    `root` (T-0630) is the repo root `frob sys doc` always has in hand
    (`frob.app.sys_runner._resolve_design_root`) -- when given, binds
    `model` against `root`'s real tree (`_code_binding.py::bind_code`) and
    threads the resulting `CodeBinding` into the matrix's THREAT003
    discharge column, so a `FAILING` row backed only by an unbound
    predicate is reported here too, not only through `frob sys audit`.
    Omitted preserves the pre-T-0630 model-only rendering. A `bind_code`
    failure (`Err(StrataError.AmbiguousCodeBinding)`) propagates fail-
    closed rather than rendering a matrix silently missing the join."""
    view_table = views if views is not None else VIEWS
    members = view_table.get(view)
    if members is None:
        _log.error("sysdoc: unknown baseline view %r", view)
        return Err(StrataError.UnknownReference)

    binding: CodeBinding | None = None
    if root is not None:
        bound = bind_code(model, root)
        if bound.is_err:
            return Err(bound.danger_err)
        binding = bound.danger_ok

    checked = _check_matrix_completeness(
        model, view, catalog, out_of_scope, views, binding, root
    )
    if checked.is_err:
        return Err(checked.danger_err)
    catalog_gaps, discharge = checked.danger_ok

    entries, excused = _matrix_entries(catalog, out_of_scope, members)
    return Ok(
        _render_matrix_text(model, view, entries, excused, catalog_gaps, discharge)
    )


def _render_matrix_text(
    model: KernelModel,
    view: str,
    entries: list[WeaknessEntry],
    excused: list[OutOfScopeEntry],
    catalog_gaps: tuple[ThreatViolation, ...],
    discharge: tuple[ThreatViolation, ...],
) -> str:
    """Assemble and log the final matrix text from its sections, split out
    of `render_audit_matrix` purely to keep that function's body short."""
    lines = _family_table_lines(model, entries, discharge)
    lines.extend(_excused_lines(excused))
    lines.extend(_catalog_gap_lines(catalog_gaps))
    text = "\n".join([f"# Audit matrix -- view {view!r}", "", *lines]).rstrip() + "\n"
    _log.info(
        "sysdoc: rendered matrix view=%r entries=%d families=%d gaps=%d",
        view,
        len(entries),
        len({e.family for e in entries}),
        len(catalog_gaps),
    )
    return text


def _check_matrix_completeness(
    model: KernelModel,
    view: str,
    catalog: tuple[WeaknessEntry, ...],
    out_of_scope: tuple[OutOfScopeEntry, ...],
    views: dict[str, frozenset[str]] | None,
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> Result[
    tuple[tuple[ThreatViolation, ...], tuple[ThreatViolation, ...]], StrataError
]:
    """The `(catalog_gaps, discharge_violations)` pair `render_audit_matrix`
    needs before it can render a single row, split out purely to keep that
    function's body short. `binding`/`root` (T-0630) pass straight through
    to THREAT003's discharge check."""
    catalog_gaps = check_catalog_completeness(view, catalog, out_of_scope, views)
    if catalog_gaps.is_err:
        return Err(catalog_gaps.danger_err)
    discharge = check_discharge_completeness(model, catalog, binding, root)
    if discharge.is_err:
        return Err(discharge.danger_err)
    return Ok((catalog_gaps.danger_ok, discharge.danger_ok))


def _matrix_entries(
    catalog: tuple[WeaknessEntry, ...],
    out_of_scope: tuple[OutOfScopeEntry, ...],
    members: frozenset[str],
) -> tuple[list[WeaknessEntry], list[OutOfScopeEntry]]:
    """The `(entries, excused)` pair for `view`'s member CWEs, sorted --
    split out of `render_audit_matrix` purely to keep that function's body
    short."""
    # frob:waive PERF004 reason="sorts once per call, not per loop iteration"
    entries = sorted(
        (e for e in catalog if e.id in members), key=lambda e: (e.family, e.id)
    )
    excused = sorted((e for e in out_of_scope if e.id in members), key=lambda e: e.id)
    return entries, excused


def _family_table_lines(
    model: KernelModel,
    entries: list[WeaknessEntry],
    discharge: tuple[ThreatViolation, ...],
) -> list[str]:
    """The `## <family>` table sections for every family in `entries`, for
    `render_audit_matrix`."""
    declared = _declared_capability_kinds(model)
    assumed = _assumed_cwes(model)
    by_cwe: dict[str, list[ThreatViolation]] = {}
    for violation in discharge:
        by_cwe.setdefault(violation.cwe, []).append(violation)

    entries_by_family: dict[str, list[WeaknessEntry]] = {}
    for entry in entries:
        entries_by_family.setdefault(entry.family, []).append(entry)

    lines: list[str] = []
    header = ("CWE", "title", "precondition", "mitigation", "status", "citation")
    for family in sorted(entries_by_family):
        lines.append(f"## {family}")
        lines.append("")
        lines.append(_md_row(header))
        lines.append(_md_row(("---", "---", "---", "---", "---", "---")))
        for entry in entries_by_family[family]:
            row = _row(
                entry, declared=declared, discharge_violations=by_cwe, assumed=assumed
            )
            lines.append(_md_row(row))
        lines.append("")
    return lines


def _excused_lines(excused: list[OutOfScopeEntry]) -> list[str]:
    """The `## out-of-scope` table section, empty when `excused` is empty,
    for `render_audit_matrix`."""
    if not excused:
        return []
    lines = ["## out-of-scope", "", _md_row(("CWE", "reason")), _md_row(("---", "---"))]
    lines.extend(_md_row((entry.id, entry.reason)) for entry in excused)
    lines.append("")
    return lines


def _catalog_gap_lines(catalog_gaps: tuple[ThreatViolation, ...]) -> list[str]:
    """The `## catalog gaps (THREAT001)` section, empty when there are no
    gaps, for `render_audit_matrix`."""
    if not catalog_gaps:
        return []
    lines = ["## catalog gaps (THREAT001)", ""]
    sorted_gaps = sorted(catalog_gaps, key=lambda v: v.cwe)
    lines.extend(f"- {gap.cwe}: {gap.detail}" for gap in sorted_gaps)
    lines.append("")
    return lines


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
