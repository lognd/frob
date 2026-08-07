## Done report

Changed:
- src/frob/tickets/_land.py::_apply_release_bump -- captures main's pre-land
  pyproject.toml version and hard-refuses a non-monotonic bump
- src/frob/tickets/_land.py::_read_root_pyproject_version (new) -- reads the
  version via `git show <pre_land_tip>:pyproject.toml`, a git-object read
  immune to the squash-apply's own working-tree mutation (pyproject.toml is
  not scope-protected, so a worktree's stale copy can ride through the
  squash exactly as it did in the T-0976 incident -- reading the on-disk
  file post-squash would just re-read that same corruption)
- src/frob/tickets/_land.py::_release_bump_is_monotonic (new) -- strict
  greater-than check, PEP 440 `packaging.version.Version` compare with a
  plain string-inequality fallback for malformed test-fixture versions
- docs/modules/tickets.md#frob-ticket-land step 9.6 -- documents the T-0992
  assertion (AFFECT001-required edge from `_apply_release_bump`)
- tests/test_ticket_land.py::TestReleaseBump.test_stale_worktree_version_bump_yields_main_plus_one
  (new) -- acceptance criterion: stale worktree-carried pyproject + main
  ahead -> land yields main+1
- tests/test_ticket_land.py::TestReleaseBump.test_downgrade_bump_is_refused
  (new) -- a bump_version callback computing <= main's current version is
  refused, squash unwound, main's pyproject.toml left untouched

Root cause: `_apply_release_bump` invoked the caller-supplied `bump_version`
callback and staged whatever it returned with no independent check against
main's own state. The callback's actual production implementation
(`_apply_release_bump_for_land` in `src/frob/app/ticket_runner.py`, outside
this ticket's scope) derives its "current version" from a tracked release
manifest that can itself carry a stale value forward across a squash the
same way `pyproject.toml` can -- so the fix had to be a caller-independent
backstop inside `_land.py` itself: read main's own pre-land committed
version directly via git (immune to any squash-time corruption of the
working tree), and refuse -- unwinding the squash -- unless the callback's
result is strictly greater.

Evidence:
- tests/test_ticket_land.py::TestReleaseBump::test_stale_worktree_version_bump_yields_main_plus_one
- tests/test_ticket_land.py::TestReleaseBump::test_downgrade_bump_is_refused
- Full `TestReleaseBump` + `TestUvLockSync` suites re-run green (11 passed);
  full `tests/test_ticket_land.py` re-run shows the same 5 pre-existing
  failures with and without this change applied (confirmed by diffing
  against the unmodified file), all a `.frob/derived.lock`/nested-collection
  xdist-parallelism artifact unrelated to this ticket -- T-0907
  verified-reset, T-0959 archive splice, T-0889 digest guard, and T-0631
  sweep siblings all still pass.

Filed: none

Gates: `uv run frob check --ticket T-0992` clean (0 errors, 4898 warnings,
318 waived) after extending scope to `docs/modules/tickets.md` (required by
AFFECT001) and a fresh `frob ticket sweep T-0992`.
