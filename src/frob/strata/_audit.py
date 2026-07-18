"""`frob sys audit` -- the CHECKING counterpart to `frob sys doc`'s rendering
(T-0115, docs/strata/threat.md#the-exhaustiveness-proof-the-point item F).

Evaluates the full three-part exhaustiveness conjunction (THREAT001 +
THREAT002 + THREAT003, and the COMPLIANCE001/002 mirror) for a model
against a CONFIGURED set of baseline views -- one per family (security,
quality, compliance) -- and reports every failing view as a named gap: a
machine-usable, CI-ready summary (`AuditReport.proved`, `AuditReport.gaps`)
rather than the human-facing markdown `_sysdoc.py::render_audit_matrix`
prints.

Zero new detection: this module calls only the ALREADY-SHIPPED per-check
functions `_threat.py::check_catalog_completeness` / `check_capability_
completeness` / `check_discharge_completeness` and `_compliance.py::
evaluate_compliance` -- the exact same joins `evaluate_threats` and `frob
sys doc` already run. The one seam this module adds is `_evaluate_family`,
which threads a per-family `views` table (`QUALITY_VIEWS` differs from the
security family's global `VIEWS`, so `evaluate_threats` -- which always
resolves against the module-global `VIEWS` -- cannot be reused as-is for
the quality family; `_evaluate_family` is the SAME three-call assembly
`evaluate_threats` itself performs, just parameterized on which view table
to resolve against)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._compliance import REGULATION_VIEWS, ComplianceViolation, evaluate_compliance
from ._errors import StrataError
from ._lint import LintViolation, evaluate_lint
from ._models import KernelModel
from ._pii import PiiViolation, evaluate_pii
from ._threat import (
    CWE_CATALOG,
    DEFAULT_BENIGN_CAPABILITIES,
    QUALITY_CATALOG,
    QUALITY_OUT_OF_SCOPE,
    QUALITY_VIEWS,
    VIEWS,
    BenignCapability,
    OutOfScopeEntry,
    ThreatViolation,
    WeaknessEntry,
    check_capability_completeness,
    check_catalog_completeness,
    check_discharge_completeness,
)

_log = get_logger(__name__)

#: Default configured views per family -- every view each family's catalog
#: ships, so a default `frob sys audit` run proves exhaustiveness against
#: EVERY baseline the repo's catalogs currently define (docs/strata/
#: threat.md#the-exhaustiveness-proof-the-point: "the exhaustiveness claim
#: is the conjunction"). A caller wanting a narrower audit passes explicit
#: view tuples.
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
DEFAULT_SECURITY_VIEWS: tuple[str, ...] = tuple(VIEWS)
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
DEFAULT_QUALITY_VIEWS: tuple[str, ...] = tuple(QUALITY_VIEWS)
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
DEFAULT_COMPLIANCE_VIEWS: tuple[str, ...] = tuple(REGULATION_VIEWS)


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class FamilyGap(BaseModel):
    """One named exhaustiveness gap: which family/view failed, the
    underlying rule id (THREAT00x / COMPLIANCE00x), and the human detail --
    the machine-usable unit `frob sys audit`'s exit code and CI summary key
    off (docs/strata/threat.md: "every gap named, owned, and expiring")."""

    model_config = ConfigDict(frozen=True)

    family: str  # "security" | "quality" | "compliance"
    view: str
    rule: str
    detail: str


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class AuditReport(BaseModel):
    """The full exhaustiveness conjunction's outcome across every configured
    view: `proved` iff `gaps` is empty. `views_checked` names exactly what
    was evaluated (family-qualified, e.g. `security:owasp-top-10`), so a
    clean report is auditable -- no view silently skipped."""

    model_config = ConfigDict(frozen=True)

    views_checked: tuple[str, ...] = ()
    gaps: tuple[FamilyGap, ...] = ()

    # frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
    @property
    def proved(self) -> bool:
        """True iff every configured view's exhaustiveness conjunction held
        across all families -- zero named gaps anywhere."""
        return not self.gaps


def _threat_gaps(
    family: str, view: str, violations: tuple[ThreatViolation, ...]
) -> tuple[FamilyGap, ...]:
    """Adapt `_threat.py::ThreatViolation`s into `FamilyGap`s for `view`,
    naming whichever id the violation actually carries (CWE, capability
    kind, or node) when `detail` is empty -- never a blank gap."""
    return tuple(
        FamilyGap(
            family=family,
            view=view,
            rule=v.rule,
            detail=v.detail or (v.cwe or v.capability or v.node or "unnamed"),
        )
        for v in violations
    )


def _compliance_gaps(
    view: str, violations: tuple[ComplianceViolation, ...]
) -> tuple[FamilyGap, ...]:
    """Adapt `_compliance.py::ComplianceViolation`s into `FamilyGap`s for `view`."""
    return tuple(
        FamilyGap(
            family="compliance",
            view=view,
            rule=v.rule,
            detail=v.detail or (v.target or v.regulation or "unnamed"),
        )
        for v in violations
    )


def _pii_gaps(violations: tuple[PiiViolation, ...]) -> tuple[FamilyGap, ...]:
    """Adapt `_pii.py::PiiViolation`s into `FamilyGap`s. `_pii.py::
    evaluate_pii` has no baseline-view concept (PII001-004 are all
    structural joins, not a catalog-completeness check like THREAT001), so
    every gap is reported under the fixed `"model"` view (T-0154)."""
    return tuple(
        FamilyGap(
            family="pii",
            view="model",
            rule=v.rule,
            detail=v.detail or (v.target or "unnamed"),
        )
        for v in violations
    )


def _lint_gaps(violations: tuple[LintViolation, ...]) -> tuple[FamilyGap, ...]:
    """Adapt `_lint.py::LintViolation`s into `FamilyGap`s. `_lint.py::
    evaluate_lint` has no baseline-view concept (LINT001-005 are all
    structural joins, not a catalog-completeness check like THREAT001), so
    every gap is reported under the fixed `"model"` view -- the same
    fixed-view shape `_pii_gaps` uses (T-0154 precedent), T-0155."""
    return tuple(
        FamilyGap(
            family="lint",
            view="model",
            rule=v.rule,
            detail=v.detail or (v.target or "unnamed"),
        )
        for v in violations
    )


def _evaluate_family(
    model: KernelModel,
    view: str,
    catalog: tuple[WeaknessEntry, ...],
    out_of_scope: tuple[OutOfScopeEntry, ...],
    benign: tuple[BenignCapability, ...],
    views: dict[str, frozenset[str]],
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT001 + THREAT002 + THREAT003 over `model` against `view`,
    resolved against the FAMILY-SPECIFIC `views` table -- the same three
    calls `_threat.py::evaluate_threats` makes, reparameterized so a
    non-security family (whose views live in a separate table, e.g.
    `QUALITY_VIEWS`) can be evaluated without `evaluate_threats`'s
    hardcoded fallback to the module-global `VIEWS` shadowing it (zero new
    detection -- see module docstring)."""
    catalog_violations = check_catalog_completeness(view, catalog, out_of_scope, views)
    if catalog_violations.is_err:
        return Err(catalog_violations.danger_err)
    capability_violations = check_capability_completeness(model, catalog, benign)
    if capability_violations.is_err:
        return Err(capability_violations.danger_err)
    discharge_violations = check_discharge_completeness(model, catalog)
    if discharge_violations.is_err:
        return Err(discharge_violations.danger_err)
    return Ok(
        (
            *catalog_violations.danger_ok,
            *capability_violations.danger_ok,
            *discharge_violations.danger_ok,
        )
    )


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_clean_proved
# frob:tests tests/unit/strata/test_audit.py::TestVulnLitmus.test_refutes_gap_per_family
# frob:tests tests/unit/strata/test_audit.py::TestHardenedLitmus.test_hardened_clean
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_pii_gap_reported
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_lint_gap_reported
# frob:waive TEST005 reason="Err branches need a deep StrataError; debt T-0160"
def evaluate_exhaustiveness(
    model: KernelModel,
    *,
    security_views: tuple[str, ...] = DEFAULT_SECURITY_VIEWS,
    quality_views: tuple[str, ...] = DEFAULT_QUALITY_VIEWS,
    compliance_views: tuple[str, ...] = DEFAULT_COMPLIANCE_VIEWS,
    benign: tuple[BenignCapability, ...] = DEFAULT_BENIGN_CAPABILITIES,
) -> Result[AuditReport, StrataError]:
    """`frob sys audit`'s model-side entrypoint: the full three-part
    exhaustiveness conjunction (THREAT001-003 for security AND quality,
    COMPLIANCE001-002 for compliance) over `model` against every configured
    view, composed from the ALREADY-SHIPPED per-check functions -- zero new
    detection (module docstring). `benign` defaults to
    `DEFAULT_BENIGN_CAPABILITIES` (T-0150) so tier-2 `may` kinds with no
    CWE-catalog analog do not fail THREAT002 by default; a caller wanting
    the pre-T-0150 strict behavior passes `benign=()`. Fails closed: an
    unknown view name in any family propagates as
    `Err(StrataError.UnknownReference)` rather than being silently
    skipped, matching every other exhaustiveness check in this package."""
    gaps: list[FamilyGap] = []
    checked: list[str] = []

    for view in security_views:
        report = _evaluate_family(model, view, CWE_CATALOG, (), benign, VIEWS)
        if report.is_err:
            return Err(report.danger_err)
        gaps.extend(_threat_gaps("security", view, report.danger_ok))
        checked.append(f"security:{view}")

    for view in quality_views:
        report = _evaluate_family(
            model, view, QUALITY_CATALOG, QUALITY_OUT_OF_SCOPE, benign, QUALITY_VIEWS
        )
        if report.is_err:
            return Err(report.danger_err)
        gaps.extend(_threat_gaps("quality", view, report.danger_ok))
        checked.append(f"quality:{view}")

    for view in compliance_views:
        compliance_report = evaluate_compliance(model, view)
        if compliance_report.is_err:
            return Err(compliance_report.danger_err)
        gaps.extend(_compliance_gaps(view, compliance_report.danger_ok.violations))
        checked.append(f"compliance:{view}")

    pii_report = evaluate_pii(model)
    if pii_report.is_err:
        return Err(pii_report.danger_err)
    gaps.extend(_pii_gaps(pii_report.danger_ok.violations))
    checked.append("pii:model")

    lint_report = evaluate_lint(model)
    if lint_report.is_err:
        return Err(lint_report.danger_err)
    gaps.extend(_lint_gaps(lint_report.danger_ok.violations))
    checked.append("lint:model")

    _log.info(
        "audit: evaluated views=%d -> %d gap(s)",
        len(checked),
        len(gaps),
    )
    return Ok(AuditReport(views_checked=tuple(checked), gaps=tuple(gaps)))


__all__ = [
    "DEFAULT_COMPLIANCE_VIEWS",
    "DEFAULT_QUALITY_VIEWS",
    "DEFAULT_SECURITY_VIEWS",
    "AuditReport",
    "FamilyGap",
    "evaluate_exhaustiveness",
]
