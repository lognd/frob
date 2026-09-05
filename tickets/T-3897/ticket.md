---
id: T-3897
title: T-0133 degrade docs must state parity is NOT guaranteed between native and
  pure-Python parser backends (cross-ref T-3895, T-3845)
state: queued
kind: docs
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/install.md
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
T-3895 (filed 2026-09-05, critical) found the native and pure-Python parser backends produce DIFFERENT parse results for the same C file (src/stpalpha/hal/setup.c: native parses fully, pure-Python fires PARSE002). T-3845 made frob-core/strata-core DEFAULT dependencies, flipping which backend nearly every consumer lands on -- previously the population split by who installed the natives, now most get the native path by default. If the backends disagree, that packaging change silently changes gate RESULTS for existing consumers, which is a correctness concern the T-0133 honest-degrade doc does not currently address: that doc promises availability-loss is handled honestly (a clear Err, never a crash) but says nothing about CORRECTNESS PARITY between the two backends. docs/guides/install.md's degrade section needs an explicit statement of what is and is not guaranteed identical across the native and pure-Python paths, cross-referencing T-3895, until that ticket's differential test and fix land. Recommendation on sequencing (for whoever picks this up): T-3895's differential test should be treated as blocking the alpha release cut even though T-3845 has already landed the dependency default -- do not revert T-3845 (reverting just re-splits the population back to divergence-by-luck rather than fixing it), but do not cut a release before T-3895's parity work lands or is at minimum measured and disclosed.