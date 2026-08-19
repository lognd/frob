---
id: T-2623
title: roughly 19 tests are red on unmodified main, hiding real regressions in the
  noise
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: measurement and triage only; any fixes land as separately-scoped
  follow-up tickets
scope_changes:
- op: remove
  glob: tests/unit/
  reason: 'triage ticket: the deliverable is a published list plus per-group follow-up
    tickets, not edits across 448 test files'
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Reported measurement

While fixing T-2602 (one red test), the agent ran the FULL `tests/unit/`
selection against unmodified main and found **20 red tests**. It grepped
every failure for the T-1995 duplicate-title guard signature ("closely
match this title"), which appeared exactly ONCE -- the test T-2602 fixed.

The other 19 are a different, pre-existing failure class. Reported shapes:
renumber-CLI `SystemExit` behavior, strata self-conform / golden-export
drift, and others not enumerated.

This count is the agent's measurement, not independently re-verified by the
coordinator, because a full `tests/unit/` run exceeds the foreground budget.
FIRST TASK on this ticket is to re-measure and publish the exact list --
treat 19 as an estimate until you have the names.

## Why this matters

`frob test` and touched-set selection are the primary verification agents
rely on, and they are trusted precisely because red means something. With
19 tests red on unmodified main:

- an agent whose change touches one of them cannot distinguish "I broke
  this" from "it was already broken", and the cheap resolution is to assume
  the latter
- a genuinely new failure hides in the noise
- one of these was red for days before anyone noticed (T-2602's), and it
  was found only because an agent happened to run an out-of-scope file and
  mentioned it in prose

This is the broken-windows shape: the signal degrades until nobody reads it,
and then a real regression lands silently.

## What to do

1. Re-measure. Publish the exact list of red tests with their failure
   signatures, grouped by apparent cause. That list is the deliverable even
   if nothing gets fixed in this ticket.
2. Classify each: genuinely broken product code, stale fixture/test, or
   environment artifact (a fresh worktree lacking built native extensions
   produces collection/evidence failures that are NOT regressions -- rule
   those out explicitly rather than counting them).
3. Fix or file per group. Groups large enough to be their own work get
   their own tickets; do not silently fold ten unrelated fixes into one
   land.

## What NOT to do

- Do NOT xfail, skip, or delete tests to reach green. A skipped test is a
  deleted test with extra steps, and this repo has already paid for a
  guard being weakened to make a fixture pass.
- Do NOT weaken a guard or detector because its own test fixture predates
  it. T-2602's correct fix was updating the FIXTURE; the guard was right.
- Do NOT count environment artifacts as fixed by rebuilding your worktree
  and declaring green -- state them as environment-dependent explicitly.

## Positive controls, both directions

- after this ticket, `tests/unit/` on unmodified main is either fully green
  OR every remaining red test is named in a filed ticket with its cause --
  no unaccounted red
- a deliberately broken test still FAILS and is still reported. Without this
  the fix is indistinguishable from suppressing the suite
- the count is stated against a known denominator (N red of M collected),
  never as a bare "fixed the failures"
