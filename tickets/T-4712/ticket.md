---
id: T-4712
title: Narrow the directive wrapper to cut only at token separation, never inside
  a path, anchor or quoted value
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4711
parent: T-4703
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fmt_directives.py
- tests/test_gates_fmt_directives.py
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
- tests/test_gates_fmt_directives.py::TestQuotedTargetNeverSplitByWrap::test_pre_change_word_boundary_cut_would_have_split_the_quoted_target
- tests/test_gates_fmt_directives.py::TestQuotedTargetNeverSplitByWrap::test_quoted_target_is_never_split_across_physical_lines
- tests/test_gates_fmt_directives.py::TestUnbreakableSingleNodeIdStillUnsplittable::test_single_long_node_id_produces_one_noqa_suffixed_line
- tests/test_gates_fmt_directives.py::TestCanonicalizeTextIdempotentTwice::test_second_format_paths_run_reports_zero_changes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4712
branch: t-4712
---
Leaf 3 of T-4703. 2 points. Narrow the existing wrapper so it cuts ONLY at token separation.
Owns src/frob/gates/_fmt_directives.py's wrap path; no new wrapper is written.

## What to build

`_wrap_cut_point` (src/frob/gates/_fmt_directives.py:417) currently cuts at ANY space
(`remaining.rfind(" ", 0, budget)`) -- that is a WORD boundary, not a token boundary. Owner
decision 2 allows a break only between targets of a multi-target list or between `key="value"`
attributes, never inside a symbol path, an anchor, or a quoted value.

Replace the space scan with a token-separation scan over the directive's own parsed token
stream (the parser from leaf 2 is the authority on where token boundaries are -- do NOT
re-implement tokenization here; call it). Keep every behaviour already tested and paid for:
- T-0991's boundary-space edge case (a space sitting exactly AT `budget`, invisible to
  `rfind`'s exclusive end bound), :450-466.
- T-4179 / T-4477's no-clean-cut path: once no cut exists within budget, the ENTIRE remainder
  is emitted as one final unsplittable physical line carrying the end-of-run noqa, never a
  mid-run cut -- the docstring at :430-448 explains why a mid-run noqa marker is not
  idempotent. That contract is load-bearing; do not weaken it.
- Idempotence: `canonicalize_text` must stay a canonicalizer (wrap when long, unwrap when it
  now fits), and the round-trip property with `fold_comment_runs` must hold.

## Positive control

- Plant a directive with a long quoted `reason="..."` containing internal spaces and assert no
  cut lands inside the quoted value -- the current word-boundary cut WOULD cut there, so
  assert the pre-change behaviour was wrong in the same test file (a failing-before assertion,
  not just a passing-after one).
- Plant a `frob:tests` whose single node id exceeds the line length alone and assert the
  unsplittable-remainder path still produces exactly one final line with the noqa suffix.
- Idempotence: run `format_paths` twice over a fixture tree and assert the second run reports
  zero changes.

## Acceptance

- Zero cuts land inside a symbol path, anchor, or quoted value across the whole repo (assert by
  re-parsing every rewritten file and requiring zero new DSL001 from leaf 2's mid-token check).
- tests/test_gates_fmt_directives.py passes, including every T-0991 / T-4179 / T-4477 case.
- `format_paths` idempotent on the second run.