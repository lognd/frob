---
id: T-0916
title: 'docs: document the Python may-raise resolver in docs/modules/arch.md'
state: done
kind: docs
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/arch.md
- src/frob/arch/_mayraise.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_mayraise.py
  reason: repointing frob:doc directives requires editing this file per ticket body
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/unit/test_arch.py
  reason: evidence file for T-0686's already-existing may-raise resolver tests
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/test_arch.py::TestMayRaiseResolver::test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction
- tests/unit/test_arch.py::TestMayRaiseResolver::test_unresolvable_call_yields_unknown
- tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_reraise_resolves_to_caught_type
- tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_except_reraise_is_unknown
- tests/unit/test_arch.py::TestMayRaiseResolver::test_recursive_cycle_converges
- tests/unit/test_arch.py::TestMayRaiseResolver::test_ambiguous_method_name_across_classes_is_unresolved
designated_repro_test: null
threat: null
component: null
---
T-0686 added `src/frob/arch/_mayraise.py` (the Python may-raise resolver:
compute_may_raise, FunctionMayRaise, UNKNOWN, UBIQUITOUS_TIER) plus
NormalizedSubscript on the shared T-0609 model, both within
src/frob/arch/**'s own scope. docs/modules/arch.md is out of T-0686's
declared scope (scope=['src/frob/arch/**', 'tests/unit/test_arch.py']),
so no doc section/anchor was added for these new public symbols; DOC002/
COV001 gate findings on src/frob/arch/_mayraise.py are waived pending
this ticket. Add a "may-raise resolver" section documenting
compute_may_raise/FunctionMayRaise/UNKNOWN/UBIQUITOUS_TIER's contract and
its relationship to the T-0623 fallibility-checks family, then update the
frob:doc anchors on _mayraise.py to point at it and drop the waivers.