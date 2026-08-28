---
id: T-3228
title: LOUD gate failure for ratchet/deprecated-baseline lock producer abandonment
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_ratchet.py
- src/frob/gates/_deprecated_baseline.py
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
Split from T-2999 (Baseline lock files: staleness warning, and a LOUD
failure when the producer that stamps them stops running).

T-2999 built the shared producer-staleness mechanism
(frob.gates._lock_producer: producer_status/all_producer_statuses,
FRESH/PINNED/ABANDONED/UNMEASURED, a pin field) and wired it into two
places: frob status's always-on "baseline locks" section (covers all
three tracked locks) and a new ERROR-severity TEST012 finding for the
coverage lock specifically (_test012_producer_abandoned in
frob.gates.__init__).

The ratchet lock (frob-ratchet.lock.json, frob.gates._ratchet) and the
deprecated-baseline lock (frob-deprecated-baseline.lock.json,
frob.gates._deprecated_baseline) are already covered by
all_producer_statuses (visible in frob status output) but have no
gate-level LOUD failure of their own yet -- unlike coverage's TEST012,
neither module currently has an existing WARN-severity gate check this
ticket could extend the same way, so wiring a new one needs its own
small design (which existing gate family it should join, whether it
needs a brand-new rule id with check-coverage.yaml registry entries, or
whether it can piggyback on an existing rule the way TEST012 did for
coverage).

At time of writing (T-2999 Done report), BOTH of these locks are
genuinely ABANDONED (7051 and 7454 commits since last stamp
respectively, neither pinned) -- this is not a hypothetical, it is the
repo's own current state.

Acceptance: an ABANDONED verdict on either lock produces a LOUD, named
gate finding (not just the frob status visibility T-2999 already
shipped), with a must-fire and a must-stay-quiet (pinned) fixture,
matching TEST012's precedent.
