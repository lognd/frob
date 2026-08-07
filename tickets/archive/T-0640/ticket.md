---
id: T-0640
title: 'strata: TIMEOUT obligation on every remote/cross-boundary flow (REL2xx)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
- design/frob.strata
- src/frob/app/sys_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'Salvage of T-0640 (docs/guides/agent-playbook.md): the REL2xx TIMEOUT

    obligation implementation is already fully landed on main (commits

    cdbd4337, 05264346, b13d2c66, plus T-0644/T-0758 follow-ups) but the

    ticket ledger record itself was never updated past queued/in-progress.

    No new code is being written in this pass, only the ticket record is

    being reconciled against what already exists on disk. The already-landed

    footprint touches design/frob.strata (per-flow attr timeout/local

    disposition + two disclosed REL200 waivers) and src/frob/app/sys_runner.py

    (CLI wiring of check_reliability_timeouts into `frob sys audit`), both

    outside the ticket''s originally declared strata-only scope -- widening

    scope here documents that footprint accurately rather than leaving scope

    narrower than the work it is being credited for.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'Salvage of T-0640 (docs/guides/agent-playbook.md): the REL2xx TIMEOUT

    obligation implementation is already fully landed on main (commits

    cdbd4337, 05264346, b13d2c66, plus T-0644/T-0758 follow-ups) but the

    ticket ledger record itself was never updated past queued/in-progress.

    No new code is being written in this pass, only the ticket record is

    being reconciled against what already exists on disk. The already-landed

    footprint touches design/frob.strata (per-flow attr timeout/local

    disposition + two disclosed REL200 waivers) and src/frob/app/sys_runner.py

    (CLI wiring of check_reliability_timeouts into `frob sys audit`), both

    outside the ticket''s originally declared strata-only scope -- widening

    scope here documents that footprint accurately rather than leaving scope

    narrower than the work it is being credited for.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_flow_without_timeout_fires
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_discharged_and_exempt_flows_clean
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_waiver_on_one_flow_keeps_sibling_flow_finding
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_code_evidence_fires
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_real_code_evidence_discharges
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_proves_against_dst
- tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_lacking_evidence_fires_against_dst
- tests/unit/strata/test_reliability.py::TestCrossFamilyWaiverScoping::test_timeout_entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
designated_repro_test: null
acceptance:
- text: Given a .strata flow crossing a service/process boundary with no timeout attr,
    when frob check runs, then REL2xx fires unless waived with a reason
  evidence:
  - tests/unit/strata/test_reliability.py::TestMissingTimeout::test_flow_without_timeout_fires
  - tests/unit/strata/test_reliability.py::TestMissingTimeout::test_waiver_on_one_flow_keeps_sibling_flow_finding
- text: Given a declared timeout, when the bound code path lacks a matching real timeout
    arg, then the check fails (proof-against-code), not merely passes on declaration
  evidence:
  - tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_code_evidence_fires
  - tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_real_code_evidence_discharges
threat: null
component: null
---
Add a flow-level TIMEOUT attribute + REL2xx checker + litmus + docs: every remote/cross-boundary flow must declare a bounded timeout (unbounded hang otherwise). Deny-by-default with reasoned-waive channel (T-0174). Discharge must be proof-against-code (real timeout arg at the call site) per T-0331's PROVABILITY CONSTRAINT, not bare declaration.