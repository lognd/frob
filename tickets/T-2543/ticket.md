---
id: T-2543
title: 'may-raise resolver still mis-types two EXHAUST002 classes: subscript KeyError
  default and int()/float() TypeError'
state: in-progress
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
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
attachments:
- path: T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md
  caption: Class A options and measured costs (T-2377 survey)
  sha256: 5d4cb8185f3b1f412139a81355d1233321ce5055838014acafa1ef6fdb996bc4
acceptance:
- text: given a python function whose only subscript indexes a statically list-shaped
    value, when compute_may_raise resolves it, then the leaked set does not name KeyError
  evidence: []
- text: given a python function that calls int() on a statically str-typed value,
    when compute_may_raise resolves it, then the leaked set does not name TypeError
  evidence:
  - tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_int_does_not_contribute_type_error
- text: given this repo's own source, when the exhaustive_handling gate runs unbudgeted
    with the gate cache bypassed, then the EXHAUST002 count is below 25
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-2377's burn-down after T-2539 removed the two unambiguous
false-positive classes (tuple `except` clauses, slice subscripts). Those
took EXHAUST002 from 74 to 56 on this repo's own source. Triaging the
remaining 56 site by site found two MORE systematic classes where the
gate is wrong about the site -- but unlike T-2539's, neither has an
obviously-correct fix, so this is a decision ticket first and an
implementation second. Do not "fix" either by loosening the gate.

CLASS A -- the subscript `KeyError` default (34 of the remaining 56).
`frob.arch._mayraise` models EVERY index subscript as `KeyError`, a
disclosed default for the dict-shaped case (see that module's own
docstring). Most real sites here are LIST indexing inside a text scan
(`lines[lineno]`), which raises `IndexError`, never `KeyError` -- so the
gate names a type the site cannot raise, and the function's genuine
`IndexError` exposure goes unreported. Both directions are wrong.
Candidate directions, neither free:
  - Infer receiver shape where it is statically obvious (a name bound
    from `.splitlines()`/`.split()`/`list(...)`, or a param annotated
    `list[...]`/`Sequence[...]`) and pick `IndexError` there.
  - Model an ambiguous subscript as `LookupError` (the true common
    parent) instead of picking a child. This is more honest but strictly
    NOISIER as `_catches` stands: `except KeyError:` does not discharge a
    raised `LookupError`. It would need a matching "an ambiguous parent
    is discharged by catching any of its children" rule, which is itself
    a soundness relaxation and needs the explicit call.

CLASS B -- `int()`/`float()` TypeError on a provably-`str` argument
(14 of the remaining 56). `_BUILTIN_RAISERS` gives `int`/`float`
`{ValueError, TypeError}`. The dominant real shape is an env-var read:
`raw = os.environ.get(X)`, `if raw is None: return default`, then
`try: int(raw) except ValueError:`. `int(str)` cannot raise `TypeError`,
so the gate demands a handler for an impossible path -- and the site
already handles the possible one. Needs a narrow "the argument is
statically a `str`" test, or a decision to accept the noise.

Worked examples for both, all currently flagged:
  A: src/frob/gates/_wire.py::_reached_in_file (KeyError, transitively
     from a list index in `_enclosing_def_is_test_function`)
  B: src/frob/testing/_coverage_refresh.py::_max_workers_override
     (TypeError from `int(raw)` where `raw` is narrowed to `str`)

BLOCKS T-2377: EXHAUST002 cannot honestly reach zero while roughly half
its remaining corpus is the detector being wrong. Every one of those
sites, "fixed" at the source, would get a handler for an exception that
cannot occur -- or a catch-all, which is exactly what this gate family
exists to prevent.
