---
id: T-draft-703785b9
title: frob check ty stage feeds non-Python files (.md) to ty when a scoped file set
  contains them, and the done-report totals fallback counts the resulting spurious
  errors as real
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: 3
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
- src/frob/check/_python.py
- src/frob/app/ticket_runner/_verify.py
- tests/unit/check/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 1792
  new_length: 1792
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26) from three crunk tickets
(T-0223, T-0140, T-0207): frob's ty stage received Markdown files
(docs/design/subsystems/*.md, tickets/*/ticket.md) and reported
invalid-syntax and unresolved-import inside code fences; T-0207's
done-report then recorded "20 error(s)" attributed to .md files in
Captured claims after a "--json produced no parsable gate-summary totals
line" fallback, contradicting the agent's clean `frob check --ticket`
runs and risking a spurious ClaimDivergence at land.

Verified on dev 990591bcf6: `_run_ty` (src/frob/check/_python.py) builds
`targets = list(files) if files else [str(root)]` with no suffix filter,
so any scoped set (a ticket's touched or declared files, `--files`) that
contains non-Python paths is handed to ty verbatim; and the done-report
fallback at src/frob/app/ticket_runner/_verify.py (T-2668 branch) keeps
the parsed `## Errors` identities as a real error count when the totals
line is missing, so ty's noise on .md becomes a comparable land claim.

Deliver: (1) `_run_ty` (and the land's touched-set ty pre-check, which
already filters to .py) restrict targets to .py/.pyi, honouring ty's own
include/exclude config, and log the dropped paths at DEBUG; (2) the
T-2668 fallback records the error count as unmeasured (None) when no
totals line parsed AND any captured finding names a non-Python file, and
logs which files, instead of promoting them to a land claim; (3) find
why `frob check --ticket --json` emitted no totals line in T-0207's run
(exit code and stderr are in that fallback's warning) and fix or refuse
loudly; (4) positive control: a scoped set with one .py and one .md
yields ty findings only for the .py; a done-report run whose ty output
names a .md file records unmeasured, not a count.
