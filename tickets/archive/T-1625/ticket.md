---
id: T-1625
title: 'strata: testsuite node declares 5277 test names as interface symbols'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: T-1623
tier: ticket
sprint: null
scope:
- design/frob.strata
- src/frob/strata/_selfconform.py
- src/frob/strata/_sync_interface.py
- tests/unit/strata/test_selfconform.py
- tests/unit/strata/test_sync_interface.py
- src/frob/strata/_code_binding.py
- src/frob/strata/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/gates/**
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: tests/**
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: design/frob.strata
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: 'narrow to files actually touched: SYS104 cross-node-reference narrowing
    (option 3) + design file regen'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/_code_binding.py
  reason: new cross-node-reference helper reuses _dotted/_join_dotted/_relative_base_dir
    from _code_binding.py
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/strata/__init__.py
  reason: 'shared worktree: __init__.py''s SYS_DUPLICATE_INTERFACE export was added
    under T-1624, still shows in T-1625''s cumulative branch diff since neither has
    landed yet'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected
- tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_duplicate_blocks_collapsed_to_one
designated_repro_test: null
threat: null
component: null
---
The `testsuite` node declares 5277 symbols in its `interface=` attr -- more than half of every interface symbol in design/frob.strata (the whole file totals roughly 9000 across all nodes; the next largest node is 919).

Those 5277 entries are test class and test function names. A test exposes nothing to anyone: no other node imports it, no consumer depends on its surface, and renaming one breaks nothing outside its own file. Declaring them as an "interface" is a category error, and it is the single largest source of noise in the self-model.

Cost: it inflates the design file threefold, it makes every sync-interface run rewrite thousands of lines (see the merge-conflict and land-noise incidents this drive), and it buries the ~3700 declarations that DO describe real cross-node surface.

Options, and the ticket should pick one with reasoning:
1. Exempt test-tree nodes from SYS104's declare-every-public-symbol obligation entirely.
2. Keep the obligation but let a node declare `interface=*` (or an explicit `interface_exempt` clearance) meaning "this node exposes no contract; do not enumerate".
3. Narrow SYS104 to symbols actually referenced across node boundaries, which would shrink every node's list, not just testsuite's.

Option 3 is the most principled and the most work; it is also the one that would fix the general problem rather than special-casing tests. Consider it seriously before defaulting to 1.

Whichever is chosen, the acceptance is that the design file describes CONTRACTS, and that a reader can see the real architectural surface without scrolling past five thousand test names.