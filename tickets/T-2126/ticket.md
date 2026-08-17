---
id: T-2126
title: Consider surfacing verify queue depth/age in fleet_status.py, symmetric to
  T-2049's quarantine line
state: queued
kind: feature
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2049's acceptance criterion 4 asked to measure (not speculatively add)
whether other state that silently changes land cost belongs in
fleet_status.py by the same argument. Measured: frob.verify._watermark.
queue_status(root) currently reports 17 queued verify entries against
this repo's own root right now (2026-08-10/11 session) -- a non-trivial,
currently-nonzero number with the same "silently changes land cost, and
nothing prints it where a coordinator already looks before dispatch"
shape as the quarantine finding T-2049 fixed (queue depth/age feeds
directly into frob.verify._backpressure.block_until_watermark_advances,
the same function _apply_backpressure calls right after the quarantine
override -- a deep queue means every land blocks longer, not just a
quarantined one).

No documented incident (unlike quarantine's two-dead-imports/one-hour
cost) ties this to a real fleet-throughput loss in this session, so
T-2049 itself did not add it -- adding a field on measurement alone,
with no incident motivating WHICH shape of display is useful (raw
depth? age vs ceiling? which profile's ceiling?), would be exactly the
speculative-field mistake T-2049's own "Do NOT fix it this way" section
warns against for the quarantine case.

Proposed: add queue_status()'s depth/oldest-entry-age to
scripts/fleet_status.py, next to the new QUARANTINE line, once either
(a) a real incident ties queue depth to lost throughput the way
quarantine did, or (b) whoever owns fleet_status.py decides the
symmetry argument alone justifies it without waiting for an incident.
