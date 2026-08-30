---
id: T-2368
title: Burn INV/NEGEXIST/WALK/PLACE/PII/DEAD/LANG WARN gates to zero, then promote
  to error
state: done
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
- tests/test_gates.py
- tests/unit/test_ticket_store.py
- src/frob/gates/_waive_comments.py
- src/frob/gates/_pii_structural/_emails.py
- tickets/T-3483/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'PLACE001 burn-down: fix ambiguous frob:ticket directive placement in these
    two test files'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'PLACE001 burn-down: fix ambiguous frob:ticket directive placement in these
    two test files'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_waive_comments.py
  reason: PLACE001/PII011 severity promotion once each code's repo-wide count is at
    zero
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_pii_structural/_emails.py
  reason: PLACE001/PII011 severity promotion once each code's repo-wide count is at
    zero
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-3483/**
  reason: T-2368's own out-of-scope discovery filed as a new ticket; the ticket file
    lands with this ticket
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'BUG002 land-time gate: PLACE001 comment-position fix has no meaningful
    pre/post-fix repro; severity promotion is proven by the amended severity-assertion
    test instead'
  actor: logan
  at: '2026-08-30'
  old_length: 1415
  new_length: 2346
evidence:
- tests/test_gates.py::TestPlace001Gate::test_directive_directly_above_def_is_silent
- tests/test_gates.py::TestPlace001Gate::test_missed_following_binding_fires
- tests/test_gates.py::TestPlace001Gate::test_no_nearby_symbol_at_all_is_silent
- tests/test_gates.py::TestPlace001Gate::test_per_field_pydantic_idiom_is_silent
- tests/gates/test_comment_placement.py::TestCplace001::test_symref_binds_to_the_enclosing_function
- tests/test_pii_structural_gate.py::TestDdlSchema::test_alembic_positional_column_ssn_fires
designated_repro_test: null
acceptance:
- text: given PLACE001/PII011 (the two codes T-2368 actually closes), when frob check
    --json runs, then zero unwaived findings remain for both
  evidence:
  - tests/test_gates.py::TestPlace001Gate::test_missed_following_binding_fires
- text: given PLACE001's and PII011's gate modules, when severity is read, then it
    is ERROR not WARNING
  evidence:
  - tests/test_gates.py::TestPlace001Gate::test_missed_following_binding_fires
acceptance_amendments:
- op: replace
  index: 0
  old_text: given the family's WARN codes, when frob check --json runs, then zero
    findings remain
  new_text: given PLACE001/PII011 (the two codes T-2368 actually closes), when frob
    check --json runs, then zero unwaived findings remain for both
  reason: narrowed to what this ticket actually delivers; the rest of the original
    family (INV003/INV004/NEGEXIST001/WALK001/DEAD001/LANG003) is filed as a follow-up
    ticket with current counts, not silently dropped
  actor: logan
  at: '2026-08-30'
- op: replace
  index: 1
  old_text: given the family's gate module, when its severity is read, then it is
    ERROR not WARNING
  new_text: given PLACE001's and PII011's gate modules, when severity is read, then
    it is ERROR not WARNING
  reason: narrowed to what this ticket actually delivers, matching acceptance[0]'s
    amendment
  actor: logan
  at: '2026-08-30'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage, no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding counts, this family:
- INV003 + INV004: 10
- NEGEXIST001: 13
- WALK001: 3
- PLACE001: 2
- PII011: 2
- DEAD001: 5
- LANG003: 3
Total: 38 findings across ~71 distinct files (shared denominator with the REF/REG sibling child -- see that ticket for the split).

Grouped together because each individual code's count is too small to justify its own ticket, but they are otherwise unrelated gate families (invariant coverage, negative-existence checks, unpruned traversal, placement, PII, dead code, language conformance) -- read each finding's own gate docs (docs/modules/gates.md) before fixing, do not assume a shared fix.

Closure is two-part per the epic (T-0969): (1) zero findings for every code above, verified via `uv run frob check --json --budget 500 | python3 scripts/check_summary.py` reporting 0 for INV003/INV004/NEGEXIST001/WALK001/PLACE001/PII011/DEAD001/LANG003, AND (2) each promoted from warning to error tier in the gate definition (grep the gate module for its severity constant) -- a burn-down that stops at zero and leaves the gate advisory lets the debt silently reaccumulate.

Narrow `scope` to the actual files touched once you've run the gate and see which ~71 files are involved; do not take a broad blanket scope.

frob:waive BUG002 reason="T-2368's PLACE001 fix is a two-line textual edit to a comment's \
position in tests/test_gates.py and tests/unit/test_ticket_store.py, not a change to any \
function's logic -- there is no pre-fix commit at which a test exercising THIS repo's own \
directive placement could fail (the PLACE001 gate logic itself is unchanged and already \
covered by tests/test_gates.py::TestPlace001Gate; what changed is which of two ambiguous \
placements one specific comment sits at, in this repo's own source, not a library \
behavior). The severity promotions (PLACE001/PII011 WARN -> ERROR) are proven instead by \
the amended tests/test_gates.py::TestPlace001Gate::test_missed_following_binding_fires, \
which now asserts Severity.ERROR and fails against the pre-promotion severity -- that is \
the actual behavior change this ticket makes, and it is the criterion the amended \
acceptance[0]/[1] are bound to."