---
id: T-0290
title: 'recursion static analysis: prove-terminating-or-error, tail-call + depth-bound
  gate'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob-core/**
- src/frob/perf/**
- src/frob/arch/**
- src/frob/graph/dsl.py
- src/frob/gates/**
- docs/modules/perf.md
- tickets.md
- tests/test_perf.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_perf.py
  reason: T-0290 perf work maps to tests/test_perf.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_perf.py::test_perf005_fires_when_descent_is_outside_the_call_args
- tests/test_perf.py::test_perf005_does_not_fire_on_super_init_call
- tests/test_perf.py::test_perf005_does_not_pair_same_named_methods_across_classes
designated_repro_test: null
acceptance:
- text: given any function, when analysis runs, then a static call graph is built
    and every recursive SCC (direct AND mutual recursion) is identified -- purely
    static, no execution
  evidence: []
- text: 'given a structurally-recursive function (each recursive call is on a provably-smaller
    argument along a well-founded order: list tail, tree child, n-1 on a non-negative
    int, or a strictly-decreasing bounded integer measure toward a guarded base case),
    when the termination checker runs, then it is PROVEN-TERMINATING and passes silently'
  evidence: []
- text: given a recursion the checker CANNOT prove terminating, then it is an ERROR
    (not a warning) -- the author must either refactor into a provable form, or attach
    a reasoned directive (frob:invariant terminates reason="..." with an optional
    measure), which is counted/auditable exactly like every other frob waiver; an
    UNREASONED unprovable recursion can never pass
  evidence: []
- text: given a tail-recursive function in a language without guaranteed TCO (Python
    especially), when detected, then it is flagged with a rewrite-as-loop suggestion
    AND requires a provable depth bound -- unbounded recursion depth that scales with
    runtime input size (stack-overflow / DoS surface) is an error unless a bound is
    proven or reasoned-waived
  evidence: []
- text: given the arch<->dup<->recursion consistency requirement, then the call graph
    is a SHARED interprocedural substrate reused by T-0288 (dup helper-inlining) and
    T-0289 (arch complexity-awareness) -- built once, not three times
  evidence: []
threat: null
component: null
---
User vision (2026-07-19): frob perf does nothing with recursion today (PERF001-004 are lexical loop smells only). Recursion is a control-flow hazard that must be either statically reasoned about or rejected. NORTH STAR (user, verbatim intent): "you should not be able to write bad code (logically similar or copied); it will be flagged" -- extend that to control flow: no recursion whose termination/depth cannot be statically bounded may pass unreasoned. DESIGN, three layers: (1) DETECT -- build a static call graph, find recursive SCCs incl. mutual recursion (frob-core, reuse for T-0288/T-0289). (2) PROVE-OR-ERROR -- termination is undecidable in general, so be SOUND not complete: prove the decidable fragment (structural descent on a well-founded argument; strictly-decreasing bounded integer measure to a guarded base case), and ERROR on everything unproven. The escape is a REASONED directive (frob:invariant terminates reason=... measure=...), auditable like any waiver -- consistent with the T-0289 arch-override philosophy (prove it, or justify it at the code; never silent). (3) DEPTH/STACK SAFETY -- tail-call detection (user example: Python has no TCO, so tail recursion over runtime-sized input is a stack-overflow/DoS bug): flag tail recursion with a rewrite-as-loop suggestion, and require a proven depth bound; recursion whose depth scales with input and has no bound is an error. CONSISTENCY: this shares the interprocedural call-graph substrate with dup helper-inlining (T-0288) and arch complexity-awareness (T-0289) -- one call-graph facility feeds dup (see through helpers), arch (complexity, mutual-recursion-via-helpers), and this (termination/depth). Unify the escape-hatch philosophy across arch/perf/recursion: the tool proves what it can, and every unprovable residue must carry a reasoned, counted directive -- that is what makes "you cannot write bad code silently" actually hold.