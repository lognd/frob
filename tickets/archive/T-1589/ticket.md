---
id: T-1589
title: 'strata self-model drift: mutation audit, threat caught_by, and k8s export
  golden fail against the real repo'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- invariants/**
- tests/unit/strata/**
- docs/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
- tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
designated_repro_test: null
threat: null
component: null
---
Four real-repo self-model tests fail on main after the T-1518/T-1575/T-1576/T-1559 lands added new nodes (frob.tickets._profile, _mutation_sweep_queue) and new capability surface:

- test_mutation_audit::test_every_may_is_load_bearing -- a declared 'may' (node=cli, atom=env.read, mode=delete among others) is no longer load-bearing: the mutation audit can delete it with no detector noticing.
- test_mutation_audit::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds -- the disclosed gap set no longer matches the measured one (an extra kind appeared).
- test_threat::test_every_shipped_entry_has_a_substantive_caught_by -- 16 shipped entries, 15 with substantive caught_by: one new entry has a placeholder.
- test_export_golden::test_k8s -- the k8s golden export drifted (NetworkPolicy egress section).

These are exactly the 'design must keep up with the code' checks the self-model exists to enforce, so they are real drift to close, not tests to relax. Update design/frob.strata declarations (frob sys sync-interface for interface= attrs), give the new threat entry a substantive caught_by, re-derive the k8s golden ONLY after confirming the diff is intended, and re-run the may-mutation audit until every may is load-bearing again.