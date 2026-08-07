---
id: T-0680
title: 'registry: route out_of_scope disposition reason through T-0382 caught_by verification'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0383
tier: ticket
sprint: null
scope:
- src/frob/gates/_registry_exhaustiveness.py
- docs/design/registry/**
- tests/test_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_no_control_warns
- tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_unresolved_rule_warns
- tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_resolved_rule_is_silent
- tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_substantive_reasoned_none_is_silent
- tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_bare_none_is_not_substantive
designated_repro_test: null
acceptance:
- text: GIVEN a registry entry with out_of_scope disposition whose reason names no
    catching control and is not a substantive reasoned-none WHEN the registry gate
    runs THEN a finding fires naming the entry
  evidence:
  - tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_no_control_warns
  - tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_unresolved_rule_warns
  - tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_resolved_rule_is_silent
  - tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_substantive_reasoned_none_is_silent
  - tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_bare_none_is_not_substantive
threat: null
component: null
---
The one remaining caught_by gap after T-0382/T-0383: registry-YAML out_of_scope:<reason> disposition strings are a separate surface from the strata model objects and never pass through T-0382's caught_by verification -- a registry entry can be excused with a reason that names no catching control and nothing checks it. Route those disposition reasons through the same verification (or an equivalent registry-side rule) so an out_of_scope registry entry either names a real catching control or carries a substantive reasoned-none, mechanically checked. Was T-0680 (ex-draft, id lost at land) in T-0383's worktree; drafts do not survive land (T-0637).