---
id: T-1035
title: 'frob-dup: nested-closure fragments cannot be individually waived (symref/binding
  mismatch)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_legacy.py
- src/frob/dup/_legacy_py.py
- src/frob/graph/dsl.py
- docs/modules/dup.md
- src/frob/check/_python.py
- tests/unit/test_check.py
- tests/unit/test_dup_legacy_py.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/check/_python.py
  reason: nested-closure symref coverage-check lives in _dup_group_covering_waivers
    (frob.check._python), not frob.dup itself -- the consumer side of the binding
    gap this ticket exists to fix
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_check.py
  reason: existing test_dup_legacy_py.py asserts the buggy class-only nested-closure
    qualname (must update to match the T-1035 fix); test_check.py is where _dup_group_covering_waivers
    regression coverage lives
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_dup_legacy_py.py
  reason: existing test_dup_legacy_py.py asserts the buggy class-only nested-closure
    qualname (must update to match the T-1035 fix); test_check.py is where _dup_group_covering_waivers
    regression coverage lives
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiver_above_nested_closure_covers_it_via_enclosing_method
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waived_group_excluded_from_headline_but_listed
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_partial_group_waiver_does_not_hide_whole_group
- tests/unit/test_dup_legacy_py.py::test_iter_functions_py_yields_qualified_names
- tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_finds_class_for_method
- tests/unit/test_dup_legacy_py.py::test_collect_locals_py_empty_for_body_with_no_bindings
designated_repro_test: null
threat: null
component: null
---
Found while working T-0862 (tests/**-only frob-dup group triage).

4 of the 154 unaccounted tests/**-only groups measured for T-0862 share a
single root cause that cannot be fixed from tests/** alone: a symref
mismatch between how `frob.dup._legacy` names a NESTED (closure) function
fragment and how `frob.graph.dsl` binds a preceding `frob:waive` comment.

`frob.dup._legacy._enclosing_class_py` (src/frob/dup/_legacy.py via
src/frob/dup/_legacy_py.py:198) walks ALL the way up a function's ancestor
chain looking for the nearest enclosing CLASS, ignoring any enclosing
FUNCTION in between. So a helper closure defined inside a test method
(e.g. `def _run_new():` nested inside
`TestArchiveRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_archive`)
gets a dup fragment symbol of `TestArchiveRaceWithConcurrentNew._run_new`
-- qualified by the enclosing CLASS only, never the enclosing METHOD.

Meanwhile `frob.graph.dsl`'s directive-to-symbol binding (used to resolve
a `frob:waive DUP001 reason="..."` comment placed directly above a `def`)
only tracks top-level defs and class methods as declared symbols -- it has
no concept of a nested closure as an independently addressable symbol. A
comment placed directly above a nested `def` binds instead to the nearest
OUTER tracked symbol (the enclosing test method), not the nested function.

Net effect: `_dup_group_covering_waivers`'s full-coverage rule
(docs/modules/dup.md#T-0375) requires every fragment's symref -- as
`frob.dup` computes it -- to be covered by a matching `frob:waive` edge --
as `frob.graph.dsl` binds it. For a nested-closure fragment these two
symbol spaces disagree, so no comment placement can ever satisfy coverage
for that fragment. Confirmed by direct probe (calling
`frob.check._python._waive_edges_for_rule` and `frob.dup.find_duplicates`
against this repo): a `frob:waive DUP001` comment placed immediately above
`tests/test_tickets_ledger_concurrency.py`'s nested `_run_new` binds to
`TestArchiveRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_archive`
(the outer test method), never to
`TestArchiveRaceWithConcurrentNew._run_new` (the fragment `frob.dup`
actually reports) -- so the waiver is silently ineffective no matter where
the comment is placed.

A second, related symptom: two SAME-NAMED nested closures in different
test methods of the same class collapse to the SAME symref (class-only
qualification loses the enclosing-method disambiguation), e.g.
`tests/test_ticket_runner_pytest_env.py`'s two `fake_guarded_subprocess_run`
closures in `TestRunPytestDirectlyStripsLeaseEnv` both report as
`TestRunPytestDirectlyStripsLeaseEnv.fake_guarded_subprocess_run` --
genuinely ambiguous fragment identity, independent of the waiver-binding
gap above.

The 4 residual groups from T-0862 (unfixable from tests/** alone):
- tests/test_tickets_ledger_concurrency.py:98,156 (nested `_run_new`
  in two different test methods of two different classes)
- tests/test_testing.py:1239,2124 (nested `fake_run_argv`)
- tests/test_gitio.py:29 + 8 sibling files, incl.
  tests/test_evidence_integrity.py's nested `git` (the pre-existing
  waiver there already has this exact problem -- it predates T-0862)
- tests/test_ticket_runner_pytest_env.py:40,71 (symref collision, not
  just a binding gap)

Fix direction (not evaluated in depth, needs design):
(a) `frob.dup._legacy`'s Python function-symbol resolution: qualify a
    nested closure's symbol by its full enclosing chain (or at minimum
    the nearest enclosing FUNCTION, not just the nearest enclosing CLASS)
    so two same-named closures in sibling methods no longer collide.
(b) `frob.graph.dsl`'s comment-to-symbol binding: either extend it to
    recognize nested function defs as independently waivable symbols
    (binding a directly-preceding comment to the nested def rather than
    falling through to the outer tracked symbol), or teach
    `_dup_group_covering_waivers` to accept a waiver bound to a fragment's
    nearest OUTER tracked symbol as sufficient coverage for a nested
    fragment (weaker, but matches what a human intuitively expects when
    they place the comment directly above the nested closure).

Scope for whoever picks this up: src/frob/dup/_legacy.py,
src/frob/dup/_legacy_py.py, src/frob/graph/dsl.py, plus
docs/modules/dup.md's T-0375 full-coverage writeup once resolved. The 4
groups above (and the pre-existing evidence_integrity.py waiver, which
should be re-verified once the binding is fixed) are this ticket's
regression fixtures.