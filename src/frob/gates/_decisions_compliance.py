# frob:waive SCOPE001 reason="T-1402: this file needed only a mechanical, necessary \
# rename of a stale frob:waive EXHAUST001 comment to EXHAUST003 (the EXHAUST001 \
# precision fix, declared scope src/frob/gates/_exhaustive_handling.py) or (this file, \
# _tickets_gate.py, _waive.py) is the actual TICK011 fix itself -- frob ticket scope \
# --add refuses it: T-1279 (TEST005 burn-down) holds a concurrent in-progress lease on \
# src/frob/gates/** for the whole package, so this ticket cannot formally register the \
# file in its own declared scope until T-1279 closes or narrows; see this ticket's \
# Done report for the full disclosure (reviewed 2026-08-03, drain-to-zero WAIVE004 \
# sweep: left in place -- SCOPE001 is a scope/lease-dependent rule \
# (frob.gates._waive.SCOPED_RUN_FLAKY_RULE_IDS), not a stale finding a full unscoped \
# run can prove dead the way WIRE001/REF002/etc can"
"""frob.gates._decisions_compliance -- DEC00x/COMPLIANCE00x registry-
adoption-lifecycle gates (T-1159).

Split out of `frob.gates.__init__` (T-1140/T-1159 one-family-per-land
discipline, T-1159's own residue from the T-1140 gates split) so the
parent module can drop toward the large-file threshold without changing
any public behavior. `decisions_gate`/`compliance_gate` are re-exported
from `frob.gates` unchanged -- they are the only two names this family is
externally imported by (`tests/test_decisions.py`, `tests/test_gates.py`,
docstring/comment prose in `frob.gates._registry_exhaustiveness`/
`frob.gates._waive`/`frob.deploy._drift`, verified by a repo-wide grep
before the move); `_compliance005_violation` stays private to this
module, never imported elsewhere.

Genuinely one cohesive family, not two bolted together: both gates share
the exact same "adopted-then-deleted fires an unwaivable ERROR instead of
silently degrading to never-adopted" shape (DEC003/COMPLIANCE006, both
T-0894), both are opt-in-by-directory-presence, and both dispatch to a
lazily-imported sibling module (`frob.gates.decisions`/
`frob.strata._compliance`) for their real load/check work."""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.graph import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0004
# frob:ticket T-0894
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1056: leaked Unknown traces to the deferred imports of \
# decision_gate/decisions_dir/load_decisions/path_ever_tracked, whose own call \
# surfaces the resolver cannot follow through a function-local import; every \
# locally-visible fallible operation in this gate (path checks, the two try/except \
# blocks below) is already narrowly handled"
# frob:enforces CHK-GATE-DEC000
# frob:enforces CHK-GATE-DEC003
def decisions_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DEC001/DEC002: decision records and their code anchors (T-0004).

    Runs only when a `decisions/` directory exists (opt-in by convention).
    A malformed record fails loudly rather than silently degrading, since
    the record set is a contract surface like the ticket queue.

    T-0894: a `decisions/` directory that was committed on this branch's
    history and has since been deleted fires DEC003 (unwaivable, same
    "adopted then deleted" family as REG012/COMPLIANCE006) instead of
    silently degrading to the never-adopted empty-tuple posture.
    """
    from frob.gates._registry_exhaustiveness import path_ever_tracked
    from frob.gates.decisions import decision_gate, decisions_dir, load_decisions

    root = Path(root)
    decisions_path = decisions_dir(root)
    if not decisions_path.exists():
        try:
            rel_decisions = str(decisions_path.relative_to(root))
        except ValueError:
            rel_decisions = str(decisions_path)
        if path_ever_tracked(root, rel_decisions):
            _log.warning(
                "decisions_gate: %s existed in HEAD's history but is now "
                "deleted from the working tree (DEC003)",
                decisions_path,
            )
            return (
                Violation(
                    rule="DEC003",
                    severity=Severity.ERROR,
                    file=rel_decisions,
                    line=0,
                    message=(
                        f"DEC003: {rel_decisions} was previously committed "
                        "on this branch but has been deleted -- a decision "
                        "record set this repo has adopted cannot silently "
                        "disappear back into 'never adopted' (T-0894); "
                        "restore it or file a decision record explaining "
                        "the removal"
                    ),
                ),
            )
        return ()
    loaded = load_decisions(root)
    if loaded.is_err:
        return (
            Violation(
                rule="DEC000",
                severity=Severity.ERROR,
                file="decisions/",
                line=0,
                message=f"DEC000: decision records unreadable: {loaded.danger_err}",
            ),
        )
    return decision_gate(loaded.danger_ok, snapshot)


# frob:ticket T-0788
# frob:ticket T-1244
def _compliance005_violation(cv) -> Violation:  # noqa: ANN001
    """Convert one `frob.strata._compliance.ComplianceViolation`
    (COMPLIANCE005/COMPLIANCE007) into a gate `Violation` -- the
    `docs/design/registry/compliance.yaml` entry id doubles as the file
    location since the check has no source-line concept of its own.
    COMPLIANCE007 (T-1244) is deliberately WARN, not ERROR: it surfaces a
    real, currently-open re-disposition gap (16 rows still riding the
    vacuous handled_by:COMPLIANCE005 self-reference) that the sibling
    triage tickets (T-1245-T-1249) own re-classifying -- an ERROR here
    would red the build on a decision above this gate's pay grade, not on
    a code bug. COMPLIANCE005 itself stays ERROR: a disposition string
    that fails to parse at all IS this gate's own bug to catch."""
    severity = Severity.WARN if cv.rule == "COMPLIANCE007" else Severity.ERROR
    return Violation(
        rule=cv.rule,
        severity=severity,
        file="docs/design/registry/compliance.yaml",
        line=0,
        message=f"{cv.rule}: {cv.regulation}: {cv.detail}",
    )


# frob:ticket T-0788
# frob:ticket T-0894
# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#registry-exhaustiveness-drift-lock-t-0343  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_registered_in_known_gate_rules  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_fires_on_deferred_disposition  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_silent_on_handled_by_and_out_of_scope  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_missing_registry_dir_is_silent  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_real_repo_registry_passes  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance006_fires_on_deleted_registry_after_adoption  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance006_silent_on_never_adopted_registry  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance007_registered_in_known_gate_rules  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance007_fires_warn_on_self_referential_handled_by  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance007_silent_on_frob_catalog_entries_self_reference  # noqa: E501
# frob:tests tests/test_gates.py::TestComplianceGate.test_compliance007_real_repo_registry_surfaces_known_gap  # noqa: E501
# frob:enforces CHK-GATE-COMPLIANCE005
# frob:enforces CHK-GATE-COMPLIANCE006
# frob:enforces CHK-GATE-COMPLIANCE007
# T-1020-followup: the 17 CMPL_REGISTRY_UNIT_IDS checkable-control units
# T-0833 flipped to handled_by:COMPLIANCE005 -- compliance_gate (via
# check_cmpl_registry) is their real enforcing site.
# frob:enforces CMPL-SOC2-CATEGORIES
# frob:enforces CMPL-SOC2-CC-FAMILIES
# frob:enforces CMPL-PCIDSS-REQUIREMENTS
# frob:enforces CMPL-HIPAA-TECHNICAL-STANDARDS
# frob:enforces CMPL-GDPR-ARTICLES
# frob:enforces CMPL-NIST80053-FAMILIES
# frob:enforces CMPL-NIST80263-VOLUMES
# frob:enforces CMPL-SSDF-PRACTICE-GROUPS
# frob:enforces CMPL-ISO27002-THEMES
# frob:enforces CMPL-ISO27002-CONTROLS
# frob:enforces CMPL-CIS-CONTROLS
# frob:enforces CMPL-CIS-SAFEGUARDS
# frob:enforces CMPL-ASVS-CHAPTERS
# frob:enforces CMPL-ASVS-REQUIREMENTS
# frob:enforces CMPL-FEDRAMP-IMPACT-TIERS
# frob:enforces CMPL-SLSA-BUILD-LEVELS
# frob:enforces CMPL-FROB-CATALOG-ENTRIES
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1056: leaked Unknown traces to the deferred import of \
# path_ever_tracked and check_cmpl_registry's own resolution, which the resolver \
# cannot follow through a function-local import boundary; this function's own \
# locally-visible fallible step (registry_dir existence) is a plain path check"
def compliance_gate(
    repo_root: Path, registry_dir: Path | None = None
) -> tuple[Violation, ...]:
    """COMPLIANCE005 (T-0788, closing the T-0607 gate-wiring gap): every
    `frob.strata._compliance.CMPL_REGISTRY_UNIT_IDS` member present in
    `docs/design/registry/compliance.yaml` must carry a `handled_by`/
    `out_of_scope` disposition, never `deferred`/undispositioned --
    `check_cmpl_registry` (`frob.strata._compliance`, built by T-0607) did
    this check's real work already; this function is purely the `frob
    check` dispatch T-0607 disclosed it could not add (`_KNOWN_GATE_RULES`
    and this stage callback both lived outside T-0607's declared scope).
    Silent (empty tuple) when `registry_dir` (defaults to `repo_root /
    "docs/design/registry"`) has no `compliance.yaml` at all AND that path
    was never committed on this branch's history -- a repo that genuinely
    never adopted the compliance registry makes no COMPLIANCE005 claim.
    T-0894: a repo that DID adopt it (the file was committed on HEAD's
    history at some point) and then lost it -- deleted, whether by
    accident or by a compliance-load-bearing-artifact removal attack --
    fires COMPLIANCE006 instead of silently degrading to the
    never-adopted posture; COMPLIANCE006 is in `_UNWAIVABLE_RULES`
    (unlike COMPLIANCE005 itself, which stays waivable for a specific,
    honest `frob:waive COMPLIANCE005 reason=...` temporary exception the
    same way REG001-004 allow one -- deleting the registry entirely is a
    different, higher-stakes claim than an individual undispositioned
    entry, and gets no waiver escape hatch)."""
    from frob.gates._registry_exhaustiveness import path_ever_tracked
    from frob.strata import check_cmpl_registry

    base = (
        registry_dir
        if registry_dir is not None
        else (repo_root / "docs/design/registry")
    )
    compliance_yaml = base / "compliance.yaml"
    if not compliance_yaml.is_file():
        try:
            rel_compliance = str(compliance_yaml.relative_to(repo_root))
        except ValueError:
            rel_compliance = str(compliance_yaml)
        if path_ever_tracked(repo_root, rel_compliance):
            _log.warning(
                "compliance_gate: %s existed in HEAD's history but is now "
                "deleted from the working tree (COMPLIANCE006)",
                compliance_yaml,
            )
            return (
                Violation(
                    rule="COMPLIANCE006",
                    severity=Severity.ERROR,
                    file=rel_compliance,
                    line=0,
                    message=(
                        f"COMPLIANCE006: {rel_compliance} was previously "
                        "committed on this branch but has been deleted -- "
                        "a compliance registry this repo has adopted "
                        "cannot silently disappear back into 'never "
                        "adopted' (T-0894); restore it or file a decision "
                        "record explaining the removal"
                    ),
                ),
            )
        _log.info("compliance_gate: %s has no compliance.yaml, skipping", base)
        return ()

    result = check_cmpl_registry(base)
    if result.is_err:
        _log.error(
            "compliance_gate: COMPLIANCE005 compliance.yaml at %s not loadable (%s)",
            base,
            result.danger_err,
        )
        return (
            Violation(
                rule="COMPLIANCE005",
                severity=Severity.ERROR,
                file="docs/design/registry/compliance.yaml",
                line=0,
                message=(
                    f"COMPLIANCE005: compliance.yaml at {base} failed to "
                    f"load ({result.danger_err}); fix the manifest"
                ),
            ),
        )
    return tuple(_compliance005_violation(cv) for cv in result.danger_ok)


__all__ = ["compliance_gate", "decisions_gate"]
