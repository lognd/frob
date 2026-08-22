---
id: T-2874
title: Waive COV007's last finding (_reap.py) and promote COV007 to ERROR
state: done
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_reap.py
- src/frob/gates/__init__.py
- docs/modules/gates.md
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: promotion requires updating gates.md's COV007 rule-table row and prose section
    to reflect the new error severity
  actor: logan
  at: '2026-08-22'
body_changes:
- mode: append
  reason: 'waive BUG002: severity promotion is not repro-shaped'
  actor: logan
  at: '2026-08-22'
  old_length: 1997
  new_length: 2715
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper
- tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_doc_anchor_on_public_symbol
- tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_a_strata_node_whose_clearance_is_not_public
- tests/test_gates.py::TestCoverageGate::test_cov007_still_fires_for_a_python_private_helper_after_t2549
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split off T-2866: 36 of COV007's 37 live warnings are now individually
waived (see T-2866's Done report). The one remaining --
src/frob/process/_reap.py::_FROB_TOKEN_RE at line 369 -- is out of scope
for T-2866 because src/frob/process/_reap.py is under T-2849's live
in-progress lease (a forkserver-leak bug fix, unrelated to documentation).

Once T-2849 lands (or its lease otherwise clears), this ticket:
  1. Writes the same individually-reasoned frob:waive COV007 comment on
     _FROB_TOKEN_RE, following the many-symbols-one-section shape
     (docs/modules/process.md's Forkserver reaping (T-2443) /
     Concurrent-check advisory (T-2473) sections cover several symbols in
     this file, not just this one -- confirm which anchor applies once
     _reap.py's current content is re-read post-T-2849, since that ticket
     may have moved lines).
  2. Re-measures `frob check --only coverage --json` unbudgeted and
     confirms COV007 is a TRUE ZERO (not just this file's own count).
  3. Promotes COV007 from WARN to ERROR in
     src/frob/gates/__init__.py::_cov007 (the `Violation(rule="COV007",
     severity=Severity.WARN, ...)` call around line 3341) -- COV007's own
     docstring does NOT forbid promotion (unlike COV006's permanent
     best-effort-resolver exemption), so this is safe once genuinely
     zero.
  4. Re-measures AGAIN after promoting and before landing -- promoting a
     WARN to ERROR can surface findings that were previously below some
     other gate's reporting threshold; this is the standing promotion
     discipline six agents have had to re-learn tonight (reverted
     promotions at counts of 1, 2, 3).
  5. Registers nothing new in `_KNOWN_GATE_RULES` -- COV007 is already
     registered there; only its severity mapping changes.

Acceptance: (0) zero COV007 warnings via the same command, confirmed
unbudgeted, (1) COV007 promoted from WARN to ERROR in
src/frob/gates/__init__.py, re-verified with a second unbudgeted
measurement after promotion.


frob:waive BUG002 reason="this ticket's real behavior change is a gate SEVERITY promotion (COV007 WARN to ERROR), not a defect a single-commit repro can express -- check-repro necessarily diffs a full commit against its parent, and any parent commit for this branch either predates the test-assertion update (old test/old code, trivially consistent) or predates the severity flip only (which would make the OLD test fail against NEW code, not a meaningful repro either way). The real evidence for this promotion is the unbudgeted frob check --only coverage --json re-measurement recorded in the Done report: COV007 warning-tier count 0 both before AND after promoting (a genuine true-zero, not a test-shaped defect)"