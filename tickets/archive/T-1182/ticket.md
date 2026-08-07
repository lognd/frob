---
id: T-1182
title: 'arch: abstraction-opportunity detector should skip same-name call-through
  forwarders'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_distinct_named_self_forwarders_not_flagged
- tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_group_with_one_non_self_named_member_still_flagged
- tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_forwarder_helper_requires_self_named_short_body
designated_repro_test: null
acceptance:
- text: GIVEN a group whose members are same-name single-statement forwarders to another
    symbol WHEN abstraction-opportunity clusters by signature THEN forwarders are
    excluded (they are deliberate indirection, not duplicated logic), measured before/after
    on the T-1083 finding set
  evidence:
  - tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_distinct_named_self_forwarders_not_flagged
  - tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_group_with_one_non_self_named_member_still_flagged
  - tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_forwarder_helper_requires_self_named_short_body
threat: null
component: null
---
Refile from the w20-arch T-1083 disposition pass (draft died with the fail-log; record on branch w20-arch commit a8085d7f): call-through forwarders (one-line delegation wrappers) coincide on signature by construction and are not extraction candidates.