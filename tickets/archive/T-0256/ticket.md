---
id: T-0256
title: 'movement-impossibility proofs: lateral/vertical isolation claims + red-team
  threat entries'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0255
parent: T-0254
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/strata/**
- design/**
- tests/**
- tickets.md
- CHANGELOG.md
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_host_isolation.py::TestLateralIsolation::test_skips_below_two_users
- tests/unit/strata/test_host_isolation.py::TestLateralIsolation::test_shared_writable_path_and_socket_fire
- tests/unit/strata/test_host_isolation.py::TestLateralIsolation::test_declared_flow_discharges_cross_user_socket
- tests/unit/strata/test_host_isolation.py::TestLateralIsolation::test_isolated_paths_do_not_fire_shared_writable_path
- tests/unit/strata/test_host_isolation.py::TestVerticalIsolation::test_skips_with_no_users
- tests/unit/strata/test_host_isolation.py::TestVerticalIsolation::test_setuid_owned_path_fires
- tests/unit/strata/test_host_isolation.py::TestVerticalIsolation::test_sudoers_always_fires_as_honest_gap
- tests/unit/strata/test_host_isolation.py::TestVerticalIsolation::test_root_unit_path_writable_by_user_fires
- tests/unit/strata/test_host_isolation.py::TestVerticalIsolation::test_write_to_higher_trust_path_fires
- tests/unit/strata/test_host_isolation.py::TestHostIsolationWaivers::test_vuln_model_fires_unwaived
- tests/unit/strata/test_host_isolation.py::TestHostIsolationWaivers::test_hardened_model_discharges_with_waivers
- tests/unit/strata/test_host_isolation.py::TestCompromisedOwnerCatalog::test_catalog_completeness_over_own_view
- tests/unit/strata/test_host_isolation.py::TestCompromisedOwnerCatalog::test_default_owasp_view_unaffected
- tests/unit/strata/test_host_isolation.py::TestCompromisedUserScenario::test_unknown_user_fails_closed
- tests/unit/strata/test_host_isolation.py::test_blast_radius
- tests/unit/strata/test_litmus_host_isolation.py::TestHostIsolationVulnLitmus::test_shared_user_model_fires_host001_and_host002
- tests/unit/strata/test_litmus_host_isolation.py::TestHostIsolationHardenedLitmus::test_isolated_model_discharges
- tests/unit/strata/test_host_isolation.py::test_movement_flows
- tests/unit/strata/test_host_isolation.py::test_blast_radius_refutes_over_shared_writable_path_with_no_declared_flow
designated_repro_test: null
threat: elevation-of-privilege
component: null
---
T-0254 child 2. The red-team scenario as first-class obligations: when a model declares 2+ runs_as users, LATERAL claims are DEMANDED (HOST001: for every service-user pair, prove NoFlow/no shared writable paths/no shared group membership/no socket reachable across users unless a declared flow exists -- derived from HostManifest intersection, not hand-written per pair) and VERTICAL claims demanded per user (HOST002: no sudoers grant, no setuid binary owned, no root-run unit executing user-writable paths, no write access to any path a higher-trust unit reads -- each either proven from the manifest or an explicit waive with sub-target per T-0174 discipline). New WeaknessEntry rows for the compromised-service-owner class joining the threat catalog views (separate view per precedent, not widening defaults). Litmus: shared-user vuln model fires HOST001/002; isolated hardened model discharges. A compromised-user scenario kind (reuse the T-0073 scenario engine: mark user compromised, closure shows blast radius = exactly that user's manifest slice, claim asserts it).