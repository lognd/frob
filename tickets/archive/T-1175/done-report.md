## Done report

Collapsed playbook section 0's steps 1-2 plus `start` into `frob ticket
work T-####`: creates/reuses `.claude/worktrees/<id-lowercased>` (or
`--worktree PATH`), merges `main` in for freshness, builds natives
in-process via `frob.natives.build_natives` (no subprocess spawn), then
runs the existing `_start` transition+sweep logic against the worktree.
Every step reuses existing machinery (plain `git worktree add`/`merge`,
`build_natives`, `_start`) -- no new subsystem.

`frob ticket land` now absorbs three pre-merge steps in-process (no CLI
subprocess spawns): `frob fmt`'s `format_paths`, `frob sys sync-
interface`'s `sync_interface_report`/`apply_sync_interface`, and the
T-1138 Tier-A `apply_tier_a_fixes` handlers -- any file one of these
rewrites becomes an ordinary uncommitted change land's own existing
wip-commit step already picks up, so no new commit path was added. After
a real (non-dry-run) land, `_print_land_proof` emits a grep-able
`LAND-PROOF: ticket=... commit=... is_ancestor_of_main=... state_on_
main=... verified=...` line (the same two checks playbook step 9 used to
ask an agent to run by hand); `--finish` runs the same verification and,
only if it passes, `git worktree remove`s `--worktree`.

Updated docs/guides/agent-playbook.md section 0 (steps 1, 2, 5, 9) to
point at the two new verbs and shrink the manual recipe accordingly.

Split `_land` (was pushing past ARCH001's 60-line budget after the new
absorption/proof/finish wiring) into `_resolve_land_root`/`_finish_land_
after_success` helpers, and `_worktree_add_or_reuse`/`_ensure_worktree_
fresh` share a new `_run_git_or_exit` helper to stay under ARCH103's
mixed-concern budget.

### Changed
```
 tickets.md | 40 ++++++++++++++++++++++++++++++++++++----
 1 file changed, 36 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestDefaultWorkWorktree::test_slug_is_lowercased_ticket_id_under_dot_claude_worktrees` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestWork::test_creates_worktree_merges_main_and_starts_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestWork::test_reuses_an_existing_worktree_and_merges_main_for_freshness` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_fmt_half_canonicalizes_a_non_canonical_directive` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_real_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_finish_removes_the_worktree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 1349 warning(s), 696 waived
- error-findings: none (measured, zero errors)
