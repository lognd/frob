---
id: T-4076
title: 'M-7: allowlist check for public/-style static-assets directories'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
blocked_by:
- T-3976
parent: T-4071
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a design decision between a refs.artifact instance and a standalone
    allowlist check, when this ticket's design step completes, then the choice is
    recorded before implementation, preferring refs.artifact if T-3976 is ready
  evidence: []
- text: given a file under public/ not on the declared allowlist, when the check runs,
    then it is flagged
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
M-7 (F-273). VERIFIED: nothing in frob models a public/-style static-assets directory as a build input with an allowlist; static-assets:check is the consumer's own npm script name, and this item asks for a frob-side rule generalizing what that script should enforce, connecting to the same declared-build-surface theme as T-3976 (refs.artifact).

FINDING THIS WOULD HAVE CAUGHT: mockServiceWorker.js shipping inside frontend/public/ (and therefore into the built dist/) even though COMP-1514's own comment claim ("never imported by a production build path") is true and was presumably verified against the import graph -- the comment is correct about the IMPORT graph, but nothing models public/ itself as a build input at all, so a stray file there ships regardless of whether anything imports it.

Proposed: extend static-assets:check (or the frob-side rule backing it) to fail if frontend/public/ contains any file not on an explicit allowlist (the consumer's current four: llms.txt, media/, robots.txt, sitemap.xml). CONNECTS TO T-3976's refs.artifact construct (a declared, individually-justified build-output surface) -- during design, decide whether this is best implemented as a refs.artifact instance (each allowlisted public/ entry justified the same way an artifact glob entry is) or a standalone allowlist check; prefer refs.artifact if it is ready, to avoid a second, parallel build-surface declaration mechanism.
