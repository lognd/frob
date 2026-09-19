---
id: T-draft-665780a8
title: 'Land phase (c): publish is a single update-ref CAS reusing T-4572''s ledger-only
  fast path'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-3053
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_splice.py
- tests/unit/test_land_publish_cas.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the publish phase, when it runs, then it updates the ref via a single
    compare-and-swap and performs no other mutation.
  evidence: []
- text: 'POSITIVE CONTROL: a test publishes while injecting a sibling ledger-only
    commit between the snapshot and the CAS, and asserts the land re-merges and retries
    to success rather than refusing. It FAILS on dev today (the land refuses with
    "dev moved away from") and passes after this leaf.'
  evidence: []
- text: Given a CAS that loses to a NON-ledger-only commit, when it retries, then
    it retries a bounded number of times and then refuses with a named error naming
    the winning commit -- never an unbounded spin.
  evidence: []
- text: Given the fast path, when it is exercised, then it is T-4572's implementation
    and not a second copy -- proven by the test importing the same symbol T-4572's
    own test binds.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LAND leaf (c) of the T-3053 split, owner-approved amendment 2026-09-19. ~3 points.

PUBLISH becomes a single compare-and-swap ref update and nothing else. It reuses the
ledger-only fast path that T-4572 builds (re-merge and retry instead of refusing), so a
sibling ledger-only commit can no longer cost a land its entire 10-25 minute compose.

Measured this week: under 5+ agents every third land bounced with "dev moved away from" and
DirtyMain. The cause is not the race -- races are normal -- it is that losing the race was
terminal instead of a retry.

Depends on leaf (a)'s skeleton and leaf (b)'s pure compose (a retry is only cheap if compose
produced a value). Coordinate with T-4572, which owns the fast path itself; this leaf wires
publish to it rather than writing a second copy.
