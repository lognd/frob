---
id: T-0523
title: burn down residual 59 COV006 findings outside gates/test_gates.py scope
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestSummarySeverityHonesty::test_cycle_summary_splits_by_severity
- tests/unit/strata/test_waive.py::TestStaleDetail::test_names_rule_node_and_reason
designated_repro_test: null
threat: null
component: null
---
T-0516 fixed the systematic COV006 FP class (two-hop private-helper chains through a same-file public wrapper, and Python import-alias name mismatches in the wrapper-reachability rescue), which dropped total repo COV006 findings from 90 to 61 (measured via frob check --only coverage on this worktree before/after). T-0516's declared scope was narrowly src/frob/gates/__init__.py + tests/test_gates.py, where all findings are now resolved (2 remaining, both legitimately waived: a ProcessPoolExecutor function-reference indirection and a module-level-data invariant test with no call path to its consumer). The other 59 COV006 findings live in test files/target modules entirely outside that scope (tests/unit/strata/*, tests/test_dup_region.py, tests/test_lang.py, tests/test_graph.py, tests/test_serve.py, tests/test_vet.py, tests/test_tickets.py, tests/system/*, frob-core/src/lib.rs bindings, etc.) and were never triaged by T-0516 -- each needs the same per-finding policy applied (fix wrong binding / add missing test call / waive with a real reason) with a fresh frob check --only coverage list, since some may already be resolved by T-0516's checker fix and need re-measuring before triage.