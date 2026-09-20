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
body_changes:
- mode: append
  reason: '2026-09-19: coordinator/owner amendment -- D-M6 splits design/frob.strata
    module by module and migration step 7 splits the ratchet lock per module, so the
    single loader/writer this ticket builds must be designed for per-module lock files
    from the start rather than retrofitted'
  actor: logan
  at: '2026-09-19'
  old_length: 2785
  new_length: 5145
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
A single <!-- frob:waive DOC006 reason="illustrative target path for the module this ticket creates -- does not exist until this ticket lands" -->`src/frob/strata/_ratchet_lock.py` owning the lock's read, write and
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


## AMENDMENT 2026-09-19 -- design for PER-MODULE lock files from the start

Binding constraint added by the coordinator on the owner's module-system
decisions (D-M6, recorded on T-4680, now closed):

**The single loader/writer/schema this ticket builds must be designed for
per-module lock files from the start -- `design/<module>.via.lock.json` -- not
for the one monolithic `docs/design/registry/capability-via-ratchet.lock.json`
with a per-module split retrofitted later.**

WHY. D-M6 decided that design/frob.strata is split module by module, by hand,
and **migration step 7 of the module system splits the ratchet lock per module**.
So the single-file lock this ticket is cleaning up is already known to be
temporary. A loader written against one global `entries` map, then retrofitted,
would be the third writer of this file rather than the last one -- which is
precisely the failure mode this ticket exists to end (SF-03: two writers, two
schemas, one file; SF-13: four regressions on the same mechanism).

WHAT THIS CHANGES ABOUT THE WORK HERE
- The loader's interface takes a MODULE, not a root path, and resolves that
  module's lock; the single global file is one implementation of that resolution,
  not the shape the API assumes.
- The schema validator validates ONE module's lock, and the "no capability keys
  outside `entries`" rule is a per-file rule, so it keeps working unchanged after
  the split.
- The key namespace is already module-prefixed (`stratamod::fs.read`,
  `testsuite::net`, `gates::fs.write`), so the split is a partition of the
  existing keyspace by the part before `::`. Do not invent a second naming
  scheme.
- Migration must be expressible as: read the one global file, write N per-module
  files, with the drift reporter (T-4670) reporting zero drift across the move.
  If the design cannot express that, it is the wrong design.

WHAT THIS DOES NOT CHANGE
This ticket still deletes the 3 shadow top-level keys and still lands the
positive control that fails at HEAD. It does NOT perform the per-module split --
that is migration step 7 of the module-system story, filed by the other planner.
This ticket only guarantees the split will not require a fourth rewrite.

The T-4598 blocker is unchanged and still real: this ticket rewrites the shared
lock file, which 5 other tickets' scopes already name (2 in-progress).
