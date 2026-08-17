---
id: T-2310
title: rapid profile needs a real verification-debt drain mechanism (design decision
  deferred from T-2290)
state: queued
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2290 fixed (c) the unverified-depth/commits-since-watermark reconciliation
and (b) a soft, non-blocking rapid-profile warning once verification debt
crosses a threshold (frob.verify._backpressure.rapid_soft_warning), but
explicitly did NOT implement direction (a): an actual drain mechanism
that advances the watermark on a cadence independent of a land (idle-time
sweep, explicit `frob verify drain`, or a coordinator-invoked catch-up).

Right now the warning this ticket added has nowhere to point an operator
except "run `frob verify now` by hand" -- which requires an operator to
notice the warning AND remember the command exists (the standing
"automatic over commands" directive this repo already holds: a command
requires knowledge of the command). Without a real drain, a rapid-profile
repo can accumulate unbounded verification debt forever, loudly warned
about but never actually resolved automatically.

This needs a design decision (which of the three drain shapes, and how it
interacts with the existing coalescing worker in frob.verify._worker) that
T-2290's own dispatch explicitly deferred rather than guessed at.
