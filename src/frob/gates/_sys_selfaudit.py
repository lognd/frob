# frob:waive INV006 preset="split-carried-prose"
"""frob.gates._sys_selfaudit -- SELFAUDIT001 self-audit-at-land family (T-1420).

Split out of `frob.gates._sys` (T-1420's LARGE001 residue-burndown, same
one-family-per-land discipline `_sys.py`'s own T-1187 split docstring
names) so the parent module keeps dropping toward the large-file
threshold without changing any public behavior. Nothing here is
re-exported from `frob.gates` -- `_sys.sys_gate` is this family's only
caller, imported back into `_sys.py` at call time.

One cohesive family: `_selfaudit_violations` folds frob's own self-
conformance/resource-contention/mode-conformance/reliability audit
surface (T-0756) and `_compliance_selfaudit_violations` folds the
`evaluate_compliance` model-evaluation layer (T-1314) into `frob check`'s
ordinary `Violation` pipeline -- both were previously reachable only via
the separate `frob sys audit` CLI verb, the exact "catalogued but check-
invisible" gap this family exists to close (see each function's own
docstring for the full incident/root-cause history carried verbatim from
`_sys.py`).
"""
# frob:ticket T-1420

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-0756
# frob:enforces CHK-GATE-SELFAUDIT001
def _selfaudit_violation(
    sub_rule: str, node: str, detail: str, design_dir: str
) -> Violation:
    """Build one SELFAUDIT001 finding wrapping a single SYS100-102/SYS2xx/
    REL2xx underlying finding -- split out of `_selfaudit_violations`
    purely to keep its loop bodies short."""
    return Violation(
        rule="SELFAUDIT001",
        severity=Severity.ERROR,
        file=design_dir,
        line=1,
        message=(f"SELFAUDIT001: self-audit family {sub_rule} node={node}: {detail}"),
        symref=node,
    )


# frob:doc docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756
# frob:waive AFFECT001 reason="T-1146 threads the SAME resource_module this function \
# already built for check_mode_conformance into check_resource_contention's module= \
# too (moved a few lines earlier, no new fact for \
# docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756 to describe -- \
# SELFAUDIT001's own shape/behavior is unchanged, only which findings it now correctly \
# skips); docs/modules/gates.md is not in T-1146's declared scope"
# frob:invariant INV-041
# frob:tests tests/test_gates.py::TestSelfAuditGate.test_selfaudit001_folds_selfconform_violation  # noqa: E501
# frob:tests tests/test_gates.py::TestSelfAuditGate.test_selfaudit001_clean_model_no_violations  # noqa: E501
# frob:tests tests/test_gates.py::TestSelfAuditGate.test_selfaudit001_suppressed_on_design_load_error  # noqa: E501
def _selfaudit_violations(
    root: Path,
    design_ids,
    design_dir: str,  # noqa: ANN001
) -> list[Violation]:
    """SELFAUDIT001 (T-0756 SELF-AUDIT AT LAND): fold frob's OWN self-
    conformance (SYS100 undeclared interface / SYS101 stale design / SYS102
    unmodeled code, `frob.strata.check_self_conformance`) plus the SYS2xx
    resource-contention (`check_resource_contention`), SYS205 mode-
    conformance (`check_mode_conformance`, T-1061 wiring the T-0701/T-1060
    check into this gate), and REL2xx reliability
    (`check_reliability_timeouts`/`check_reliability_health`) audit
    families -- until this ticket only reachable via the separate
    `frob sys audit` CLI verb (`frob.app.sys_runner._run_audit`) -- into
    `frob check`'s own gate pipeline (this function's caller, `sys_gate`).

    Root cause this closes (docs/modules/gates.md
    #self-audit-at-land-selfaudit001-t-0756):
    T-0724 enabled a check whose own landing reddened frob's OWN self-audit
    undisclosed -- nothing blocked that land, because `frob sys audit` was
    never itself a gate `frob check`/`frob ticket land` consulted, only a
    separately-run command a reviewer had to remember to invoke by hand.
    Folding these families into `frob check`'s ordinary Violation pipeline
    means `frob ticket land`'s EXISTING post-merge `check_gates`/`check_
    gate_findings` re-verification (`frob.tickets._land.land`, T-0754/
    T-0846) already refuses a landing that reddens this surface, with zero
    new land-time wiring needed -- the fix is making this surface a gate at
    all, not adding a second preflight call site.

    One SELFAUDIT001 `Violation` per underlying finding (never coalesced),
    each carrying the ORIGINAL rule id (SYS100/SYS101/SYS102/SYS2xx/SYS205/
    REL2xx) and node in its message/symref, so a reader can tell exactly
    which family fired without re-running `frob sys audit` separately.
    SYS205's own evaluation failure (`bind_code`'s `Err`) is skipped the
    SAME way `check_self_conformance`'s is above -- one sub-family's
    binding failure must not silently blank the whole gate. Suppressed
    (matching DOC003/SYS001-004's posture) whenever any design file failed
    to load -- self-audit cannot be honestly evaluated against a partial
    model."""
    if design_ids.errors:
        _log.debug(
            "SELFAUDIT001: suppressed, %d design file(s) failed to load",
            len(design_ids.errors),
        )
        return []

    from frob.strata import (
        Module,
        bind_code,
        check_mode_conformance,
        check_reliability_health,
        check_reliability_timeouts,
        check_resource_contention,
        check_self_conformance,
        merge_models,
    )

    model = merge_models(design_ids.models)
    violations: list[Violation] = []

    selfconform = check_self_conformance(model, root)
    if selfconform.is_err:
        _log.warning(
            "SELFAUDIT001: self-conformance evaluation failed (%s), skipping "
            "that sub-family",
            selfconform.danger_err,
        )
    else:
        violations.extend(
            _selfaudit_violation(v.rule, v.node, v.detail, design_dir)
            for v in selfconform.danger_ok.violations
        )

    # T-1061: `resource_module` is a throwaway `Module` carrying only
    # `design_ids.resources` (T-1061's own `DesignIds` field), since
    # `check_mode_conformance`'s only use for a `Module` argument is
    # `.resources` (the `lock`/`arbitrated_by` arbiter lookup,
    # `_mode_conformance.py` module docstring). T-1146: built BEFORE the
    # `check_resource_contention` call below (moved up from its original
    # position just above `check_mode_conformance`) so the SAME `Module`
    # can also be passed as `check_resource_contention`'s `module=` --
    # SYS203/SYS201's arbiter-awareness (T-1025/T-1149) was fully built
    # and tested but never wired into this LIVE gate until now (this
    # ticket's own disclosed-gap closure).
    resource_module = Module(name="selfaudit-resources", resources=design_ids.resources)

    contention = check_resource_contention(
        model, store_ids=design_ids.store_ids, module=resource_module
    )
    violations.extend(
        _selfaudit_violation(v.rule, v.node, v.detail, design_dir)
        for v in contention.violations
    )

    binding = bind_code(model, root)
    if binding.is_err:
        _log.warning(
            "SELFAUDIT001: mode-conformance evaluation failed (%s), skipping "
            "that sub-family",
            binding.danger_err,
        )
    else:
        mode_conformance = check_mode_conformance(
            model, resource_module, binding.danger_ok, root
        )
        violations.extend(
            _selfaudit_violation(v.rule, v.node, v.detail, design_dir)
            for v in mode_conformance.violations
        )

    timeouts = check_reliability_timeouts(model, root)
    if timeouts.is_err:
        _log.warning(
            "SELFAUDIT001: reliability-timeouts evaluation failed (%s), "
            "skipping that sub-family",
            timeouts.danger_err,
        )
    else:
        violations.extend(
            _selfaudit_violation(v.rule, v.node, v.detail, design_dir)
            for v in timeouts.danger_ok.violations
        )

    health = check_reliability_health(model, root)
    if health.is_err:
        _log.warning(
            "SELFAUDIT001: reliability-health evaluation failed (%s), "
            "skipping that sub-family",
            health.danger_err,
        )
    else:
        violations.extend(
            _selfaudit_violation(v.rule, v.node, v.detail, design_dir)
            for v in health.danger_ok.violations
        )

    return violations


# frob:ticket T-1314
# frob:enforces CHK-GATE-SELFAUDIT001
def _compliance_selfaudit_violation(view: str, cv, design_dir: str) -> Violation:  # noqa: ANN001
    """Build one SELFAUDIT001 finding wrapping a single `evaluate_compliance`
    `ComplianceViolation` (`rule`/`regulation`/`target`/`detail`, NOT a
    `node` field -- `target` is `ComplianceViolation`'s firing flow/node
    id) -- split out purely to keep `_compliance_selfaudit_violations`'s
    loop body short, mirroring `_selfaudit_violation` above. Deliberately
    `Severity.WARN` (see `_compliance_selfaudit_violations`'s docstring
    for the tier decision and its rationale)."""
    return Violation(
        rule="SELFAUDIT001",
        severity=Severity.WARN,
        file=design_dir,
        line=1,
        message=(
            f"SELFAUDIT001: compliance evaluation view={view!r} "
            f"sub_rule={cv.rule} regulation={cv.regulation} "
            f"target={cv.target}: {cv.detail}"
        ),
        symref=cv.target or "",
    )


# frob:doc docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756
# frob:ticket T-1314
# frob:invariant INV-041
# frob:tests tests/test_gates.py::TestSelfAuditGate.test_selfaudit001_folds_compliance_violation  # noqa: E501
# frob:tests tests/test_gates.py::TestSelfAuditGate.test_selfaudit001_compliance_clean_model_no_violations  # noqa: E501
# frob:tests tests/test_gates.py::TestSelfAuditGate.test_selfaudit001_compliance_suppressed_on_design_load_error  # noqa: E501
def _compliance_selfaudit_violations(
    root: Path,
    design_ids,  # noqa: ANN001
    design_dir: str,
) -> list[Violation]:
    """SELFAUDIT001 (T-1314, extending the T-0756 precedent): fold
    `frob.strata.evaluate_compliance` -- until this ticket reachable only
    via the separate `frob sys audit` CLI verb, exactly the "catalogued
    but check-invisible" gap `_selfaudit_violations` closed for self-
    conformance/contention/mode/reliability -- into `frob check`'s own
    gate pipeline (this function's caller, `sys_gate`).

    Root cause this closes (reviewer-confirmed gap from the T-1242/T-1244
    close, this ticket's own body): `evaluate_compliance` had ZERO call
    sites under `src/frob/gates/` -- only the registry-string
    COMPLIANCE005/006/007 checks (`frob.gates._decisions_compliance`) were
    wired into `frob check`; the actual model-evaluation layer (a model
    with an `exposure:public-web` node and no privacy-policy mitigation,
    for example) ran only under manual `frob sys audit`. A green `frob
    check` could sit beside a red `frob sys audit` with nothing tying the
    two together -- exactly the divergence class this folding regression-
    tests against (`TestSelfAuditGate.test_selfaudit001_folds_compliance_
    violation`).

    Runs `evaluate_compliance` once per `DEFAULT_COMPLIANCE_VIEWS` entry
    against the SAME merged model `_selfaudit_violations` builds, with
    `COMPLIANCE_OUT_OF_SCOPE` as `out_of_scope` and the live
    `_KNOWN_GATE_RULES` as `known_rule_ids` -- mirroring
    `frob.strata._audit._compliance_pii_lint_fingerprint_gaps`'s own
    argument shape (the one place this call was already made, just never
    from a gate). `policy` (COMPLIANCE003) is left unset: no gate-visible
    input feeds a `PrivacyPolicy` yet, so that sub-check stays silent
    here exactly as it already is for a caller that omits `policy`
    (`evaluate_compliance`'s own documented behavior) -- not a
    regression, a narrower first cut than `frob sys audit` can offer once
    a repo wires a real policy in.

    Tier decision (WARN, not ERROR): unlike `_selfaudit_violations`'s
    other sub-families (all ERROR), a compliance-catalog finding folded
    in here is a NEW, previously-invisible-to-`frob check` surface for
    every repo that already has a `design/` directory today, with no
    grace period -- flipping straight to ERROR would turn latent
    (previously advisory-only) compliance gaps into a hard `frob check`
    failure the moment this ticket lands, for repos that never opted
    into strict compliance enforcement. WARN gets the finding into every
    `frob check` run (closing the green-check-red-audit divergence
    without a separate command) while leaving it non-blocking until a
    repo's own compliance posture is deliberately promoted, matching
    COMPLIANCE007's own WARN precedent
    (`frob.gates._decisions_compliance._compliance005_violation`'s
    docstring) for the same "surfaces a real gap, not yet a proven code
    bug for every model" reasoning. Suppressed (matching every other
    sub-family here) whenever any design file failed to load."""
    if design_ids.errors:
        _log.debug(
            "SELFAUDIT001: suppressed (compliance), %d design file(s) failed to load",
            len(design_ids.errors),
        )
        return []

    from frob.gates._waive import _KNOWN_GATE_RULES
    from frob.strata import DEFAULT_COMPLIANCE_VIEWS, evaluate_compliance, merge_models
    from frob.strata._compliance import COMPLIANCE_OUT_OF_SCOPE

    model = merge_models(design_ids.models)
    violations: list[Violation] = []
    for view in DEFAULT_COMPLIANCE_VIEWS:
        report = evaluate_compliance(
            model,
            view,
            out_of_scope=COMPLIANCE_OUT_OF_SCOPE,
            known_rule_ids=_KNOWN_GATE_RULES,
        )
        if report.is_err:
            _log.warning(
                "SELFAUDIT001: compliance evaluation failed for view=%r (%s), "
                "skipping that view",
                view,
                report.danger_err,
            )
            continue
        violations.extend(
            _compliance_selfaudit_violation(view, cv, design_dir)
            for cv in report.danger_ok.violations
        )
    return violations
