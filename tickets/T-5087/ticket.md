---
id: T-5087
title: 'strata linker: import-cycle detection with path (hard error), two-sided accepts
  contract, per-module audit hook for the SYS gates'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-5082
- T-5102
parent: T-5081
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_link.py
- src/frob/strata/_audit.py
- src/frob/gates/_sys.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given modules a, b, c where a imports b, b imports c and c imports a, when
    linked, then linking fails with a hard error printing the path a -> b -> c ->
    a.
  evidence: []
- text: Given a cross-module flow declared only by the importer, when linked, then
    linking fails naming the flow, the exporting node and the missing `accepts`; and
    likewise when only the exporter declares `accepts`.
  evidence: []
- text: Given a cross-module flow declared on both sides, when linked, then it passes
    and the resulting fact base is equivalent to today's merged model modulo qualnames.
  evidence: []
- text: 'Given a module name, when the per-module audit hook is invoked via the SYS
    gates, then the exhaustiveness conjunction is evaluated over exactly that module''s
    nodes -- positive control: a planted gap in module M is reported for M and not
    for a sibling.'
  evidence: []
- text: Given a module importing a module BELOW it in the declared hierarchy, when
    linked, then it is a compile error naming BOTH modules (the importer and the importee)
    and their positions.
  evidence: []
- text: 'Given an `accepts f from <module>` naming a module ABOVE the declaring module,
    when linked, then it is an error: accepts goes down only.'
  evidence: []
- text: 'Given the upward-only import rule, when the SCC check runs, then it is a
    redundant assertion that never fires; positive control: a synthetic model with
    a downward import is caught by the upward-only check FIRST, and a test asserts
    the SCC assertion itself would also have fired on a hand-built cyclic import set.'
  evidence: []
- text: Given a cross-module flow, when linked, then it is declared by the LOWER module
    (which alone can name both ends) and accepted by the upper one; a flow declared
    by the upper module is an error.
  evidence: []
- text: Given a module importing a module BELOW it in the declared hierarchy, when
    linked, then it is a compile error naming BOTH modules (the importer and the importee)
    and their positions.
  evidence: []
- text: 'Given an `accepts f from <module>` naming a module ABOVE the declaring module,
    when linked, then it is an error: accepts goes down only.'
  evidence: []
- text: 'Given the upward-only import rule, when the SCC check runs, then it is a
    redundant assertion that never fires; positive control: a synthetic model with
    a downward import is caught by the upward-only check FIRST, and a test asserts
    the SCC assertion itself would also have fired on a hand-built cyclic import set.'
  evidence: []
- text: Given a cross-module flow, when linked, then it is declared by the LOWER module
    (which alone can name both ends) and accepted by the upper one; a flow declared
    by the upper module is an error.
  evidence: []
- text: Given a module importing a module BELOW it in the declared hierarchy, when
    linked, then it is a compile error naming BOTH modules (the importer and the importee)
    and their positions.
  evidence: []
- text: 'Given an `accepts f from <module>` naming a module ABOVE the declaring module,
    when linked, then it is an error: accepts goes down only.'
  evidence: []
- text: 'Given the upward-only import rule, when the SCC check runs, then it is a
    redundant assertion that never fires; positive control: a synthetic model with
    a downward import is caught by the upward-only check FIRST, and a test asserts
    the SCC assertion itself would also have fired on a hand-built cyclic import set.'
  evidence: []
- text: Given a cross-module flow, when linked, then it is declared by the LOWER module
    (which alone can name both ends) and accepted by the upper one; a flow declared
    by the upper module is an error.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The link step. A new src/frob/strata/_link.py joins the per-module elaboration
results using only export surfaces, and enforces:
  - import cycle detection as a HARD error (D-M2) printing the full path
    `a -> b -> c -> a`. Expect the 16 existing bidirectional module pairs to
    fail; each is decided individually in its migration leaf, never bulk-waived.
  - two-sided cross-module flow contract (D-M3): for every Flow whose src and
    dst modules differ, the importer declares the `flow` AND the exporter
    declares `accepts <flow> from <module>` on the exported node. Either side
    missing is an error. Deny by default; this is a well-formedness predicate
    over existing Flow facts, so no kernel primitive is added.
  - a per-module audit hook that src/frob/gates/_sys.py calls, so the per-family
    exhaustiveness conjunction can be scoped to one module's nodes instead of
    the whole design. src/frob/strata/_audit.py grows the module-scoped entry
    point.

## Unblock log
- 2026-09-19: unblocked by T-4659 -- filing artifact: T-4659 is an unrelated in-flight land that was captured by a bad id extraction; the real blocker is the elaborator leaf T-5102
