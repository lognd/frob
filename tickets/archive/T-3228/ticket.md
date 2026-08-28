---
id: T-3228
title: LOUD gate failure for ratchet/deprecated-baseline lock producer abandonment
state: done
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
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_waive.py
- tests/unit/gates/test_deprecated_baseline.py
- docs/design/registry/check-coverage.yaml
- docs/modules/gates.md
- tests/test_waive_gate.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_debt_deprecated.py
  reason: DEPR006 wired into the existing DEPR family for the deprecated-baseline
    lock; WAIVE011 wired into the existing WAIVE family for the ratchet lock (no other
    existing gate owns either mechanism cleanly) -- both reuse T-2999 _lock_producer.producer_status,
    matching TEST012s precedent
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_waive.py
  reason: DEPR006 wired into the existing DEPR family for the deprecated-baseline
    lock; WAIVE011 wired into the existing WAIVE family for the ratchet lock (no other
    existing gate owns either mechanism cleanly) -- both reuse T-2999 _lock_producer.producer_status,
    matching TEST012s precedent
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/gates/test_deprecated_baseline.py
  reason: DEPR006 wired into the existing DEPR family for the deprecated-baseline
    lock; WAIVE011 wired into the existing WAIVE family for the ratchet lock (no other
    existing gate owns either mechanism cleanly) -- both reuse T-2999 _lock_producer.producer_status,
    matching TEST012s precedent
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/gates/test_waive.py
  reason: DEPR006 wired into the existing DEPR family for the deprecated-baseline
    lock; WAIVE011 wired into the existing WAIVE family for the ratchet lock (no other
    existing gate owns either mechanism cleanly) -- both reuse T-2999 _lock_producer.producer_status,
    matching TEST012s precedent
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: DEPR006 wired into the existing DEPR family for the deprecated-baseline
    lock; WAIVE011 wired into the existing WAIVE family for the ratchet lock (no other
    existing gate owns either mechanism cleanly) -- both reuse T-2999 _lock_producer.producer_status,
    matching TEST012s precedent
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/gates.md
  reason: DEPR006/WAIVE011 doc anchors
  actor: logan
  at: '2026-08-28'
- op: remove
  glob: tests/unit/gates/test_waive.py
  reason: WAIVE009/010 tests actually live in tests/test_waive_gate.py, not tests/unit/gates/test_waive.py
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_waive_gate.py
  reason: WAIVE009/010 tests actually live in tests/test_waive_gate.py, not tests/unit/gates/test_waive.py
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/__init__.py
  reason: wired waive011_violations into the WAIVE00* import list and _assemble_gate_report
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/gates/test_deprecated_baseline.py::TestDepr006ProducerAbandoned::test_abandoned_producer_fires_error
- tests/unit/gates/test_deprecated_baseline.py::TestDepr006ProducerAbandoned::test_pinned_producer_stays_quiet
- tests/test_waive_gate.py::TestWaive011ProducerAbandoned::test_abandoned_producer_fires_error
- tests/test_waive_gate.py::TestWaive011ProducerAbandoned::test_pinned_producer_stays_quiet
designated_repro_test: tests/unit/gates/test_deprecated_baseline.py::TestDepr006ProducerAbandoned::test_abandoned_producer_fires_error
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3bc56e3a099c2311a279b0e6280e62063d37851f
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