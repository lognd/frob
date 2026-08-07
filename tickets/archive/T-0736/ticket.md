---
id: T-0736
title: 'scaffold conformance: managed boilerplate blocks (Makefile shim, guard hooks,
  gitignore) drift-checked by doctor across all repos'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/scaffold/**
- src/frob/doctor.py
- docs/**
- src/frob/app/**
- src/frob/__main__.py
- Makefile
- .gitignore
- tests/unit/test_scaffold_managed.py
- tests/system/test_cli_scaffold_apply.py
- tests/system/test_cli_doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/**
  reason: replay of worktree scope trail on main-schema ledger (old parser could not
    run ledger ops post-merge)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/doctor.py
  reason: replay of worktree scope trail on main-schema ledger (old parser could not
    run ledger ops post-merge)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/app/**
  reason: replay of worktree scope trail on main-schema ledger (old parser could not
    run ledger ops post-merge)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/__main__.py
  reason: replay of worktree scope trail on main-schema ledger (old parser could not
    run ledger ops post-merge)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: Makefile
  reason: replay of worktree scope trail on main-schema ledger (old parser could not
    run ledger ops post-merge)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .gitignore
  reason: replay of worktree scope trail on main-schema ledger (old parser could not
    run ledger ops post-merge)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/test_scaffold_managed.py
  reason: replay of worktree scope trail on main-schema ledger (old parser could not
    run ledger ops post-merge)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/system/test_cli_scaffold_apply.py
  reason: replay of worktree scope trail on main-schema ledger (old parser could not
    run ledger ops post-merge)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: replay of worktree scope trail on main-schema ledger (old parser could not
    run ledger ops post-merge)
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_scaffold_managed.py::TestScaffoldConformanceStatus::test_clean_after_apply
- tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::test_creates_missing_and_updates_stale
- tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::test_idempotent_second_run_is_noop
- tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::test_refuses_to_clobber_foreign_hook
- tests/system/test_cli_scaffold_apply.py::TestScaffoldApplyCli::test_apply_reports_changes
- tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_unhealthy_when_scaffold_blocks_missing
- tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_healthy_after_scaffold_apply
designated_repro_test: null
acceptance:
- text: GIVEN a repo missing the current guard hooks or Makefile shim WHEN frob doctor
    runs THEN a finding names each missing/stale managed block with frob scaffold
    apply as remedy; GIVEN apply runs THEN the repo conforms idempotently AND this
    repo itself passes the check
  evidence:
  - tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_unhealthy_when_scaffold_blocks_missing
  - tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_healthy_after_scaffold_apply
threat: null
component: null
---
User directive 2026-07-22: per-repo boilerplate keeps being fixed per-repo (T-0732 Makefile; T-0574's install_worktree_lease_hook/install_stash_guard are library calls bootstrapped NOWHERE -- the incidents happened in this very repo and it still lacks the guards). Structural fix, mirroring the deploy script<->model drift-lock pattern frob already owns: (1) scaffold templates define MANAGED BLOCKS (marked regions: Makefile core-shim, .gitignore standard entries, hook/guard installs) versioned with frob; (2) "frob scaffold apply" idempotently installs/updates the managed blocks + hooks in any repo; (3) doctor (or a SCAF gate) reports when a repo's managed blocks are missing/stale vs the installed frob version -- so every repo in the estate gets TOLD when it lacks current standards instead of silently rotting; (4) bootstrap THIS repo via the new command as the first consumer (closing T-0574's reviewer flag); (5) at close, file per-sibling adoption tickets via frob fleet route (real filings, TICK006 applies).