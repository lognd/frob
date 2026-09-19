---
id: T-draft-8ed0c939
title: Apply the directive-ergonomics fixes repo-wide in one quiet-window land, before/after
  counts as acceptance
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4710
- T-4711
- T-4712
- T-4713
- T-4714
- T-4742
- T-4743
parent: T-4703
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Leaf 8 of T-4703. 3 points. Apply every fix repo-wide, in one accounted sweep. Blocked by leaves
1 through 7. This leaf is where the story's numbers are proven; it writes no new logic.

## What to do

Run the Tier-A fixes from leaves 1, 4, 5 and 6 across src/ and tests/, scoped and committed in
reviewable batches (the `only_paths` discipline exists precisely so a sweep is not one
unreviewable whole-tree write -- src/frob/gates/_fix_engine_text.py:113-150, T-1391).

## Acceptance -- every number measured before AND after, pasted in the Done report

Baselines, measured by the coordinator 2026-09-19 18:15 across src/ and tests/ (reproduce with a
scratchpad script, do not trust these numbers without re-running the script on the pre-sweep
tree first -- a baseline that cannot be reproduced is not a baseline):

| metric | before |
| --- | --- |
| `# frob:` directive lines | 30,915 |
| lines carrying a `# noqa` suffix | 5,663 (18%) |
| runs of 3+ consecutive directive lines | 1,712 |
| largest run | 73 lines |
| lines carrying two or more directives | 88 |

After the sweep, report each of these again, plus:
- the noqa residue characterized (how many are a single over-long token, how many anything else
  -- anything in the second category is a bug in leaf 5, not residue);
- the count of each non-canonical separator spelling, before and after (leaf 6);
- the count of reverse `frob:tests` copies deleted vs moved (leaf 1).

## Positive control (this leaf's own)

- The GRAPH must be unchanged. Snapshot the full edge set before the sweep and after; assert
  they are identical. A sweep that changes the graph has corrupted a directive.
- `frob check` finding set before and after: identical, modulo the new rules' own findings going
  to zero. Any OTHER rule's count moving is a finding to investigate, not to accept.
- `ruff check src tests` clean -- owner decision 1: hand-run ruff must not be broken.
- Re-run every fix a second time and assert zero further changes (the sweep converged).

## Dispatch discipline (coordinator amendment, owner-approved)

This leaf's scope is src/** and tests/**, so it collides with every live lease in the fleet.
It therefore runs in a COORDINATOR-DECLARED DISPATCH-QUIET WINDOW, as ONE land with
`--allow-cross-ticket`, AFTER every other leaf of T-4703 has landed. It is never dispatched
alongside other in-progress tickets and is never split across several lands.

Its acceptance is exactly the before/after counts -- 30,915 directive lines, 5,663 noqa-carrying
lines, 1,712 stacks of 3+ -- together with ZERO gate-finding deltas on every rule other than the
new rules this story introduces (which go to zero). Any other rule's count moving is a defect to
investigate, not a result to accept.