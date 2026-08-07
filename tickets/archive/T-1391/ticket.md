---
id: T-1391
title: FMT001's Tier-A fix pass rewrites the whole tree, colliding with land scope
  discipline
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- tests/test_gates_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'The ticket''s stated fix (diff-scope FMT001''s Tier-A pass when it runs
    in a

    land context) is not achievable purely inside _fix_engine.py: the only

    call site that needs to pass a restricted path set is

    _absorb_pre_land_fixes in src/frob/app/ticket_runner/_land_cmd.py, which

    currently calls apply_tier_a_fixes with no scoping information at all.

    Without touching this one call site, the new optional parameter added to

    apply_tier_a_fixes/fix_fmt001_directive_wrap would be dead code and the

    acceptance criterion ("a land whose ticket scope excludes a file... is

    left untouched") would remain unmet. Adding this single file, changing

    only the one call site to pass the ticket''s touched-file set through to

    apply_tier_a_fixes, keeps the edit narrowly targeted to closing this

    ticket''s own acceptance criteria, not incidental unrelated work.

    '
  actor: logan
  at: '2026-08-01'
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'Reverting the previous scope --add: touching _land_cmd.py pulls in a

    cascade of scope-closure warnings (its own transitive private helpers in

    __init__.py, _verify.py, _close_cmd.py, plus unrelated _fix_engine.py

    helpers in _suppress.py/_doclink_docanchor.py) that would balloon this

    ticket far past its intended surface. Wiring the actual land call site is

    better done as its own follow-up ticket once this ticket lands the

    diff-scoping mechanism in _fix_engine.py itself.

    '
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_leaves_an_out_of_scope_file_untouched
- tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_none_preserves_whole_tree_behaviour
- tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_skips_nonexistent_path_without_error
designated_repro_test: null
acceptance:
- text: 'GIVEN a land whose ticket scope excludes a file elsewhere in the tree carrying
    a non-canonical frob: directive, WHEN land runs its Tier-A pre-fix pass, THEN
    that out-of-scope file is left untouched'
  evidence:
  - tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_leaves_an_out_of_scope_file_untouched
  - tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_skips_nonexistent_path_without_error
- text: GIVEN a frob check --fix invoked outside a land, WHEN the Tier-A FMT001 handler
    runs, THEN its existing whole-tree behaviour is preserved
  evidence:
  - tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_none_preserves_whole_tree_behaviour
threat: null
component: null
---
fix_fmt001_directive_wrap (src/frob/gates/_fix_engine.py ~L491) calls format_paths over the entire root rather than the diff. Its docstring justifies this: widening scope 'cannot make an unrelated file worse' because format_paths only rewrites genuinely non-canonical directive runs.

That reasoning is sound about file CONTENT and wrong about LAND SCOPE DISCIPLINE. A content-preserving rewrite of an out-of-scope file is still an out-of-scope WRITE, and land's own guards then reject the land that triggered it.

Measured 2026-08-01 across two independent agent series: land's pre-fix pass mechanically rewrote frob:waive reason comments in src/frob/app/_daemon_proxy.py on lands that had nothing to do with that file. One agent was forced to widen T-1385's declared scope by a file purely to absorb the collateral edit -- corrupting that ticket's scope record to work around a tool defect. Another agent misdiagnosed it as its primary land blocker and reported four tickets as unlandable.

The fix is to diff-scope the pass when it runs in a land context (FMT001 itself is already diff-scoped -- only this HANDLER widened it). Preserve whole-tree behaviour for a standalone frob check --fix.

Note for whoever takes this: T-1341 is concurrently editing this same file to add an E501 suppression handler, and was briefed to resolve an FMT001-vs-noqa precedence question. Coordinate rather than racing it.