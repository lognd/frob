## Done report

## Done report

Design: land's release-bump step (`_apply_release_bump` in
src/frob/tickets/_land.py) now calls a new `_sync_uv_lock_for_land(root,
final_id)` right after a real version bump is staged -- it runs `uv lock`
through the guarded `run_argv` seam (T-0778), `git add`s the result, and
unwinds the staged squash on failure the same way a bump-callback failure
already did. Skipped (Ok(None), no spawn) when `root` has no
pyproject.toml, so library callers/test fixtures without a real uv
project are unaffected. Separately, `_refuse_if_main_dirty` now tolerates
one specific dirty shape before refusing: a new
`_restore_lock_version_only_drift(root)` helper checks whether uv.lock is
the SOLE dirty path and its diff is exactly a `version = "..."`
line-flip inside the `name = "frob"` stanza (via
`_diff_is_frob_version_line_only`); if so it auto-restores
(`git checkout -- uv.lock`) and the dirty check is re-evaluated. Any
other drift (a real lock change, a second dirty file) is left untouched
and still refuses with DirtyMain exactly as before.

Changed:
  src/frob/tickets/_land.py::_apply_release_bump
  src/frob/tickets/_land.py::_sync_uv_lock_for_land (new)
  src/frob/tickets/_land.py::_refuse_if_main_dirty
  src/frob/tickets/_land.py::_restore_lock_version_only_drift (new)
  src/frob/tickets/_land.py::_diff_is_frob_version_line_only (new)
  src/frob/tickets/_land.py::_LOCK_VERSION_LINE (new)

Evidence:
  tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit
  tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse
  tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
  tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses
  tests/test_ticket_land.py::TestUvLockSync::test_lock_sync_spawn_failure_unwinds_squash
  (all 5 bound to acceptance[0] via `frob ticket evidence --accepts 0`)
  Full `tests/test_ticket_land.py` regression run: 71 passed
  (`uv run --frozen pytest tests/test_ticket_land.py -q -p no:cacheprovider`)

  Reviewer-required additions (round 2): `test_dirty_lock_version_plus_
  other_line_still_refuses` exercises `_diff_is_frob_version_line_only`'s
  `len(changed) != 2` rejection on the destructive-restore path -- uv.lock
  is the SOLE dirty path but its diff has the frob version-line flip PLUS
  an unrelated changed line (a `source` value); asserts DirtyMain refusal
  AND that uv.lock's dirty content is left byte-for-byte untouched (no
  auto-restore). `test_lock_sync_spawn_failure_unwinds_squash` mirrors
  the existing `test_bump_failure_unwinds_squash` shape but fails the
  `uv lock` spawn itself (via a fake `run_argv` returning rc=1) after a
  real bump succeeds -- asserts `ReleaseBumpFailed`, main's HEAD sha
  unchanged, and a fully clean working tree (the `reset --hard`/`clean
  -fd` unwind fired).

Filed: none

Gates: `uv run --frozen frob check --ticket T-0793` chunked loop
(lint/static/gates-fast/gates-native/gates-security, per the agent
playbook's stall-avoidance recipe) all clean: 0 errors across every
stage after adding scope for tests/test_ticket_land.py (COV002/SCOPE001)
and re-running `frob ticket sweep T-0793` (PRE001). `lint`'s one
remaining `ty` diagnostic (tests/test_gitio.py:316) is pre-existing and
outside this ticket's scope, untouched by this change.

Deviations: scope extended by one file --
`frob ticket scope T-0793 --add tests/test_ticket_land.py --reason-file
...` -- the regression tests for this behavior live alongside the rest
of `_land.py`'s test suite per repo convention; recorded via the CLI
with a reason, not a silent expansion.

uv.lock itself was NOT touched by this ticket's diff (it stays out of
worktree scope per docs/guides/agent-playbook.md#4b -- `frob ticket land`
owns it). The pre-existing frob-version-line flap observed repeatedly
during this session's own `uv run`/`frob check` invocations was
`git checkout -- uv.lock`'d back to the committed state before every
commit, never staged.

### Changed
```
 src/frob/tickets/_land.py | 129 +++++++++++++++++++++++++++++++++++++++++++++-
 tests/test_ticket_land.py | 108 ++++++++++++++++++++++++++++++++++++++
 tickets.md                |  94 +++++++++++++++++++++++++++++++--
 3 files changed, 326 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_line_only_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_lock_sync_spawn_failure_unwinds_squash` (pytest node id, verified passing when recorded)
