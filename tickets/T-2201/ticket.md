---
id: T-2201
title: 'T-2114''s pre-land gate detects frob: directives by substring matching block_text,
  the same lexical question T-2183 just fixed with grammar-parsed comment nodes, and
  its family list is hardcoded to COV001/TEST001'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: own repro/regression test for the substring-directive gate fix lives in
    this shared test module
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_no_edges_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_both_edges_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_empty_touched_set_is_a_no_op
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_directive_looking_line_inside_a_docstring_does_not_satisfy_the_gate
designated_repro_test: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_directive_looking_line_inside_a_docstring_does_not_satisfy_the_gate
acceptance:
- text: 'Measured at src/frob/app/ticket_runner/_land_cmd.py:3311-3312, the gate decides
    with: has_doc = ''frob:doc'' in block_text or ''frob:waive COV001'' in block_text;
    has_tests = ''frob:tests'' in block_text or ''frob:waive TEST001'' in block_text.
    Substring matching, so a directive-looking string inside a docstring or string
    literal satisfies the gate and a real directive written in an unexpected position
    is missed. T-2183 landed hours earlier (e5a297bf88e9) answering the identical
    question -- ''is this line a genuine frob: directive?'' -- with frob.lang.raw_tree/COMMENT_TYPES
    placing the line inside a real grammar COMMENT node, deliberately excluding docstrings.
    Reuse that machinery. This test MUST fail against current main: a new public symbol
    whose ONLY ''frob:doc'' text sits inside a docstring or string literal must NOT
    satisfy the gate.'
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_no_edges_refuses_the_land
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_both_edges_does_not_refuse
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_empty_touched_set_is_a_no_op
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_directive_looking_line_inside_a_docstring_does_not_satisfy_the_gate
- text: 'The family list is hardcoded, and this is the THIRD instance of one-family-at-a-time:
    T-1907 gated the type family, T-2114 generalised its shape to COV001/TEST001,
    and the ARCH/lint families still accumulate per land -- measured now at ARCH001
    4, ARCH103 1, E501 1, PERF004 1 on the unscoped floor, up from 8 code errors earlier
    today to 15. Parameterise the gate over the families a diff can introduce rather
    than adding a third hardcoded pair; otherwise the next family repeats this ticket.'
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_no_edges_refuses_the_land
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_both_edges_does_not_refuse
- text: 'Do NOT fix the substring check by making the pattern stricter (anchoring,
    requiring a leading ''#''). T-2183 already proved that shape wrong: its occurrence
    2 was a genuinely comment-positioned directive inside a docstring, which no pattern
    tightening separates -- the question is whether the GRAMMAR says the line is a
    comment, not what the text looks like. Do NOT reintroduce a full unscoped frob
    check at land time either; that is the ~208s cost T-1684 deliberately removed
    and T-2114 correctly avoided by working from the diff alone.'
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_no_edges_refuses_the_land
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_both_edges_does_not_refuse
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_empty_touched_set_is_a_no_op
  - tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
threat: null
component: null
anchor: false
anchor_reason: null
---
