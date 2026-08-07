---
id: T-1434
title: Confirm whether frob ticket land or its worktree-merge flow ever reverts a
  freshly stamped frob-coverage.lock.json
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- docs/guides/agent-playbook.md
- src/frob/tickets/_land_git_ops.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'Investigation confirmed the root cause lives in

    src/frob/tickets/_land_git_ops.py''s `_auto_resolve_out_of_scope_conflicts`

    (the out-of-scope merge-conflict auto-resolver), not in _land.py itself --

    _land.py only calls it. Fixing the confirmed defect (a genuine merge

    conflict on frob-coverage.lock.json is resolved by blindly keeping one

    side, discarding the other''s freshly stamped data with no freshness/

    ratchet comparison) requires touching the function that actually performs

    the resolution. Adding this file to scope; a regression test for the fix

    belongs in tests/test_ticket_land.py, the existing home for every other

    land-merge-conflict test (TestOutOfScopeConflictAutoResolved and

    siblings), so that file is added too.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Investigation confirmed the root cause lives in

    src/frob/tickets/_land_git_ops.py''s `_auto_resolve_out_of_scope_conflicts`

    (the out-of-scope merge-conflict auto-resolver), not in _land.py itself --

    _land.py only calls it. Fixing the confirmed defect (a genuine merge

    conflict on frob-coverage.lock.json is resolved by blindly keeping one

    side, discarding the other''s freshly stamped data with no freshness/

    ratchet comparison) requires touching the function that actually performs

    the resolution. Adding this file to scope; a regression test for the fix

    belongs in tests/test_ticket_land.py, the existing home for every other

    land-merge-conflict test (TestOutOfScopeConflictAutoResolved and

    siblings), so that file is added too.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_ticket_land.py::TestCoverageLockConflictMerges::test_conflicting_lock_merges_to_the_higher_of_both_sides
designated_repro_test: null
threat: null
component: null
---
T-1419's own fix (a read-after-write durability check in
_run_stamp_coverage) confirms the committed frob-coverage.lock.json's write
path itself is durable within a single frob check --stamp-coverage call
(check_runner.py is write_coverage_lock's only caller repo-wide, verified
by grep). The remaining open question from T-1419's acceptance criterion 2
-- a freshly stamped lock reverting to an OLDER committed value SOME TIME
AFTER a successful stamp run, corroborated independently by the T-1270
agent (land left a stray lock diff it resolved with `git checkout` on that
file) -- points at a LATER git-level event: a merge, a `frob ticket land`
run, or an agent manually restoring the file to resolve what looked like an
unwanted diff.

Investigate src/frob/tickets/_land.py (and the surrounding land/merge
worktree flow) for any path where frob-coverage.lock.json ends up restored
to an older committed value after a genuine stamp: e.g. a land run against
a worktree/root where coverage.xml is not present (it is gitignored and
ephemeral) re-generating or leaving stale lock content, or the dirty-check/
auto-restore machinery (_refuse_if_main_dirty's uv.lock precedent at
_land.py:783) treating an unexpectedly-dirty coverage lock the same way
uv.lock's frob-version drift is auto-restored. Confirm whether land ever
touches frob-coverage.lock.json at all versus this being purely an agent
workflow habit (running `git checkout -- frob-coverage.lock.json` by hand,
per docs/guides/agent-playbook.md's land-owned-files guidance) that needs a
playbook correction instead of a code fix.