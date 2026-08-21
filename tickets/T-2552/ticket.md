---
id: T-2552
title: 'builtin-raiser table attributes impossible raises: int/float TypeError, getattr/next
  default-arg overloads'
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
- src/frob/arch/_mayraise.py
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_mayraise.py
  reason: the may-raise resolver builtin-raiser tables, their tests and docs
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_arch.py
  reason: the may-raise resolver builtin-raiser tables, their tests and docs
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/arch.md
  reason: the may-raise resolver builtin-raiser tables, their tests and docs
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_int_does_not_contribute_type_error
- tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_getattr_with_default_raises_nothing
- tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_next_with_default_raises_no_stop_iteration
designated_repro_test: tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_int_does_not_contribute_type_error
acceptance:
- text: given a function that calls int() or float(), when compute_may_raise resolves
    it, then the leaked set contains ValueError and not TypeError
  evidence:
  - tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_int_does_not_contribute_type_error
- text: given a function that calls getattr() with a default argument, when compute_may_raise
    resolves it, then the leaked set does not contain AttributeError, while the two-argument
    form still contributes it
  evidence:
  - tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_getattr_with_default_raises_nothing
- text: given a function that calls next() with a default argument, when compute_may_raise
    resolves it, then the leaked set does not contain StopIteration
  evidence:
  - tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_next_with_default_raises_no_stop_iteration
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: c1328b82a138b3684d6efdb408172f126a7909e9
---
Split out of T-2543 so that ticket's remaining criteria (Class A, the
subscript `KeyError` default, and the EXHAUST002 count target) stay
honest -- this is the Class B half plus two more of exactly the same
character, all landed together because they are all one table.

`frob.arch._mayraise._BUILTIN_RAISERS` attributed three exceptions to
calls that provably cannot raise them. Each fix is a SYNTACTIC test --
no type inference, and no special-casing of the one idiom the survey
happened to surface:

1. `int`/`float` -> `TypeError`. Raised only when the argument is not
   string/number-shaped AT ALL, which is a static type error, not a
   runtime input condition. Established by positive control, not
   assumption: `ty check` on a probe flags `int(raw)` where
   `raw: str | None` and `int({"a": 1})`, both `error[invalid-argument-
   type]`, and does NOT flag `int(raw)` once an `if raw is None: return`
   has narrowed it -- i.e. the type checker discriminates exactly the
   case this resolver cannot. `ty` is a gate inside `frob check` and its
   findings are ERROR severity (verified by dropping the probe into
   src/frob/ and reading `frob check --only ty --json`: 2 diagnostics,
   severity=error, exit=1). So the residual risk is not unowned; it is
   owned by a STRICTER gate. `ValueError` -- the real runtime condition
   -- stays, and all 26 affected sites already handled it.

2. `getattr(o, name, default)` -> `AttributeError`. The 3-positional-arg
   overload returns the default instead of raising.

3. `next(it, default)` -> `StopIteration`. The 2-positional-arg overload
   likewise.

(2) and (3) are `_DEFAULT_ARG_DISCHARGES`, keyed on bare callee name ->
the positional arity at which the default is present. `NormalizedCall.
args` already carried arity (T-0632), so no model change was needed. The
narrow forms (2-arg `getattr`, 1-arg `next`) are unaffected and still
contribute their raise -- covered by a must-still-fire assertion in the
same test.

MEASURED, unbudgeted, `FROB_NO_GATE_CACHE=1`:
  EXHAUST002  56 -> 47
  EXHAUST003 141 -> 141 (untouched by design)
Every `TypeError`, `AttributeError` and `StopIteration` mention is gone
from the family's messages; what remains is 40 `KeyError` (T-2543's
Class A) and 7 `ValueError`.