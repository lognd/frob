---
id: T-5776
title: 'Audit the 42 epics: close all-children-done ones via TIER003, record an outcome
  check or a dropped reason for the rest'
state: planned
kind: docs
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5780
- T-5761
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
flavour: null
due: null
rank: null
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- tickets/T-*/ticket.md
- scripts/check_epic_audit_closed.py
- tests/gates_suite/test_tier_gate.py
scope_breadth_ack: true
scope_breadth_ack_reason: bulk ledger audit over epic rows only; ticket-count-scaled
  by design
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/check_epic_audit_closed.py
  reason: positive-control script + its unit test for the --evidence-cmd binding
  actor: logan
  at: '2026-09-25'
- op: add
  glob: tests/gates_suite/test_tier_gate.py
  reason: positive-control script + its unit test for the --evidence-cmd binding
  actor: logan
  at: '2026-09-25'
triage_changes:
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '8'
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-25'
- field: kind
  old_value: feature
  new_value: docs
  reason: T-5776 is a pure ledger audit (tickets/T-*/ticket.md + two real epic closes
    through the state machine) with no code diff of its own -- docs-kind for the --evidence-cmd
    binding
  actor: logan
  at: '2026-09-25'
body_changes:
- mode: append
  reason: record the E3 scope cut and the close-timeout friction ticket per coordinator
    instruction
  actor: logan
  at: '2026-09-25'
  old_length: 747
  new_length: 1549
- mode: append
  reason: record final close outcome
  actor: logan
  at: '2026-09-25'
  old_length: 1549
  new_length: 1944
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Audit the 42 epics: close the all-children-done ones via TIER003, and for the rest record an outcome check or file a dropped reason.

Positive control: post-audit, zero epics are both all-children-done and still open; every remaining open epic has either an outcome-check field or a dropped child recording why not.

Doc page: docs/modules/tickets-lifecycle.md

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

## Unblock log
- 2026-09-24: unblocked by T-draft-76f89687 -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block


Scope cut (coordinator-approved 2026-09-24/25): the audit of the 40 (live: 41) still-open epics that are NOT all-children-done is deferred to T-draft-31c35523 ("audit the 40 open epics: outcome-check or dropped child per epic", parent T-5748, blocked by T-5776, milestone v0.536.0, 8 pts). This leaf (T-5776) closes the 2 all-children-done epics (T-3611, T-4513) properly through the real close flow (verified children, real frob:outcome-metric, evidence, done-report). Also filed T-draft-e03cfa51 (bug, high priority, parent T-5630, milestone v0.535.0): frob ticket close's internal own-obligations check spawns frob check --only gates with a hardcoded 600s timeout with no override, which refused both close attempts under tonight's fleet load -- traced to src/frob/app/ticket_runner/_close_cmd.py.

Both epics closed successfully once fleet load dropped under 6 (coordinator instruction): T-3611 done (frob:outcome-metric, cmd-evidence via frob ticket epic T-3611), T-4513 done (frob:outcome-metric, pytest evidence reused from child T-4506, --skip-mutation-evidence used per TEST016's own escape hatch since the mutation sweep measured unrelated fleet-touched files, not T-4513's own scope).