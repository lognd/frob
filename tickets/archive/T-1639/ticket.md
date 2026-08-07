---
id: T-1639
title: CrossTicketLeakage treats a QUEUED ticket's scope as a lock, so filing a ticket
  blocks unrelated lands
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land.py
- docs/modules/tickets.md
- tests/unit/test_land_cross_ticket_leakage.py
- tests/system/test_cli_doctor.py
- tests/test_ticket_land.py
- tests/unit/test_doctor_runner_t1276.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_cross_ticket_leakage.py
  reason: regression tests for the QUEUED/PLANNED-does-not-block fix
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: 'shared-worktree accumulation: these T-1634 test files are on the same branch
    as T-1639''s diff'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'shared-worktree accumulation: these T-1634 test files are on the same branch
    as T-1639''s diff'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: 'shared-worktree accumulation: these T-1634 test files are on the same branch
    as T-1639''s diff'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_queued_sibling_scope_overlap_does_not_block
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_planned_sibling_scope_overlap_does_not_block
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_allow_cross_ticket_overrides_the_refusal
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_does_not_block
designated_repro_test: null
threat: null
component: null
---
CrossTicketLeakage refuses a land when the branch touches files covered by a DIFFERENT ticket's declared scope and that ticket is "still open (not done/dropped)". Open includes QUEUED -- a ticket nobody has started, with zero commits and no worktree.

Consequence: filing a ticket reserves its declared scope against every other land, immediately, before any work exists. A ticket declaring `tests/**` blocks every land that touches a test. On 2026-08-06 a freshly filed ticket (T-1637, queued, unstarted) blocked an unrelated land (T-1636) over 12 files that only overlapped by declaration.

This inverts the intended incentive. Scope declarations exist so two agents do not collide, and this repo asks tickets to declare scope generously and early so nothing is silently out of bounds. But if a queued scope is a lock, then the safe move becomes declaring the NARROWEST possible scope at filing time, or not filing until you are ready to start -- both of which defeat the accounting the ticket queue exists for. It gets worse with queue depth: ~45 tickets were filed in one session here, many with broad scopes, so the set of files no land may touch grows with every ticket filed.

The existing lease model already draws the right distinction: `frob.tickets._leases` reserves scope for tickets that are actually IN PROGRESS in a worktree, with liveness probing so a dead agent's claim expires. CrossTicketLeakage should respect that same line.

Proposed:
- A QUEUED ticket's scope does not block a land. It is an intention, not a claim.
- An IN-PROGRESS ticket's scope does block, exactly as today -- that is a real concurrent writer with real commits.
- If a queued ticket's scope overlap is still worth surfacing, surface it as a WARNING naming the ticket, not a refusal.

Verify before implementing: confirm the current behavior really does treat queued as blocking (the refusal message says "not done/dropped", which implies it does) and check whether `_scope_covers`/the lease layer already has a state filter that was simply not applied here. If the distinction already exists somewhere, reuse it rather than adding a second notion of "active".

Note the interaction with cross-ticket leakage's genuine purpose (T-1618): the check is valuable and must keep firing for the case it was built for -- a shared series worktree carrying a sibling's committed work onto main. That case involves real commits, so gating on in-progress does not weaken it.