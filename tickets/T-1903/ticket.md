---
id: T-1903
title: Pre-land strata parse guard runs BEFORE the Tier-A rewrite, so it cannot catch
  corruption the rewrite itself introduces
state: queued
kind: bug
origin: agent
created: '2026-08-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09 by the T-1900 implementer, read directly from src/frob/app/ticket_runner/_land_cmd.py.

Inside _absorb_pre_land_fixes, the call order is:

  _assert_design_loads_pre_land(...)   <- synchronous parse guard on design/frob.strata
  _tier_a_pre_land_step(...)           <- the step that REWRITES design/frob.strata

The guard validates the file's state BEFORE the rewrite that can corrupt it. It therefore structurally cannot catch corruption introduced by the Tier-A pass itself -- which is exactly the T-1900 incident: SYS-IFACE-ORDER re-rendered an empty 'attr interface=[];' into an unparseable block, the land emitted 'strata parse failed' to stderr, and STILL printed 'LAND-PROOF verified=True' and reported success. main was left with an unparseable self-model three times running.

WHY THIS IS CRITICAL SEPARATELY FROM T-1900. T-1900 fixes the one handler that happened to corrupt the file. THIS ticket is about the guard that was supposed to make any such handler bug impossible to publish. Fixing only T-1900 leaves the next corrupting Tier-A handler equally free to land: the check exists, runs, passes, and proves nothing about the artifact actually committed. A verification that runs before the mutation it is meant to verify is not a weaker check -- it is a false green, and false greens are worse than no check because they are trusted.

REQUIRED FIX:
1. Re-run the design-parse assertion AFTER _tier_a_pre_land_step (keep the before-check too if it gives a better error message for pre-existing breakage -- the point is that the AFTER check must exist).
2. A post-rewrite parse failure must REFUSE the land, not warn. Landing an unparseable self-model silently degrades every sys/SELFAUDIT gate downstream.
3. Audit _absorb_pre_land_fixes for any OTHER guard sequenced before a mutation it is meant to cover -- this is a class of bug, and one instance of it usually means the ordering was never treated as load-bearing.
4. Regression test: a Tier-A handler that deliberately emits unparseable output must cause the land to FAIL, with the failure naming the handler.

Related: T-1900 (the handler bug this failed to catch), T-1872 (introduced that handler).