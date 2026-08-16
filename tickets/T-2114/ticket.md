---
id: T-2114
title: Rapid land does not gate the doc/test-edge families on symbols the land itself
  adds, so every new public symbol reds the floor until a deferred sweep catches it
  (T-1907's fix applied to one family only)
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
evidence_scope:
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_no_edges_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_both_edges_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_empty_touched_set_is_a_no_op
designated_repro_test: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
threat: null
component: null
anchor: false
anchor_reason: null
---

## Description

Rapid-profile land does not gate the COV001/TEST001 doc/test-edge families
on public symbols the ticket's own diff adds. T-1907 fixed this shape for
the type family alone (`_assert_touched_files_type_check_pre_land`): a new
public top-level symbol with no `frob:doc`/`frob:tests` edge lands clean
under the rapid profile and is only caught by the deferred post-land
sweep, against an already-published commit -- publishing the error floor
red for every land that adds a symbol, until the sweep eventually runs.

## Plan

Generalize T-1907's diff-scoped, bounded check
(`_assert_touched_files_type_check_pre_land`) to the doc/test-edge
families: add `_assert_new_public_symbols_have_doc_and_test_edge_pre_land`
in `_land_cmd.py`, wired into `_land_core_prepare` for every profile
including rapid. Two `ast.parse` calls per touched `.py` file (current
worktree content, and the same file at merge-base via `git show`) find
symbols new by name and require a `frob:doc`/`frob:tests` edge on each --
never a full `GraphSnapshot`/coverage_gate build, keeping the ~208s cost
T-1684 took off the land critical path off it.