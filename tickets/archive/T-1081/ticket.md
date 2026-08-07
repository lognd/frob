---
id: T-1081
title: 'arch: ARCH102 fires on newly-split src/frob/gates/_waive.py (35 exports, 4
  clusters)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_waive.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: cohering _waive.py into smaller sibling modules to clear ARCH102 requires
    updating __init__.py's re-export imports to the new module paths, the same mechanical
    consequence T-1072 hit when it first created _waive.py
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_ticket_attr_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_gates.py::TestActiveTicket::test_explicit_flag_wins
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
---
Post-gates-split (the recent frob.gates.__init__ -> frob.gates._waive extraction), gates-native's archgate stage reports an unwaived ARCH102 on src/frob/gates/_waive.py: 35 top-level exports split across 4 unrelated naming/usage clusters. Out of scope for T-1066/T-1068 (both explicitly excluded from touching src/frob/gates/**); needs either a genuine further split of _waive.py or a reasoned frob:waive ARCH102 the way sibling gates modules already carry (see src/frob/gates/__init__.py's own ARCH102 waiver for the pattern).