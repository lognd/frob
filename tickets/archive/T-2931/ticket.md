---
id: T-2931
title: Generalize WIRE001's dynamic-dispatch exemption to recognize atexit.register
  callbacks
state: done
kind: feature
origin: human
created: '2026-08-25'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- src/frob/gates/_wire.py
- tests/unit/test_wire001_atexit_register.py
- tickets/T-3240/ticket.md
- src/frob/tickets/_unlanded.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_wire001_atexit_register.py
  reason: new must-fire/must-stay-quiet fixture file, plus the filed follow-up ticket's
    own ledger file
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-3240/ticket.md
  reason: new must-fire/must-stay-quiet fixture file, plus the filed follow-up ticket's
    own ledger file
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/tickets/_unlanded.py
  reason: must re-point the frob:waive WIRE001 follow_up citation off T-2931 onto
    its successor before close (LiveTrackerCited)
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: 'T-4770: preserve regex-lookbehind detail trimmed from _wire.py'
  actor: logan
  at: '2026-09-19'
  old_length: 876
  new_length: 1604
evidence:
- tests/unit/test_wire001_atexit_register.py::TestWire001AtexitRegister::test_function_registered_via_atexit_is_not_flagged
- tests/unit/test_wire001_atexit_register.py::TestWire001AtexitRegister::test_function_with_no_caller_anywhere_still_flagged_positive_control
- tests/unit/test_wire001_atexit_register.py::TestWire001AtexitRegister::test_class_registered_via_atexit_still_flagged_anchor_control
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0e3a0c5eba169046c1cb63f685496059a60ad133
---
`_unlanded.py::_remove_scratch_file`'s only caller is `atexit.register(_remove_scratch_file, path)` inside `_scratch_file_for_suffix` (T-2645) -- a dynamic registration WIRE001's call-graph resolver structurally cannot see, the same class of gap this repo already carved a named exemption for (`frob.gates._waive._WIRE001_RESCUE_EXEMPT_RULE`, covering autouse pytest fixtures and pydantic validators).

Generalize that exemption (or add a sibling one) to recognize `atexit.register(<callback>, ...)` as a valid dynamic-dispatch pattern, so a genuinely-only-atexit-called private function does not need a per-site `frob:waive WIRE001 follow_up=...` that requires perpetually pointing at SOME open ticket forever.

Scope: src/frob/gates/_waive.py (the exemption predicate), src/frob/gates/_wire.py (the WIRE001 gate itself, if the exemption needs to be consulted there instead).


T-4770 follow-up (condensed from _DOTTED_WRAPPER_MARKERS's docstring in
src/frob/gates/_wire.py, trimmed for DOCARCH002's 12-line cap): the
concrete example is _scratch_file_for_suffix's registration of
_remove_scratch_file. _WRAPPER_MARKER_NAMES covers
memoize_per_run(_target)-shaped wrapper markers; _wire_reach_patterns'
wrapper_pattern matches them as a BARE name immediately before `(` --
(?<![A-Za-z0-9_.])'s negative lookbehind explicitly excludes a
dot-preceded match, so a bare "register" alternative would either miss
atexit.register( entirely or false-positive on any OTHER object's
unrelated .register( method sharing the bare name. The qualifier is
"atexit", producing the exact alternative atexit\.register\(.