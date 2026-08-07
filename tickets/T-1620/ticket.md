---
id: T-1620
title: Degraded-run detection misses zero-findings under-reports and sub-threshold
  mass staleness
state: queued
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/perf/**
- src/frob/app/ticket_runner/_land_cmd.py
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
This is the blocker that keeps waiver auto-delete disabled on the land path, and the reason T-1579 was reverted.

`_degraded_verification_reason` (src/frob/gates/_fix_engine.py) detects a degraded gates run from two structural signals: stale/missing natives and a skipped gate stage. It does NOT detect the case that actually keeps happening -- a gate that runs to completion and reports ZERO findings for a rule because its analysis substrate is silently under-powered.

Measured 2026-08-05 in a worktree: the perf gate reported zero PERF004 findings repo-wide (main reports many), `_degraded_verification_reason` returned None, and `_worktree_natives_verifiably_healthy` answered "healthy". Everything said the run was fine. Consequences: T-1579's escape opened and deleted 55 live waivers, and separately 4 DEPR005/DEAD001 waivers were deleted because their rules hold fewer than `_WAIVE004_MASS_INVALIDATION_THRESHOLD` (5) waivers each, so the mass-invalidation guard cannot see them at all.

Two distinct holes, both needing closing:

1. ZERO-FINDINGS UNDER-REPORT. A gate that returns zero findings for a rule the repo demonstrably trips elsewhere is suspicious. Give the perf/reach substrate (and any other gate with an optional analysis layer) a way to declare "I ran, but my analysis was degraded", and make `_degraded_verification_reason` consume it. A comparison against a recorded baseline of expected per-rule finding counts is one workable shape: a rule that historically finds N>0 and suddenly finds 0 is a degradation signal, not a clean bill of health.

2. SUB-THRESHOLD MASS STALENESS. The mass-invalidation guard is a COUNT heuristic and is structurally blind to any rule with fewer than 5 waivers. Those waivers are exactly as vulnerable, with no guard at all. Either drop the threshold to something that cannot be dodged by rarity, or make the guard proportional (all waivers of a rule going stale at once is suspicious whether that is 2 of 2 or 40 of 40 -- arguably MORE suspicious at 2 of 2).

Until both are closed, WAIVE004 auto-delete stays excluded from the land path (see the T-1592 comment in src/frob/app/ticket_runner/_land_cmd.py) and T-1579 stays queued. This ticket unblocks both; say so explicitly in its Done report.

Design note learned the hard way: "the detector found something somewhere" is NOT proof the detector worked. A partially degraded run finds some things and misses others, and that is the most dangerous state because it looks healthy from every angle we currently measure.