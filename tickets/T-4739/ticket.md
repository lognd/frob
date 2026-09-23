---
id: T-4739
title: 'Land phase (b): compose is pure over a snapshot, out of tree, no git or ledger
  writes'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-3053
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_compose.py
- tests/unit/test_land_compose_pure.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the compose phase, when it runs, then it performs no git write, no ledger
    write and acquires no lock; it returns a composed result value.
  evidence: []
- text: 'POSITIVE CONTROL: a test runs compose against a read-only snapshot with the
    git index and the ledger made write-hostile, and asserts compose still succeeds
    and returns its result. It FAILS on dev today (compose writes during the phase)
    and passes after this leaf.'
  evidence: []
- text: Given the same snapshot, when compose runs twice, then it produces the same
    composed result both times -- purity proven by repetition, not by inspection.
  evidence: []
- text: Given a compose result, when publish rejects it, then compose need not be
    re-run from scratch against a changed tree; the result is a value the retry path
    can re-merge.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LAND leaf (b) of the T-3053 split, owner-approved amendment 2026-09-19. ~3 points.

COMPOSE becomes PURE over a snapshot: it takes the snapshot built by prepare, produces the
composed result out of tree, and performs NO git writes, NO ledger writes and NO lock
acquisition. Today compose interleaves reads, writes and lock holds, which is why a 10-25
minute compose can lose its publish race and have nothing to retry with -- the work is not
a value it can re-publish, it is a set of side effects already applied.

A pure compose is also a retryable compose: leaf (c)'s CAS can re-merge and retry precisely
because compose produced a value rather than a mutation.

Depends on leaf (a)'s phase skeleton.
