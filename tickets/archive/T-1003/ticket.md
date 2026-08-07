---
id: T-1003
title: 'land ergonomics: resolve root from any cwd + internal uv.lock reset (kill
  the pre-land ritual)'
state: done
kind: ux
origin: human
created: '2026-07-27'
priority: medium
parent: T-0999
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner.py
- tests/test_ticket_land.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: 'The root-resolution change to land() itself (not just its CLI wrapper)

    triggers AFFECT001 against its docs/modules/tickets.md#frob-ticket-land

    doc anchor -- documenting the new step 0 (root resolution) and the

    amended steps 3/9.8 (worktree-side uv.lock reset, stacked-sibling

    absorption) requires touching that one doc file to close the drift this

    ticket''s own code change created.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_ticket_land.py::TestLandChainedCdRootResolution::test_root_equal_to_a_real_linked_worktree_resolves_and_lands
- tests/test_ticket_land.py::TestLandChainedCdRootResolution::test_root_equal_to_the_primary_checkout_itself_still_refuses
- tests/test_ticket_land.py::TestUvLockSync::test_worktree_side_lock_flap_auto_restored_before_wip_commit
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse
- tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake
designated_repro_test: null
acceptance:
- text: given a shell whose cwd is inside the worktree and flapped uv.lock files on
    both sides, when frob ticket land runs, then it lands correctly with no manual
    checkout or cd
  evidence:
  - tests/test_ticket_land.py::TestLandChainedCdRootResolution::test_root_equal_to_a_real_linked_worktree_resolves_and_lands
threat: null
component: null
---
Churn item 4 (~15 occurrences): every land needs git checkout -- uv.lock on both sides plus cd-to-root (the root==worktree guard fires on chained cds). Land should resolve the primary checkout from the worktree git common dir itself regardless of cwd, and perform the uv.lock flap reset internally on both sides before the dirty check, making `frob ticket land T-x --worktree <p>` correct from anywhere with no ritual.