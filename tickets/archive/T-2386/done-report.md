## Done report

Provenance-manifest-based fix for T-2384's sync-skills half. _sync_one_kind
previously rmtree'd every ~/.claude/<kind>/<name> with no repo-side
counterpart (destructive to a second repo sharing ~/.claude) and
copytree(dirs_exist_ok=True)'d over any existing destination unconditionally
(silently overwrote hand-maintained or other-repo content).

Fix: <claude_dir>/.frob-sync-manifest.json, keyed by resolved repo root,
records which <kind>/<name> entries THIS repo installed. Removal is
restricted to entries this repo's own manifest previously recorded, now
absent repo-side. Copy-in refuses (a SyncCollision, reported via
SkillsSyncReport.collisions and run's SKIPPED lines) when the destination
exists and this repo does not already own it, unless --force. Reused the
existing refuse-without-force convention (scaffold/project.py's
render_project/install_worktree_lease_hook exists()->OutputExists guard)
rather than inventing a third cooperative mechanism -- the BEGIN/END
managed-block convention (_managed.py) does not fit: it rewrites known
regions of one file in place, this rewrites whole arbitrarily-named
directory trees.

Two pre-existing tests (test_removes_stale_claude_side_entry,
test_run_reports_synced_and_removed_counts) tested the OLD destructive
first-run-deletes-anything-unowned behavior; both rewritten to prime the
manifest via a first sync before asserting removal, matching the new
provenance-restricted semantics. Six new tests in TestSyncSkillsProvenance
cover: two-repo non-interference (alternating syncs, twice), hand-maintained
survives untouched (no counterpart AND same-named collision cases), --force
overwrite-then-own, same-repo-twice-is-a-no-op, and the on-disk manifest
shape.

All tests use tmp_path --claude-dir, never the real ~/.claude, per the
ticket's own instruction.

Filed as part of T-2384's series: T-2399 (PORT001 meta-gate, coordinator
directive) and T-2398 (source-root retarget group 1) queued as siblings, not
completed in this ticket.

### Changed
```
 tickets/T-2386/ticket.md | 18 +++++++++++++++++-
 1 file changed, 17 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_syncs_new_repo_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_updates_existing_entry_in_place` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_removes_stale_claude_side_entry_this_repo_previously_installed` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_missing_repo_directories_are_a_no_op` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_files_directly_under_claude_dir_are_left_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_second_repo_does_not_delete_first_repos_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_hand_maintained_entry_is_never_deleted_or_overwritten` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_hand_maintained_entry_collides_instead_of_being_overwritten` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_force_overwrites_collision_and_claims_ownership` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_same_repo_sync_twice_is_a_no_op_second_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_manifest_records_only_this_repos_owned_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestMakefileRecipeDelegates::test_recipe_body_is_a_single_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestRun::test_run_reports_synced_and_removed_counts` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestRun::test_run_defaults_to_home_claude_when_no_override_given` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2241, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/sync-skills-provenance/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/sync-skills-provenance/src/frob/vet/_capability.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2386, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
