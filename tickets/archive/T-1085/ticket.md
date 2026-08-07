---
id: T-1085
title: 'arch: abstraction-opportunity app package extraction (T-0393/T-1067 remainder,
  5 findings)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/_snapshot.py
- src/frob/app/debt_runner.py
- src/frob/app/deprecated_runner.py
- src/frob/app/release_runner.py
- src/frob/app/perf_runner.py
- tests/test_debt_runner.py
- tests/test_deprecated_runner.py
- tests/test_perf_runner.py
- docs/modules/app.md
- tests/unit/test_app_runners_batch5.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_snapshot.py
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/debt_runner.py
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/deprecated_runner.py
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/release_runner.py
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/perf_runner.py
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_debt_runner.py
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_deprecated_runner.py
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_release_runner.py
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_perf_runner.py
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/app.md
  reason: 'T-1085: narrow scope to the exact app/ files touched (app/ contended this
    wave with T-1106 daemon + tickets agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: src/frob/app/
  reason: 'T-1085: narrow off the broad src/frob/app/ glob now that the exact touched
    files are scoped explicitly -- app/ is contended this wave (T-1106 daemon, tickets
    agent''s ticket_runner.py)'
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: tests/test_release_runner.py
  reason: 'T-1085: tests/test_release_runner.py does not exist; the real release_runner
    tests live in tests/unit/test_app_runners_batch5.py::TestReleaseRunner'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_app_runners_batch5.py
  reason: 'T-1085: tests/test_release_runner.py does not exist; the real release_runner
    tests live in tests/unit/test_app_runners_batch5.py::TestReleaseRunner'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_debt_runner.py::TestDebtRunner::test_json_mode_lists_debt_entries
- tests/test_deprecated_runner.py::TestDeprecatedRunner::test_json_mode_lists_deprecated_entries
- tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_snapshot_build_graph_err_exits_1
- tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_success_writes_manifest
designated_repro_test: null
threat: null
component: null
---
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). Of the
84 remaining abstraction-opportunity findings, `src/frob/app/**` carries 5:
`check_runner.py` 2 groups (`_skip_note_result`/`_missing_tool_result`/
`tool_unavailable_result`/`tool_disabled_result`/`parse_junit_xml` sharing
`(str, str) -> ToolResult`; `_deploy_drift_result`/`_deploy_conformance_result`/
`_derived_state_integrity_result`/`_run_clang_format`/`_run_cargo_fmt_check`/
`_run_cargo_valgrind`/`_run_bind` sharing `(Path) -> ToolResult | None`),
`debt_runner.py` 1 (`_load_snapshot`/`_load_snapshot`/`_snapshot` sharing
`(Path)` -- note the duplicate NAME within the group, worth checking for a
literal same-file duplicate first), `deploy_runner.py` 1
(`_design_dir`/`_design_dir`/`_read_ledger_text_or_empty`/
`_read_archive_text_or_empty` sharing `(Path) -> str` -- again a repeated
name), `perf_runner.py` 1 (`_heat`/`_collect` sharing `(AppConfig) -> None`).

The `check_runner.py` `ToolResult`-builder groups look like the most
promising genuine extraction (several near-identical "build a skip/
unavailable/disabled ToolResult with this message" constructors); the
`debt_runner.py`/`deploy_runner.py` groups with a repeated function name
inside one group are worth checking FIRST for a literal same-file
duplicate (two defs with the same name, one shadowing the other, possibly
dead code) before assuming they're two genuinely distinct functions that
happen to collide.

Re-measure `uv run frob check --only arch --json` (filter to
abstraction-opportunity + `src/frob/app/`) before starting; other tickets
may land in the interim and change the count.