---
id: T-2894
title: extend frob_core.py_function_metrics to carry exception_types/is_slice natively
  (unblocks T-2799)
state: queued
kind: feature
origin: human
created: '2026-08-25'
priority: medium
parent: T-2790
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob-core/src/arch_python.rs
- frob-core/frob_core.pyi
- tests/unit/test_arch_python_native.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2799 (wire frob_core.py_function_metrics into archgate's per-function
metrics walk) measured a net SLOWDOWN when wired as scoped (attempt 1,
2026-08-21, 6+ trials per side, alternating order): native-ON 27-45s vs
native-OFF 21-30s. Root cause, confirmed again on 2026-08-25 by reading
both sides directly:

- `frob_core.py_function_metrics`'s `catches` entries are
  `(line, exception_type: str | None)` -- ONE type per `except` clause
  (frob-core/src/arch_python.rs:283, `except_exception_type`).
  `frob.arch._normalized.NormalizedCatch` needs BOTH `exception_type`
  (single, representative) AND `exception_types` (the full tuple --
  T-2539's own fix, `_py_except_exception_types` in
  src/frob/arch/_python.py) so a multi-type `except (A, B):` clause does
  not silently read as catching only `A` downstream in
  `frob.arch._mayraise._catches`/EXHAUST002. The native kernel drops
  every member after the first.
- `frob_core.py_function_metrics`'s `subscripts` entries are bare `line:
  int` (frob-core/src/arch_python.rs:284/338). `NormalizedSubscript`
  needs `is_slice: bool` (T-2539: a slice-only subscript like `d[1:2]`
  cannot raise `KeyError`/`IndexError`, so the may-raise resolver must
  not treat it the same as `d[k]`). The native kernel does not carry
  this at all.

Because both fields feed real may-raise resolution (not cosmetic), any
caller dispatching to the native kernel must run a compensating
Python-side walk to backfill `exception_types`/`is_slice` for every
catch/subscript event. That compensating walk plus the PyO3 marshalling
of every event into fresh Python objects measured as MORE expensive
than the pure-Python walk it was meant to replace -- this is the
mechanism behind attempt 1's measured slowdown, not a fluke or fleet
noise.

## Scope

`frob-core/src/arch_python.rs` (the `py_function_metrics` extraction
walk and its `catches`/`subscripts` collection), `frob-core/frob_core.
pyi` (the return-shape docstring), plus T-1222's golden/parity tests
that pin the exact tuple shape (`tests/unit/test_arch_python_native.py`
and its golden fixtures) -- widen `catches` to `(line,
exception_type: str | None, exception_types: tuple[str, ...])` and
`subscripts` to `(line: int, is_slice: bool)`, matching
`_py_except_exception_types`/the T-2539 slice-only subscript rule on
the Python side exactly (byte-identical output is the acceptance bar,
same as T-1222's own).

## Acceptance

- `py_function_metrics`'s `catches`/`subscripts` shapes carry
  `exception_types`/`is_slice` natively -- no compensating Python-side
  walk needed to backfill either field.
- Byte-identical `NormalizedModule` output vs. the pure-Python path
  across the same corpora T-1222/T-2799 attempt 1 used (multi-except
  clauses, slice and non-slice subscripts included).
- Unblocks T-2799: re-measure wiring `py_function_metrics` into
  `_py_build_function`/`_py_build_module` with the SAME A/B methodology
  attempt 1 used (6+ trials per side, alternating order) once this
  lands -- do not assume it wins without re-measuring.
