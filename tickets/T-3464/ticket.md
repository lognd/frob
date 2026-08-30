---
id: T-3464
title: 'verify watermark stuck at 00a415c978ec: quarantine re-raises every drain cycle,
  blocking every land repo-wide'
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
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
found while landing T-3449 (a plain ticket-state drop with zero code diff).

MEASURED: frob verify status shows watermark=fcd61039d608373ae5d8138ed4bb0532653c62c2, oldest unverified=00a415c978ec155c6a46bbb0582ab996dc927f58 (ticket T-3399), age >3000s, commits-since-watermark=13-15 and climbing. Every land attempt (and a direct 'frob verify now') re-derives the SAME 5 findings for this one commit:
  COV003 tests/unit/test_scaffold_project.py
  SELFAUDIT001 src/frob/gates/_policy_weakening_gate.py
  SELFAUDIT001 tests/unit/strata/test_strata_core_gil.py
  SELFAUDIT001 tests/unit/test_sync_claude_config_stale_guard_t3408.py
  SELFAUDIT001 tests/unit/verify/test_worker.py

Each of these 5 findings is repeatedly logged as 'rapid sweep: 5 of 5 new identities no longer reproduced at file time (T-3222) -- recorded as rapid debt, NOT filed as a ticket', immediately followed by 'verify worker: 5 new finding(s) ... could NOT be filed -- watermark NOT advanced (ownerless, T-2324's own hard constraint: never silently certify this)'. So the watermark can never advance past 00a415c978ec: the findings are transient/non-reproducing (correctly not filed as regressions per T-3222), but T-2324's ownerless-finding constraint refuses to let that same non-filing ALSO advance the watermark, so the exact same 5 phantom findings get re-derived and re-quarantined on every single verify cycle -- forever, until a human manually runs 'frob verify dispose' each time (which I did once; the very next verify_now cycle re-raised the identical quarantine).

This is a structural livelock: T-3222 (don't file vanished findings) and T-2324 (don't silently advance the watermark past unfiled findings) are individually correct but together mean this watermark position can NEVER progress on its own. It currently blocks EVERY land in the repo (T-3449's land failed twice on this before I found and manually cleared it once with frob verify dispose; it will re-raise for the next agent's land attempt too since the watermark is still stuck at the same commit).

SUGGESTED FIX (not attempted -- outside this discovery's scope/budget): give T-2324's ownerless-finding path a way to advance the watermark specifically when the SAME finding set has already been dismissed/found-non-reproducing N times in a row (or persist the dispose decision so the identical batch is not re-derived), rather than re-deriving and re-raising an identical quarantine on every cycle indefinitely.