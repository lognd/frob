---
id: T-2720
title: 'COV005: reduce false positives on brand-new private helpers sharing a directive
  anchor'
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_coverage_sites.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: test fixture required by the ticket itself (BEFORE-fixture-then-narrow discipline);
    COV005 false-positive/must-still-fire coverage lives here alongside the existing
    TestCoverageGate class
  actor: logan
  at: '2026-08-20'
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov005_directive_rebound_to_private_symbol_flags
- tests/test_gates.py::TestCoverageGate::test_cov005_same_symbol_no_rebind_is_clean
- tests/test_gates.py::TestCoverageGate::test_cov005_no_old_blob_is_clean
- tests/test_gates.py::TestCoverageGate::test_cov005_new_private_helper_sharing_anchor_with_undisturbed_public_is_clean
designated_repro_test: tests/test_gates.py::TestCoverageGate::test_cov005_new_private_helper_sharing_anchor_with_undisturbed_public_is_clean
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed while working T-1614's periodic waive-audit pass (scan batch
watermark-commit=None, catchup window items 13-30,32,33 in
.claude/hooks/root-write-guard.py).

COV005 (src/frob/gates/__init__.py::_cov005/_cov005_file) flags a
frob:doc/frob:tests/frob:ticket directive that bound a PUBLIC symbol at
diff.base but now binds a PRIVATE symbol whose span overlaps the diff's
hunks -- meant to catch a directive silently riding onto a newly
extracted helper (T-0297: caught real bugs in scan_tree/renumber_one).

18 individual frob:waive COV005 directives found in this batch alone (all
in .claude/hooks/root-write-guard.py, one file), plus 5 more already
waived elsewhere (src/frob/gates/_coverage_sites.py, T-1943), all citing
the SAME root cause: a brand-new private helper added near an existing
public def picks up a (kind, target) key already used by some unrelated
PUBLIC symbol elsewhere in the same file (this repo's own convention of
reusing one frob:doc anchor across every public function a doc page
covers, already called out in _cov005's own docstring as a known source
of noise) -- not an actual rebind of an existing directive onto a new
symbol. 23 total site waivers, same reason, across at least 2 files and
several tickets (T-1943, T-2481, T-2487) -- a growing, unbounded count
under the current design, not a shrinking one.

Every individual waiver reviewed in T-1614's audit is honest (each
verified as a genuinely brand-new private helper, not a rebind of a
real pre-existing directive) -- this is not a cop-out, it is a detector
precision gap worth narrowing at the source instead of continuing to
accumulate per-site waivers.

Proposed direction (needs real investigation, not assumed): tighten
_cov005_file's rebind detection so a NEW symbol is only flagged when the
OLD public symbol's own span is GONE/renamed at the new revision (i.e.
the specific public def the directive used to sit on has disappeared or
shrunk to make room for the new private helper) rather than merely
"some symbol somewhere in the file used to hold this (kind, target) key
publicly." Do not weaken the check for the real T-0297 case (a directive
literally riding from a deleted/renamed public function onto a
newly-extracted helper) -- add a test fixture reproducing the current
false-positive shape (new unrelated private helper inserted near an
existing public def that shares an anchor with a different, undisturbed
public symbol) alongside the existing rebind-must-still-fire fixtures
before narrowing anything.