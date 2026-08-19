---
id: T-2664
title: DOCENUM001 passes with member ids listed but never documented
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
- src/frob/gates/_docenum.py
- tests/test_docenum_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_decisions.py
  reason: correct implementation file; DOCENUM001 lives in _docenum.py not _decisions.py
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/gates/_docenum.py
  reason: correct implementation file; DOCENUM001 lives in _docenum.py not _decisions.py
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_docenum_gate.py
  reason: T-2664 extends docenum001_gate; new coverage must live in its existing test
    file
  actor: logan
  at: '2026-08-19'
body_changes:
- mode: append
  reason: BUG002 unsatisfiable by construction for a brand-new test class against
    a fresh WARN-severity check; documented per playbook's stated escape hatch rather
    than fabricating a repro commit split
  actor: logan
  at: '2026-08-19'
  old_length: 1702
  new_length: 2326
evidence:
- tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_no_doc_row_fires_warn
- tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_doc_row_does_not_fire
- tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_documented_via_heading_section_does_not_fire
- tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_member_mismatch_still_fires_alongside_undocumented
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2613 fixed DOCENUM001 by syncing docs/modules/gates.md's `frob:enumerates`
members= list to the real `_KNOWN_GATE_RULES` set. That closed the gate --
but DOCENUM001 only ever checks that the declared MEMBER LIST matches the
real rule-id set, never that each listed member has an actual
documentation row/section anywhere in the file. Adding a bare id to the
member list is enough to go green.

Effect, confirmed directly (T-2662): three of the seven ids T-2613 added
(MILE001, MILE002, WAIVE009 before T-2639 landed its own row) had zero
documentation rows in docs/modules/gates.md's own gate-catalog table --
DOCENUM001 read clean throughout. The anchor was in sync; the actual
protection it exists for (every gate rule id is documented somewhere a
human can read) was not delivered. Same shape as the WAIVE009-not-wired-
into-run_gates incident this same session found: a rule can be declared
correct by its own enumeration gate while doing none of the work the
enumeration was meant to guarantee.

Proposal: extend DOCENUM001 (or add a sibling rule, e.g. DOCENUM002) so
that every id in the enumerated member list must also resolve to a real
table row (or a `## <RULE> (...)` prose section, matching this file's own
two documentation shapes) in the same file -- not just appear as a bare
string in the members= list. A member with no corresponding row/section
should fail the gate the same way a member ABSENT from the real rule set
does today.

This is a gate-contract change (widens what DOCENUM001 requires to pass),
not a bug fix -- deliberately out of T-2662's own docs-only scope. Filed
per T-2662's own brief instruction to record this judgment as a ticket
rather than implement it inline.


frob:waive BUG002 reason="new WARN-severity check added under a fresh test class; --check-repro reports TEST_ABSENT_AT_PARENT against merge-base (T-2025 limitation -- the test does not exist at the parent commit at all, so no pre-fix-vs-post-fix comparison is reachable without committing the test alone first purely to satisfy this check). Confirmatory-only evidence: all 4 new tests plus the 11 pre-existing docenum001 tests pass post-change (frob test exit=0); positive/negative controls for both the new WARN check and the pre-existing ERROR mismatch check are exercised directly in TestDocenum001UndocumentedMembers."