---
id: T-1761
title: wire SYS109 (T-1627 stale via-symbol check) into frob sys audit
state: done
kind: invariant
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_audit.py
- src/frob/gates/_sys_selfaudit.py
- src/frob/strata/__init__.py
- src/frob/strata/_effects.py
- docs/modules/gates.md
- docs/strata/surface.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: SYS109/SELFAUDIT001 fold needs a regression test in the gate test module,
    same file every sibling SELFAUDIT001 sub-family test lives in
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_stale_via_symbol_violation
designated_repro_test: null
threat: null
component: null
---
T-1627 added symbol-form `via "path::qualname"` entries and an `exclusive`
grant trailer to the strata `may` grammar, plus a real detector for one of
the new failure modes: `frob.strata._effects.check_stale_via_symbols`
(SYS109, docs/strata/surface.md#may-scope) finds a symbol-form `via` entry
whose named symbol resolves to nothing under the node's own bound files
(renamed, moved, deleted, or mistyped).

The detector function and its model (`StaleViaSymbolViolation`) are built
and independently unit-tested (tests/unit/strata/test_effects.py::
TestStaleViaSymbol), but T-1627's own declared scope did not include
`src/frob/strata/_audit.py` / `frob.gates._sys_selfaudit` (the actual
`frob sys audit`/SELFAUDIT001 CLI wiring for SYS100-107) or
`src/frob/strata/__init__.py` (the package's public re-export list) --
both are needed to make SYS109 a real, run-by-default gate finding
instead of a function nothing outside its own tests calls.

Plan:
- Export `check_stale_via_symbols`/`StaleViaSymbolViolation` from
  `frob.strata`'s `__init__.py` alongside the sibling SYS100-108 checks.
- Call `check_stale_via_symbols` from wherever `_audit.py` (or
  `_sys_selfaudit.py`) already calls `check_capability_conformance`/the
  other `_selfconform.py` checks, folding its findings into the same
  `frob sys audit`/`frob check --only sys` surface under the SYS109 rule
  id `_selfconform.py`'s own module docstring already documents.
- Wire severity into `_sys_selfaudit._selfaudit_severity` if SYS109 needs
  a config-overridable tier (it does not appear to -- SYS109 is always
  ERROR per its own catalog entry -- confirm before assuming otherwise).
- Remove the now-obsolete `frob:waive WIRE001` this ticket leaves on
  `check_stale_via_symbols` once a real caller exists.

Scope: src/frob/strata/_audit.py, src/frob/gates/_sys_selfaudit.py,
src/frob/strata/__init__.py, src/frob/strata/_effects.py (waiver removal
only), docs/modules/gates.md (drop the "GAP" sentence on SYS109's row),
docs/strata/surface.md (drop the "GAP" paragraph in the T-1627 section).