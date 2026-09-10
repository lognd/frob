---
id: T-4393
title: TICK004 rot severity uses local date.today(), not UTC-deterministic across
  CI runners
state: queued
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
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
Windows-only CI (run 34415921529, head 7ad69b30f): `FAIL  gate:TICK  11 errors, 1092 warnings, 0 unresolved, 0 waived`. TICK is one of the unwaivable gate families (0 waived on every platform), so unlike DRIFT001/LARGE001 this is not a waiver-matching miss -- it is a genuine difference in what severity gets COMPUTED for the same tickets.md content on the same commit. Ubuntu and macOS pass the same gate on the same commit with these same tickets reported only at WARN.

The 11 errors are all `TICK004` (`_tick004_queue_rot`) escalations to `Severity.ERROR` at `age_days > threshold * 2` (e.g. `T-2982 (high priority) has sat queued for 15d (threshold 7d)` -- `15 > 7*2=14`), for tickets that sit exactly one day past the 2x-threshold boundary (10 plain high-priority tickets at 15d/threshold-7d, plus `T-3004`'s decomposed-but-stalled-children branch, which uses the same age-driven severity). `age_days = (today - t.created).days` where `today = date.today()` (`src/frob/gates/_tickets_gate.py:444`) reads the LOCAL system clock, not a UTC-anchored date. A local-time read is not guaranteed to agree across CI runner images/timezones for jobs dispatched from the same matrix at (near-)the same wall-clock instant -- a one-day skew right at a rot threshold's 2x boundary is exactly enough to flip a WARN into an ERROR on one platform while every other platform in the same run reports WARN for the identical ticket.

Fix: make `_tick004_queue_rot`'s "today" (and the same pattern at `_tickets_gate.py:1714`'s `date.today()` LEDGERV1 sunset check, if it has the same platform-dependent-local-time shape) deterministic and platform-independent -- anchor on `datetime.now(timezone.utc).date()` (or an explicitly injected/UTC clock) rather than the bare local `date.today()`, so the same commit produces the same TICK004 severity on every platform regardless of local runner timezone. Add a test that freezes/injects a UTC "today" exactly at a 2x-threshold boundary and asserts the same severity regardless of the local system timezone (e.g. patch `time.tzset`/`TZ` env, or mock the clock, to a non-UTC zone and assert no change in computed severity).
