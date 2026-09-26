---
id: T-6542
title: consumer repos never get the frob ticket merge-driver; done-report stages a
  conflicted ticket file and commits conflict markers
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
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
- src/frob/tickets/_merge_driver.py
- src/frob/scaffold/
- src/frob/tickets/_done_report.py
- tests/unit/tickets/test_merge_driver_install.py
- docs/modules/tickets-lifecycle.md
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
Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-404: merging main into a ticket worktree in a consumer repo conflicted on tickets/T-0420/ticket.md because `frob ticket merge-driver` is registered only in the frob repo's own git config, never installed by `frob init`/scaffold/adopt in consumer repos. The next `frob ticket done-report` then failed on the malformed frontmatter but had already staged the conflicted file, so the markers were committed. Deliver: (1) `frob init`/scaffold/adopt (and doctor) install the ledger merge driver into the repo's .git/config and .gitattributes, doctor reports its absence as REQUIRED; (2) ledger verbs refuse to stage or commit a ticket file that fails to parse (conflict markers, bad frontmatter) and name the file; (3) positive control: consumer-repo fixture with a ledger conflict resolves via the driver, and a planted conflict-marker file is refused by done-report.
