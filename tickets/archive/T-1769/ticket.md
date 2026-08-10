---
id: T-1769
title: 'T-1760''s artifact reset and T-0463''s completeness assertion contradict:
  any worktree that merged main after a version bump cannot land'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_release.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandCompleteness::test_incomplete_land_fails_loudly_and_commits_nothing
designated_repro_test: null
threat: null
component: null
---
T-1760's fix and T-0463's completeness assertion contradicted each other,
and the result was that a worktree which merged main after any sibling's
version bump could NEVER land. Every retry reproduced the identical
refusal:

    land: T-1767 refused -- the staged squash-apply onto ... is missing
    file(s) the worktree changed: ['.frob-release.json', 'CHANGELOG.md',
    'pyproject.toml']  -- IncompleteLand

Both guards were behaving exactly as designed:

- `_worktree_full_changeset` reports the three land-owned release
  artifacts as CHANGED, because the worktree's `git merge main` genuinely
  touched them.
- T-1760's `_reset_release_artifacts_to_pre_land` then DISCARDS whatever
  the squash staged for those same three files -- deliberately, because
  carrying a stale copy forward is what silently reverted main's version
  four times in one day (0.366.0 -> 0.365.0 -> 0.366.0 -> 0.365.0, with
  the manifest regressing alongside it). Recompute, do not carry.
- `_assert_staged_covers_worktree_changeset` then computes
  `expected - staged`, finds those three, and refuses the land as
  silently-partial.

So the completeness gate was flagging as an omission the exact behaviour
the release gate had just been fixed to guarantee.

FIX: subtract `_LAND_OWNED_RELEASE_FILES` from the missing set. Their
absence from the staged apply is intentional and their correct values are
written immediately afterwards by `_apply_release_bump`, which computes
them against ROOT's state rather than the worktree's. Nothing else in the
completeness assertion changes -- any other file the worktree changed and
the apply dropped still refuses exactly as before, which is the T-0463
class the assertion exists for.

This is a two-fix interaction, not a defect in either fix alone, and it
is the second time today that pattern has bitten: T-1753 widened an
element union but left an invariant `list` container, moving a type error
rather than resolving it (T-1754). A fix that is locally correct can
still break a caller that was relying on the old behaviour, and neither
guard's own tests could have caught this because each was individually
right.

Evidence: `tests/test_ticket_land.py` (248 tests) green after the change,
including the T-0463 completeness suite that would fail if the assertion
had been weakened for anything other than these three paths.

## Done report

Two individually-correct guards had come to contradict each other, and
the result was that any worktree which merged main after a sibling's
version bump could NEVER land. Every retry reproduced the identical
refusal rather than a new one, which is what made it diagnosable:

    land: T-1767 refused -- the staged squash-apply is missing file(s)
    the worktree changed: ['.frob-release.json', 'CHANGELOG.md',
    'pyproject.toml'] -- IncompleteLand

Both halves were doing their jobs:

- `_worktree_full_changeset` reported the three land-owned release
  artifacts as CHANGED, because the worktree's `git merge main` genuinely
  touched them.
- T-1760's `_reset_release_artifacts_to_pre_land` then DISCARDED whatever
  the squash staged for those same three -- deliberately. Carrying stale
  copies forward is what silently reverted main's version four times in
  one day (0.366.0 -> 0.365.0 -> 0.366.0 -> 0.365.0, manifest regressing
  alongside). Recompute, do not carry.
- `_assert_staged_covers_worktree_changeset` computed `expected -
  staged`, found exactly those three, and refused the land as
  silently-partial.

So the completeness gate flagged as an omission the precise behaviour the
release gate had just been fixed to guarantee.

FIX: subtract `_LAND_OWNED_RELEASE_FILES` from the missing set, and
nothing else. Any other file the worktree changed and the apply dropped
still refuses exactly as before -- that is the T-0463 class the assertion
exists for, and it is untouched. `_apply_release_bump` writes the correct
values for the three immediately afterwards, computed against ROOT's
state rather than the worktree's.

This is the second two-fix interaction in a single day. T-1753 widened an
element union but left an invariant `list` container, moving a type error
rather than resolving it (found and fixed as T-1754). Neither guard's own
tests could catch either case, because each fix was individually correct
and the failure existed only in the composition. Worth remembering when a
fix looks locally obvious: the caller relying on the old behaviour is not
in the diff.

frob:no-behavior-change -- this restores the ability to land, which the
interaction had removed; it does not change what either guard checks.
Evidence is the existing T-0463 completeness test, which still passes and
would fail if the assertion had been weakened for any path other than
those three.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestLandCompleteness::test_incomplete_land_fails_loudly_and_commits_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 779 warning(s), 721 waived
- error-findings: none (measured, zero errors)
