---
id: T-2083
title: Post-merge land verification still fails open on two unmeasured paths; a Done
  report missing its Captured claims section skips verification entirely
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'given a Done report with no ### Captured claims section, when frob ticket
    land runs its post-merge re-verification, then the outcome is recorded and surfaced
    as SKIPPED-UNMEASURED rather than silently passing -- this test MUST fail against
    current main'
  evidence: []
- text: given passing_ids or check_gates is None, when re-verification runs, then
    the skip is surfaced with its reason rather than returning a clean result indistinguishable
    from a real pass
  evidence: []
- text: given any skipped verification, when LAND-PROOF is emitted, then verified=True
    is not reported for a claim that was never actually measured
  evidence: []
- text: given the change is proposed, when the frequency of missing Captured claims
    sections across recent lands is counted, then that number is recorded in the ticket
    BEFORE any refusal behaviour is enabled
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
---
## Context

T-2076 (landed `062a9877a`) fixed ONE instance of a defect class: the
land-time verification treated "could not measure" as "found nothing", so a
branch introducing new error-severity findings landed unblocked from any
agent shell. `_refuse_full_check_for_agent` (T-0627) was working exactly as
designed; the bug was one layer up, in verification code reading an empty
result as a clean result.

That was the measured mechanism behind T-1584 landing 8 error-severity
findings under a Done report that read "land-parity: clean -- 0 unscoped
error(s)".

## The remaining sites, enumerated (not guessed)

T-2076's agent read `src/frob/tickets/_land_verify.py` while diagnosing and
listed every unmeasured-to-`Ok(None)` skip it found. Two are closed by
T-2076's fix; two are NOT, and are the subject of this ticket:

STILL OPEN:
  1. `_reverify_done_report_claims_post_merge`:
     `passing_ids is None or check_gates is None` -> skip
  2. `_reverify_done_report_claims_post_merge`:
     no `### Captured claims` section present in the Done report at all
     -> skip

CLOSED BY T-2076 (recorded so nobody re-fixes them):
  3. `_reverify_gate_state_claim`: `claims.gate_errors is None` -- the claim
     was already unmeasured at done-report capture time, same
     `_shared_check_spawn_fn` closure, so T-2076's fix closes this going
     forward too
  4. `_reverify_gate_state_claim`: `fresh is None` -- the exact site T-2076
     fixed

## Why site 2 is the serious one

A Done report that simply lacks a `### Captured claims` section causes the
entire post-merge re-verification to be skipped. That means the way to
bypass verification is to omit a section -- an absence, not an action.
Nothing refuses, nothing warns, and the land reports success. An agent that
hand-writes a Done report in a slightly different shape silently loses its
own verification, and neither it nor the operator learns that anything was
skipped.

Note the repo has an adjacent precedent for exactly this reasoning: LAND-PROOF
reports `verified=True` on ancestry alone, and has done so on a commit
containing none of the ticket's code. "Verified" must mean something was
actually checked.

## DO NOT FIX IT THIS WAY

- **Do not make a missing/unmeasurable claim a hard land refusal without
  first measuring how often it fires.** If a large fraction of current Done
  reports lack the section, flipping it to refuse would stop the fleet. Count
  first, across recent lands, and report the number BEFORE changing
  behaviour. If it is common, the correct first step is loud, attributed
  surfacing plus a metric, then tightening once the count is near zero.
- **Do not fix this by making the Done report format stricter for agents.**
  A format rule agents must remember is not enforcement -- this session has
  already established that a written rule which was not followed is not the
  fix. Prefer generating or validating the section mechanically.
- **Do not treat "skipped" and "passed" as the same outcome in any log line,
  summary, or LAND-PROOF field.** The whole defect class is those two being
  indistinguishable to a reader. A skip must be visibly a skip.
- **Do not add another full `frob check` spawn.** Land cost is already the
  fleet's throughput ceiling (~210s inside the land lock, and
  `_LAND_LOCK_TIMEOUT_S`=600s exceeds the 540-580s shell cap, so a slower
  land is SIGKILLed with no diagnostic -- that is T-2065).

## The general rule

Ask of every guard what it does when its input is MISSING, not merely bad.
Empty output, a refused subprocess, a failed git call, a truncated budget --
if any of those routes to "nothing found", the guard fails open. This repo
has now hit that shape at three separate layers: the sweep reporting CLEAN on
a dirty tree (T-1703), a grep on an errored command reading as a genuine
zero, and this one.
