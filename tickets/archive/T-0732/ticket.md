---
id: T-0732
title: 'worktree warm pool: shared cargo target/native wheel cache + pre-warmed worktrees'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/scaffold/**
- docs/guides/**
- tests/integration/test_interfaces.py
- tests/system/test_cli_doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/integration/test_interfaces.py
  reason: 'Makefile/docs-only ticket: evidence is the sanctioned pre-existing CLI-dispatch
    + doctor-natives tests (playbook section 5); close requires them in scope'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: 'Makefile/docs-only ticket: evidence is the sanctioned pre-existing CLI-dispatch
    + doctor-natives tests (playbook section 5); close requires them in scope'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present
designated_repro_test: null
acceptance:
- text: GIVEN a fresh worktree after the change WHEN make core runs THEN it completes
    in under 10s with warm shared cache (measured), and a cold clone still builds
    correctly
  evidence: []
threat: null
component: null
---
User directive 2026-07-22: kill the make core cold-build boilerplate (minutes per fresh worktree, ~30 worktrees today; T-0340 fixed re-eviction at 0.6s steady-state but not cold starts; T-0175s Done report has the investigation). Deliver: (1) shared CARGO_TARGET_DIR (or maturin wheel cache) keyed per clone so a fresh worktree's make core reuses compiled artifacts -- target seconds, measure before/after; (2) optionally a warm pool: frob scaffold pool N pre-creates worktrees with natives built + main merged, agents lease from the pool, a background refresh re-warms after lands. (1) alone captures most of the win; (2) is the stretch.