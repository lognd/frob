---
id: T-3306
title: 'protect-secrets F-003: only 1 of 6 reported false positives reproduced, determine
  why the other 5 did not'
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/protect-secrets.py
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
FOLLOW-UP TO F-003 (../diax FROBLEMS.md). F-003 itself was fixed directly by
the coordinator in ~/.claude/hooks/protect-secrets.py and needs no ticket for
the fix. This ticket is narrower: the ORIGINAL report claimed 6 blocked
cases (a `mv <dotenv>.example` command, and a heredoc writing prose that
merely MENTIONED the filename into FROBLEMS.md, among others), but only 1 of
those 6 was confirmed to actually reproduce against the live hook when
re-tested. The other 5 either did not reproduce, or were not re-tested.

WHAT TO DO: reproduce each of the 6 originally-reported cases against the
CURRENT (fixed) ~/.claude/hooks/protect-secrets.py (remember: this is the
materialized copy; the source is .claude/hooks/protect-secrets.py in this
repo -- edit/verify against the source per this repo's standing note that
editing the materialized copy loses fixes). For each of the 5 that did not
reproduce, determine WHY: was the original report imprecise about the exact
command text, did the fix already cover more cases than the coordinator
realized, or is there a still-live false positive the coordinator's narrow
fix missed. Write the answer up plainly -- "could not reproduce, and here is
why" is itself the deliverable if that is the honest finding.

WHAT NOT TO DO: do not assume the fix is complete just because 1 case now
passes -- the whole point of this ticket is that "5 of 6 unverified" is not
the same as "5 of 6 fine".

MUST-FIRE / MUST-STAY-QUIET: not applicable in the usual sense -- the
deliverable is a written determination per case, plus a NEW regression test
for any genuinely still-live false positive found, plus (if none are found)
an explicit statement that all 6 are now covered or were mis-reported.
