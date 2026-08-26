---
id: T-1607
title: 'Language expansion: remaining ranked languages, in research-recommended batches'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: low
parent: T-1597
tier: ticket
sprint: post-1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-1607/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/lang/**
  reason: 'T-2446: explicitly a decomposition-pending placeholder (''split into further
    child tickets rather than attempting all at once -- this ticket is the placeholder
    the research output turns into a concrete plan''); narrowing the parent to its
    own ledger shard, real file scopes belong to the not-yet-filed batch children'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: docs/**
  reason: 'T-2446: explicitly a decomposition-pending placeholder (''split into further
    child tickets rather than attempting all at once -- this ticket is the placeholder
    the research output turns into a concrete plan''); narrowing the parent to its
    own ledger shard, real file scopes belong to the not-yet-filed batch children'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/**
  reason: 'T-2446: explicitly a decomposition-pending placeholder (''split into further
    child tickets rather than attempting all at once -- this ticket is the placeholder
    the research output turns into a concrete plan''); narrowing the parent to its
    own ledger shard, real file scopes belong to the not-yet-filed batch children'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tickets/T-1607/**
  reason: 'T-2446: explicitly a decomposition-pending placeholder (''split into further
    child tickets rather than attempting all at once -- this ticket is the placeholder
    the research output turns into a concrete plan''); narrowing the parent to its
    own ledger shard, real file scopes belong to the not-yet-filed batch children'
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: cannot split without T-1598's deferred research output; do not manufacture
    a ranking to unblock
  actor: logan
  at: '2026-08-19'
  old_length: 714
  new_length: 1417
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Implement the remaining ranked languages from the research ticket's target list, in the batch order it recommends, after the five named languages have proven the contract.

Split into further child tickets per batch rather than attempting all at once -- this ticket is the placeholder the research output turns into a concrete plan. Each batch must clear the parameterized adapter conformance suite before the next begins.

Expect the cost per language to FALL sharply after the first few if the contract is right, and to stay flat if it is wrong. A flat cost curve is the signal that the contract ticket did not actually succeed and should be revisited before continuing -- report it rather than grinding through.

Cannot be meaningfully split yet: this ticket's own job is to turn
T-1598's research output (the ranked 20-50 language list, sourced
across TIOBE/RedMonk/Octoverse/SO/IEEE Spectrum, with the recommended
batch order) into concrete per-batch child tickets. T-1598 was
deliberately deferred -- it requires live multi-source web research and
must not be attempted from model memory (see T-1598's own body note).

Manufacturing a batch order or a language ranking here to unblock this
ticket would be the exact mistake T-1598's deferral was meant to
prevent, just one ticket downstream. Leaving this queued, untouched,
until T-1598 actually produces its research output. No child tickets
filed this round.
