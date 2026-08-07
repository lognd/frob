---
id: T-0521
title: 'SCOPE001: bare directory scope entries (no trailing slash) never expand and
  silently drop from a ticket''s real scope'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_models.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets.py
  reason: regression test for fix lives here
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_tickets.py::TestScopeMatching::test_bare_dir_entry_no_trailing_slash_globs_recursively
designated_repro_test: null
threat: null
component: null
---
Found while working T-0515: _scope_globs (frob.tickets._models) only expands a bare directory entry to dir/** when the entry ENDS WITH a trailing slash and has no glob metacharacters -- an entry written as 'docs/modules' (no trailing slash, as several existing tickets.md scope blocks use) is instead treated as a literal fnmatch pattern equal to that exact string, which can never match a real file path (docs/modules/gates.md, etc). This means any ticket whose author typed a bare directory name without the trailing slash silently has that entry as dead weight in scope -- SCOPE001 fires on every file under it, and PRE001's sweep sees it as empty. T-0515 hit this directly (docs/modules / docs/strata entries had to be corrected to docs/modules/ / docs/strata/ mid-ticket). Fix direction: either warn/normalize at TicketSpec construction time (strip trailing slash requirement, treat any scope entry with no glob metacharacters and no dot-extension as an implied directory prefix), or add a lint that flags scope entries shaped like a bare directory name lacking a trailing slash. Grep tickets.md for scope entries matching a bare path segment (no /, no ., no *) to gauge how many existing tickets are silently affected.