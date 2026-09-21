"""SYS/SELFAUDIT rule liveness sweep (T-4993, T-4804/SF-01).

SF-01 measured `.frob/telemetry.jsonl` (31,459 rows, 614,294 rule fires
across 82 distinct rule ids) and found NOT ONE fire starting with `SYS`,
with `SELFAUDIT001` appearing exactly once, even though 79+ SYS/SELFAUDIT/
REL/PII/THREAT/VMOD/CLAIM rule ids are registered
(`frob.gates.known_gate_rule_ids`). Per memory/silent-zero-is-the-
dominant-bug-class.md and memory/catalogued-is-not-enforced.md, a
registered-and-documented rule is not the same claim as a rule that can be
shown firing -- only a planted violation the rule must report proves the
matcher actually works (memory/positive-control-or-it-proves-nothing.md).

THIS MODULE is the meta-test T-4804's decision requires: it enumerates
every currently-registered rule id in the SYS/SELFAUDIT/REL/PII/THREAT/
VMOD/CLAIM families straight from the real registration surface
(`frob.gates.known_gate_rule_ids`, never a grep -- a grep-derived list
would silently miss a dynamically-registered rule and duplicates the
enumerator T-4993's sibling gate-kernel ticket already owns), and fails
for any one of them with no liveness fixture on record.

DESIGN CHOICE: rather than re-authoring 91 new planted-violation fixtures
duplicating logic this repo already has (NO DUPLICATION -- house rule),
`_LIVENESS_FIXTURES` below maps each registered rule id to the pytest
node id of an EXISTING, already-passing unit test elsewhere in this repo
that plants that exact violation and asserts the rule reports it (e.g.
`REL_MISSING_CIRCUIT_BREAKER`/"REL230" in
`tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::
test_external_node_without_circuit_breaker_fires`). This suite's own,
durable value is the mapping's COMPLETENESS, not the plant logic itself:
`test_every_registered_rule_has_a_liveness_fixture` (the meta-test) fails
loudly the moment a new rule is registered with no entry here, and
`test_liveness_mapping_has_no_stale_entries`/
`test_every_mapped_fixture_node_id_actually_exists_and_passes` guard the
mapping itself against rotting (a renamed/deleted test silently orphaning
its rule's "proof").

`design/litmus/sys_liveness.strata` is this suite's one design-level
(not KernelModel-level) positive control:
`test_sys_liveness_litmus_design_proves_sys204_end_to_end` parses and
elaborates it through the REAL surface grammar and asserts SYS204 fires,
proving the family survives real surface syntax, not only a hand-built
`KernelModel`.

POSITIVE CONTROL FOR THIS FILE ITSELF: with `_LIVENESS_FIXTURES` emptied
(or any registered rule id removed from it), `test_every_registered_rule_
has_a_liveness_fixture` fails, naming the missing rule id(s) -- verified
manually against HEAD c8f56ef10 (79 registered rule ids, this file did
not exist, so the meta-test's assertion had nothing to pass against at
all -- import-time `ModuleNotFoundError`, the same failing state an empty
mapping now produces on purpose).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from frob.gates import known_gate_rule_ids
from frob.strata import elaborate, parse_module
from frob.strata._access import (
    SYS_UNARBITRATED_MODE_CONFLICT,
    resource_contention_violations,
)
from frob.strata._ast import Module

#: The rule-id families this ticket's decision (T-4804/SF-01) covers.
#: Matches the prefix set the mission briefing enumerates verbatim.
_LIVENESS_FAMILIES: tuple[str, ...] = (
    "SYS",
    "SELFAUDIT",
    "REL",
    "PII",
    "THREAT",
    "VMOD",
    "CLAIM",
)


def _repo_root() -> Path:
    """Walk up from this file until the directory carrying `frob.toml` --
    the same convention every other litmus-golden test in this repo uses
    (e.g. `tests/unit/strata/test_litmus_surface.py::_repo_root`) so this
    suite resolves fixture node ids and the litmus design against the
    real checkout regardless of pytest's invocation cwd."""
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "frob.toml").is_file():
            return candidate
    raise RuntimeError("could not locate repo root (no frob.toml above this file)")


#: rule id -> pytest node id (relative to the repo root) of an EXISTING
#: test elsewhere in this repo that plants that rule's violation and
#: asserts the rule reports it. Built once by walking every currently
#: registered SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM rule id and finding
#: its existing planted-violation proof (module docstring: no
#: duplication of that plant logic here). Every value below was verified
#: passing at authorship time
#: (`pytest <these node ids> -q` -> `91 passed`).
_LIVENESS_FIXTURES: dict[str, str] = {
    "PII001": "tests/unit/strata/test_pii.py::TestPiiCatalog::test_unknown_category_is_pii001",  # noqa: E501
    "PII002": "tests/unit/strata/test_litmus_pii.py::TestPiiVulnLitmus::test_vuln_pii002_names_the_crossing_flow",  # noqa: E501
    "PII003": "tests/unit/strata/test_litmus_pii.py::TestPiiVulnLitmus::test_vuln_pii003_names_the_store",  # noqa: E501
    "PII004": "tests/unit/strata/test_litmus_pii.py::TestPiiVulnLitmus::test_vuln_pii004_names_the_underlabeled_flow",  # noqa: E501
    "PII010": "tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires",  # noqa: E501
    "PII011": "tests/test_pii_structural_gate.py::TestEmailShapeValues::test_email_literal_fires",  # noqa: E501
    "PII012": "tests/test_pii_structural_gate.py::TestKeywordSweep::test_identifier_keyword_fires_at_suggestion_severity",  # noqa: E501
    "REL001": "tests/test_release.py::test_release_gate_flags_missing_bump",
    "REL002": "tests/test_release.py::TestReleaseGateCoherence::test_clean_repo_has_no_rel002",  # noqa: E501
    "REL200": "tests/unit/strata/test_reliability.py::TestMissingTimeout::test_flow_without_timeout_fires",  # noqa: E501
    "REL201": "tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_code_evidence_fires",  # noqa: E501
    "REL210": "tests/unit/strata/test_reliability.py::TestMissingHealth::test_daemon_without_health_fires",  # noqa: E501
    "REL211": "tests/unit/strata/test_reliability.py::TestUnprovenHealth::test_declared_health_with_no_code_evidence_fires",  # noqa: E501
    "REL220": "tests/unit/strata/test_retry.py::TestMissingBackoff::test_retry_flow_without_backoff_fires",  # noqa: E501
    "REL221": "tests/unit/strata/test_retry.py::TestNonIdempotentRetry::test_retry_into_unguarded_dst_fires",  # noqa: E501
    "REL222": "tests/unit/strata/test_retry.py::TestUnprovenBackoff::test_declared_backoff_with_no_code_evidence_fires",  # noqa: E501
    "REL230": "tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_external_node_without_circuit_breaker_fires",  # noqa: E501
    "REL231": "tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL240": "tests/unit/strata/test_fallback.py::TestMissingFallback::test_critical_node_without_fallback_fires",  # noqa: E501
    "REL241": "tests/unit/strata/test_fallback.py::TestUnprovenFallback::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL250": "tests/unit/strata/test_spof.py::TestSpof::test_singleton_node_with_critical_inbound_fires",  # noqa: E501
    "REL260": "tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_queue_node_without_bounded_intake_fires",  # noqa: E501
    "REL261": "tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL270": "tests/unit/strata/test_observability.py::TestMissingObservability::test_boundary_flow_without_observability_fires",  # noqa: E501
    "REL271": "tests/unit/strata/test_observability.py::TestUnprovenObservability::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL272": "tests/unit/strata/test_observability.py::TestMissingCorrelation::test_second_hop_without_correlation_fires",  # noqa: E501
    "REL280": "tests/unit/strata/test_slo.py::TestMissingSlo::test_service_node_without_slo_fires",  # noqa: E501
    "REL281": "tests/unit/strata/test_slo.py::TestUnprovenSlo::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL290": "tests/unit/strata/test_ssot.py::TestMissingOwner::test_multi_writer_store_without_owner_fires",  # noqa: E501
    "REL291": "tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL300": "tests/unit/strata/test_txn.py::TestMissingTxnBoundary::test_multi_store_write_op_without_boundary_fires",  # noqa: E501
    "REL301": "tests/unit/strata/test_txn.py::TestUnprovenTxnBoundary::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL310": "tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost::test_interactive_node_without_bounded_cost_fires",  # noqa: E501
    "REL311": "tests/unit/strata/test_interactive_cost.py::TestUnprovenBoundedCost::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL320": "tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion::test_event_node_without_schema_version_fires",  # noqa: E501
    "REL321": "tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL330": "tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_queue_node_without_delivery_semantics_fires",  # noqa: E501
    "REL331": "tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL340": "tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_chain_below_bound_clean",  # noqa: E501
    "REL350": "tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_multi_service_write_op_without_saga_fires",  # noqa: E501
    "REL351": "tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL360": "tests/unit/strata/test_shared_state.py::TestSharedState::test_mutable_node_shared_by_two_services_fires",  # noqa: E501
    "REL370": "tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_clock_dependent_flow_without_ordering_strategy_fires",  # noqa: E501
    "REL371": "tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL372": "tests/unit/strata/test_clock_ordering.py::TestWallClockOnly::test_bare_wall_clock_read_fires_rel372",  # noqa: E501
    "REL380": "tests/unit/strata/test_starvation.py::TestUtilization::test_arbitrated_by_node_is_the_serialization_point",  # noqa: E501
    "REL381": "tests/unit/strata/test_starvation.py::TestUtilization::test_undeclared_demand_fails_closed",  # noqa: E501
    "REL382": "tests/unit/strata/test_starvation.py::TestWriterStarvation::test_read_heavy_writer_with_no_alpha_fires_advisory",  # noqa: E501
    "REL383": "tests/unit/strata/test_starvation.py::TestUnboundedWait::test_contended_write_access_with_no_timeout_fires",  # noqa: E501
    "REL390": "tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_kernel_interface_node_without_classification_fires",  # noqa: E501
    "REL391": "tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL392": "tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_deployed_process_node_without_bounds_fires",  # noqa: E501
    "REL393": "tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL394": "tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_compiled_artifact_node_without_compat_window_fires",  # noqa: E501
    "REL395": "tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "REL396": "tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_boot_chain_stage_node_without_attestation_fires",  # noqa: E501
    "REL397": "tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_no_code_evidence_fires",  # noqa: E501
    "RELWAIVE002": "tests/unit/strata/test_reliability.py::TestCrossFamilyWaiverScoping::test_timeout_entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family",  # noqa: E501
    "SELFAUDIT001": "tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_findings_in_touched_files_refuses_and_unwinds",  # noqa: E501
    "SYS001": "tests/gates_suite/test_sys.py::TestSysGate::test_sys001_dangling",
    "SYS002": "tests/gates_suite/test_test_gate.py::TestTestGate::test_match_waiver_prefix_reach_gated_to_package_scoped_rules",  # noqa: E501
    "SYS003": "tests/unit/test_conftest_self_scan_fixture.py::TestFrobSelfScanArtifactsSharing::test_sys003_filter_ignores_other_rules",  # noqa: E501
    "SYS004": "tests/gates_suite/test_sys.py::TestSysGate::test_sys004_load_failure",
    "SYS100": "tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys100_core_violation_still_fires_and_is_not_auto_resolved",  # noqa: E501
    "SYS101": "tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_fires",  # noqa: E501
    "SYS102": "tests/unit/strata/test_selfconform.py::TestUnmodeledCode::test_unmodeled_code_fires",  # noqa: E501
    "SYS103": "tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103",  # noqa: E501
    "SYS105": "tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_outside_profile_fires",  # noqa: E501
    "SYS106": "tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires",  # noqa: E501
    "SYS107": "tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory::test_via_less_grant_on_large_node_fires",  # noqa: E501
    "SYS108": "tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires",  # noqa: E501
    "SYS109": "tests/gates_suite/test_sys.py::TestSelfAuditGate::test_selfaudit001_folds_stale_via_symbol_violation",  # noqa: E501
    "SYS110": "tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_real_symbol_outside_declared_set_fires",  # noqa: E501
    "SYS111": "tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused",  # noqa: E501
    "SYS112": "tests/gates_suite/test_sys.py::TestSelfAuditGate::test_selfaudit001_folds_sys112_ambient_reason_violation",  # noqa: E501
    "SYS113": "tests/unit/strata/test_selfconform_core_rules.py::TestZeroMatchCodeGlob::test_must_fire_when_code_glob_matches_nothing",  # noqa: E501
    "SYS200": "tests/unit/strata/test_contention.py::TestDuplicatePort::test_two_nodes_same_port_fires",  # noqa: E501
    "SYS201": "tests/unit/strata/test_contention.py::TestOverlappingPath::test_owns_subtree_overlap_fires_write_capable",  # noqa: E501
    "SYS202": "tests/unit/strata/test_contention.py::TestSharedPipe::test_same_pipe_name_fires",  # noqa: E501
    "SYS203": "tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_two_writers_fires_mode_blind",  # noqa: E501
    "SYS204": "tests/unit/strata/test_access.py::TestResourceContentionViolations::test_two_writers_no_arbiter_fires",  # noqa: E501
    "SYS205": "tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_read_mode_fails_on_a_write_open",  # noqa: E501
    "SYSWAIVE002": "tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus::test_stale_waiver_reported_as_syswaive002_gap",  # noqa: E501
    "SYSWAIVE003": "tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged",  # noqa: E501
    "THREAT001": "tests/unit/strata/test_threat.py::TestCatalogCompleteness::test_missing_entry_is_a_violation",  # noqa: E501
    "THREAT002": "tests/unit/strata/test_threat.py::TestCapabilityCompleteness::test_unknown_capability_kind_is_a_violation",  # noqa: E501
    "THREAT003": "tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus::test_sub_target_waiver_does_not_suppress_a_different_sub_target",  # noqa: E501
    "THREAT004": "tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_undeclared_sink_is_threat004",  # noqa: E501
    "THREAT005": "tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_unclassified_sink_kind_is_threat005",  # noqa: E501
    "THREAT006": "tests/unit/strata/test_threat.py::TestCaughtByIntegrity::test_fabricated_cwe_reference_fails_closed",  # noqa: E501
    "VMOD001": "tests/test_gates_vmodel.py::TestVmodelGate::test_fires_vmod001_on_construction_error",  # noqa: E501
    # SYS900 (T-4993 follow-on): the branch-scoped SYS audit's UNRESOLVED
    # "unmeasured" verdict, planted by pointing it at a worktree that does
    # not exist.
    "SYS900": "tests/gates_suite/test_sys.py::TestSysGateForBranch::test_missing_worktree_reports_unmeasured",  # noqa: E501
}


def _registered_rule_ids_in_scope() -> frozenset[str]:
    """Every rule id `frob.gates.known_gate_rule_ids` (the real
    registration surface -- never a grep, per this ticket's sequencing
    note) currently reports in the SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM
    families this leaf's decision (T-4804) covers."""
    return frozenset(
        rid for rid in known_gate_rule_ids() if rid.startswith(_LIVENESS_FAMILIES)
    )


def test_every_registered_rule_has_a_liveness_fixture() -> None:
    """THE META-TEST (T-4993's positive control): every rule id the real
    registration surface reports in scope must have a liveness fixture
    on record in `_LIVENESS_FIXTURES` -- fails loudly, naming the exact
    missing ids, for any registered rule this suite has not proven can
    fire. At HEAD c8f56ef10 (before this file existed) this assertion
    had nothing to run at all; with `_LIVENESS_FIXTURES` populated below
    it must pass, and stays a live tripwire for every future rule."""
    registered = _registered_rule_ids_in_scope()
    mapped = frozenset(_LIVENESS_FIXTURES)
    missing = sorted(registered - mapped)
    assert not missing, (
        f"{len(missing)} registered SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM "
        f"rule id(s) have no liveness fixture recorded in "
        f"_LIVENESS_FIXTURES: {missing}. Per T-4804's decision, add a "
        "fixture that plants the violation and proves the rule reports "
        "it -- or, if the rule genuinely cannot be made to fire, record "
        "that as a finding on T-4804 (never delete the rule, never skip "
        "silently)."
    )


def test_liveness_mapping_has_no_stale_entries() -> None:
    """The inverse of the meta-test: `_LIVENESS_FIXTURES` names no rule id
    that is no longer registered -- a rule id retired from the registry
    should have its mapping entry removed in the same change, not left
    to rot and silently overstate coverage."""
    registered = _registered_rule_ids_in_scope()
    stale = sorted(frozenset(_LIVENESS_FIXTURES) - registered)
    assert not stale, (
        f"_LIVENESS_FIXTURES names rule id(s) no longer reported by "
        f"frob.gates.known_gate_rule_ids(): {stale} -- remove the stale "
        "entry/entries (or the rule id was renamed; update the mapping)."
    )


def test_every_mapped_fixture_node_id_actually_exists_and_passes() -> None:
    """Runs every mapped fixture test IN ONE real, non-parallel pytest
    subprocess and asserts the whole batch passes -- the mapping is only
    as trustworthy as the tests it points at, so this guards against a
    renamed/deleted/broken fixture silently orphaning its rule's liveness
    proof (the exact "catalogued is not enforced" gap this whole ticket
    exists to close, applied recursively to this suite's own mapping).
    Deliberately ONE subprocess for all 91 node ids (not one per rule):
    this repo's own xdist-parallel runner spawns workers per test, and a
    worker that itself forks 91 nested pytest subprocesses starves the
    shared box under fleet load (measured: a worker crash, "suspect OOM
    or a hard crash", the first time this ran with one subprocess per
    rule) -- `-p no:xdist` on the inner call keeps it single-process, and
    batching the node ids into one inner pytest invocation keeps this
    suite's own footprint to one extra interpreter start, not 91."""
    root = _repo_root()
    node_ids = sorted(set(_LIVENESS_FIXTURES.values()))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *node_ids,
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:xdist",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        "one or more liveness fixture(s) did not pass:\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )


def test_sys_liveness_litmus_design_proves_sys204_end_to_end() -> None:
    """`design/litmus/sys_liveness.strata`'s one design-level (not
    hand-built `KernelModel`) positive control: two nodes access the same
    named resource in conflicting (`write`/`write`) modes with no
    arbiter/lock declared anywhere in the module, so SYS204 must fire
    once parsed and elaborated through the REAL surface grammar --
    proving the T-0700 obligation survives real surface syntax, the same
    parse -> elaborate -> check pipeline `frob check` itself uses, not
    only a hand-built `KernelModel` the way
    `tests/unit/strata/test_access.py::TestResourceContentionViolations::
    test_two_writers_no_arbiter_fires` already does at the model level."""
    root = _repo_root()
    source = (root / "design" / "litmus" / "sys_liveness.strata").read_text(
        encoding="utf-8"
    )
    parsed = parse_module(source)
    assert parsed.is_ok, f"sys_liveness.strata failed to parse: {parsed.danger_err}"
    module: Module = parsed.danger_ok
    elaborated = elaborate(module)
    assert elaborated.is_ok, (
        f"sys_liveness.strata failed to elaborate: {elaborated.danger_err}"
    )
    model = elaborated.danger_ok
    report = resource_contention_violations(model, module)
    fired = {v.rule for v in report.violations}
    assert SYS_UNARBITRATED_MODE_CONFLICT in fired, (
        "design/litmus/sys_liveness.strata's two conflicting-write "
        f"accessors did not fire {SYS_UNARBITRATED_MODE_CONFLICT}; got "
        f"{fired!r}"
    )
    conflicting_nodes = {v.node for v in report.violations} | {
        v.peer for v in report.violations
    }
    assert conflicting_nodes == {"ledger_writer_a", "ledger_writer_b"}
