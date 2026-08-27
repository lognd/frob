---
id: T-3140
title: 'T-3034 residual: 10 test failures need deeper per-item investigation'
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_clean.py
- tests/test_makefile_lock_sync.py
- tests/test_gates.py
- tests/unit/test_exports.py
- tests/unit/test_coordinator_scripts.py
- tests/test_app_daemon_proxy.py
- tests/unit/test_app_runners_t1822_already_landed.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
T-3034 per-test triage: after fixing the 13 tests that were straightforward test-side staleness (see T-3034's own Done report for the list -- over_broad_literal_globs package-prefix resolution gap, frob ack --reason requirement, start's empty-scope refusal, an import-retarget monkeypatch trap, two handler-signature drifts, a DOCENUM001 fixture gap, and a stats commit-count fixture gap), 8 of the original 26 Linux-suite failures remain uncharacterized to a confident verdict and are filed here rather than guessed at, per this drive's own "do not batch-fix without reading each one individually" instruction.

Each of the 8 below, with what was actually observed:

1. tests/test_clean.py::test_makefile_coverage_recipe_never_escalates_clean_tier
   Regex `^coverage: \$\(STAMP\)\n(?:\t.*\n)*` no longer matches -- the real
   Makefile recipe is now `coverage: core` (not `coverage: $(STAMP)`), and no
   longer calls `uv run frob clean` at all (its body is now
   `frob ticket reconcile && frob doctor && frob coverage --full`). This test
   guards a real safety property (coverage's clean tier must never be
   --all/--deep, which would delete .frob/ and destroy the forensics this
   ticket's sibling test proves tier-1 preserves) -- NEEDS INVESTIGATION into
   whether that property still holds somewhere in the current recipe/`frob
   coverage --full`'s own internals before the test is just loosened to match
   new text; if the safety property moved into `frob coverage --full` itself,
   the fix is a new test against THAT, not a Makefile-text regex.

2. tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump
3. tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject
   Both parse the `upload:` Makefile recipe for `bump_version.py`/
   `frob release sync`/`git add ... pyproject.toml ... uv.lock` text that no
   longer exists -- the recipe is now just `upload: clean` +
   `uv run frob release publish`, with a comment saying the T-0789 lock-sync
   property is "still true", now inlined into `publish`. Likely TEST-SIDE
   staleness (rewrite to test `frob release publish`'s own module instead of
   Makefile text) but not fixed here since it means reading
   src/frob/app/release_runner.py's actual sequencing to confirm the property
   really still holds before rewriting the test to assert it there.

4. tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
   `_KNOWN_RULE_FIXABILITY` (checked into src/frob/gates/, NOT tests/ --
   outside this ticket's declared scope) is missing `{'SYS100': 'auto'}` that
   a fresh scan now reports. Looks like simple checked-in-literal drift (a new
   rule SYS100 was added with auto-fixability and the literal never got
   regenerated) -- low risk, but touches a production file this ticket's
   scope does not cover.

5. tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
   Reports real missing __init__.py exports for frob.ci_report.*,
   frob.ci_validity.*, frob.doctor.native_degrade_warning, frob.ghio.*,
   frob.repo_meta.is_frob_own_repo, testing._coverage_wait.CoverageLockUnavailable
   -- looks like a batch of recently-added public symbols never got the
   frob-exports pass run against them. NEEDS someone to run
   `frob exports src/frob` (etc) and either regenerate __init__.py or confirm
   these are deliberately excluded.

6. tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
   `assert not any(...)` failed -- something IS being flagged that shouldn't
   be. Not root-caused; needs the actual WIRE violation read directly
   (`frob check --only wire` against this test's fixture) to see which CLI
   dest triggered it and whether _config_external.py genuinely drifted or the
   test fixture is stale.

7. tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked
   Expected a live worktree with an unlanded commit (no lease file) to
   resolve via fallback scan with leaked=False/worktree='t-2583'; got
   leaked=True/worktree=None instead -- the fallback scan this test exists to
   prove appears not to be finding the live worktree any more. Possible
   real regression in the coordinator lease-fallback scan; needs stepping
   through scripts/coordinator (or wherever this fallback lives) against the
   test's exact fixture shape.

8. tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
   Daemon-served and in-process `frob check --only gates --delta --json`
   payloads differ ONLY in the gate-summary's own text: the daemon path now
   prepends "[REPLAY age=1.0s, unchanged tree]" that the in-process path
   never emits. The test's own `_normalize_gate_timing` already strips
   non-reproducible PER-GATE timing but was never taught about this REPLAY
   annotation. Likely: either (a) the REPLAY annotation is a genuine,
   intentional daemon-only feature and the normalizer needs to also strip
   it, or (b) the daemon should not be injecting request-serving metadata
   into a payload that is supposed to byte-for-byte match the in-process
   path, in which case this is a small product-side leak. Needs a decision,
   not a guess.

9. tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers::test_no_markers_prints_nothing_and_returns_empty
   caplog.records != [] -- a WARNING from frob.tickets._models (over_broad_
   literal_globs's own "could not be resolved from pyproject.toml
   [project].name -- UNRESOLVED" message, same resolver as T-3034's already-
   fixed group of 5 over_broad_literal_globs failures) leaks into this
   unrelated caplog assertion via propagation to the root logger, even
   though this ticket's own scope ("src/mod.py") is narrow, not over-broad.
   over_broad_literal_globs(root) appears to run (and WARN) unconditionally
   during `_render_already_landed_markers` regardless of whether the
   ticket's scope needs package-prefix resolution at all -- worth checking
   whether that call is even necessary on this code path, or whether the
   WARN should be logged at a lower level / only when a package-prefix glob
   is actually present in scope.

10. tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_real_subcommand_unanchored_warns_unbound
    `assert all(v.severity == Severity.WARN for v in warned)` failed -- some
    DOC004 violations for "$ frob check --delta" now come back at a
    different severity than WARN. Not root-caused; needs the actual
    violation list printed to see which severity and why.

## Plan
Each of the 10 items above needs its own read of the relevant source before
a fix lands -- do not batch-fix. Where the root cause is a genuine product
regression, fix product code with the existing test as the repro (test-first,
BUG002). Where it is checked-in-literal/Makefile-recipe staleness, update the
literal/test to match current, verified behavior (not just to make the
assertion pass). Split further into per-item tickets if a fix turns out to be
non-trivial once investigated.
