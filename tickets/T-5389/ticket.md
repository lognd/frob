---
id: T-5389
title: 'Post-land sweep residue 2026-09-23_0726: FLAGCOV001:frob.toml '
state: done
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_config_external.py
  reason: forwarding tuple missing ticket_attach_remove_path/ticket_attach_remove_all
    dests (FLAGCOV001)
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/unit/test_app_config_flag_coverage.py::TestT5151TicketAttachRemoveFlagsReachAppConfig::test_from_external_carries_remove_path_from_parsed_argv
- tests/unit/test_app_config_flag_coverage.py::TestT5151TicketAttachRemoveFlagsReachAppConfig::test_from_external_carries_remove_all_from_parsed_argv
- tests/unit/test_app_config_flag_coverage.py::TestT5151TicketAttachRemoveFlagsReachAppConfig::test_absent_remove_flags_default_none_and_false
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5389
branch: t-5389
---
Findings raised by a post-land sweep and disposed against this ticket by the coordinator's runner to keep the quarantine clear. Fix each in scope:
FLAGCOV001:frob.toml