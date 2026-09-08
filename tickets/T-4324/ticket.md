---
id: T-4324
title: frob verify status and ticket show hide live rapid-debt.jsonl sweep-deferred
  debt
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/verify_runner.py
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
Found while working T-4318 (which is scoped to src/frob/app/ticket_runner/_land_cmd.py
and src/frob/app/ticket_runner/_rapid_sweep.py -- the deferred-sweep budget fix --
and cannot house this fix; the ticket author's own SECOND DEFECT paragraph names
a separate scope: src/frob/app/verify_runner.py and/or src/frob/verify/_watermark.py,
wherever frob verify status's "unverified depth" is computed, plus wherever
rapid-debt.jsonl entries are read back).

MEASURED (2026-09-08): .frob/rapid-debt.jsonl carries 5 live
skipped: post-land-unscoped-sweep-deferred entries (T-4197, T-4301, T-4305,
T-4306, T-4307) that were never cleared or promoted because their deferred
sweep reported UNMEASURABLE (see T-4318). Yet:

- `frob ticket show T-XXXX` for all 5 tickets prints only `[done]`, no
  unverified/debt marker at all.
- `frob verify status` reports "unverified depth (queued land-intents): 0"
  and "quarantine: clear" -- both read clean despite the 5 live debt entries.

An UNMEASURABLE sweep currently reaches nobody outside a log file nobody
reads. A commit that stays unverified needs to be visible wherever a
verified result would be: in `frob ticket show`'s status line, and in
`frob verify status`'s unverified-depth/quarantine summary.

FIX DIRECTION (not dictated): read .frob/rapid-debt.jsonl's live
(uncleared/unpromoted) skipped: post-land-unscoped-sweep-deferred entries
into both surfaces above -- `frob ticket show` should print something
besides a bare `[done]` for a ticket with a live debt entry, and
`frob verify status`'s "unverified depth" count should include them.

T-4318 partially addresses the root cause (the deferred sweep's --budget
truncation) by passing full=True to _unscoped_error_findings for the
detached sweep child, which should sharply reduce how often this debt is
created going forward -- but does not fix the status-visibility gap for
debt that is created (whether by a genuinely wedged full check, a refused
spawn, or historical entries already in rapid-debt.jsonl).
