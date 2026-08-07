---
id: T-1769
title: 'T-1760''s artifact reset and T-0463''s completeness assertion contradict:
  any worktree that merged main after a version bump cannot land'
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_release.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
