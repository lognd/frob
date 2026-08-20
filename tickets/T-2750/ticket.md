---
id: T-2750
title: ARCH103 and DRIFT002 regressions introduced by T-2738's close-promotes-drafts
  fix
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
## Genuine regressions from T-2738's land

Unlike most sweep-raised findings in this repo lately, these two pass
BOTH tests and are real work.

    ARCH103   src/frob/app/ticket_runner/_close_cmd.py
    DRIFT002  src/frob/tickets/_land.py

Q1 -- do they reproduce on current main? YES, both at ERROR severity,
measured with `frob check --json --no-cache`.

Q2 -- did the blamed land touch the files? YES:

    git show --stat b864a1074
      src/frob/app/ticket_runner/_close_cmd.py | 84 ++++++++++++++
      src/frob/tickets/_land.py                | 55 ++++++++++-

Both findings carry a real `commit_sha` (b864a1074) and `ticket_id`
(T-2738), so the attribution engine connected them correctly.

## Why the distinction matters

Most quarantine batches this session were pre-existing debt surfaced by
the repaired deferred verification (T-2713/T-2715), carrying null
commit_sha and untouched files -- detection events, not regressions.
T-2732 was 137 findings of which 136 were already-waived note-severity
sites. This is the opposite case: attributed, reproducing, error-severity,
in files the land demonstrably rewrote. Do not treat it as more of the
same.

## What T-2738 was

The fix for `frob ticket close` not promoting pending `T-draft-*`
follow-ups, so a closed ticket's drafts were silently lost. Good fix,
real bug -- it added 84 lines to `_close_cmd.py` and 55 to `_land.py`,
and these two findings are the cost of that addition.

## What to do

Fix both. ARCH103 and DRIFT002 are structural rules about the shape of
the code that was added, not about whether the feature works, so this
should not require revisiting T-2738's design.

Read T-2738's own diff first -- the fix is recent and coherent, and the
right remedy is almost certainly to bring the new code into line with the
rules rather than to waive them. If either finding turns out to be a
false positive of the rule rather than a real problem with the code, that
is a legitimate outcome, but say so with the measurement and fix the rule.

## Positive controls, both directions

- both findings stop reproducing on `frob check --no-cache` after the fix
- ARCH103 and DRIFT002 still fire on a planted genuine violation of each,
  written as a real fixture -- a narrowing that silences the rule is a
  regression, and this repo has shipped that mistake before
- T-2738's own behavior is unchanged: closing a ticket still promotes its
  pending drafts, and its tests still pass

## Note

These were disposed out of quarantine against this ticket so the fleet
could keep landing. That is bookkeeping and explicitly NOT a judgement
that they are acceptable.
