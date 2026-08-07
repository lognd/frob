---
id: T-0420
title: 'frob check output: split the single gates line into named per-family stages
  + a gate summary; consistent coloring incl pre-summary warnings'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0410
tier: ticket
sprint: null
scope:
- src/frob/app/
- src/frob/check/
- tests/system/test_cli_check.py
- tests/unit/test_check.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/system/test_cli_check.py
  reason: T-0420's gate-family split changed the shape of _run_gates's return value
    and the [gates] diagnostic tag these two test files assert on; updating them to
    the new gate:<FAMILY>/gate-summary shape is part of implementing this ticket,
    not a separate change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_check.py
  reason: T-0420's gate-family split changed the shape of _run_gates's return value
    and the [gates] diagnostic tag these two test files assert on; updating them to
    the new gate:<FAMILY>/gate-summary shape is part of implementing this ticket,
    not a separate change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 requires bumping pyproject.toml's version + frob release stamp (.frob-release.json,
    uv.lock lockfile hash) whenever a ticket adds a public symbol (AppConfig.check_skip_unchanged,
    _ColorizedLevelFormatter) -- routine release bookkeeping for this ticket's change,
    not separate work
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 requires bumping pyproject.toml's version + frob release stamp (.frob-release.json,
    uv.lock lockfile hash) whenever a ticket adds a public symbol (AppConfig.check_skip_unchanged,
    _ColorizedLevelFormatter) -- routine release bookkeeping for this ticket's change,
    not separate work
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 requires bumping pyproject.toml's version + frob release stamp (.frob-release.json,
    uv.lock lockfile hash) whenever a ticket adds a public symbol (AppConfig.check_skip_unchanged,
    _ColorizedLevelFormatter) -- routine release bookkeeping for this ticket's change,
    not separate work
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_check.py::TestSummarySeverityHonesty::test_warn_only_gate_summary_splits_errors_and_warnings
- tests/unit/test_check.py::TestRunGatesDelta::test_no_baseline_falls_back_to_full_set_with_warning
designated_repro_test: null
threat: null
component: null
---
User UX asks (3 related output issues): (1) The pre-summary WARNING lines (PII010/SEC110/module-policy auto-inject) print as PLAIN uncolored log output while the pass/FAIL summary is colored -- make coloring consistent (or route these through the same formatter), TTY-aware (no ANSI in non-TTY). (2) The gates stage is ONE line with a timing blob [archgate=.. clones=.. coverage=.. ..]; SPLIT it into named per-family stage lines (like ruff-check/ruff-format/ty) -- TEST/COV/DRIFT/SCOPE/SEC/PII/PERF/SYS/DOC/... each its own pass/FAIL line with its count -- and a GATE SUMMARY (totals: N errors, M warnings, K waived) at the end. (3) De-dupe the reporting: frob-arch/frob-dup show as their own stages AND as archgate/clones inside the gates timing -- once T-0410-arch-double-run is fixed, ensure each is reported ONCE with a clear name. Goal: a human reads named stages + a clean summary, not a monolithic gates blob.