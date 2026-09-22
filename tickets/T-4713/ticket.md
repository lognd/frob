---
id: T-4713
title: Directive stack lint (N+ consecutive, default 4) plus a Tier-A fix that merges
  same-kind directives into multi-target headers
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4710
- T-4711
- T-4712
parent: T-4703
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_directive_stack.py
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_gates_directive_stack.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
evidence:
- tests/test_gates_directive_stack.py::TestStackThresholdOffByOne::test_n_minus_one_is_not_a_finding
- tests/test_gates_directive_stack.py::TestStackThresholdOffByOne::test_n_is_exactly_one_finding
- tests/test_gates_directive_stack.py::TestOnlyStackedSymbolFires::test_stacked_symbol_fires_alongside_a_scattered_run_of_the_same_length
- tests/test_gates_directive_stack.py::TestMultiTargetLineCountsOnce::test_multi_target_edges_sharing_an_origin_count_as_one_line
- tests/test_gates_directive_stack.py::TestDstack001MergeFix::test_interleaved_doc_tests_doc_collapses_to_one_doc_then_one_tests
- tests/test_gates_directive_stack.py::TestDstack001MergeFix::test_tests_doc_tests_puts_tests_first_not_a_hardcoded_kind_order
- tests/test_gates_directive_stack.py::TestDstack001MergeFix::test_merge_is_idempotent
- tests/test_gates_directive_stack.py::TestDstack001MergeFix::test_only_paths_scoping_leaves_an_unlisted_file_untouched
- tests/test_gates_directive_stack.py::TestDstack001MergeFix::test_non_default_attrs_leaves_the_stack_untouched
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4713
branch: t-4713
---
Leaf 4 of T-4703. 3 points. Stack lint plus the Tier-A merge fix. Blocked by leaf 1 (reverse-copy
removal) because merging stacks that leaf 1 is about to delete measures the wrong thing.

## What to build

(a) A lint: a run of N+ consecutive directive lines above ONE symbol is a finding. N is
    configurable via frob.toml, default 4. Baseline to beat: 1,712 runs of 3+, largest 73
    lines (measured 2026-09-19 18:15, before leaf 1).
(b) A Tier-A fix that merges the run:
    - same-kind directives collapse into leaf 2's multi-target form;
    - groups are ordered by FIRST-SEEN kind, so the interleaved (doc, tests, doc) case collapses
      to one doc header then one tests header -- not reordered alphabetically, not stably
      interleaved;
    - the merged header is wrapped at token separation (leaf 3) to fit the line length.
(c) Register the rule in `_KNOWN_GATE_RULES` (src/frob/gates/_waive.py) and document it in
    docs/modules/gates.md's rule table plus a section under the Tier-A handler list, alongside
    `fix_fmt001_directive_wrap`.

Dispatch shape: `TIER_A_HANDLERS` in src/frob/gates/_fix_engine.py:1270 binds every handler to
the uniform `(root, snapshot, queue, ticket_id) -> list[FixApplied]` call shape; the handler
body belongs in src/frob/gates/_fix_engine_text.py, whose stated seam is exactly this -- a
handler that rewrites the ONE source line a lint-style Violation names, as opposed to the
graph-driven family in `_fix_engine.py` and the artifact-resync family in `_fix_engine_sync.py`
(see that module's docstring, :1-25). Honour `only_paths`-style scoping the way
`fix_fmt001_directive_wrap` does (src/frob/gates/_fix_engine_text.py:113-150): a whole-tree
rewrite is an out-of-scope WRITE and land's own guards reject it (T-1391, measured).

## Positive control

- Plant the interleaved (doc, tests, doc) stack and assert the output is exactly one doc header
  and one tests header, in that order. Plant (tests, doc, tests) and assert tests comes first --
  so the test cannot pass on a hardcoded kind order.
- Plant a stack of exactly N-1 and assert NO finding; N and assert one. The off-by-one is the
  whole configurability surface.
- Assert the merged form produces a byte-identical EDGE SET to the original stack (parse both,
  compare) -- the merge must never change the graph.
- Plant a stack above a symbol and a same-length run of directives NOT above one symbol; only
  the former fires.

## Acceptance

- Edge set identical before and after the merge on the whole repo (parse-and-compare, count in
  the Done report).
- Stack count (runs of 3+) after this leaf, reported against the leaf-1 number and the 1,712
  pre-story baseline.
- No new ARCH001 on any touched file (the merge shrinks line count; assert it never grows one).