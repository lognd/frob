---
id: T-2322
title: 'T-2303 child: split ARCH001/ARCH103 over-threshold functions in _land_cmd.py
  (land-critical, high regression risk)'
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: T-2303
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/telemetry.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_new.py
evidence_scope:
- tests/unit/test_land_auto_rebase.py
- tests/test_telemetry.py
- tests/unit/test_ticket_new_scope_plausibility_t2192.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: probe scope/lease status
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_merges_the_worktree_onto_the_new_main_tip
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_squash_then_rebase_conflicts_but_merge_does_not
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land
- tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
- tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all
- tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_wrong_file_now_warns
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3db9fbe21299af22b451c7526b4adc04d18cfc17
---
Child of T-2303 (parent scope: ARCH001/ARCH103/PERF004/SELFAUDIT001 debt
found by T-2206's sweep). This is the ARCH001/ARCH103 piece.

LAND-CRITICAL, HIGH-REGRESSION-RISK: every one of these findings is in
`src/frob/app/ticket_runner/_land_cmd.py`, the file `frob ticket land`
itself runs on every single land in this repo (docs/guides/agent-
playbook.md section 13 measures it as the single largest, most
frequently-touched file in the land critical path). A regression here
does not fail one ticket -- it can stall or corrupt every concurrent
agent's land, fleet-wide. This needs a dedicated, careful pass with its
own thorough test coverage BEFORE and AFTER any split, not a quick
mechanical fix. Do not attempt this opportunistically inside another
ticket's scope.

FINDINGS (measured against the tree as of T-2206's sweep; re-measure
`frob check --only archgate` before starting, since line numbers will have
moved):

- ARCH001 `src/frob/app/telemetry.py::_home_config_state_hash` -- 72 lines
  (threshold 60)
- ARCH001 `src/frob/app/ticket_runner/_land_cmd.py::_auto_sync_worktree_onto_main`
  -- 151 lines (threshold 60)
- ARCH001 `src/frob/app/ticket_runner/_land_cmd.py::_land` -- 120 lines
  (threshold 60)
- ARCH001 `src/frob/app/ticket_runner/_land_cmd.py::_new_public_symbols_missing_doc_or_test_edge`
  -- 62 lines (threshold 60)
- ARCH001 `src/frob/app/ticket_runner/_new.py::_scope_plausibility_file_words`
  -- 68 lines (threshold 60)
- ARCH103 `src/frob/app/ticket_runner/_land_cmd.py::_assert_new_public_symbols_have_doc_and_test_edge_pre_land`
  -- mixes I/O, string-formatting, and 4 decision points in one body
- ARCH103 `src/frob/app/ticket_runner/_land_cmd.py::_long_function_symrefs_over_threshold_at_merge_base`
  -- mixes I/O, string-formatting, and 2 decision points in one body

APPROACH GUIDANCE (not prescriptive -- the assigned agent should verify):
extract each over-threshold function's distinct phases into named private
helpers (the pattern this repo already uses throughout `_land_cmd.py`
itself, e.g. `_perf_gate_parse_files`/`_relativize_perf_violation_file`
alongside `perf_gate` in `src/frob/gates/__init__.py`, landed by T-2314 as
a much smaller-scale precedent) -- never collapse logic or change
behavior. Each extraction needs its own test coverage (new `frob:tests`
edges) and the WHOLE existing `_land_cmd.py`/`_new.py`/`telemetry.py` test
suites must stay green before landing, not just the touched functions'
own tests (an import retarget silently breaks `mock.patch` targets in
files a diff never touches -- confirmed twice in one session per this
repo's own playbook memory).

Cross-reference: T-2314 (landed) fixed the SEPARATE PERF gate waiver
defect this same T-2206 sweep also flagged in `_land_cmd.py` -- unrelated
to this ARCH work, do not conflate.

Scope: src/frob/app/telemetry.py, src/frob/app/ticket_runner/_land_cmd.py,
src/frob/app/ticket_runner/_new.py.