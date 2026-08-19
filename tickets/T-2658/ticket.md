---
id: T-2658
title: Recovered from T-2615's phantom TICK006 citation of T-draft-b8d1b183
state: dropped
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2615's Done report claimed T-draft-b8d1b183 was filed, but T-draft-b8d1b183 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> ves its own ticket
rather than a half-measure bolted onto this one. Filed T-2645 to track
that as a deliberate follow-up, not a silent drop. Filed as
T-draft-b8d1b183 (will renumber at land).

Did NOT retroactively rewrite the 101 historical CHANGELOG.md lines
(explicitly out of scope per the ticket

## Drop reason
- 2026-08-19: Draft T-draft-b8d1b183's intended work (design an explicit author-controlled 'what changed' changelog field, since generated entries currently read as bug reports not release notes) is already tracked by a separately-promoted real id: T-2642, same exact title 'changelog entries read as bug reports, not release notes', same scope (src/frob/release/_fragments.py, src/frob/app/ticket_runner/_land_cmd.py), state=queued (not yet done, still live and doable). Measured: 'sed -n' on tickets/T-2642/ticket.md confirms identical title/scope on current main. The draft commit (cfd1b1e9f, T-2615's worktree branch) never merged into main (git merge-base --is-ancestor cfd1b1e9f main -> false) -- the TICK006 citation is phantom because the work was independently promoted/refiled as T-2642 through a different path, not lost. No action needed here; T-2642 is the live tracking ticket for this design question. (absorbed by T-2642)
