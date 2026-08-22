---
id: T-2539
title: may-raise resolver reports false EXHAUST002 leaks for multi-type except clauses
  and slice subscripts
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_normalized.py
- src/frob/arch/_python.py
- src/frob/arch/_mayraise.py
- src/frob/gates/_exhaustive_handling.py
- docs/modules/arch.md
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_normalized.py
  reason: the may-raise resolver, its python adapter, the exhaustiveness gate consuming
    it, their docs and tests
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/arch/_python.py
  reason: the may-raise resolver, its python adapter, the exhaustiveness gate consuming
    it, their docs and tests
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/arch/_mayraise.py
  reason: the may-raise resolver, its python adapter, the exhaustiveness gate consuming
    it, their docs and tests
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_exhaustive_handling.py
  reason: the may-raise resolver, its python adapter, the exhaustiveness gate consuming
    it, their docs and tests
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/arch.md
  reason: the may-raise resolver, its python adapter, the exhaustiveness gate consuming
    it, their docs and tests
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_arch.py
  reason: the may-raise resolver, its python adapter, the exhaustiveness gate consuming
    it, their docs and tests
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_arch.py::TestCaughtTypeNames::test_tuple_clause_reports_every_member
- tests/unit/test_arch.py::TestCaughtTypeNames::test_python_adapter_records_every_tuple_member
- tests/unit/test_arch.py::TestCaughtTypeNames::test_tuple_except_discharges_every_member
- tests/unit/test_arch.py::TestSliceSubscriptRaisesNothing::test_python_adapter_marks_slice_subscripts
- tests/unit/test_arch.py::TestSliceSubscriptRaisesNothing::test_slice_only_function_leaks_no_key_error
designated_repro_test: tests/unit/test_arch.py::TestSliceSubscriptRaisesNothing::test_python_adapter_marks_slice_subscripts
acceptance:
- text: given a python function whose sole handler is a multi-type `except (A, B):`,
    when compute_may_raise resolves it, then no member of the tuple appears in the
    leaked set
  evidence:
  - tests/unit/test_arch.py::TestCaughtTypeNames::test_tuple_clause_reports_every_member
  - tests/unit/test_arch.py::TestCaughtTypeNames::test_python_adapter_records_every_tuple_member
  - tests/unit/test_arch.py::TestCaughtTypeNames::test_tuple_except_discharges_every_member
  - tests/unit/test_arch.py::TestSliceSubscriptRaisesNothing::test_python_adapter_marks_slice_subscripts
  - tests/unit/test_arch.py::TestSliceSubscriptRaisesNothing::test_slice_only_function_leaks_no_key_error
- text: given a python function whose only subscript is a slice, when compute_may_raise
    resolves it, then KeyError is not in the leaked set
  evidence:
  - tests/unit/test_arch.py::TestCaughtTypeNames::test_tuple_clause_reports_every_member
  - tests/unit/test_arch.py::TestCaughtTypeNames::test_python_adapter_records_every_tuple_member
  - tests/unit/test_arch.py::TestCaughtTypeNames::test_tuple_except_discharges_every_member
  - tests/unit/test_arch.py::TestSliceSubscriptRaisesNothing::test_python_adapter_marks_slice_subscripts
  - tests/unit/test_arch.py::TestSliceSubscriptRaisesNothing::test_slice_only_function_leaks_no_key_error
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 8a93de7c083453b38d57cfce25fa8ef0c8c4da1a
---
Found while burning EXHAUST002 down for T-2377. Two independent modeling
defects in `frob.arch._mayraise`'s inputs made the exhaustiveness gate
demand a handler for an exception the source provably cannot raise --
the worst false-positive direction, because the cheapest way to satisfy
it is a blanket `except Exception:` that hides the real error classes the
gate exists to surface.

1. MULTI-TYPE EXCEPT CLAUSE. `frob.arch._python._py_except_exception_type`
   resolved `except (A, B):` to its FIRST member only (its own docstring
   says so), and `NormalizedCatch` has one `exception_type` field to hold
   it. Every consumer asking "does this function catch T?" therefore
   answered NO for every member after the first. `except (OSError,
   ValueError):` read as catching `OSError` alone, so `ValueError` -- and,
   via `_EXCEPTION_PARENT`, `JSONDecodeError` -- were reported escaping.

2. SLICE SUBSCRIPT. `_py_collect_body_events` records every `subscript`
   node as a `NormalizedSubscript`, and `_resolve_call_contributions`
   gives each one the curated dict-index `KeyError` default. A slice
   (`lines[start + 1 :]`) clamps out-of-range bounds on every builtin
   sequence -- it cannot raise `KeyError` or `IndexError` at all.

Measured on this repo's own source, unbudgeted, cache-bypassed:
EXHAUST002 74 -> 69 (fix 1) -> 56 (fix 2). EXHAUST003 unchanged at 141.