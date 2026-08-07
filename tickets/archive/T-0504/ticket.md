---
id: T-0504
title: 'class-directive placement lint (T-0470 prong 2): detect a nearby symbol the
  directive plausibly SHOULD have bound to, not raw line distance'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestPlace001Gate::test_missed_following_binding_fires
- tests/test_gates.py::TestPlace001Gate::test_per_field_pydantic_idiom_is_silent
- tests/test_gates.py::TestPlace001Gate::test_directive_directly_above_def_is_silent
- tests/test_gates.py::TestPlace001Gate::test_no_nearby_symbol_at_all_is_silent
designated_repro_test: null
threat: null
component: null
---
PLACE001 was prototyped in T-0470 and deliberately dropped: distance-from-class-start fires on the legitimate per-field frob:waive idiom inside large pydantic config classes (fields are not RawSymbols, so directives above them always class-fallback by construction -- e.g. AppConfig's SCOPE001 waiver 150+ lines past the class line). A sound signal must instead detect a nearby symbol the directive plausibly should have bound to via 'following' but did not reach. Counterexample preserved in the comment above src/frob/gates/__init__.py's dropped-PLACE001 note (near line 961). Scope: src/frob/gates/__init__.py, tests/test_gates.py.