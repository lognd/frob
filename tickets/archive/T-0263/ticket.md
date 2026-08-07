---
id: T-0263
title: 'Kerberos/AD movement vectors: delegation abuse, Kerberoasting, S4U, cross-realm
  as HOST/KRB obligations'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0256
- T-0262
- T-0282
parent: T-0254
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/strata/**
- design/**
- tickets.md
- tests/unit/strata/
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0263 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
evidence:
- tests/unit/strata/test_krb_movement.py::TestKrb001::test_fires
- tests/unit/strata/test_krb_movement.py::TestKrb001::test_skips_constrained
- tests/unit/strata/test_krb_movement.py::TestKrb002::test_fires
- tests/unit/strata/test_krb_movement.py::TestKrb002::test_no_spn_no_finding
- tests/unit/strata/test_krb_movement.py::TestKrb002::test_waivable_with_gmsa_reason
- tests/unit/strata/test_krb_movement.py::TestKrb003::test_chains
- tests/unit/strata/test_krb_movement.py::TestKrb003::test_non_chaining_same_trust_discharges
- tests/unit/strata/test_krb_movement.py::TestKrb004::test_fires
- tests/unit/strata/test_krb_movement.py::TestKrb004::test_same_trust_realms_discharge
- tests/unit/strata/test_krb_movement.py::TestKrbScen::test_all
- tests/unit/strata/test_krb_movement.py::TestKrbScen::test_constrained_bounded_to_targets
- tests/unit/strata/test_krb_movement.py::TestKrbScen::test_unknown_node_fails_closed
- tests/unit/strata/test_krb_movement.py::TestKrbCatalog::test_catalog_completeness_over_own_view
- tests/unit/strata/test_litmus_krb_movement.py::TestKrbMovementVulnLitmus::test_vuln_model_fires_all_four_rules
- tests/unit/strata/test_litmus_krb_movement.py::TestKrbMovementHardenedLitmus::test_hardened_model_discharges
designated_repro_test: null
threat: elevation-of-privilege
component: null
---
T-0254: the red-team Kerberos playbook as demanded, provable obligations extending T-0256's movement-impossibility family. KRB001 unconstrained delegation: any node declaring delegation unconstrained is a hard finding (it lets a compromised service impersonate ANY user to ANY service -- the worst lateral+vertical vector) -- must be re-declared constrained/rbcd or waived with a written accepted-risk reason and sub-target. KRB002 Kerberoasting exposure: an SPN bound to a principal whose credential class is a human-memorable/user password (not a machine account or gMSA) is roastable -- demand gMSA/machine-account or a waiver. KRB003 constrained-delegation blast radius: for a node with constrained delegation, prove the target SPN set does not transitively reach a higher-trust principal (S4U2Proxy chaining) -- reachability over the SPN graph, counterexample trace on failure. KRB004 cross-realm containment: a one-way/transitive trust must not create an undeclared path from a low-trust realm to a high-trust service. Each rule joins a separate compromised-domain-principal threat view (WeaknessEntry rows: CWE-522/CWE-269/CWE-284 class) per the separate-view precedent, NOT widening defaults. Reuse the T-0073 scenario engine for a compromised-service-account scenario whose closure shows the Kerberos blast radius. Litmus: an unconstrained-delegation + roastable-SPN vuln model fires KRB001/002; a gMSA + constrained + non-chaining hardened model discharges all four.