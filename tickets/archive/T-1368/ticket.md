---
id: T-1368
title: stamp() return value discarded in _apply_release_bump_for_land, can silently
  drop .frob-release.json writes
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_ticket_runner_land_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: 'T-1368: unit tests for the fix to _apply_release_bump_for_land''s discarded
    stamp() Result'
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_stamp_failure_propagates_instead_of_staging_stale_manifest
designated_repro_test: null
threat: null
component: null
---
Found while working T-1358 (release-quartet desync land outage).

`_apply_release_bump_for_land` (src/frob/app/ticket_runner/_land_cmd.py)
calls `frob.release.stamp(root, fresh_snapshot.danger_ok, new_version)` to
write `.frob-release.json` after bumping pyproject.toml/CHANGELOG.md, but
never checks `stamp`'s `Result` return value -- a write failure there
(e.g. `stamp`'s own `enforce_worktree_lease` refusal, or any future
failure mode `stamp` grows) is silently swallowed, and the function
proceeds to `git add .frob-release.json` regardless, staging whatever
content (possibly stale) happens to be on disk.

T-1358 added a defense-in-depth coherence check inside
`_apply_release_bump` (src/frob/tickets/_land_release.py) that catches
and repairs this class of desync after the fact, but the root silent-drop
in `_land_cmd.py` itself is still live and outside T-1358's declared
scope. Suggested acceptance: check `stamp(...)`'s return value in
`_apply_release_bump_for_land` and propagate `Err` to
`Err(LandError.ReleaseBumpFailed)` instead of discarding it.