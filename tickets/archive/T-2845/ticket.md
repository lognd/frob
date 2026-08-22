---
id: T-2845
title: Split scripts/fleet_status.py into readiness/procscan/rot submodules
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- scripts/fleet_readiness.py
- scripts/fleet_procscan.py
- scripts/fleet_rot.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestFleetStatusLarge001WaiverParses::test_waiver_still_suppresses_large001
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 930f0cf551b34de24b3d8dc3d7574ee4a3123d92
---
scripts/fleet_status.py (4121 lines) has a real, investigated seam: at least four distinguishable concerns share the file with no cross-calls between their private helpers -- (1) ticket readiness/scope-lease collision computation (leases/in_progress_ticket_scope_leases/scope_intersections/ticket_readiness), (2) /proc-based land-process/host-load/forkserver detection (land_process_rows/host_load/swap_pressure/orphaned_forkserver_count and siblings), (3) ticket-rot reporting (rotting_tickets/_print_ticket_rot and its epic/blocker helpers), and (4) the _print_* fleet-report formatting functions that compose 1-3's output for `main()`.

Extraction into sibling scripts/ modules (e.g. scripts/fleet_readiness.py, scripts/fleet_procscan.py, scripts/fleet_rot.py) was rejected in T-2824 (LARGE001 batch) purely on scope grounds: a new file is not covered by T-2824's enumerated file-list scope (no glob to grow into).

This is LOWER RISK than a package-internal split: design/frob.strata's scripts_ops node already grants scripts/** a blanket fs.write/fs.read/exec capability with no per-file declaration needed, and this script is not imported by any src/frob module (confirmed via git grep -- zero importers), so there is no external caller's import path to preserve, only fleet_status.py's own `if __name__ == "__main__": main()` entrypoint and whatever CLI docs point at `python3 scripts/fleet_status.py`.