---
id: T-1527
title: WIRE001 text-scan misses ErrorSet member-access wiring (no-paren false positive)
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestWireGate::test_new_errorset_class_referenced_by_bare_member_access_is_not_flagged
- tests/test_gates.py::TestWireGate::test_new_class_never_referenced_by_member_access_is_still_flagged
designated_repro_test: null
threat: null
component: null
---
WIRE001's _is_reached_outside_diff_tests text scan looks for a
`ShortName(` call-shaped occurrence to prove a diff-added symbol is
reached outside its own tests (src/frob/gates/_wire.py). A typani
ErrorSet subclass is never referenced this way -- callers spell it
`ClassName.Member` (bare attribute access, no parens) and the class
itself is only ever named in a `Result[..., ClassName]` type
annotation, also paren-free. A genuinely wired ErrorSet whose only
callable (the function that returns Result[_, ClassName]) has a real
external caller still trips WIRE001 on the ErrorSet class itself.
Found while working T-1516 (CoverageRefreshError in
src/frob/testing/_coverage_refresh.py): native_coverage_refresh is
called from _coverage_wait.py's _run_native_refresh, but
CoverageRefreshError itself has no call-shaped occurrence anywhere.
Teach the text scan an ErrorSet-member-access shape (ClassName\.[A-Za-z_]
or a `-> Result[..., ClassName]`/`Err(ClassName.` occurrence) the same
way T-1502 teaches it the wrapper-bare-name shape.