---
id: T-2731
title: 137 pre-existing ARCH/PERF findings surfaced by the first honest verification
  run (misblamed on T-2723's land)
state: dropped
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
## What this is

The 137 ARCH/PERF findings that the deferred verification raised into
quarantine at 2026-08-20T08:32Z, blamed on batch `b35f47220` (T-2723's
land).

    PERF004  54     ARCH103  24     ARCH001  22
    ARCH102  15     PERF003  15     PERF002   5
    E501      1     PERF001   1
    -----------------------------------------
    total   137 findings across 116 files

## They are real, and the blame is wrong

Measured: `b35f47220` touched exactly ONE source file
(`src/frob/gates/_gate_cache.py`). Of the 116 files carrying quarantined
findings, **0 were touched by it**. Every finding also carries
`commit_sha: null` and `ticket_id: null` -- the attribution engine could
not connect any of them to a commit, which is correct, because they
predate the batch.

So: real pre-existing debt, wrongly presented as a regression from one
land. This ticket is their home. Quarantine is not a home -- an
undisposed finding blocks deferred landing repo-wide.

## Why they surfaced now, all at once

This is a CONSEQUENCE OF FIXING VERIFICATION, not a new regression.
Before T-2713 and T-2715 landed, the deferred verification ran under a
budget that silently dropped most gate families and recorded a rolling
baseline of TWO findings against a tree that genuinely had ~40 error
identities. It reported GREEN and advanced the watermark regardless.

With both fixed, the first complete verification saw the real floor for
the first time and raised all of it. That is the machinery working. But
it means the FIRST honest run after repairing a measurement will always
look like a catastrophic regression, and the quarantine mechanism has no
way to tell "newly detected" from "newly introduced".

That distinction is worth building: a finding whose file was untouched by
the blamed batch, with a null commit_sha, is a DETECTION event, not a
regression event. Consider whether quarantine should raise on those at
all, or should raise separately and not block landing.

## What to do with the 137

Work them as ordinary debt, grouped by rule -- PERF004 and ARCH103/ARCH001
dominate and are likely a small number of underlying causes rather than
137 independent problems. Where a group shares one cause, fix the cause
and report the group; that is what T-1614's audit did for its two waiver
groups (see T-2719, T-2720).

Do NOT dismiss them wholesale. They were disposed out of quarantine
against THIS ticket so the fleet could keep landing; that disposal is a
bookkeeping move and explicitly not a judgement that they are acceptable.

## Positive controls for any fix in this set

Per rule group: the finding must stop reproducing at the named site, AND
a planted genuine violation of that rule must still fire. A narrowing fix
that stops detecting anything is a regression -- this repo has shipped
that mistake before.

## Drop reason
- 2026-08-20: Duplicate-with-a-named-survivor, NOT a false positive: I filed T-2731 for the 137 quarantined ARCH/PERF findings moments before the rapid sweep auto-filed the identical set as T-2732. Same 137 findings, same 116 files. T-2732 survives because the quarantine's own cleared_reason references it; T-2731's analysis (the misattribution measurement and the detection-vs-regression distinction) has been appended to T-2732 verbatim, so nothing is lost. (absorbed by T-2732)
