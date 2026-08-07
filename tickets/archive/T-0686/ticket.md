---
id: T-0686
title: 'python may-raise resolver: raise sites + callee propagation + builtin-raiser
  table, Unknown fail-closed'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0659
parent: T-0685
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestMayRaiseResolver::test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction
- tests/unit/test_arch.py::TestMayRaiseResolver::test_unresolvable_call_yields_unknown
- tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_reraise_resolves_to_caught_type
- tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_except_reraise_is_unknown
- tests/unit/test_arch.py::TestMayRaiseResolver::test_recursive_cycle_converges
- tests/unit/test_arch.py::TestMayRaiseResolver::test_ambiguous_method_name_across_classes_is_unresolved
designated_repro_test: null
acceptance:
- text: GIVEN a fixture chain f->g->h where h raises ValueError and g catches it and
    f calls dict subscript WHEN the resolver runs THEN f's may-raise is exactly {KeyError}
    plus the ubiquitous tier and a fixture with an unresolvable call yields Unknown
  evidence:
  - tests/unit/test_arch.py::TestMayRaiseResolver::test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction
threat: null
component: null
---
Child 1 of T-0685. Over the normalized model (NormalizedRaise/NormalizedCall) plus T-0659's sound Python name-binding: per-function may-raise = own raises (resolve the raised type where statically evident; bare raise re-raises the active set) + union of resolved callees' sets (fixpoint over the call graph, cycles converge) + builtin-raiser table for subscript/attribute/arithmetic/casts/io. Unresolved callee -> Unknown, fail-closed. except clauses SUBTRACT what they catch (mind exception hierarchies: except Exception catches ValueError). Async-ubiquitous tier (MemoryError/KeyboardInterrupt/SystemExit) tracked separately. Deliverable is the queryable analysis + tests on hand-built fixtures with known surfaces; gates/advisories are T-0688's job.