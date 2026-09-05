---
id: T-draft-b07ddcf7
title: 'CrossTicketLeakage: T-3844''s blanket tickets/** scope blocks T-3843''s own
  ticket.md/done-report.md from landing'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-3844/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tickets/**
  reason: 'narrow to the actual over-broad-scope finding: T-3844''s own scope declaration,
    not the whole ledger'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tickets/T-3844/ticket.md
  reason: 'narrow to the actual over-broad-scope finding: T-3844''s own scope declaration,
    not the whole ledger'
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-05 attempting frob ticket land T-3843 --worktree
.claude/worktrees/t-3843:

    ERROR: land: T-3843 branch carries 2 file(s) covered by T-3844's own
    scope, and T-3844 is still open on main -- landing would silently ship
    T-3844's work ahead of its own close: ['tickets/T-3843/done-report.md
    (declared)', 'tickets/T-3843/ticket.md (declared)']

T-3844 declares scope ['frob.toml', 'tickets/**'] -- a blanket glob that
covers every OTHER open ticket's own ticket.md/done-report.md, not just
files T-3844 itself needs to touch. CrossTicketLeakage correctly refuses
any such sibling's land while T-3844 is open, since T-3844's declared
scope makes every ticket-ledger write look like it might be T-3844's own
work landing early.

WORSE: T-3844's own ticket body explicitly says it is WAITING on T-3843:
"Post-promotion full --no-cache re-measurement showing the error count
unchanged (1, or 0 after T-3843)." So T-3844 wants T-3843 landed FIRST,
but T-3844's own scope declaration is what blocks T-3843 from landing --
a self-inflicted ordering deadlock with no blocked_by edge recording the
real dependency.

NOT fixed as part of T-3843 (out of scope for that ticket -- it may not
touch T-3844 or the ticket-ledger cross-ticket-leakage machinery) --
filed per the "found while working T-3843" convention.

WHAT TO DO (not decided here, for whoever picks this up):
  - T-3844 should probably declare blocked_by: [T-3843] given its own
    body's explicit ordering requirement, and/or narrow its tickets/**
    scope to whatever subset of the ledger it genuinely needs to touch
    (likely frob.toml plus specific rule-registry/ticket-model files, not
    the whole tickets/ tree) so routine ticket-ledger writes by OTHER
    open tickets stop tripping CrossTicketLeakage.
  - More generally: a scope glob wide enough to match every ticket's own
    ticket.md is a shape CrossTicketLeakage/TICK009 (scope-breadth) should
    probably flag at frob ticket scope/start time, not only discovered at
    land time on an unrelated sibling ticket.

Filed while working T-3843 (DOC006 frontmatter-title fix), which is
otherwise implemented, fixture-covered, and evidenced but cannot land
until this is resolved (or T-3844 closes/narrows its own scope).
