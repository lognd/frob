## Done report

T-1007's fix was already landed as a side effect of T-1009 (single-source
version work): the same commit (71c12667, "land T-1009 single-source
version") introduced `_root_release_manifest`, `_required_release_bump`,
and rewrote `_apply_release_bump_for_land` in
src/frob/app/ticket_runner.py to derive the REL001 bump baseline from
ROOT's own git HEAD (`git show HEAD:.frob-release.json`) rather than the
worktree-carried on-disk manifest/pyproject that rides the squash-apply --
exactly the fix this ticket describes, including matching `frob:ticket
T-1007` directives and docstrings already citing this ticket by id. The
commit also landed the regression coverage
(tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand
and ::TestRootReleaseManifestReadsRootHead) proving the callback reads
through git-show at HEAD and ignores a stale worktree-disk copy.

No further code change was needed in this ticket's scope
(src/frob/app/ticket_runner.py, tests/**): re-ran the existing suite fresh
in this worktree to confirm it is real, passing, and covers the exact
behavior this ticket's acceptance criterion asks for (bump computed from
root's true pre-land manifest, not the worktree's), then bound this
ticket's evidence to that existing coverage and closed it as already
satisfied rather than leaving it queued against work that had already
landed under a sibling ticket.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_no_manifest_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_class_none_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_unreadable_graph_fails` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_reads_head_manifest_not_worktree_disk_copy` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_no_manifest_at_head_returns_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 6251 warning(s), 377 waived
- error-findings: INV006@src/frob/gates/_opaque.py
