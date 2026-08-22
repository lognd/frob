---
id: T-2593
title: 'over-broad scope is disclosed but never enforced: 21 open tickets hold wildcard
  write leases, 0 acknowledged'
state: dropped
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a1d951d47d5dc095504d37cef999d845adce9e87
---
## Measured

89 open tickets. 69 declare a scope. **21 of them hold WILDCARD leases, and
all 21 have `scope_breadth_ack: false`.**

Four claim effectively the entire repository:

    T-1608  tests/**  src/frob/**  docs/**
    T-1609  docs/**   src/frob/**  tests/**
    T-1656  src/frob/**  tests/**
    T-1661  tests/**  src/frob/**

Others: T-1598 `docs/**`, T-1549 `src/frob/tickets/**`, T-2080 and T-2202
`src/frob/gates/**`, T-2251 `src/frob/_cli_parsers/**`, T-2450
`src/frob/verify/**` + `src/frob/app/ticket_runner/**`, plus the T-1599..1604
language series on `src/frob/lang/**` and `tests/fixtures/lang/**`.

## Why this is latent rather than currently burning

Leases bind only at `in-progress` (T-0453), so a queued wildcard scope
blocks nothing today. That design choice is CORRECT and should not change.

The hazard is that it is exactly one `frob ticket start` from detonating.
The moment any of those four goes in-progress it holds a write lease on
every source file, every test, and every doc in the repo, and the entire
fleet's lands begin refusing with CrossTicketLeakage until it lands. With
five or six agents running, that is a full stall, not a slowdown.

## Root cause: breadth is disclosed, never enforced

The honest acknowledged-broad channel EXISTS -- `scope_breadth_ack` plus a
mandatory `--scope-breadth-ack-reason` (WAVE14-B). Nothing requires it.

- `TICK009` is WARN severity.
- `_warn_scope_breadth_on_start` (`_lifecycle.py:1206`) states its own
  posture explicitly: "Purely a disclosure -- never blocks or exits
  nonzero".

So the measured outcome is 21 of 21 wildcard tickets never using the
channel built for them. An optional guard against a convenient default is
not a guard; the ack rate is 0%, which is what an unenforced control
predicts.

## Required fix

Make an over-broad scope REFUSE at `frob ticket start` unless
`scope_breadth_ack` is set with its reason. Keep the existing ack channel
exactly as the escape hatch -- this ticket adds enforcement, it does not
add a new mechanism, and it must not weaken `ScopeRemoveOrphansEvidence`
or any other existing guard.

Decide and document the breadth THRESHOLD by measurement, not by taste.
`large_glob_warnings`/TICK009 already compute a match count; reuse that
number rather than inventing a second breadth measure -- two measures of
the same property will desync. A repo-wide glob (`src/frob/**`, `tests/**`,
`docs/**`) should be refused without an ack regardless of threshold.

Do NOT auto-narrow a scope for the caller. Narrowing requires knowing which
files the work will touch, which the tool cannot infer; the correct
behavior is to refuse and make the author choose.

## The 21 existing tickets

Do NOT bulk-edit them in this ticket -- that would need a write lease over
every one of their ticket files, which is the same over-broad-claim problem
this ticket is about. Enforcement at `start` handles them naturally: each
gets refused when someone tries to work it, and is narrowed then, by the
person who knows what it will touch. Note that behavior in the ticket body
so the first agent to hit a refusal understands it is intended.

## Positive controls, both directions

- a ticket scoped `src/frob/**` with `scope_breadth_ack=false`: `start`
  REFUSES with a message naming the offending glob and the ack flag
- the same ticket with the ack set and a reason: `start` SUCCEEDS. Without
  this case the fix is indistinguishable from banning broad scopes
- a normally-scoped ticket (a handful of explicit files): `start` succeeds
  with no new friction and no new prompt
- a queued wildcard ticket that is never started: still blocks nothing,
  confirming the in-progress-only lease semantics are untouched

## Drop reason
- 2026-08-19: obsolete: enforcement already landed by T-1866 plus T-2446 (frob ticket start refuses an over-broad scope unless scope_breadth_ack is set with a reason, via the same large_glob_warnings/TICK009 breadth measure); verified directly in worktree, 5 of 5 positive-control tests pass (test_start_refuses_over_broad_scope, test_start_over_broad_scope_ack_bypasses_refusal, test_start_precise_scope_warns_nothing, test_start_scope_breadth_ack_flag_sets_field_before_refusal, test_start_scope_breadth_ack_without_reason_refuses); re-measured the 21 wildcard-scope tickets directly and only the 6 genuinely over-broad ones (T-1608 T-1609 T-1656 T-1661 T-1598 T-1549) fail to start unacked, narrow ones are correctly left alone; one unrelated gap found and filed separately as its own ticket rather than folded in here (absorbed by T-1866)
