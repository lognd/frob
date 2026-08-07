---
id: T-1555
title: 'type-debt pass: clear all ty diagnostics (incl. signature drift in landed
  land-machinery) + ruff format/check backlog'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/refactor/_directives.py
- src/frob/refactor/_prose.py
- src/frob/strata/_mutation_audit.py
- tests/test_refactor.py
- tests/unit/test_check_native_cargo_runners.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: type-debt pass surface
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/refactor/_directives.py
  reason: type-debt pass surface
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/refactor/_prose.py
  reason: type-debt pass surface
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: type-debt pass surface
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_refactor.py
  reason: type-debt pass surface
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_check_native_cargo_runners.py
  reason: type-debt pass surface
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_refactor.py::TestDirectiveCarrier::test_attached_waiver_moves_with_symbol
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_kill_switch_disabled
designated_repro_test: null
acceptance:
- text: GIVEN uv run ty check src tests THEN 0 diagnostics, and GIVEN uv run ruff
    format --check and ruff check over src+tests THEN both clean, with all touched
    tests passing and frob check --land-parity at 0 unscoped errors
  evidence:
  - tests/test_refactor.py::TestDirectiveCarrier::test_attached_waiver_moves_with_symbol
  - tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file
  - tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_kill_switch_disabled
threat: null
component: null
---
Post-wave-4 full check reports the ty tool's diagnostics in ## Errors (26 gate-summary errors, 53 tool-level): includes REAL signature drift in freshly-landed code (_land_cmd.py:1630 _pre_commit_unscoped_error_sweep arg, :1965 _write_post_land_verify_marker arg -- wave-3/4 integration seams) plus accumulated debt in refactor/_directives, _prose, strata/_mutation_audit, tests/test_coverage.py (T-1516/17 signature evolution). Also owed: ruff-format ~34 files, ruff-check ~6. One dedicated quiet-window pass: fix every ty diagnostic properly (no type: ignore unless argued), run repo-wide ruff format + check --fix, verify affected tests, land.