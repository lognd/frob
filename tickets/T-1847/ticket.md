---
id: T-1847
title: Warm-tree re-check before raising quarantine on an UNATTRIBUTED finding
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
found while working T-1697: frob verify status/dispose end-to-end validation against the live quarantine (unresolved-import at tests/unit/strata/test_capacity.py, unattributed) confirmed the dispose path works, but surfaced a design gap in _raise_quarantine_for_red_batch: an UNATTRIBUTED finding raises quarantine unconditionally, same as an attributed one. That is correct in principle (cannot-verify is never verified), but in practice an unattributed finding whose shape looks like cold-worktree native-extension noise (unresolved-import, no commit in the batch reaches it) raises quarantine on every fresh worktree's first check, training operators to dismiss reflexively -- which erodes the signal for the real finding the breaker exists to catch. Add a warm-tree re-check specifically for the UNATTRIBUTED+native-extension-adjacent shape before persisting the raise, so cold-worktree noise does not reach a human's dispose queue at all.