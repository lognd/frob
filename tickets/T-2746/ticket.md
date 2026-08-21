---
id: T-2746
title: WIRE001 cannot see a @property's own attribute-access caller (false positive)
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
- src/frob/gates/_wire.py
- tests/unit/test_wire001_property_attribute_access.py
- src/frob/cycle/graph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/test_wire.py
  reason: correct test path to match this repo's actual per-shape WIRE001 test file
    convention (tests/unit/test_wire001_*.py), tests/test_wire.py does not exist
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_wire001_property_attribute_access.py
  reason: correct test path to match this repo's actual per-shape WIRE001 test file
    convention (tests/unit/test_wire001_*.py), tests/test_wire.py does not exist
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/cycle/graph.py
  reason: 'close blocker: LiveTrackerCited on graph.py''s WIRE001 waiver whose follow_up
    cites this ticket; measurement confirms the waiver is now redundant post-fix,
    must remove it in this ticket''s own scope to close'
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: BUG002 refuses because the fix already landed as a sibling passenger before
    this ticket's own land; waiving with a measured, cited explanation rather than
    forcing a fake re-fail/re-pass cycle for a defect already proven fixed
  actor: logan
  at: '2026-08-20'
  old_length: 1234
  new_length: 1903
evidence:
- tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_via_attribute_access_is_not_flagged
- tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_with_no_caller_anywhere_still_flagged_positive_control
- tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_ordinary_new_method_still_flagged_positive_control
designated_repro_test: tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_via_attribute_access_is_not_flagged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
WIRE001's text-scan reach check (`frob.gates._wire._wire_reach_patterns`)
only recognizes call-shaped (`short(`) and by-reference (wrapper marker
/ dict-table value / ErrorSet member-access) usages of a newly-added
symbol. A `@property`'s only legal Python access shape is attribute
access with NO trailing parens (`graph.degraded_languages`, never
`graph.degraded_languages()`), which none of the existing patterns
match -- so any brand-new `@property` on a class gets a WIRE001 false
positive on its very first real, non-test caller, forcing a waiver
every time rather than the gate correctly recognizing it as reached.

Observed concretely at `DependencyGraph.degraded_languages`
(src/frob/cycle/graph.py, T-2700): `find_cycles` in the SAME file reads
it via plain attribute access one line below the property's own
definition, and WIRE001 still fired.

Scope: teach `_wire_reach_patterns`/`_is_reached_outside_diff_tests` a
property-shaped alternative (bare `short` NOT followed by `(` or other
call-token, gated on `record.kind == SymbolKind.METHOD` plus a way to
tell "this method is decorated `@property`" from the snapshot/AST) so a
genuine attribute-access caller of a new property counts as reached
without needing a waiver.

frob:waive BUG002 reason="the designated repro test passes at this land's parent commit because the actual defect fix (_is_property/_PROPERTY_DECORATOR_RE/property_access_pattern in src/frob/gates/_wire.py) already rode onto main as a passenger of a sibling ticket's land before this ticket's own land ran -- confirmed via git log/git show on main, not assumed; this land's own diff is the follow-on cleanup (removing the now-redundant WIRE001 waiver at src/frob/cycle/graph.py, measured directly at that site with the waiver removed: zero WIRE001 findings) needed only to satisfy the LiveTrackerCited close blocker, not a re-fix of the original defect" follow_up=""