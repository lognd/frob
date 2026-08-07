---
id: T-1471
title: 'test_mutation_audit second-detector gap set drifted: env.read now unaccounted
  (pre-existing, found during T-1415)'
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/test_mutation_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
designated_repro_test: null
threat: null
component: null
---
Discovered while verifying T-1415/T-1400 in worktree w4k-test005: tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds fails on main tip (8462af0b) unrelated to any change in this session -- gap_kinds now includes an extra 'env.read' not in the test's expected set. design/frob.strata already declares 'may "env.read";' (line 967) predating this worktree's session. Likely landed by a recent main ticket (T-1439/T-1465 series) that widened env capability modes without updating this test's expected set. Needs: update the test's expected gap_kinds set (or the underlying second-detector-gap classification) to match current reality.