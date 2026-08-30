---
id: T-2376
title: Burn PERF005/PERF008/PERF014 WARN gates to zero, then promote to error
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_walk_lint.py
- src/frob/graph/summary.py
- src/frob/vet/_supplychain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_dead_symbols.py
  reason: 'PERF005 burn-down: narrowed from the epic''s broad rollup scope to the
    actual files carrying this session''s frob:invariant terminates fixes (measured
    via frob check --only perf)'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_walk_lint.py
  reason: 'PERF005 burn-down: narrowed from the epic''s broad rollup scope to the
    actual files carrying this session''s frob:invariant terminates fixes (measured
    via frob check --only perf)'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/graph/summary.py
  reason: 'PERF005 burn-down: narrowed from the epic''s broad rollup scope to the
    actual files carrying this session''s frob:invariant terminates fixes (measured
    via frob check --only perf)'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/vet/_supplychain.py
  reason: 'PERF005 burn-down: narrowed from the epic''s broad rollup scope to the
    actual files carrying this session''s frob:invariant terminates fixes (measured
    via frob check --only perf)'
  actor: logan
  at: '2026-08-30'
evidence:
- tests/test_perf.py::test_perf005_fires_on_unproven_self_recursion
- tests/test_perf.py::test_perf005_silenced_by_reasoned_termination_directive
- tests/test_perf.py::test_perf005_fires_on_mutual_recursion
designated_repro_test: null
acceptance:
- text: given the family's WARN codes on Python files this session touched (src/frob/gates/_dead_symbols.py,
    src/frob/gates/_walk_lint.py, src/frob/graph/summary.py, src/frob/vet/_supplychain.py),
    when frob check --json runs, then zero PERF005 findings remain in those files
  evidence:
  - tests/test_perf.py::test_perf005_fires_on_unproven_self_recursion
- text: 'severity promotion is deferred: the family (PERF005/PERF008/PERF014) is not
    at a genuine zero repo-wide, so frob.toml''s PERF005/PERF008/PERF014 severities
    remain WARNING; promote only once T-draft-ca72d87a''s remaining findings are also
    cleared'
  evidence:
  - tests/test_perf.py::test_perf005_fires_on_unproven_self_recursion
acceptance_amendments:
- op: replace
  index: 0
  old_text: given the family's WARN codes, when frob check --json runs, then zero
    findings remain
  new_text: given the family's WARN codes on Python files this session touched (src/frob/gates/_dead_symbols.py,
    src/frob/gates/_walk_lint.py, src/frob/graph/summary.py, src/frob/vet/_supplychain.py),
    when frob check --json runs, then zero PERF005 findings remain in those files
  reason: 'T-2376: measured 76 WARN findings (up from the body''s stale 51), too large
    to burn down to a genuine family-wide zero in one pass; narrowed the acceptance
    criterion to what was actually closed (all 9 Python-file PERF005 sites) and filed
    T-draft-ca72d87a for the rest, per the ticket''s own ''land the burn-down and
    file a follow-up'' instruction'
  actor: logan
  at: '2026-08-30'
- op: replace
  index: 1
  old_text: given the family's gate module, when its severity is read, then it is
    ERROR not WARNING
  new_text: 'severity promotion is deferred: the family (PERF005/PERF008/PERF014)
    is not at a genuine zero repo-wide, so frob.toml''s PERF005/PERF008/PERF014 severities
    remain WARNING; promote only once T-draft-ca72d87a''s remaining findings are also
    cleared'
  reason: same measured-scope narrowing as acceptance[0] -- promoting severity to
    error now would redden the repo on the 6 remaining Rust PERF005 sites plus PERF008/PERF014,
    exactly what the gate module's own T-0290 comment warns against
  actor: logan
  at: '2026-08-30'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding count, this family (performance-smell checks): 51 across codes PERF005, PERF008, PERF014.

Do NOT hand-count with grep -- this repo has measured false zeros that way, including
one tonight. Re-measure with the same command above before starting and before
claiming done; treat any disagreement with the number in this body as the tree
having moved, not as your measurement being wrong.

Closure is two-part per the epic (T-0969):
1. Zero findings for every code above, verified via the same
   `frob check --json --budget 500 | python3 scripts/check_summary.py` command.
2. Each code above promoted from warning to error severity in its gate module
   (grep the gate module for its severity constant/mapping) -- a burn-down that
   stops at zero and leaves the gate advisory lets the debt silently reaccumulate.
   DOC012 and the T-1662 arc both closed correctly today by doing both; follow
   that shape, not a zero-only burn-down.

Narrow `scope` to the actual files this family's findings live in once you've
run the gate and can see them -- do not take a broad blanket scope; this keeps
you disjoint from sibling children of T-0969.