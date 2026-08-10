---
id: T-1987
title: land's Tier-A fmt auto-fix rewraps noqa-suppressed frob:waive comments, regressing
  ARCH001
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fmt_directives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
land's absorbed Tier-A fmt auto-fix rewrapped a single-line
`# frob:waive WALK001 reason="..."  # noqa: E501` comment inside
frob.graph._walk_repo_files into 4 lines using backslash continuations,
during both the T-1970 and T-1968 lands (2026-08-10). The comment was
already noqa-suppressed and needed no reflow.

The rewrap had two effects:
1. It pushed src/frob/graph/__init__.py::_walk_repo_files from 60 to 63
   lines, tripping ARCH001 (threshold 60) -- a real gate regression on
   main, fixed directly (reverted to the single-line form) as part of
   landing T-1968.
2. Backslash-continued frob:waive/frob:tests comments do not appear to
   be reliably re-parsed as the same single logical directive by every
   scanner -- this is adjacent to, but distinct from, T-1970/T-1968's
   own mention/use-escape work and was not diagnosed further here.

Scope this ticket to find/fix the Tier-A fmt auto-fix handler that
performs this backslash-continuation rewrap (likely in
src/frob/gates/_fmt_directives.py, absorbed into `frob ticket land`
per docs/guides/agent-playbook.md section 0 step 5) so it either skips
already-noqa-suppressed long directive lines, or wraps them in a form
that keeps line-count-sensitive gates (ARCH001) and directive parsing
unaffected.
