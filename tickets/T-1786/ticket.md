---
id: T-1786
title: Give the land lock a discoverable, side-effect-free visibility surface (frob
  doctor or similar)
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1779 closed gaps 1 and 3 (pre-dispatch LandInProgress guard for every
mutating verb; `frob worktree remove` with T-1739 liveness) and confirmed
gap 2 already existed (`_land_precheck`'s DirtyMain check already refuses
a land starting on top of someone else's staged content, T-1740's
callout already names the paths).

Gap 4 (from T-1779's body, "consider making the land lock advisory-
visible to a human") was intentionally left as a follow-up rather than
half-built: a `frob doctor`-style single line (or equivalent) that tells
a coordinator "a land is in progress for T-XXXX" WITHOUT running `pgrep`
or a command whose only purpose is the probe. The primitive already
exists (`frob.tickets._leases.refuse_if_land_in_progress`); this ticket
is just giving it a dedicated, side-effect-free read surface.
