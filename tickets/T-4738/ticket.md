---
id: T-4738
title: 'Land phase (a): explicit phase enum, one logged transition per phase, .frob/land-status.json
  per phase'
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
- src/frob/tickets/_land_queue.py
- tests/unit/test_land_phase_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a land runs to completion, when its log is read, then it contains exactly
    one transition line per phase in the order prepare -> compose -> publish -> post-publish,
    each with a duration and an outcome.
  evidence: []
- text: 'POSITIVE CONTROL: a test runs a land and asserts .frob/land-status.json reports
    the phase at each step, and that a land interrupted mid-phase leaves a status
    file naming the phase it was in. It FAILS on dev today (no phase enum, no status
    file) and passes after this leaf.'
  evidence: []
- text: Given .frob/land-status.json, when a second process reads it during an in-flight
    land, then it names the current phase without attaching to or blocking the land.
  evidence: []
- text: Given this leaf, when the existing land test suite runs, then it passes unchanged
    -- no work moves between phases in this leaf.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LAND leaf (a) of the T-3053 split, owner-approved amendment 2026-09-19. ~2 points.

The land is a hand-compensated saga across four stores with no explicit notion of what phase
it is in. When it wedges -- and this week it wedged repeatedly -- nobody, human or agent, can
tell from outside whether it is composing, publishing or sweeping.

Make the phase EXPLICIT and OBSERVABLE:
- a phase enum: prepare -> compose -> publish -> post-publish
- exactly ONE logged transition per phase, at INFO, carrying the phase name, its inputs,
  its duration and its outcome
- .frob/land-status.json written on every phase entry and exit, so a coordinator can read
  the current phase of an in-flight land without attaching to the process

This is leaf (a) and it is DISPATCHABLE NOW: it adds the skeleton and the observability
without moving any work between phases. Leaves (b) compose-out-of-tree and (c) publish-via-CAS
move the work into the skeleton afterwards.
