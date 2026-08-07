---
id: T-1066
title: 'arch: resolve deep-nesting on graph/summary.py::_tarjan_sccs (T-0394 remainder)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/summary.py
- src/frob/gates/_arch.py
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/commands/check.md
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_arch.py
  reason: evidence tests for the deep-nesting arch-exempt directive
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/commands/check.md
  reason: 'scope-closure: analyze_project and sibling arch checks already carry frob:doc
    anchors into these two files'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/arch.md
  reason: 'scope-closure: analyze_project and sibling arch checks already carry frob:doc
    anchors into these two files'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_arch.py::TestDeepNestingArchExempt::test_reasoned_exempt_suppresses_finding
- tests/unit/test_arch.py::TestDeepNestingArchExempt::test_unreasoned_exempt_still_fires
- tests/unit/test_arch.py::TestDeepNestingArchExempt::test_exempt_on_unrelated_function_does_not_leak
designated_repro_test: null
threat: null
component: null
---
Filed from T-0394 (re-measured deep-nesting: 18 findings not the stale "2"
in the original body; 14 in-scope after excluding strata/**/vet/** sibling
trees, 13 genuinely refactored down to depth<=4 -- see T-0394's Done
report). One remains: src/frob/graph/summary.py::_tarjan_sccs (depth 5).
It already carries a reasoned `frob:waive ARCH001` comment (long-function)
arguing this iterative Tarjan's SCC's index/lowlink/on-stack bookkeeping
plus its explicit work-stack unwind loop are one indivisible algorithm --
splitting the unwind step would thread the index/lowlink/stack triple
across a new boundary per visited node, adding indirection without
separating a real sub-concern. deep-nesting is unwaivable by code comment
(same channel as abstraction-opportunity, frob.gates._unwaivable_channel_
rules), so this needs either a real decomposition that a reviewer confirms
does not violate the ARCH001 reasoning above, or (more likely, given the
existing reasoning already holds for the sibling long-function rule) a
scoped textbook-algorithm exemption added to the deep-nesting detector
itself (mirroring how ARCH001 already carries a reasoned per-function
override path) -- evaluate both options; do not force a split that
contradicts the standing ARCH001 rationale on the same function.