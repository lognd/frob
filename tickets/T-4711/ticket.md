---
id: T-4711
title: Multi-target directive grammar and the one documented continuation form, with
  a DSL001 mid-token break check
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4710
parent: T-4703
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
- docs/modules/graph.md
- tests/unit/graph/test_dsl.py
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
- tests/unit/graph/test_dsl.py::TestMultiTargetDirectives::test_multi_target_tests_emits_one_edge_per_target
- tests/unit/graph/test_dsl.py::TestMultiTargetDirectives::test_multi_target_doc_emits_one_edge_per_target
- tests/unit/graph/test_dsl.py::TestMultiTargetDirectives::test_comma_inside_quoted_title_is_not_a_separator
- tests/unit/graph/test_dsl.py::TestMultiTargetDirectives::test_single_target_verbs_are_unaffected_by_a_comma
- tests/unit/graph/test_dsl.py::TestMultiTargetDirectives::test_multi_target_with_empty_entry_is_a_named_refusal
- tests/unit/graph/test_dsl.py::TestDsl001MidTokenBreak::test_join_mid_symbol_path_is_reported_by_dsl001
- tests/unit/graph/test_dsl.py::TestDsl001MidTokenBreak::test_same_target_broken_at_token_boundary_is_clean
- tests/unit/graph/test_dsl.py::TestMultiTargetFoldRoundTrip::test_multi_target_directive_survives_a_continuation_split
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4711
branch: t-4711
---
Leaf 2 of T-4703. 3 points. Multi-target directive grammar plus the ONE documented
continuation form. Owns the parser; no gate or fixer changes live here.

## What to build

(a) Multi-target parsing: `# frob:tests a.py::A.m, b.py::B.n` and `# frob:doc path#a, path#b`
    -- same kind, comma-separated, one Edge emitted per target with identical kind/src/attrs.
    Comma inside a quoted value is NOT a separator.
(b) Adopt the trailing-backslash continuation as THE one continuation form. It is already
    half-supported: `_fold_continuations` / `fold_comment_runs`, src/frob/graph/dsl.py:
    1431-1545 (T-0286 / T-0441 / T-0987) already fold a run before tokenizing, already stop
    the fold on a genuinely-valid directive start (`_is_genuine_directive_start`, :1503), and
    already treat an unfoldable trailing backslash literally. This leaf documents that
    behaviour as the contract and closes the gaps the multi-target form opens (a run that ends
    mid-list; a continuation whose first token is a bare target rather than prose).
    The indented-hash alternative is explicitly NOT built.
(c) DSL001 mid-token break detection: a folded run whose join point lands INSIDE a symbol path,
    an anchor, or a quoted value is a `MalformedDirective` whose reason NAMES the fix. This is
    the parser-side half of owner decision 2; the wrapper-side half is leaf 3. T-2857 already
    measured this exact corruption shape and left a comment about it at
    src/frob/graph/dsl.py:586 (`frob:describes path::Class.metho d_further_here` -- a wrapped
    continuation's trailing space landing mid-identifier); that comment is the repro to
    promote into a real check.
(d) docs/modules/graph.md: multi-target grammar, the one continuation form, the mid-token rule.

## Positive control

- Plant a directive whose continuation joins mid-symbol-path and assert DSL001 fires with a
  reason naming the fix. Plant the same directive broken at a real token boundary and assert
  it does NOT fire.
- Plant a multi-target `frob:tests` with a comma inside a quoted title and assert one target,
  not two.
- Round-trip property: fold(unfold(x)) == x for every multi-target and continued shape.

## Acceptance

- Multi-target directives of both kinds parse to the same edge set as the equivalent stack.
- Mid-token break is a DSL001 finding naming its fix; token-boundary break is clean.
- Full existing tests/unit/graph/test_dsl.py passes unchanged (no regression on the 30,915
  existing single-target lines).