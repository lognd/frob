---
id: T-1084
title: 'arch: abstraction-opportunity arch package extraction (T-0393/T-1067 remainder,
  27 findings)'
state: dropped
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). After
T-1067's extraction pass (gitio/testing._runners `_excerpt`, vet package
TTL-cache helper), `src/frob/arch/**` itself carries 27 of the remaining
84 abstraction-opportunity findings: `_async_hazards.py` 3, `_concurrency.py`
1, `_concurrency_model.py` 2, `_cpp.py` 2, `_exceptions.py` 3,
`_fallibility.py` 1, `_kotlin.py` 8, `_ocp.py` 1, `_patterns.py` 3,
`_python.py` 1, `_solid.py` 1, `_typescript.py` 1.

Most of these are NOT the T-1068 language-parity shape (every member
carries a distinct language tag) -- `_is_language_parity_family` already
excludes those. What remains splits into two real classes worth
re-triaging file by file rather than assuming either uniformly:

1. Genuine coincidental-signature collisions across UNRELATED functions
   inside one file (e.g. `_async_hazards.py`'s 32-member `(Node) -> bool`
   group mixes `_is_async_def`, `_kt_has_override_modifier`,
   `_is_trivial_getter`, `_contains_splat`, and 28 others with no shared
   concern) -- these are large groups where at most a handful of members
   are truly duplicate logic; do NOT force a single extraction across an
   entire group just because the detector grouped them by signature.
2. Genuine per-language SHAPE duplication where the language tags are
   NOT all distinct (so T-1068's exclusion correctly does not apply) --
   e.g. `_kotlin.py`'s `_kt_build_class`/`_rust_build_class_shell`/
   `_ts_build_class`/`_ts_build_interface`/`_ts_build_enum` group has two
   `_ts_` members, meaning `_ts_build_class` and `_ts_build_interface`/
   `_ts_build_enum` really are three separate concerns colliding by
   signature only, not one language-parity family, and worth reading
   individually.

Read each group's actual member bodies before deciding extract vs.
accept-as-FP; do not batch-waive (abstraction-opportunity is unwaivable
by design). If a genuine new FP class turns up beyond what T-1068 already
covers (e.g. local nested-closure helpers -- `def walk(node): ...` defined
inside a larger function, recurring by trivial signature across
unrelated tree-walks -- observed in `frob.vet._capability`, may recur
here too), raise it as its own T-0370/T-1068-style detector-precision
ticket rather than hand-waiving it here.

Re-measure `uv run frob check --only arch --json` (filter to
abstraction-opportunity + `src/frob/arch/`) before starting; other
tickets may land in the interim and change the count.

## Failure log
- 2026-07-28 attempt 1: triage of all 27 groups found none safely extractable in src/frob/arch/ scope without reversing prior reviewed design decisions (T-0686) or fragmenting deliberate check-registry/per-language-mirror conventions; filed T-1112 for the one genuine detector-precision gap found

## Drop reason
- 2026-07-28: triage of all 27 groups (read every member body) found none safely extractable in src/frob/arch/ scope without reversing a prior reviewed design decision (T-0686) or fragmenting the deliberate check-registry/per-language-mirror conventions; the one genuine detector-precision gap found is filed separately, not this ticket's own extraction plan (absorbed by T-1112)