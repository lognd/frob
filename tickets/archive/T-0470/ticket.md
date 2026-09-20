---
id: T-0470
title: 'waiver over-breadth + class-ignore placement lint: (1) _match_waiver matches
  symref-LESS (file-scoped) findings by file OR package-PREFIX, so one frob:waive
  can suppress broadly; (2) warn when a class-bound frob:waive/directive is not at
  the class top (likely mis-scoped)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0470 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
body_changes:
- mode: append
  reason: moving DOCARCH001 change-narrative out of the test docstring per T-4420
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 751
- mode: append
  reason: 'T-4770: preserve AppConfig example and test-proof detail trimmed from _waive_comments.py'
  actor: logan
  at: '2026-09-19'
  old_length: 751
  new_length: 1395
evidence:
- tests/gates_suite/test_test_gate.py::TestTestGate::test_waive003_flags_waiver_reaching_multiple_packages
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_test_gate.py::TestTestGate.test_match_waiver_prefix_reach_gated_to_package_scoped_rules's docstring used to say: 'T-0470 counterexample: BEFORE this fix, _match_waiver's directory-prefix branch ran for every symref-less violation regardless of rule -- any rule whose violation.file happened to be directory-shaped (no extension) inherited unbounded prefix reach it was never reviewed for. A non-package-scoped rule (i.e. not in _PACKAGE_SCOPED_RULES) with a directory-shaped file must now match ONLY a waiver whose own site is that exact file/directory string -- never a waiver nested somewhere under it via the prefix fallback.' Moved here; the test docstring now states only what it verifies.


T-4770 follow-up (condensed from _PLACE001_LOOKAHEAD's comment block in
src/frob/gates/_waive_comments.py, trimmed for DOCARCH002's 12-line
cap): the concrete example is src/frob/app/config.py's AppConfig,
`frob:waive SCOPE001` at line 212, 150+ lines past the class's
`class AppConfig:` line (only FUNCTION/METHOD/CLASS/CONST/TYPE are
RawSymbols). See _place001_missed_symbol's docstring for the full
argument and TestPlace001Gate for both the non-vacuous positive (a
directive separated from its intended def by one blank line too many)
and the AppConfig-shaped negative (a directive above a field, real
code before the next real method).