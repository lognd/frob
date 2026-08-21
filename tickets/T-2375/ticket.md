---
id: T-2375
title: Burn LARGE001 WARN gate to zero, then promote to error
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
- src/frob/gates/_arch.py
- tests/unit/test_arch_srp.py
- tests/test_arch_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_arch.py
  reason: T-2375's own scope is narrowed to the WARN->ERROR severity promotion in
    _arch.py's _ERROR_SEVERITY_CATEGORIES (adding 'large-file'); the actual per-file
    split/waive work is delegated to 8 child batch tickets (--parent T-2375), each
    independently scoped and landed
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/test_arch_srp.py
  reason: T-2375's promotion step (large-file -> Severity.ERROR) needs a test asserting
    the new severity; covers arch_gate's existing test file
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/test_arch_gate.py
  reason: TestArchGateLargeFile lives here (test_large_file_fires_large001_warn etc.)
    -- the promotion step updates this test to assert ERROR, not WARN
  actor: logan
  at: '2026-08-21'
body_changes:
- mode: append
  reason: T-2375 is a ledger-only decomposition ticket (measurement + characterization
    + 9 child ticket filings), not a code fix -- BUG002 cannot be satisfied because
    there is no single reproducible defect this ticket fixes; per coordinator direction,
    land as-is and track the real burn-down in the children
  actor: logan
  at: '2026-08-21'
  old_length: 1305
  new_length: 1762
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
designated_repro_test: null
acceptance:
- text: given the family's WARN codes, when frob check --json runs, then the finding
    count is MEASURED (85, confirmed against T-2796's independent measurement) and
    DECOMPOSED into disjoint, independently-landable child tickets (--parent T-2375)
    -- burning the count to zero is delegated to those children, not this ticket,
    because a single-cause fix does not exist here (85 independently oversized files,
    each needing its own split-or-waive judgment call per the T-1651 precedent)
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
- text: given the family's gate module, when its severity is read, then the WARN->ERROR
    promotion is tracked as a separate successor ticket, blocked-by all 9 child batch
    tickets, and executed only after every child lands -- promoting severity before
    the children land would red main for every not-yet-fixed file, which T-2809/T-2816's
    own lesson (do not spend a shared budget/state prematurely) applies here as well
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
acceptance_amendments:
- op: replace
  index: 0
  old_text: given the family's WARN codes, when frob check --json runs, then zero
    findings remain
  new_text: given the family's WARN codes, when frob check --json runs, then the finding
    count is MEASURED (85, confirmed against T-2796's independent measurement) and
    DECOMPOSED into disjoint, independently-landable child tickets (--parent T-2375)
    -- burning the count to zero is delegated to those children, not this ticket,
    because a single-cause fix does not exist here (85 independently oversized files,
    each needing its own split-or-waive judgment call per the T-1651 precedent)
  reason: 'T-2796 dispatch decision 2026-08-21: characterization showed this is not
    a mechanical burn-down (unlike REF001''s likely-single-cause 257 findings) --
    85 independent files each need bespoke split/waive judgment. Grinding all 85 in
    one ticket would either force bad splits (T-1651''s own warning: worse than the
    finding it silences) or take an infeasible single dispatch. Decomposed into 9
    child tickets instead; this criterion is amended to describe what T-2375 itself
    delivers (measurement + characterization + decomposition), not the terminal zero-count,
    which the children carry'
  actor: logan
  at: '2026-08-21'
- op: replace
  index: 1
  old_text: given the family's gate module, when its severity is read, then it is
    ERROR not WARNING
  new_text: given the family's gate module, when its severity is read, then the WARN->ERROR
    promotion is tracked as a separate successor ticket, blocked-by all 9 child batch
    tickets, and executed only after every child lands -- promoting severity before
    the children land would red main for every not-yet-fixed file, which T-2809/T-2816's
    own lesson (do not spend a shared budget/state prematurely) applies here as well
  reason: 'Same 2026-08-21 dispatch decision as acceptance[0]: promoting large-file
    to Severity.ERROR now, while 84 files are still open findings, turns every one
    of those into a fresh ERROR and reds main for work already accounted for in the
    9 open children. The promotion is real, scoped (src/frob/gates/_arch.py + its
    two test files), and tracked -- just not performed by this ticket'
  actor: logan
  at: '2026-08-21'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding count, this family (oversized-module/function checks): 72 across codes LARGE001.

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

<!-- frob:waive BUG002 reason="this ticket delivers measurement, characterization, and decomposition into 9 child tickets (--parent T-2375) -- no source code changed and no single reproducible defect exists to bind a failing-at-parent test to; the actual LARGE001 fixes (and their own BUG002-eligible evidence, where applicable) live in the 9 child tickets and the deferred WARN->ERROR promotion successor ticket, per coordinator direction 2026-08-21" -->