---
id: T-1746
title: Implement real fix for WIRE001 same-file test-fixture reuse false positive
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_tickets_mutation_evidence.py
- src/frob/gates/_wire.py
- tests/test_gates.py
- tickets/archive/T-1558/ticket.md
- src/frob/gates/_waive.py
- design/frob.strata
- tickets/T-1746/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: the T-1746 rule change (same-file test_* callers now count as reached) directly
    conflicts with test_test_helper_called_only_from_its_own_defining_file_is_still_flagged's
    locked-in old-behavior assertion; that test must be updated to match the new,
    intentionally more permissive rule
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-1558/ticket.md
  reason: T-1746 renamed the WIRE001 test T-1558's own evidence citation points at
    (test_test_helper_called_only_from_its_own_defining_file_is_still_flagged -> split
    into two tests reflecting the new same-file-test-caller rule); update the stale
    citation
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'COV002 leftover from T-1764''s own commit: _waive004_dead_count_by_rule
    needs its own frob:ticket edge'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'COV002 leftover from T-1764: gates node interface change needs its own
    frob:ticket edge'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1746/**
  reason: SCOPE001 flags the ticket's own ticket.md/done-report.md under v2 storage
    (same fix T-1719/T-1764 needed)
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestWireGate::test_test_helper_called_from_a_real_test_in_the_same_file_is_not_flagged
- tests/test_gates.py::TestWireGate::test_test_helper_called_only_from_a_non_test_helper_is_still_flagged
designated_repro_test: null
threat: null
component: null
---
`tests/test_tickets_mutation_evidence.py::_repo_with_add_change` carries
a `frob:waive WIRE001` (T-1727's own land) because WIRE001's same-file
exclusion rule (T-1592/T-1558's precedent: a test-tree symbol's OWN
defining file never counts as a "reached" caller, only a DIFFERENT test
file does) does not recognize a shared fixture helper reused by two
test classes within one file as wired, even though every call site is a
real `test_*` method, verifiable by reading the file directly.

Two ways to close this honestly:
1. Move `_repo_with_add_change` to a location a genuinely different
   test file could plausibly reuse (a shared fixtures module), so a real
   cross-file caller exists and the waiver can be dropped.
2. If same-file test-fixture reuse is a legitimate, common shape (it
   plausibly is -- DUP001 actively REQUIRES this exact extraction
   whenever two test classes in one file develop near-identical setup
   bodies), extend WIRE001's `_wire_test_path_excluded` same-file rule
   to also recognize a call from ANY `test_*`-prefixed function/method
   in the SAME file as a genuine reach class, not just cross-file reuse.

Either fix removes the T-1727 waiver's need to exist.

## Done report

Implemented the real fix for WIRE001's same-file test-fixture-reuse false
positive (T-1746's option 2): `_wire.py`'s same-file exclusion
(`_wire_test_path_excluded`) is no longer absolute for a test-tree
symbol. `_is_reached_outside_diff_tests` now also scans the symbol's OWN
defining file, but only counts a match as "reached" there when the call
site sits inside a genuine `test_*`-prefixed function/method
(`_enclosing_def_is_test_function`, a lightweight indentation-climbing
text scan -- deliberately not a full AST walk, matching this module's
existing bare-text-scan bias toward recall over precision). A helper
called only from another non-test helper in the same file, never from a
real test, still trips WIRE001 -- the genuinely-unwired case stays
caught.

This let T-1727's `frob:waive WIRE001 ... follow_up="T-1746"` on
`_repo_with_add_change` (tests/test_tickets_mutation_evidence.py) be
removed outright -- the gate itself no longer false-positives on it.

Split `_is_reached_outside_diff_tests`'s per-path scan body into
`_reached_in_file` and the exclusion/require-test-caller decision into
`_wire_scan_decision` to keep the parent function under ARCH001's
60-line threshold.

Updated `tests/test_gates.py::TestWireGate.
test_test_helper_called_only_from_its_own_defining_file_is_still_flagged`
(the test that locked in the OLD, now-superseded behavior) into two
tests: one confirming the new same-file-test-caller allowance, one
confirming the genuinely-unwired same-file case still fires. Fixed the
now-stale evidence citation in the archived T-1558 ticket that named the
old test by its old name.

Changed:
- src/frob/gates/_wire.py: _wire_test_path_excluded (docstring only, no
  behavior change to its own return value), _is_reached_outside_diff_tests
  (now delegates to two new helpers), _wire_scan_decision (new, private),
  _reached_in_file (new, private), _TEST_FUNC_DEF_RE/_ANY_FUNC_DEF_RE (new
  module constants), _enclosing_def_is_test_function (new, private)
- tests/test_gates.py: TestWireGate split test (see above)
- tests/test_tickets_mutation_evidence.py: removed the now-obsolete
  frob:waive WIRE001 on _repo_with_add_change
- tickets/archive/T-1558/ticket.md: fixed stale evidence citation

Evidence:
- tests/test_gates.py::TestWireGate.test_test_helper_called_from_a_real_test_in_the_same_file_is_not_flagged
- tests/test_gates.py::TestWireGate.test_test_helper_called_only_from_a_non_test_helper_is_still_flagged
- 29/29 tests/test_gates.py -k TestWireGate pass
- 18/18 tests/test_tickets_mutation_evidence.py pass

Gates: `uv run frob check --ticket T-1746` (FROB_NO_GATE_CACHE=1, fresh)
exit 0, every gate:* family passes. `uv run frob check --land-parity`
(fresh) reports clean (0 unscoped errors). ruff-check/format failures
present are pre-existing repo-wide debt in files this ticket never
touched, confirmed by re-checking after every edit.

### Changed
```
 design/frob.strata               |  38 ++++-----
 docs/modules/app.md              |  28 +++++++
 src/frob/_cli_parsers/_check.py  |  14 ++++
 src/frob/app/_config_external.py |   2 +
 src/frob/app/check_runner.py     |  77 ++++++++++++++++++
 src/frob/app/config.py           |   6 ++
 src/frob/gates/_waive.py         | 125 ++++++++++++++++++++++++++++
 tests/test_waive_gate.py         | 171 +++++++++++++++++++++++++++++++++++++++
 tickets/T-1746/ticket.md         |  42 +++++++++-
 tickets/T-1764/done-report.md    |  81 +++++++++++++++++++
 tickets/T-1764/ticket.md         |  67 ++++++++++++++-
 11 files changed, 629 insertions(+), 22 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1295 warning(s), 734 waived
- error-findings: none (measured, zero errors)
