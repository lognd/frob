---
id: T-2096
title: 'Citation-rewrite gap: renumber only rewrites tickets/**/*.md and frob:ticket
  directives, not docstring prose or commit messages'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_renumber_v2.py
- tests/test_tickets_collision.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_collision.py
  reason: BUG002 evidence for T-2096 lives in this test file
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_tickets_collision.py::TestRenumberOneV2::test_unrewritten_docstring_prose_citation_is_surfaced
- tests/test_tickets_collision.py::TestRenumberOneV2::test_fully_rewritten_renumber_surfaces_nothing
designated_repro_test: tests/test_tickets_collision.py::TestRenumberOneV2::test_unrewritten_docstring_prose_citation_is_surfaced
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2079 (and originally noted in T-1669/T-2079's own
ticket body): `frob ticket renumber`/`_scan_v2_reference_files`
(src/frob/tickets/_renumber_v2.py) only rewrites whole-word citations
inside `tickets/**/*.md` (ticket.md/done-report.md) plus code
`frob:ticket` directives (`_scan_code_references`). Free-form docstring
prose outside that glob, and commit messages, are never rewritten -- this
is exactly what forced a hand-fix after a renumber for T-2060.

Either extend the rewrite to cover source docstring prose (not just
frob:ticket directive lines) and commit-message-adjacent citations, or
build a surfacing mechanism that lists every unrewritten citation to the
operator after a renumber so it is never silently left stale.