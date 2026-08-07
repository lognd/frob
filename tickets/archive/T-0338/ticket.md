---
id: T-0338
title: 'frob ticket land: own the full worktree->main flow (merge, REL001 bump+stamp,
  native rebuild, sweep refresh, evidence/done-report validation)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- src/frob/release/**
- tickets.md
- tests/unit/test_ticket_store.py
- docs/modules/tickets.md
- tests/test_ticket_land.py
- tests/unit/test_ticket_runner_land_release.py
- pyproject.toml
- CHANGELOG.md
- uv.lock
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: T-0338 tickets work maps to tests/unit/test_ticket_store.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/tickets.md
  reason: T-0338 tickets work maps to docs/modules/tickets.md
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_ticket_land.py
  reason: test coverage lives outside src/frob/app|tickets scope globs; REL001 version-bump
    files needed for the new public land() parameters
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: test coverage lives outside src/frob/app|tickets scope globs; REL001 version-bump
    files needed for the new public land() parameters
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: test coverage lives outside src/frob/app|tickets scope globs; REL001 version-bump
    files needed for the new public land() parameters
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: test coverage lives outside src/frob/app|tickets scope globs; REL001 version-bump
    files needed for the new public land() parameters
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: test coverage lives outside src/frob/app|tickets scope globs; REL001 version-bump
    files needed for the new public land() parameters
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: test coverage lives outside src/frob/app|tickets scope globs; REL001 version-bump
    files needed for the new public land() parameters
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_ticket_land.py::TestReleaseBump::test_bump_applied_and_reported
- tests/test_ticket_land.py::TestReleaseBump::test_no_bump_needed_reports_none
- tests/test_ticket_land.py::TestReleaseBump::test_bump_failure_unwinds_squash
- tests/test_ticket_land.py::TestReleaseBump::test_no_callback_is_noop
- tests/test_ticket_land.py::TestRebuildNatives::test_invoked_when_native_source_touched
- tests/test_ticket_land.py::TestRebuildNatives::test_skipped_when_no_native_source_touched
- tests/test_ticket_land.py::TestRebuildNatives::test_rebuild_failure_does_not_block_land
- tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_rewrites_version_and_prepends_changelog_entry
- tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_missing_version_line_fails
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_no_manifest_is_noop
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_class_none_is_noop
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_unreadable_graph_fails
- tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn::test_success_returns_true
- tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn::test_failure_returns_false_and_logs
designated_repro_test: null
acceptance:
- text: given an implementer's worktree branch with a single commit (code + new files
    + evidence + Done report), when the coordinator runs frob ticket land <id> --from
    <branch>, then frob git-merges the branch into main (splicing tickets.md conflicts),
    refreshes the pre-work sweep (T-0236), validates the Done-report heading + evidence
    resolve, and reports one clear success/failure -- no manual patch-apply, no missed
    untracked files
  evidence: []
- text: given the merged change alters public API, when land runs, then frob computes
    the required version via frob.release, bumps pyproject.toml + writes/updates the
    CHANGELOG entry + runs frob release stamp automatically (REL001 is coordinator-mechanical,
    never hand-work), and if the stamp's build step uninstalls the editable natives
    it rebuilds them (make core) before the final gate check
  evidence: []
- text: given a REJECT-worthy branch (failing gates, missing evidence, weakened strictness
    check flagged), when land runs, then it refuses to merge and reports why -- land
    is gated, not a rubber stamp
  evidence: []
threat: null
component: null
---
Coordinating implementer worktrees onto main is currently ~15 manual coordinator steps, each a recurring papercut (2026-07 campaign): implementers leave work UNCOMMITTED so landing is git diff|git apply, which (a) silently omits new untracked files, (b) is ATOMIC so one conflicting tickets.md hunk rolls back ALL files with a false 'applied cleanly', (c) forces the coordinator to hand-do every REL001 bump+CHANGELOG+stamp because pyproject is out of every ticket's scope, and (d) frob release stamp's build uninstalls the maturin-develop natives (see [[worktree-natives-artifact]]). WORKFLOW FIX already adopted (free): implementers now commit their work as a single worktree-branch commit incl. new files. This ticket builds the tool that consumes that: extend  (T-0236 already added post-merge sweep refresh) into the ONE command that owns merge (real per-file 3-way, splice_ledger for tickets.md) + REL001 bump/stamp (frob.release already computes required version) + native rebuild + evidence/Done-report validation + gate check, refusing on any failure. This removes the entire class of coordinator plumbing friction and makes the review-gated loop a two-command cycle (dispatch, land). See memory [[coordinator-landing-workflow]] for the exhaustive friction list this replaces.