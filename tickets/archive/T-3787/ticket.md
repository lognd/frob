---
id: T-3787
title: 'frob land: support landing onto a non-main target branch (unblocks off-main
  v1.0.0 dev after alpha)'
state: done
kind: feature
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_models.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/_config_external.py
- tests/ticket_land_suite/test_land_target_branch.py
- docs/modules/tickets-landing.md
- tests/ticket_land_suite/test_verify_intent.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-3787: land --branch/--onto target-branch support + config default; touches
    land flow, models, CLI arg, config field, LAND-PROOF, tests, docs'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-3787: land --branch/--onto target-branch support + config default; touches
    land flow, models, CLI arg, config field, LAND-PROOF, tests, docs'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-3787: land --branch/--onto target-branch support + config default; touches
    land flow, models, CLI arg, config field, LAND-PROOF, tests, docs'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: 'T-3787: land --branch/--onto target-branch support + config default; touches
    land flow, models, CLI arg, config field, LAND-PROOF, tests, docs'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-3787: land --branch/--onto target-branch support + config default; touches
    land flow, models, CLI arg, config field, LAND-PROOF, tests, docs'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/ticket_land_suite/test_land_target_branch.py
  reason: 'T-3787: land --branch/--onto target-branch support + config default; touches
    land flow, models, CLI arg, config field, LAND-PROOF, tests, docs'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-3787: land --branch/--onto target-branch support + config default; touches
    land flow, models, CLI arg, config field, LAND-PROOF, tests, docs'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/ticket_land_suite/test_verify_intent.py
  reason: 'T-3787: _land_proof_checks gained a target_branch kwarg (LAND-PROOF ancestry
    now checks the real land target); this test stubs that function and its lambda
    must accept the new kwarg'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: design/frob.strata
  reason: 'T-3787: new land-suite test file exercises fs.write + exec (subprocess)
    capabilities; declare it in the testsuite node''s capability via-lists (SELFAUDIT001)'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: 'T-3787: exec+fs.write via-list ratchet ceilings bumped +1 for the new land-suite
    test file (SYS111)'
  actor: logan
  at: '2026-09-05'
body_changes:
- mode: append
  reason: capture branch-landing requirement + post-alpha release-hygiene rationale
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 1273
evidence:
- tests/ticket_land_suite/test_land_target_branch.py::TestLandOntoNonMainBranch::test_real_land_onto_dev_lands_on_dev_not_main
- tests/ticket_land_suite/test_land_target_branch.py::TestDefaultTargetUnchanged::test_default_land_targets_main_and_reports_main
- tests/ticket_land_suite/test_land_target_branch.py::TestTargetBranchRefusals::test_missing_target_branch_refuses
- tests/ticket_land_suite/test_land_target_branch.py::TestTargetBranchRefusals::test_target_branch_root_is_not_on_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

frob's land flow is currently hardcoded to land onto `main` (src/frob/tickets/_land.py, "squash-apply onto main"), and the root-write guard forces all work through leased worktrees off main. This ticket adds support for landing a ticket's worktree onto a configurable NON-MAIN target branch.

## Why (release hygiene, user directive 2026-09-04)

After the alpha (a green release), remote `main` must stay frozen at that green release -- NOT dirtied by new development -- until a SECOND green release with more functionality is confirmed. This feature lets post-alpha v1.0.0 development land onto a dedicated dev branch (with full frob gates/accounting) instead of main, so the published remote main stays green while new work accumulates and is proven, then merged/pushed only when the second release is green.

## Sequencing

Deferred until AFTER the alpha is cut. Pre-alpha work (win32 drain to real-green, flaky layer) takes priority. This is the first defined v1.0.0 feature.

## Acceptance (sketch)

- `frob ticket land` accepts a target branch (flag or config), defaulting to main (backward compatible).
- Land-proof / ledger / gates operate against the chosen target branch, not assuming main.
- The root-write guard and worktree flow remain intact.