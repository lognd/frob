---
id: T-3055
title: 'Land: call-site-guard architecture produces two-site defect classes fixed
  at one site -- four instances found in a single audit'
state: dropped
kind: bug
origin: human
created: '2026-08-26'
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
## Failure log
- 2026-08-30 attempt 1: structurally infeasible: ticket carries a completely empty body -- tickets/T-3055/ticket.md has never contained anything beyond YAML frontmatter since its own filing commit (8246e2423, 2026-08-26, confirmed via git show: the diff adds ONLY the frontmatter block, zero body lines). The coordinator's own brief for this ticket says 'read the body; pick the ONE consolidation it recommends first' -- there is no body describing the 'call-site-guard architecture'/'two-site defect classes' claim or naming the 'four instances found in a single audit' the title refers to. Searched the repo for any trace of this investigation (git grep -i 'call-site-guard'/'two-site defect' across the whole tree, and the surrounding day's commit log) -- found nothing: no FROBLEMS.md entry, no other ticket, no doc section describes it. Cannot pick 'the ONE consolidation it recommends' when no recommendation was ever recorded anywhere; guessing at four unnamed defect instances and inventing a consolidation plan would not be implementing this ticket's actual intent, just producing unrelated work under its id. Needs the ticket's own body populated by whoever has the original audit findings before this can be worked.

## Drop reason
- 2026-08-30: Bodyless since its filing commit 8246e2423: no description of the four call-site-guard instances exists anywhere in the repo (FROBLEMS.md, commit log, docs searched). Refile with the audit findings if the owner still wants this; nothing is workable as filed.
