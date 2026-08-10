---
id: T-1954
title: 'DOC002: src/frob/tickets/_land.py:2179 frob:doc anchor for T-1922 does not
  resolve'
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
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Full unscoped frob check on main (commit caf23ffc0a7c, measured while closing T-1933/T-1935) found: [gate:DOC] src/frob/tickets/_land.py:2179 DOC002 -- frob:doc anchor 'docs/modules/tickets.md#outofscopewaivedeletion-false-refusal-on-a-stale-worktree-t-1922' does not resolve to any real anchor in docs/modules/tickets.md; closest suggested match is #mega-glob-scope-refused-at-start-t-1866. Looks like T-1922's land added the frob:doc directive with a slug that never got a matching heading/anchor added to docs/modules/tickets.md, or the doc's heading text drifted after the directive was written. Not attributable to T-1933/T-1935 (neither touched src/frob/tickets/_land.py). Fix: either add the missing anchor to docs/modules/tickets.md, or correct the frob:doc directive's slug to point at the real section documenting T-1922's OutOfScopeWaiveDeletion fix.