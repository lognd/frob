---
id: T-1175
title: 'tickets: one-verb lifecycle -- frob ticket work (setup) and land absorbing
  fmt + sync-interface + Tier-A fixes + on-main proof + finish'
state: done
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- docs/guides/agent-playbook.md
- tests/test_ticket_work_and_land_finish.py
- design/frob.strata
- src/frob/_cli_parsers/_ticket.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: new tests for the work/land--finish verbs this ticket implements
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: sync-interface + the work/land --finish argparse wiring both touch these;
    already implicitly in scope's src/frob/app/** intent
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/_cli_parsers/_ticket.py
  reason: sync-interface + the work/land --finish argparse wiring both touch these;
    already implicitly in scope's src/frob/app/** intent
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestDefaultWorkWorktree::test_slug_is_lowercased_ticket_id_under_dot_claude_worktrees
- tests/test_ticket_work_and_land_finish.py::TestWork::test_creates_worktree_merges_main_and_starts_ticket
- tests/test_ticket_work_and_land_finish.py::TestWork::test_reuses_an_existing_worktree_and_merges_main_for_freshness
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_fmt_half_canonicalizes_a_non_canonical_directive
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_real_land
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_finish_removes_the_worktree
designated_repro_test: null
acceptance:
- text: GIVEN frob ticket work T-#### WHEN run from root THEN it creates/reuses the
    named worktree, verifies base freshness against main tip, builds natives, and
    starts the ticket -- one command replacing playbook contract steps 1-2 plus start
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestWork::test_creates_worktree_merges_main_and_starts_ticket
  - tests/test_ticket_work_and_land_finish.py::TestWork::test_reuses_an_existing_worktree_and_merges_main_for_freshness
- text: GIVEN frob ticket land WHEN run THEN it first runs frob fmt on touched files,
    sys sync-interface (applying the interface diff in-land), and the T-1137 Tier-A
    fix handlers; after landing it prints a machine-checkable proof line (land hash
    + is-ancestor-of-main + ticket state on main) and offers --finish to remove the
    worktree only when every series land verifies
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_fmt_half_canonicalizes_a_non_canonical_directive
  - tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_real_land
  - tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_finish_removes_the_worktree
threat: null
component: null
---
User directive 2026-07-29: agents should only run frob commands and write content requiring actual thinking. The remaining per-ticket ritual (playbook section 0) is ~10 mechanical steps; steps 1-2, 5, and 9 are pure command sequences frob can own. This collapses them into two verbs. The playbook contract section then shrinks to: work, think, land. Absorb-not-add: reuse the existing fmt/sync-interface/fix-engine/land machinery, no new subsystems.