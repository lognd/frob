---
id: T-2781
title: add tests/test_tickets_parent.py to testsuite exec-capability via-list
state: dropped
kind: docs
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
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
T-2770's new test file tests/test_tickets_parent.py calls subprocess.run
for git init (same shape tests/test_tickets_tiers.py already uses) and
trips SELFAUDIT001 (SYS100, node=testsuite, capability 'exec' observed
but not declared) because design/frob.strata's testsuite node's exec
capability via-list does not include it. design/frob.strata was under a
live cross-worktree lease (T-2557) at fix time and could not be added to
T-2770's own scope, so the finding is waived there instead
(frob:waive SELFAUDIT001) pending this ticket. Add
tests/test_tickets_parent.py to the via-list at design/frob.strata:1428,
then this ticket's waiver in test_tickets_parent.py can be removed.

## Drop reason
- 2026-08-21: no longer needed: test_tickets_parent.py rewritten to not use subprocess/git init at all (new_ticket/write_ticket work fine without a git repo), so the testsuite exec-capability via-list never needed this file added
