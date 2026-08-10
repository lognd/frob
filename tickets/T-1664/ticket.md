---
id: T-1664
title: Semantic checks must report UNRESOLVED, never silently pass when they cannot
  analyse
state: in-progress
kind: security
origin: human
created: '2026-08-06'
priority: high
blocked_by:
- T-1663
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/**
- src/frob/check/**
- src/frob/gates/_models.py
- src/frob/check/_python.py
- docs/modules/gates.md
- tests/unit/test_check_gates_summary.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'narrowed to the MVP structural mechanism: Severity.UNRESOLVED, its counting/rendering
    in check/_python.py, and doc/tests -- per-gate substrate declarations (item 2)
    are follow-up residue, not this ticket''s scope'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/**
  reason: 'narrowed to the MVP structural mechanism: Severity.UNRESOLVED, its counting/rendering
    in check/_python.py, and doc/tests -- per-gate substrate declarations (item 2)
    are follow-up residue, not this ticket''s scope'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tests/**
  reason: 'narrowed to the MVP structural mechanism: Severity.UNRESOLVED, its counting/rendering
    in check/_python.py, and doc/tests -- per-gate substrate declarations (item 2)
    are follow-up residue, not this ticket''s scope'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_models.py
  reason: 'narrowed to the MVP structural mechanism: Severity.UNRESOLVED, its counting/rendering
    in check/_python.py, and doc/tests -- per-gate substrate declarations (item 2)
    are follow-up residue, not this ticket''s scope'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/check/_python.py
  reason: 'narrowed to the MVP structural mechanism: Severity.UNRESOLVED, its counting/rendering
    in check/_python.py, and doc/tests -- per-gate substrate declarations (item 2)
    are follow-up residue, not this ticket''s scope'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/gates.md
  reason: 'narrowed to the MVP structural mechanism: Severity.UNRESOLVED, its counting/rendering
    in check/_python.py, and doc/tests -- per-gate substrate declarations (item 2)
    are follow-up residue, not this ticket''s scope'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_check_gates_summary.py
  reason: 'narrowed to the MVP structural mechanism: Severity.UNRESOLVED, its counting/rendering
    in check/_python.py, and doc/tests -- per-gate substrate declarations (item 2)
    are follow-up residue, not this ticket''s scope'
  actor: logan
  at: '2026-08-10'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The rule this drive learned the hard way, made structural.

Every serious incident in this drive traced to the same shape: an analysis layer that could not look, reporting that it found nothing, indistinguishable from a clean result.
- The perf gate reported ZERO PERF004 findings with stale natives while every health check said healthy -- the escape hatch it unlocked deleted 55 live frob:waive directives.
- A mypy oracle sharing .mypy_cache across xdist workers returned zero diagnostics for a file that had one.
- A suite run truncated before its summary line and read as success.
- The capability scanner returns an empty capability set for a language it has no pattern table for -- "no capabilities observed" and "I cannot analyse this language" are currently the same answer.

Requirement: when a semantic check CANNOT resolve, it must say so. An unresolved call target, an unparseable file, a missing language adapter, a stale analysis substrate -- each must produce an explicit UNRESOLVED/DEGRADED finding demanding a declaration or a waiver, never a silent pass.

Concretely:
1. A distinguished outcome in the gate result model separating "checked, found nothing" from "could not check". Today both collapse to an empty violation list.
2. Gates that depend on an optional substrate (natives, a language adapter, a resolver) declare that dependency and report degradation when it is absent -- the structural signal T-1620 asks for, generalised beyond perf.
3. `frob check` surfaces degraded stages in its summary line, so a run that could not analyse half the repo cannot read as a clean run.

This is the single highest-leverage item in the epic. Semantic checks FAIL DIFFERENTLY from lexical ones: a regex always produces an answer, while a resolver can genuinely not know -- so raising checks to semantics without this makes silent under-reporting MORE likely, not less. Sequence it early, ideally alongside the first (c)-class rewrite rather than after several.