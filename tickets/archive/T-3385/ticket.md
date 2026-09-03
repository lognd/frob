---
id: T-3385
title: Wire check_fix_all and ticket_migrate_fill_gaps into AppConfig (_BOOL_FLAGS
  gap)
state: dropped
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FLAGCOV001 (and separately test_app_config_flag_coverage / test_flag_coverage_gate, per Series EE) both point at the same root cause: dest='check_fix_all' (src/frob/_cli_parsers/_check.py) and dest='ticket_migrate_fill_gaps' (src/frob/_cli_parsers/_ticket/_progress.py) are consumed downstream as cfg.check_fix_all / cfg.ticket_migrate_fill_gaps but neither name is in _BOOL_FLAGS in _config_external.py, so _apply_bool_flags never copies the parsed CLI value onto AppConfig -- same field-forwarding bug class as T-3257. Fix: add both dests to _BOOL_FLAGS.

## Drop reason
- 2026-08-29: duplicate: falsified premise -- fix landed directly under T-3346, this draft never got a real T-#### id and never left the worktree (absorbed by T-3346)
