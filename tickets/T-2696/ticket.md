---
id: T-2696
title: Populate PII010/011/012 symref (dormant over-forgiveness hole, T-1666 successor)
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_pii_structural/**
- tests/test_pii_structural_gate.py
- tickets/T-draft-fae57bcc/**
evidence_scope:
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: tests exercising the new symref-population fix, plus the classify follow-up
    filed as part of this ticket's own work
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-draft-fae57bcc/**
  reason: tests exercising the new symref-population fix, plus the classify follow-up
    filed as part of this ticket's own work
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_pii_structural_gate.py::TestSymrefPopulation::test_class_field_symref_is_class_dot_none_shape
- tests/test_pii_structural_gate.py::TestSymrefPopulation::test_orm_column_inside_method_symref_is_nested_dotted
- tests/test_pii_structural_gate.py::TestSymrefPopulation::test_email_literal_inside_function_symref_is_function_name
- tests/test_pii_structural_gate.py::TestSymrefPopulation::test_keyword_sweep_identifier_symref_is_function_name
- tests/test_pii_structural_gate.py::TestSymrefPopulation::test_module_level_field_symref_is_none
- tests/test_pii_structural_gate.py::TestSymrefPopulation::test_enclosing_qualname_nested_method_is_dotted
- tests/test_pii_structural_gate.py::TestSymrefPopulation::test_enclosing_qualname_module_level_is_none
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Successor to T-1666's PERF/PII/SEC005 symref sweep (that ticket's own note:
"Needs the same live-waiver-population check T-1659 did for OPAQUE001/
CACHE001 before fixing").

Investigation (T-1666) found:

- PERF001-014: NOT this bug shape. `Violation.symref`'s own docstring
  (src/frob/gates/_models.py) explicitly names PERF as an intentionally
  file/module-scoped rule family alongside TEST005/TEST006 ("Left None for
  rules that are inherently file/module-scoped ... where a file-level
  waiver is the correct and intentional precision, not a shortcut"). No
  fix needed.

- SEC005 (src/frob/gates/_taint_gate.py): currently 0 live violations
  repo-wide (measured directly via `taint_gate(Path("."))`, 1208 tracked
  .py files scanned). No live waiver-population exposure exists to close
  right now.

- PII010/PII011/PII012 (src/frob/gates/_pii_structural/*.py): genuinely
  missing symref, same structural shape as CACHE001/OPAQUE001's dormant
  hole. Measured via `pii_structural_gate(Path("."))`: 93 raw violations,
  21 (rule, file) pairs carry 2+ violations under what is currently a
  single file-scope match -- real over-forgiveness exposure. Practical
  current impact is small (only 1 currently UNWAIVED PII012 error exists
  repo-wide after waiver matching -- tests/test_capability_registry.py:902
  -- everything else already nets correctly under the file-scope
  fallback), so this is a dormant hole shape, not an active incident.

Scope of the actual fix: thread per-violation enclosing-symbol resolution
(a GraphSnapshot-based symref lookup, mirroring src/frob/perf/_recursion.
py's own `_enclosing_symref` pattern -- NOT the same as PERF's docstring-
declared intentional file-scoping) through the 5 PII-structural violation
emitters (_crosslang.py, _emails.py, _env_access.py, _keywords.py,
_python_fields.py) so `Violation.symref` is set for PII010/011/012. This
is real engineering (new dependency: these scanners do not currently
receive a GraphSnapshot), not a re-waive task -- keep it out of any future
classification/re-waive ticket the way T-1659 (fix) and T-1666 (classify)
were kept separate here.

After symref is populated, re-run `pii_structural_gate` and re-triage any
newly-unwaived findings per-site (same discipline T-1666/T-1668 used for
OPAQUE001) -- do not blanket re-forgive.