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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/summary.py
- src/frob/gates/_arch.py
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/commands/check.md
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
body_changes:
- mode: append
  reason: condense arch-exempt deep-nesting marker rationale into T-1066 body
  actor: logan
  at: '2026-09-19'
  old_length: 1290
  new_length: 2920
evidence:
- tests/unit/arch_suite/test_complexity.py::TestDeepNestingArchExempt::test_reasoned_exempt_suppresses_finding
- tests/unit/arch_suite/test_complexity.py::TestDeepNestingArchExempt::test_unreasoned_exempt_still_fires
- tests/unit/arch_suite/test_complexity.py::TestDeepNestingArchExempt::test_exempt_on_unrelated_function_does_not_leak
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
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

<!-- narrative-moved:src/frob/arch/_python.py:111:T-1066 -->
: T-1066: matches an `# arch-exempt: deep-nesting reason="..."` directive on
: a leading-comment line directly above a function's `def`/`async def`
: (same physical placement `frob:waive ARCH001` already uses above a
: function, e.g. `_tarjan_sccs`'s existing waiver in
: `frob.graph.summary`). Deliberately spelled WITHOUT a `frob:` prefix --
: `frob.graph.dsl._LINE_RE` treats any `frob:<token>` comment as an
: attempted directive and DSL001s it if the verb is not registered there,
: and registering a new verb means editing `frob.graph.dsl` (outside this
: ticket's `src/frob/arch/**`-scoped territory); a distinct, non-`frob:`
: marker sidesteps that collision entirely rather than smuggling a new
: verb through a module this ticket must not touch. deep-nesting is also
: DELIBERATELY excluded from the generic `frob:waive` graph-edge channel
: (`frob.gates._unwaivable_channel_rules`'s docstring: `ArchSuggestion`s
: for this category never become `Violation`s, so no waiver edge could
: ever bind to one) -- this marker is a SEPARATE, detector-owned
: exemption, not a workaround of that boundary. It exists for exactly the
: case ARCH001's own reasoned-waiver path already covers for
: long-function: a genuinely irreducible algorithm (textbook iterative
: Tarjan's SCC, explicit work-stack unwind) where a forced split would add
: indirection without separating a real sub-concern, not a blanket escape
: hatch. `reason=` is REQUIRED (mirrors `frob:waive`'s WAIVE001
: discipline) -- an empty or missing reason does not match and the
: finding still fires.