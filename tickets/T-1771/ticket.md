---
id: T-1771
title: uv.lock is excluded from the release quartet coherence check and only synced
  inside the bump branch
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_release.py
- tests/unit/test_land_release_coherence.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Owner directive: all version syncing should be handled automatically.

It is not. Observed on main: `pyproject.toml` and `.frob-release.json`
both declared 0.368.0 while `uv.lock` still recorded frob 0.367.0,
tripping REL002 and requiring a hand `frob release sync`.

Two gaps compose to produce it:

- `_sync_uv_lock_for_land` is only ever called from inside
  `_apply_release_bump`'s "a bump was reported" branch. A land where the
  `bump_version` callback returns `Ok(None)` -- no API change, or the
  version already moved by other means -- never syncs the lock at all.
- `_ensure_release_quartet_coherent` runs unconditionally at the end of
  every land, which is right, but compares ONLY `pyproject.toml` against
  `.frob-release.json`. `uv.lock` is not in the comparison. The
  "quartet" is a trio in practice, and its own docstring's promise --
  "the quartet is coherent when land finishes" -- was not true of the
  fourth member.

The consequence is not cosmetic: `uv run`/`uv lock` re-derives that
version line on every invocation, so a stale lock flaps dirty repo-wide
and trips DirtyMain/SCOPE001 for whichever worktree runs anything next.
Same class of self-inflicted, fleet-wide land blocker as T-1755 (the
sweep's uncommitted writes) and T-1740 (a refused land's staged index).

ALREADY FIXED in the commit that files this ticket:
`_ensure_uv_lock_coherent` now runs as part of the unconditional
coherence step, comparing the lock's recorded frob version against
pyproject's and re-syncing when they differ, regardless of how the
version got where it is. `_read_working_uv_lock_version` returns `None`
for a missing or unparsable lock, meaning "nothing to compare" and never
"they agree". 260 tests across `test_land_release_coherence.py` and
`test_ticket_land.py` green.

REMAINING WORK for whoever takes this ticket:

1. Regression coverage for the real shape: a land whose `bump_version`
   returns `Ok(None)` while `uv.lock` is a version behind must leave the
   lock in step afterwards. Assert the lock's RECORDED VERSION, not that
   a sync helper was called.
2. Audit the rest of the quartet promise. `CHANGELOG.md` is the fourth
   member and is likewise not compared by the coherence check -- decide
   whether a missing changelog entry for the current version belongs
   here or in REL001, and write down which.
3. Rename `_ensure_release_quartet_coherent`, or fix its docstring, so
   the name and the guarantee match. A guard whose name overstates its
   coverage is exactly how this went unnoticed for as long as it did.
