---
id: T-2386
title: 'sync-skills: provenance-aware sync to stop cross-repo agents/skills deletion'
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/_skills_sync.py
- tests/unit/test_skills_sync.py
- docs/commands/sync-skills.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_skills_sync.py::TestSyncSkills::test_syncs_new_repo_entries
- tests/unit/test_skills_sync.py::TestSyncSkills::test_updates_existing_entry_in_place
- tests/unit/test_skills_sync.py::TestSyncSkills::test_removes_stale_claude_side_entry_this_repo_previously_installed
- tests/unit/test_skills_sync.py::TestSyncSkills::test_missing_repo_directories_are_a_no_op
- tests/unit/test_skills_sync.py::TestSyncSkills::test_files_directly_under_claude_dir_are_left_alone
- tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_second_repo_does_not_delete_first_repos_entries
- tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_hand_maintained_entry_is_never_deleted_or_overwritten
- tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_hand_maintained_entry_collides_instead_of_being_overwritten
- tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_force_overwrites_collision_and_claims_ownership
- tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_same_repo_sync_twice_is_a_no_op_second_run
- tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_manifest_records_only_this_repos_owned_entries
- tests/unit/test_skills_sync.py::TestSkillsSyncRenderLint::test_no_render001_violations_for_skills_sync
- tests/unit/test_skills_sync.py::TestMakefileRecipeDelegates::test_recipe_body_is_a_single_line
- tests/unit/test_skills_sync.py::TestRun::test_run_reports_synced_and_removed_counts
- tests/unit/test_skills_sync.py::TestRun::test_run_defaults_to_home_claude_when_no_override_given
designated_repro_test: tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::test_hand_maintained_entry_is_never_deleted_or_overwritten
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: d95f49054e140c69f54c4e016a503001eac0b8dc
---
Child of T-2384 (sync-skills half). _sync_one_kind currently rmtree's every
~/.claude/<kind>/<name> with no repo-side counterpart, and copytree's in
with dirs_exist_ok=True unconditionally. Two frob-enabled repos sharing one
~/.claude flap/destroy each other's agents and skills.

Fix: provenance manifest at <claude_dir>/.frob-sync-manifest.json keyed by
repo identity (resolved repo_root path), recording which <kind>/<name>
entries THIS repo installed. Removal is restricted to entries this repo's
own manifest previously recorded that are now absent repo-side -- never an
entry owned by another repo or never-synced (hand-maintained). Copy-in
refuses (collision, reported, not silently overwritten) when the
destination exists and is not already owned by this repo's manifest,
unless --force.

Acceptance (from T-2384):
[1] two repos syncing into the same ~/.claude never remove/overwrite each
    other's entries; running either sync twice in a row is a no-op the
    second time.
[2] a ~/.claude with hand-maintained agents/skills, first sync run:
    nothing deleted, nothing overwritten (reported as collision instead).

All tests exercise a tmp_path --claude-dir, never the real ~/.claude.