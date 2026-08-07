---
id: T-0644
title: 'strata: HEALTH liveness+readiness obligation on every service node'
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
- src/frob/app/sys_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'REL2xx health-obligation CLI wiring: extend the same check_reliability_*
    sys_runner call site T-0640 uses (dispatch mandate: wire the new rule, do not
    ship invoked-by-nothing), mirroring T-0640''s precedent'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/strata/test_reliability.py::TestMissingHealth::test_daemon_without_health_fires
- tests/unit/strata/test_reliability.py::TestMissingHealth::test_discharged_daemon_nodes_clean
- tests/unit/strata/test_reliability.py::TestMissingHealth::test_waiver_on_one_node_keeps_sibling_node_finding
- tests/unit/strata/test_reliability.py::TestUnprovenHealth::test_declared_health_with_no_code_evidence_fires
- tests/unit/strata/test_reliability.py::TestUnprovenHealth::test_declared_health_with_real_code_evidence_discharges
- tests/unit/strata/test_reliability.py::TestUnprovenHealth::test_declared_health_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_reliability.py::TestCrossFamilyWaiverScoping::test_timeout_entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family
designated_repro_test: null
acceptance:
- text: Given a service node with no liveness/readiness declared, when checked, then
    the obligation fires
  evidence:
  - tests/unit/strata/test_reliability.py::TestMissingHealth::test_daemon_without_health_fires
threat: null
component: null
---
Every service node must declare liveness+readiness health checks. Proof-against-code: the declared health endpoint/probe must be found in the bound code (T-0331 PROVABILITY CONSTRAINT).