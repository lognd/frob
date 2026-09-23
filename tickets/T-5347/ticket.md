---
id: T-5347
title: 'DOCARCH002 Tier-A handler (T-4694) reloads the whole ticket archive per finding
  and writes ledger bodies during every land''s repo-wide pre-land pass: lands wedge
  for hours'
state: done
kind: bug
origin: human
created: '2026-09-22'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine.py
- tests/gates_suite/test_fix_engine.py
- tests/narrative/test_docarch002_fix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
evidence:
- tests/narrative/test_docarch002_fix.py::TestDocarch002PreLandPlanOnly::test_archive_loaded_once_and_zero_ledger_writes_in_pre_land_mode
- tests/narrative/test_docarch002_fix.py::TestDocarch002PreLandPlanOnly::test_bare_check_fix_mode_still_writes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5347
branch: t-5347
---
Traceback captured 2026-09-22 22:03 with faulthandler on a wedged land (T-5267, 18 min at 100 percent CPU; T-5291 for 52 min): apply_tier_a_fixes -> fix_docarch002_narrative_move -> _docarch002_fix_one_file -> _docarch002_migrate_one -> _docarch002_existing_body -> tickets._store.load_archive -> yaml.load: the full archived-ticket YAML parse runs once PER DOCARCH002 finding, and the pre-land pass is repo-wide (thousands of findings), so a land never reaches its first phase stamp. It also performs ledger body writes (set_body) for every finding as a side effect of landing an unrelated ticket. Coordinator hotfix e1b14b8248 unregistered DOCARCH002 from TIER_A_HANDLERS on dev. Proper fix: load the archive once per run (memoize on the snapshot), never write the ledger from a pre-land pass, scope the handler to the landing ticket's touched files (T-5106 note), then re-register with a positive control: a pre-land pass over a fixture with 50 DOCARCH002 findings loads the archive once and makes zero ledger writes.