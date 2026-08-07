---
id: T-1089
title: 'arch: split ticket_runner.py (3957), tickets/__init__.py (4260), tickets/_land.py
  (4762) -- T-1086 residue (refile after T-1087 id collision)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/**
- docs/design/registry/EXHAUSTIVENESS-GATE.md
- docs/modules/app.md
- docs/modules/tickets.md
- tests/system/test_cli_ticket_land.py
- tests/system/test_spawn_budget.py
- tests/test_ticket_runner_quiet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/**
  reason: 'T-1089: package split touches new file paths under ticket_runner/, plus
    the frob:doc/frob:tests edges in docs and tests that pointed at the old monolithic
    file path and needed re-pointing'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: 'T-1089: package split touches new file paths under ticket_runner/, plus
    the frob:doc/frob:tests edges in docs and tests that pointed at the old monolithic
    file path and needed re-pointing'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/app.md
  reason: 'T-1089: package split touches new file paths under ticket_runner/, plus
    the frob:doc/frob:tests edges in docs and tests that pointed at the old monolithic
    file path and needed re-pointing'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1089: package split touches new file paths under ticket_runner/, plus
    the frob:doc/frob:tests edges in docs and tests that pointed at the old monolithic
    file path and needed re-pointing'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_ticket_land.py
  reason: 'T-1089: package split touches new file paths under ticket_runner/, plus
    the frob:doc/frob:tests edges in docs and tests that pointed at the old monolithic
    file path and needed re-pointing'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_spawn_budget.py
  reason: 'T-1089: package split touches new file paths under ticket_runner/, plus
    the frob:doc/frob:tests edges in docs and tests that pointed at the old monolithic
    file path and needed re-pointing'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_ticket_runner_quiet.py
  reason: 'T-1089: package split touches new file paths under ticket_runner/, plus
    the frob:doc/frob:tests edges in docs and tests that pointed at the old monolithic
    file path and needed re-pointing'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_default_clamps_frob_tree_but_pins_runner_output
- tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_verbose_skips_the_clamp
- tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_rewrites_version_and_prepends_changelog_entry
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps
- tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_reads_head_manifest_not_worktree_disk_copy
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_parses_multiple_findings_from_errors_section
- tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn
designated_repro_test: null
acceptance:
- text: given the three files, when the splits land, then each follows the T-1072/T-1076/T-1086
    package discipline (families to private modules, surface re-exported, zero caller
    edits, directives and allowlist entries carried) and no file exceeds 2000 lines
  evidence:
  - tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_default_clamps_frob_tree_but_pins_runner_output
  - tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps
  - tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn
threat: null
component: null
---
Refile: T-1086's residue draft was renumbered to T-1087 by its land, then the SAME id was assigned to the security chain's VET-wiring filing by a concurrent land -- the splits-residue block lost the race and vanished (the T-1042/T-1043 incident class, id-allocation side; the T-1036 splice guard protects blocks, not id assignment). Content: the three remaining monsters from the T-0395 tier-2 program, smallest-first, one land per file acceptable.