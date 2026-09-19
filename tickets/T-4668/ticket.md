---
id: T-4668
title: 'SF-03: one loader, one writer, one schema for capability-via-ratchet.lock.json
  -- delete the 3 shadow top-level keys'
state: queued
kind: bug
origin: agent
created: '2026-09-19'
priority: high
blocked_by:
- T-4598
parent: T-4664
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_ratchet_lock.py
- docs/design/registry/capability-via-ratchet.lock.json
- tests/unit/strata/test_ratchet_lock_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the committed lock carries 3 capability keys at the JSON top level (stratamod::fs.read
    11 vs entries 12, stratamod::fs.write 4 vs 7, testsuite::net 14 vs 27) that _load_capability_ratchet_lock
    ignores, when this lands, then a test asserts the lock has zero capability keys
    outside entries and that every entry carries accepted_count, reason AND ticket
    -- a positive control that fails at HEAD c8f56ef10 on those 3 keys and on entries[testsuite::fs.write],
    which has no ticket field.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
SF-03 (HIGH). Leaf of story A (T-4664) under epic T-4662. Story points: 2.

EVIDENCE, re-verified by the planner at HEAD c8f56ef10 by loading the JSON:
docs/design/registry/capability-via-ratchet.lock.json contains, besides
`entries`, `generated_by` and `schema_version`, THREE top-level capability keys
whose values diverge from the real ones:

    key                   top level           entries
    stratamod::fs.read    11  (T-4443)        12  (T-4512)
    stratamod::fs.write     4  (T-2923)         7  (T-4512)
    testsuite::net         14  (T-3618)        27  (T-4110)

`git log -S'"testsuite::net"'` points at 29bef0d7e (T-2923's land) as the commit
that first wrote them at the top level; the diff shows the same three entries
written twice, once correctly inside `entries` and once appended after
`schema_version`. They have been BUMPED SINCE (T-4443, T-3618), so a writer is
still touching them.

The reader ignores them. src/frob/strata/_effects.py:1441-1455,
`_load_capability_ratchet_lock`, ends:

    entries = data.get("entries") if isinstance(data, dict) else None
    return entries if isinstance(entries, dict) else {}

So three ceilings carry a second, divergent, authoritative-LOOKING value that
nothing enforces, and a human reading the file to disposition a growth can read
the wrong number.

TWO WRITERS, TWO SCHEMAS, ONE FILE: entries["testsuite::fs.write"] is
{"accepted_count": 542, "reason": "testsuite glob growth"} with NO `ticket`
field, because the T-4495 auto-accept writer at src/frob/strata/_effects.py:1422
writes {"accepted_count", "reason"} only, unlike the SYS111 writer at
src/frob/gates/_fix_engine_sync.py:1362 which writes a `ticket`.

WHAT TO BUILD
A single `src/frob/strata/_ratchet_lock.py` owning the lock's read, write and
schema: one typed model (pydantic), one loader returning a typani Result, one
writer both call sites will migrate to, and a schema validator that refuses a
lock with any capability key outside `entries` or any entry missing
accepted_count / reason / ticket. Delete the three shadow keys in the same
change. Migrating the two existing writers to it is deliberately NOT in this
leaf's scope -- that is A4, which owns _fix_engine_sync.py.

POSITIVE CONTROL (the test that fails today)
A test asserting (a) the committed lock has zero capability keys at the JSON top
level -- fails today on the 3 keys above -- and (b) every entry carries
accepted_count, reason AND ticket -- fails today on testsuite::fs.write.

BLOCKER: T-4598 (KERNEL DECOUPLING epic) -- shared registry files must be
append-shared, not whole-file leases. This leaf's whole job is rewriting
docs/design/registry/capability-via-ratchet.lock.json, so it is exactly the case
T-4598 exists to unblock; starting it before T-4598 serialises the fleet.
