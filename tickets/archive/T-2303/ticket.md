---
id: T-2303
title: ARCH001/ARCH103/PERF004/SELFAUDIT001 debt in _land_cmd.py, telemetry.py, _new.py,
  design (found by T-2206 sweep)
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/telemetry.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_rapid_sweep.py
evidence_scope:
- tests/test_telemetry.py
- tests/unit/test_new_ticket_scope_overlap_warning.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: design
  reason: collides with T-1656's live lease on design/frob.strata; SELFAUDIT001 design
    debt split out, not fixed in this pass
  actor: logan
  at: '2026-08-19'
body_changes:
- mode: append
  reason: 'BUG002 waiver: fix already landed onto main as a passenger of T-1549''s
    own land; repro test structurally cannot fail at parent any more'
  actor: logan
  at: '2026-08-20'
  old_length: 2324
  new_length: 3092
evidence:
- tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
- tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_corrupt_row_is_named_loudly_not_silently_coerced
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Genuine, currently-reproducing findings from T-2206's post-land sweep that
are real structural debt, not something safe to fix blind inside a
"sweep regression" ticket's remaining budget. Re-measured against the
current tree (2026-08-17) and confirmed still present:

- ARCH001 src/frob/app/telemetry.py -- `_home_config_state_hash` has 72
  lines (threshold 60)
- ARCH001 src/frob/app/ticket_runner/_land_cmd.py -- `_auto_sync_worktree_onto_main`
  has 151 lines (threshold 60); `_land` has 120 lines (threshold 60);
  `_new_public_symbols_missing_doc_or_test_edge` has 62 lines (threshold 60)
- ARCH001 src/frob/app/ticket_runner/_new.py -- `_scope_plausibility_file_words`
  has 68 lines (threshold 60)
- ARCH103 src/frob/app/ticket_runner/_land_cmd.py -- `_assert_new_public_symbols_have_doc_and_test_edge_pre_land`
  and `_long_function_symrefs_over_threshold_at_merge_base` mix I/O,
  string-formatting, and multiple decision points in one body
- PERF004/PERF008 src/frob/app/ticket_runner/_land_cmd.py -- a sort() call
  in a loop (line ~3494), Path(...).resolve() and run_argv() called inside
  loops with loop-invariant arguments
- PERF008 src/frob/app/ticket_runner/_rapid_sweep.py -- commit_ticket_ledger_change(...)
  called inside a loop with loop-invariant arguments
- SELFAUDIT001 design -- 2 undeclared capability effects (fs.read/fs.write
  in test files) plus fs.write via-list on core at 22 sites, above the
  committed ratchet ceiling of 21 (docs/design/registry/capability-via-ratchet.lock.json)

The attribution engine marked all of these UNATTRIBUTED with many (6-16)
candidate commits reaching each finding, or no candidates at all --
consistent with long-accumulated ambient debt across `_land_cmd.py`'s land
machinery, not something introduced by T-2199 (the land this sweep
nominally fired from). `_land_cmd.py` in particular is the single largest,
most frequently-touched file in the land critical path (see
docs/guides/agent-playbook.md section 13's own measurements of the same
file) -- these ARCH/PERF findings there are a standing consequence of that,
not a regression.

Filed from T-2206 rather than fixed there because splitting a 120-151 line
land-critical function safely needs its own scoped, reviewed ticket -- not
something to force inside a sweep-regression ticket's remaining budget.

frob:waive BUG002 reason="T-2303's own fix (PERF004/PERF005/PERF008 waivers + frob:invariant terminates in telemetry.py/_new.py) already landed onto main as an undisclosed-turned-disclosed passenger of T-1549's own --allow-cross-ticket land (both tickets share one series worktree branch, T-1549 landed first per coordinator instruction 2026-08-19/20). main now already contains the fix, so the designated repro test structurally cannot fail at parent any more -- confirmatory-only is the only possible outcome from this point forward, not evidence the original repro was ever weak. git diff main -- src/frob/app/telemetry.py src/frob/app/ticket_runner/_new.py is empty; this land is now a ledger-close operation over already-shipped code, not a fresh code change."