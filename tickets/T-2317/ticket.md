---
id: T-2317
title: wire T-2310's spawn_deferred_drain into the land call site (blocked by T-2303
  lease during T-2310)
state: done
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets-verify-sweep.md
- tests/unit/test_land_cmd_drain_wiring.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_cmd_drain_wiring.py
  reason: T-2317 wiring test
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_real_rapid_land_spawns_both_sweep_and_drain
- tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_dry_run_spawns_neither
- tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_no_commit_sha_spawns_neither
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 632bc2d02c89d179614690a3d4f80bafac69170f
---
T-2310 implemented the automatic watermark-drain machinery in full
(frob.verify._drain: spawn_deferred_drain, run_drain_async, DrainError;
frob verify drain-async CLI verb; tests/unit/verify/test_drain.py with
all 4 coordinator-required positive controls passing) but could NOT wire
the actual trigger call site: frob.app.ticket_runner._land_cmd's
_land_core_finish_post_land (the rapid-land branch, alongside the
existing spawn_deferred_post_land_sweep call) is the one remaining call
site, and both _land_cmd.py and _rapid_sweep.py were held under a live
cross-worktree scope lease by T-2303 for T-2310's entire duration.

This is a two-line change:

    if rapid_land:
        if not report.dry_run and report.commit_sha is not None:
            from frob.app.ticket_runner._rapid_sweep import (
                spawn_deferred_post_land_sweep,
            )

            spawn_deferred_post_land_sweep(
                root, cfg.ticket_id, report.final_id, report.commit_sha
            )
            # T-2310: fire the automatic watermark drain alongside the
            # existing sweep spawn -- same call site, same "detached,
            # never gates the land" posture.
            from frob.verify._drain import spawn_deferred_drain

            spawn_deferred_drain(root, cfg.ticket_id)
        return Ok(report)

Acceptance:

1. `spawn_deferred_drain` is called from `_land_core_finish_post_land`'s
   rapid-land branch, immediately after `spawn_deferred_post_land_sweep`,
   with the same guard (`not report.dry_run and report.commit_sha is not
   None`).
2. A test asserts the drain is spawned on a real rapid land (mirroring
   whatever existing test covers the sweep spawn at this call site).
3. `docs/modules/tickets-verify-sweep.md`'s "Automatic watermark drain"
   section's own closing paragraph (which names this exact gap) is
   updated to remove the "deliberately does NOT change" caveat once this
   lands.

No design decision remains open -- frob.verify._drain's own module
docstring records the full five-constraint decision from the coordinator
verbatim. This is pure wiring, safe to do the moment src/frob/app/
ticket_runner/_land_cmd.py and _rapid_sweep.py are free of T-2303's
lease.