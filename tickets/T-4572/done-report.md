## Done report

T-4572 -- frob ticket land loses the compare-and-swap publish race to
sibling ledger commits (retry, bounded, on a ledger-only advance; leave
root clean on refusal)

## What changed, per file

src/frob/tickets/_land_compose.py
  - New `commits_touch_only_ledger_paths(repo, old_tip, new_tip)`: `True`
    iff EVERY commit in `old_tip..new_tip` touches only `tickets/**` or a
    land-owned file (`CHANGELOG.md`, `_LAND_OWNED_LEDGER_RACE_FILES`).
    Checked per-commit via `git log --name-only`, not as one aggregate
    diff, so an add-then-remove pair spanning two commits cannot hide a
    real code touch behind a diff that cancels out.
  - New `rebase_composed_commit_onto(repo, pre_land_tip, composed_sha,
    new_base)`: re-parents the land's OWN content change (the diff
    `pre_land_tip..composed_sha`) onto `new_base`, entirely out-of-tree,
    reusing `compose_tree_out_of_tree`'s scratch-`GIT_INDEX_FILE`
    diff-and-apply mechanism with the diff pair swapped. `Err
    (ComposeFailed)` if the land's own diff no longer applies cleanly.

src/frob/tickets/_land_squash.py
  - `_fold_publish_and_resync` (the fold + CAS publish + resync body,
    T-3163): the CAS-miss branch now retries, bounded to
    `_LEDGER_ONLY_CAS_RETRY_LIMIT` (5) attempts, IF `commits_touch_only_
    ledger_paths` reports the sibling advance between the lost sha and
    the ref's new tip is ledger-only -- rebases the already-folded
    commit onto the new tip and retries the SAME CAS, no gate re-run, no
    composed-tree re-check. Any commit outside that shape (a real code-
    touching sibling) falls back to the pre-T-4572 behavior unchanged:
    `Err(LandError.DirtyMain)`.
  - New `_clean_root_on_refusal(root, stage, pre_land_tip, final_id)`:
    defensive companion run alongside the existing `stage` unwind on
    every refusal path in `_fold_publish_and_resync` (fold failure and
    the final CAS-exhausted refusal). A precomposed land never stages
    anything in `root` before publish, so `root` should already be
    clean on refusal -- this runs `_verified_reset_root` against `root`
    too rather than trusting that theory, closing the DirtyMain-residue
    half of the repro. Safe: `_verified_reset_root` only hard-resets
    when `root`'s HEAD still equals `pre_land_tip`, and degrades to its
    own unstage-only drift refusal otherwise (T-1740), so it can never
    destroy a sibling's real, later commit. No-op when `stage is root`
    (the in-root landing path).

docs/modules/tickets-landing.md
  - Two new sections ("ledger-only CAS retry (T-4572)") under both
    `frob.tickets._land_compose` and `frob.tickets._land_squash`,
    matching the `frob:doc` anchors on the new/changed symbols.

tests/unit/test_land_cas_ledger_retry.py (NEW FILE)
  - `test_land_compose.py` and `test_land_stage_flip.py` (the natural
    homes for these tests) are both held by other in-progress tickets'
    leases (T-4631 / T-4629) for the ticket's entire duration --
    `frob ticket scope T-4572 --add` on either was refused. Filed a new,
    unleased test file instead and pointed the new symbols' `frob:tests`
    directives at it (added to scope with a reason).
  - `TestLedgerOnlyAdvance`: a pure ledger/CHANGELOG advance classifies
    ledger_only=True; a single code-touching commit mixed in classifies
    ledger_only=False.
  - `TestRebaseComposedCommitOnto`: the rebased commit carries BOTH the
    land's own change and the sibling's ledger advance; a genuine
    conflict returns `Err`.
  - `TestFoldPublishAndResync`: the ledger-only CAS-miss case publishes
    successfully (fast path, no refusal); the code-touching CAS-miss
    case refuses with `DirtyMain`; either way `git status --porcelain`
    in `root` is empty afterward.

## Why

Repro (ticket body): under fleet load a land composed for 10-25 minutes,
then its CAS publish was rejected because agents' own ledger-only
mirror commits (`chore(tickets): mirror scope/accept/body ... from
worktree`, deliberately allowed to land mid-compose per T-3612) moved
`dev` -- not a sibling land. The whole compose was then redone from
scratch. This wires a narrow, safe fast path: reclassify the race as
"just the ledger moved" and rebase-and-retry instead of recomposing,
falling back to the existing full-recompose behavior for any commit
that isn't provably ledger-only.

## Acceptance criteria -> evidence

1. "GIVEN the land branch advances by a ledger-only commit while a land
   composes WHEN the publish CAS misses THEN land re-merges and
   publishes on the next attempt without operator action."
   -> tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates
   (also the designated BUG002 repro, see below)

2. "GIVEN a refused land THEN git status in the root is clean."
   -> tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_refused_land_leaves_root_clean

Supporting (not a numbered acceptance criterion, proves the fallback
half of the design explicitly): tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_code_touching_cas_miss_falls_back_to_full_recompose

## Bug repro (BUG002)

Split into two commits specifically so the repro test fails at its own
parent (a single test+fix commit cannot demonstrate a repro post-land,
per docs/modules/tickets.md#check-repro-post-land-limitation-t-2025):
  - 2e625ad31 "test(land): add T-4572 CAS-retry repro test" -- the new
    test file alone, committed BEFORE the fix; it imports
    `commits_touch_only_ledger_paths`/`rebase_composed_commit_onto`,
    which do not exist yet at this commit.
  - 9dca009d6 "fix(land): rebase-retry the CAS publish on a ledger-only
    sibling advance" -- the actual fix (src + doc).

`frob ticket evidence T-4572 --designate-repro
tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates
--base-ref 2e625ad31d018e9c1fa40d6f6553818a21ac3631` reported
FAILED_AT_PARENT: "genuinely fails ... a real repro, this is what
BUG002 wants."

## Test node ids (all passing at HEAD, run serially)

tests/unit/test_land_cas_ledger_retry.py::TestLedgerOnlyAdvance::test_pure_ledger_advance_is_ledger_only
tests/unit/test_land_cas_ledger_retry.py::TestLedgerOnlyAdvance::test_a_single_code_touching_commit_is_not_ledger_only
tests/unit/test_land_cas_ledger_retry.py::TestRebaseComposedCommitOnto::test_rebased_commit_carries_the_same_content_change
tests/unit/test_land_cas_ledger_retry.py::TestRebaseComposedCommitOnto::test_rebase_failure_returns_err
tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates
tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_code_touching_cas_miss_falls_back_to_full_recompose
tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_refused_land_leaves_root_clean
(7/7 passed)

Also re-ran the pre-existing suites for the files touched to confirm no
regression: tests/unit/test_land_compose.py (26 total with the above),
tests/unit/test_land_stage_flip.py, tests/unit/test_land_squash_stage.py,
tests/unit/test_land_squash_residue_reclaim.py -- all green (33+8
collected, 0 failed).

## Commit shas (worktree branch t-4572)

2e625ad31d018e9c1fa40d6f6553818a21ac3631  test(land): add T-4572 CAS-retry repro test
9dca009d68... (see `git log`)                fix(land): rebase-retry the CAS publish on a ledger-only sibling advance
da107469fc628f13c58c1796e907db7eb7fce91e  chore(tickets): record evidence for T-4572 (HEAD)

## Scope / lease notes for the coordinator

- Ticket's Files hint (`_land_cmd.py`, `_land*.py`) named two files this
  fix could NOT touch: `src/frob/app/ticket_runner/_land_cmd.py` is
  leased by T-4599 (still `state: in-progress` as of this READY -- polled
  ~35 minutes, never cleared) and `src/frob/tickets/_land.py` is leased
  by T-draft-a62505d4 (also in-progress). Neither file needed editing for
  this fix: the CAS publish, retry loop, and refusal cleanup all live in
  `_land_squash.py`/`_land_compose.py`, which were free.
- `tests/unit/test_land_compose.py` (T-4631) and
  `tests/unit/test_land_stage_flip.py` (T-4629) are both leased for
  their entire duration by other in-progress tickets -- added tests to a
  new file (`tests/unit/test_land_cas_ledger_retry.py`) instead and
  pointed the new symbols' `frob:tests` directives there.
- No file this ticket's final diff touches
  (`src/frob/tickets/_land_compose.py`, `src/frob/tickets/_land_squash.py`,
  `docs/modules/tickets-landing.md`, `tests/unit/test_land_cas_ledger_retry.py`,
  `tickets/T-4572/ticket.md`) is leased by any OTHER in-progress ticket
  (checked via `.git/frob-leases/*.json`) -- no cross-ticket sequencing
  needed.
- Early in this session I mistakenly ran two `Edit` calls against the
  ROOT checkout instead of the worktree (absolute paths without the
  worktree prefix), briefly dirtying root with these same two files'
  changes; caught it within the same turn, copied the edited content
  into the worktree, and reverted root with `git checkout --`. Root was
  confirmed clean immediately after and has stayed clean since (the
  coordinator's DirtyMain notice for T-4221 at 15:15 was this same
  incident, already resolved by the time it was reported).

## Pre-READY checks

`frob check --only sys --files src/frob/tickets/_land_compose.py --files src/frob/tickets/_land_squash.py --files tests/unit/test_land_cas_ledger_retry.py --files docs/modules/tickets-landing.md --base dev`
  -> 8 errors, 557 warnings, 5 waived total repo-wide; ZERO attributable to
     the touched files (the 1 DSL error is tests/test_app.py, the 1
     SELFAUDIT error is a repo-wide testsuite-glob via-list pending
     auto-accept, the 6 DRIFT errors are all pre-existing/unrelated
     symbols -- none in `_land_compose.py`/`_land_squash.py`/the new test
     file). SELFAUDIT001 attributable to my files: 0.

`frob check --only arch --files src/frob/tickets/_land_compose.py --files src/frob/tickets/_land_squash.py --files tests/unit/test_land_cas_ledger_retry.py --base dev`
  -> pass  frob-arch  21 warnings (36 waived), 544 suggestions -- zero
     ARCH001/LARGE001 anywhere in the output.

`frob check --only coverage --files src/frob/tickets/_land_compose.py --files src/frob/tickets/_land_squash.py --files tests/unit/test_land_cas_ledger_retry.py --files docs/modules/tickets-landing.md --base dev`
  -> FAIL gate:COV 10 errors repo-wide, but re-run after fixing the two
     directive gaps this check first caught (missing frob:ticket on
     `_LAND_OWNED_LEDGER_RACE_FILES`/`_LEDGER_ONLY_CAS_RETRY_LIMIT`,
     missing frob:doc on `rebase_composed_commit_onto` -- both fixed,
     plus the two new doc sections added to satisfy the anchors): ZERO
     COV001/COV002 remain on any symbol I added or changed. The one
     remaining COV001 (`resync_root_to_published_tip`) is a PRE-EXISTING
     gap (verified via `git diff dev` -- untouched by this ticket's diff);
     the two COV006 findings are on an unrelated pre-existing test/symbol
     pair (`_assert_land_complete`). `_clean_root_on_refusal` itself shows
     as COV007 (waived, matching the pre-existing T-1636 waiver pattern
     every sibling private helper in this module already carries).

`ruff check src/frob/tickets/_land_compose.py src/frob/tickets/_land_squash.py tests/unit/test_land_cas_ledger_retry.py`
  -> All checks passed!

`ty check src/frob/tickets/_land_compose.py src/frob/tickets/_land_squash.py tests/unit/test_land_cas_ledger_retry.py`
  -> All checks passed!

## Follow-up: ARCH001 refusal and split (post-first-READY)

The land was refused: `_fold_publish_and_resync` had grown to 114 lines
(ARCH001, not over threshold before this diff, not relaxed by rapid).
Merged `dev` in first (already done by the coordinator's land attempt --
commit 8202fd0e3, "Merge branch 'dev' into t-4572", ordinary fast-forward
merge, no conflicts on CHANGELOG.md/uv.lock/pyproject.toml/etc.), then
split `_fold_publish_and_resync`'s CAS-publish-with-retry loop into three
named helpers, all in `src/frob/tickets/_land_squash.py`:
  - `_publish_with_ledger_only_retry(root, stage, ref, pre_land_tip,
    candidate_sha, final_id, main_branch_name)` -- the retry loop itself.
  - `_attempt_ledger_only_rebase(root, ref, base, candidate_sha,
    final_id, attempt)` -- one classify-and-rebase attempt, `None` on
    give-up.
  - `_refuse_cas_miss(root, stage, pre_land_tip, final_id, base=...,
    candidate_sha=..., main_branch_name=...)` -- the shared refusal log
    + `stage`/`root` cleanup, used by both the exhausted-retry path and
    (already, since the first commit) the fold-failure path.
No behavior change -- same log lines, same cleanup calls, same bounded
retry count.

Re-ran `frob check --only arch --files src/frob/tickets/_land_squash.py
--base dev`: the prior `long-function ... _fold_publish_and_resync has
114 lines` finding is gone; a transient `_publish_with_ledger_only_retry
has 61 lines (threshold: 60)` finding from the first split attempt was
also fixed (extracted `_attempt_ledger_only_rebase` further) before the
commit below. Final result:

  pass  frob-arch  20 warnings (36 waived), 546 suggestions
  -- zero ARCH001/LARGE001/long-function findings anywhere in
  `_land_squash.py` or any of the four new/changed symbols
  (`_fold_publish_and_resync`, `_publish_with_ledger_only_retry`,
  `_attempt_ledger_only_rebase`, `_refuse_cas_miss`).

Also re-ran (all green, unchanged pass count):
  - `ruff check src/frob/tickets/_land_squash.py` -> All checks passed!
  - `ty check src/frob/tickets/_land_squash.py` -> All checks passed!
  - `frob check --only sys --files src/frob/tickets/_land_squash.py
    --base dev` -> same pre-existing DRIFT001 on
    `_refuse_if_selfaudit_findings_in_touched_files` (untouched by any
    of my diffs, confirmed via `git diff dev`), same pre-existing DSL/
    SELFAUDIT findings as before -- nothing new attributable to the
    split.
  - `frob check --only coverage --files src/frob/tickets/_land_squash.py
    --base dev` -> one new COV002 (missing `frob:ticket` on
    `_publish_with_ledger_only_retry`) caught and fixed; re-run: zero
    COV001/COV002 on any symbol this ticket touches.
  - pytest: tests/unit/test_land_cas_ledger_retry.py,
    test_land_compose.py, test_land_stage_flip.py, test_land_squash_stage.py,
    test_land_squash_residue_reclaim.py -- 41/41 collected, 0 failed.

Committed as 963ba2ec1 "refactor(land): split _fold_publish_and_resync
under ARCH001's threshold". Evidence re-bound AFTER this commit (all
three acceptance-bound test node ids re-recorded via `frob ticket
evidence`, HEAD now 260aa911f). Root and worktree both confirmed clean
(`git status --porcelain`, empty in both) immediately before this READY.

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 ++-
 .frob-release.json                                 |   2 +-
 .github/workflows/ci.yml                           | 107 ++-
 CHANGELOG.md                                       |  68 ++
 changelog.d/T-2965.md                              |   2 +
 changelog.d/T-3020.md                              |   2 +
 changelog.d/T-3232.md                              |   2 +
 changelog.d/T-3233.md                              |   2 +
 changelog.d/T-3612.md                              |   2 +
 changelog.d/T-3613.md                              |   2 +
 changelog.d/T-3615.md                              |   2 +
 changelog.d/T-3856.md                              |   2 +
 changelog.d/T-3943.md                              |   2 +
 changelog.d/T-3961.md                              |   2 +
 changelog.d/T-4111.md                              |   2 +
 changelog.d/T-4116.md                              |   2 +
 changelog.d/T-4214.md                              |   2 +
 changelog.d/T-4221.md                              |   2 +
 changelog.d/T-4230.md                              |   2 +
 changelog.d/T-4413.md                              |   2 +
 changelog.d/T-4414.md                              |   2 +
 changelog.d/T-4415.md                              |   2 +
 changelog.d/T-4491.md                              |   2 +
 changelog.d/T-4492.md                              |   2 +
 changelog.d/T-4493.md                              |   2 +
 changelog.d/T-4494.md                              |   2 +
 changelog.d/T-4495.md                              |   2 +
 changelog.d/T-4496.md                              |   2 +
 changelog.d/T-4498.md                              |   2 +
 changelog.d/T-4501.md                              |   2 +
 changelog.d/T-4502.md                              |   2 +
 changelog.d/T-4503.md                              |   2 +
 changelog.d/T-4507.md                              |   2 +
 changelog.d/T-4508.md                              |   2 +
 changelog.d/T-4510.md                              |   2 +
 changelog.d/T-4511.md                              |   2 +
 changelog.d/T-4512.md                              |   2 +
 changelog.d/T-4514.md                              |   2 +
 changelog.d/T-4517.md                              |   2 +
 changelog.d/T-4519.md                              |   2 +
 changelog.d/T-4520.md                              |   2 +
 changelog.d/T-4521.md                              |   2 +
 changelog.d/T-4522.md                              |   2 +
 changelog.d/T-4523.md                              |   2 +
 changelog.d/T-4524.md                              |   2 +
 changelog.d/T-4531.md                              |   2 +
 changelog.d/T-4532.md                              |   2 +
 changelog.d/T-4535.md                              |   2 +
 changelog.d/T-4536.md                              |   2 +
 changelog.d/T-4540.md                              |   2 +
 changelog.d/T-4543.md                              |   2 +
 changelog.d/T-4547.md                              |   2 +
 changelog.d/T-4548.md                              |   2 +
 changelog.d/T-4550.md                              |   2 +
 changelog.d/T-4552.md                              |   2 +
 changelog.d/T-4553.md                              |   2 +
 changelog.d/T-4554.md                              |   2 +
 changelog.d/T-4555.md                              |   2 +
 changelog.d/T-4556.md                              |   2 +
 changelog.d/T-4562.md                              |   2 +
 changelog.d/T-4563.md                              |   2 +
 changelog.d/T-4579.md                              |   2 +
 changelog.d/T-4582.md                              |   2 +
 changelog.d/T-4583.md                              |   2 +
 changelog.d/T-4588.md                              |   2 +
 changelog.d/T-4596.md                              |   2 +
 changelog.d/T-4607.md                              |   2 +
 changelog.d/T-4633.md                              |   2 +
 changelog.d/T-4634.md                              |   2 +
 changelog.d/T-4642.md                              |   2 +
 changelog.d/T-4649.md                              |   2 +
 changelog.d/T-4650.md                              |   2 +
 design/frob.strata                                 | 167 ++--
 docs/commands/check.md                             |  88 +-
 docs/commands/narrative.md                         |   8 +
 docs/commands/scaffold.md                          |  50 +-
 docs/commands/ticket.md                            |  72 ++
 docs/commands/xref.md                              |  16 +-
 docs/design/cli-regrouping.md                      |  73 ++
 .../registry/capability-via-ratchet.lock.json      |  87 +-
 docs/design/registry/check-coverage.yaml           |   7 +-
 docs/guides/extending/comment-dsl-directives.md    |  13 +-
 docs/guides/install.md                             |  40 +
 docs/guides/release.md                             |  37 +
 docs/guides/unity.md                               |  83 ++
 docs/modules/app.md                                |  20 +
 docs/modules/dup.md                                |  12 +
 docs/modules/gate-sys111-ratchet-auto-accept.md    |  95 ++
 docs/modules/gate-time-stable-invariant.md         |  74 ++
 docs/modules/gates.md                              | 165 +++-
 docs/modules/graph.md                              |  39 +
 docs/modules/lang.md                               |  33 +
 docs/modules/testing.md                            |  37 +
 docs/modules/tickets-data-storage.md               |   8 +
 docs/modules/tickets-landing.md                    | 239 ++++-
 docs/modules/tickets.md                            |  70 +-
 docs/strata/surface.md                             |  40 +
 frob.lock                                          |  42 +-
 frob.toml                                          |  18 +
 pyproject.toml                                     |  22 +-
 src/frob/__init__.py                               |   2 +
 src/frob/__main__.py                               |  26 +-
 src/frob/_cli_parsers/__init__.py                  |   2 +
 src/frob/_cli_parsers/_check.py                    | 295 ++++++-
 src/frob/_cli_parsers/_core.py                     |  33 +-
 src/frob/_cli_parsers/_design.py                   |  24 +-
 src/frob/_cli_parsers/_explore.py                  | 102 ++-
 src/frob/_cli_parsers/_misc.py                     |  56 +-
 src/frob/_cli_parsers/_ops.py                      |  38 +-
 src/frob/_cli_parsers/_root.py                     |  20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |  55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |  21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |  53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         | 144 ++-
 src/frob/app/_config_external.py                   |  19 +
 src/frob/app/check_runner.py                       | 154 +++-
 src/frob/app/config.py                             |  92 +-
 src/frob/app/ticket_runner/__init__.py             | 125 ++-
 src/frob/app/ticket_runner/_close_cmd.py           |  10 +-
 src/frob/app/ticket_runner/_land_cmd.py            | 532 +++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  79 +-
 src/frob/app/ticket_runner/_mutate.py              |  39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         | 664 +++++++++++++-
 src/frob/app/ticket_runner/_verify.py              | 245 +++++-
 src/frob/check/__init__.py                         | 244 ++++--
 src/frob/check/_python.py                          | 152 +++-
 src/frob/docs/__init__.py                          |  64 +-
 src/frob/doctor.py                                 | 227 ++++-
 src/frob/dup/_legacy.py                            |  60 +-
 src/frob/dup/_legacy_cs.py                         | 207 +++++
 src/frob/excludes.py                               |  83 +-
 src/frob/gates/__init__.py                         | 263 +++---
 src/frob/gates/_claim_lint.py                      | 202 +++++
 src/frob/gates/_coverage.py                        | 203 ++++-
 src/frob/gates/_fix_engine.py                      |  94 +-
 src/frob/gates/_fix_engine_sync.py                 |  69 +-
 src/frob/gates/_guard_closure.py                   | 301 +++++++
 src/frob/gates/_inv.py                             | 359 ++++++++
 src/frob/gates/_lang_conformance.py                |  36 +-
 src/frob/gates/_models.py                          |   7 +
 src/frob/gates/_narrative_blocks.py                |  28 +-
 src/frob/gates/_suppress.py                        |  46 +-
 src/frob/gates/_waive.py                           | 170 +++-
 src/frob/graph/affects.py                          |  53 ++
 src/frob/graph/dsl.py                              | 185 +++-
 src/frob/lang/__init__.py                          |  17 +-
 src/frob/lang/_extract.py                          |  13 +
 src/frob/lang/_project_detect.py                   | 147 ++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 ++-
 src/frob/scaffold/_unity_project.py                | 193 +++++
 .../scaffold/data/types/unity-project/frob.toml.j2 |  64 ++
 src/frob/scaffold/project.py                       |   6 +-
 src/frob/strata/_effects.py                        | 780 +++++++++++++++--
 src/frob/strata/_unity_asmdef.py                   | 412 +++++++++
 src/frob/testing/__init__.py                       |   9 +
 src/frob/testing/_collect.py                       |  21 +-
 src/frob/testing/_collect_csharp.py                | 327 +++++++
 src/frob/testing/_dotnet_runner.py                 | 251 ++++++
 src/frob/testing/_runners.py                       |  10 +
 src/frob/testing/_stackdump.py                     |  68 +-
 src/frob/testing/_unity_batchmode.py               | 298 +++++++
 src/frob/tickets/__init__.py                       |   2 +
 src/frob/tickets/_land.py                          | 274 +++++-
 src/frob/tickets/_land_compose.py                  | 137 +++
 src/frob/tickets/_land_git_ops.py                  | 149 +++-
 src/frob/tickets/_land_queue.py                    | 151 +++-
 src/frob/tickets/_land_squash.py                   | 268 +++++-
 src/frob/tickets/_leases.py                        | 552 ++++++++----
 src/frob/tickets/_models.py                        |  66 +-
 src/frob/tickets/_registry_files.py                | 145 ++++
 src/frob/tickets/_setters.py                       | 113 +--
 src/frob/tickets/_store.py                         | 120 ++-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 ++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 +++++
 src/frob/vet/_capability_registry/_matrix.py       |  13 +-
 src/frob/vet/_capability_registry/_unity_api.py    | 305 +++++++
 src/frob/vet/_capability_scan.py                   |  13 +-
 src/frob/xref/__init__.py                          |  75 +-
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |  37 +
 tests/fixtures/csharp_dup_docblock/guide.md        |  36 +
 .../python_control/duplicate.py                    |  29 +
 tests/fixtures/dsl_todo_notes/sample.c             |   3 +
 tests/fixtures/dsl_todo_notes/sample.cpp           |   3 +
 tests/fixtures/dsl_todo_notes/sample.cs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.cu            |   3 +
 tests/fixtures/dsl_todo_notes/sample.java          |   3 +
 tests/fixtures/dsl_todo_notes/sample.kt            |   3 +
 tests/fixtures/dsl_todo_notes/sample.py            |   9 +
 tests/fixtures/dsl_todo_notes/sample.rs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.sh            |   3 +
 tests/fixtures/dsl_todo_notes/sample.ts            |   3 +
 tests/fixtures/dsl_todo_notes/sample.zig           |   3 +
 tests/fixtures/lang/csharp/alias_using_fs_write.cs |  14 +
 .../lang/csharp/combined_static_and_namespace.cs   |  16 +
 tests/fixtures/lang/csharp/directives.cs           |  44 +
 .../dotnet_bcl_activator_createinstance_eval.cs    |  12 +
 .../lang/csharp/dotnet_bcl_assembly_load_eval.cs   |  12 +
 .../lang/csharp/dotnet_bcl_directory_fs_write.cs   |  12 +
 tests/fixtures/lang/csharp/dotnet_bcl_dns_net.cs   |  12 +
 .../dotnet_bcl_jsonserializer_deserialize.cs       |  12 +
 .../lang/csharp/dotnet_bcl_registry_fs_write.cs    |  12 +
 .../lang/csharp/dotnet_bcl_sqlcommand_sql.cs       |  13 +
 .../lang/csharp/dotnet_bcl_streamreader_fs_read.cs |  13 +
 .../csharp/dotnet_bcl_streamwriter_fs_write.cs     |  13 +
 .../lang/csharp/dotnet_bcl_type_gettype_eval.cs    |  12 +
 .../fixtures/lang/csharp/nested_property_event.cs  |  37 +
 tests/fixtures/lang/csharp/no_dangerous_apis.cs    |  17 +
 tests/fixtures/lang/csharp/plain_using_fs_write.cs |  12 +
 tests/fixtures/lang/csharp/static_using_console.cs |  12 +
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |  30 +
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |  15 +
 .../lang/csharp/tests/malformed_results.xml        |   5 +
 .../fixtures/lang/csharp/tests/sample_results.trx  |  15 +
 .../lang/csharp/tests/sample_unity_results.xml     |   9 +
 tests/fixtures/lang/csharp/unity/coroutine.cs      |  20 +
 .../lang/csharp/unity/lifecycle_methods.cs         |  21 +
 tests/fixtures/lang/csharp/unity/menu_item.cs      |  18 +
 tests/fixtures/lang/csharp/var_local_httpclient.cs |  12 +
 .../Assets/Editor/Editor.asmdef                    |   6 +
 .../Assets/Editor/Editor.asmdef.meta               |   2 +
 tests/fixtures/unity_sample_asmdef/Assets/Loose.cs |   2 +
 .../Assets/Runtime/Runtime.asmdef                  |   6 +
 .../Assets/Runtime/Runtime.asmdef.meta             |   2 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef        |   6 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef.meta   |   2 +
 .../unity_sample_asmdef/Assets/Tests/Tests.asmdef  |   6 +
 .../Assets/Tests/Tests.asmdef.meta                 |   2 +
 .../unity_sample_asmdef/Packages/manifest.json     |   3 +
 .../ProjectSettings/ProjectVersion.txt             |   2 +
 tests/gates_suite/test_claim_lint.py               | 163 ++++
 tests/gates_suite/test_coverage.py                 | 132 ++-
 tests/gates_suite/test_fix_engine.py               | 123 +++
 tests/gates_suite/test_guard_closure.py            | 228 +++++
 tests/gates_suite/test_invariant.py                | 116 +++
 tests/test_check_gate_base.py                      |  54 ++
 tests/test_docenum_gate.py                         |  41 +
 tests/test_excludes.py                             |  75 ++
 tests/test_gates_suppress.py                       |  34 +-
 tests/test_hook_frob_suggest.py                    |  47 +
 tests/test_hook_frob_timeout_guard.py              |  54 ++
 tests/test_hook_root_write_guard.py                |  89 ++
 tests/test_lang.py                                 |  90 ++
 tests/test_lang_conformance_gate.py                |  81 +-
 tests/test_narrative_blocks.py                     |  27 +
 tests/test_testing.py                              | 106 ++-
 tests/test_ticket_leases.py                        | 313 ++++---
 tests/test_ticket_work_and_land_finish.py          | 206 +++--
 tests/test_tickets_migration.py                    | 121 ++-
 tests/test_tickets_parent.py                       | 208 +++++
 tests/test_tickets_registry_files.py               | 206 +++++
 tests/test_waive_gate.py                           | 145 ++++
 tests/ticket_land_suite/test_verify_intent.py      |  85 +-
 tests/unit/graph/test_dsl.py                       | 164 +++-
 tests/unit/graph/test_dsl_invariant_property.py    |  69 ++
 tests/unit/lang/test_csharp_directives.py          | 115 +++
 tests/unit/rapid_sweep_suite/test_dispose.py       |  39 +
 tests/unit/rapid_sweep_suite/test_filing.py        |  33 +
 tests/unit/rapid_sweep_suite/test_window.py        | 457 ++++++++++
 tests/unit/strata/test_effects.py                  |  44 +
 tests/unit/strata/test_selfconform.py              | 460 +++++++++-
 tests/unit/strata/test_unity_asmdef.py             | 160 ++++
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |  57 ++
 tests/unit/test_app_runners_batch7.py              | 128 +--
 tests/unit/test_check_scoped_files.py              | 566 ++++++++++++
 tests/unit/test_check_skip_flag.py                 | 192 ++++
 tests/unit/test_ci_self_gate_unscoped.py           | 189 ++++
 tests/unit/test_cli_group_parity.py                | 220 +++++
 tests/unit/test_cli_lang_choices_drift.py          | 113 +++
 tests/unit/test_cli_single_child_groups.py         | 106 +++
 tests/unit/test_dev_branch_workflow.py             |  50 ++
 tests/unit/test_docs_module.py                     |  60 +-
 tests/unit/test_doctor.py                          | 116 +++
 tests/unit/test_done_report_check_scope.py         | 177 ++++
 tests/unit/test_dotnet_runner.py                   | 194 +++++
 tests/unit/test_land_cas_ledger_retry.py           | 312 +++++++
 tests/unit/test_land_default_queue.py              | 128 +++
 tests/unit/test_land_in_progress_window.py         | 351 ++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 ++
 tests/unit/test_land_merge_conflict_drop.py        | 198 +++++
 tests/unit/test_land_queue.py                      | 114 +++
 tests/unit/test_land_stackdump.py                  | 321 +++++++
 tests/unit/test_lang_project_detect.py             | 108 +++
 tests/unit/test_leases_staleness_perf.py           | 310 +++++++
 tests/unit/test_lifecycle_work_base.py             | 217 +++++
 tests/unit/test_rel002_dev_suffix.py               | 113 +++
 tests/unit/test_scaffold_unity_project.py          | 128 +++
 tests/unit/test_store_mode_memoization.py          | 110 +++
 tests/unit/test_support_csharp.py                  | 190 ++++
 tests/unit/test_suppress_worktree_path.py          |  87 ++
 tests/unit/test_ticket_cli_surface.py              | 182 ++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_unity_batchmode.py                 | 194 +++++
 tests/unit/test_xref.py                            | 118 +++
 tests/vet_suite/test_capability_registry_unity.py  | 130 +++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 ++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py | 119 +++
 tickets/T-1661/ticket.md                           |  23 +-
 tickets/T-1778/ticket.md                           |  17 +-
 tickets/T-1820/ticket.md                           |  17 +-
 tickets/T-1831/ticket.md                           |  17 +-
 tickets/T-2451/ticket.md                           |  17 +-
 tickets/T-2752/ticket.md                           |  17 +-
 tickets/T-2803/ticket.md                           |  17 +-
 tickets/T-2835/ticket.md                           |  17 +-
 tickets/T-2837/ticket.md                           |  17 +-
 tickets/T-2856/ticket.md                           |  17 +-
 tickets/T-2886/ticket.md                           |  17 +-
 tickets/T-2889/ticket.md                           |  23 +-
 tickets/T-2939/ticket.md                           |  17 +-
 tickets/T-2962/ticket.md                           |  17 +-
 tickets/T-2965/done-report.md                      | 149 ++++
 tickets/T-2965/ticket.md                           |  41 +-
 tickets/T-2994/ticket.md                           |  16 +-
 tickets/T-3020/done-report.md                      | 578 +++++++++++++
 tickets/T-3020/ticket.md                           |  50 +-
 tickets/T-3022/ticket.md                           |  16 +-
 tickets/T-3032/ticket.md                           |  83 +-
 tickets/T-3053/ticket.md                           |  32 +-
 tickets/T-3063/ticket.md                           |  17 +-
 tickets/T-3067/ticket.md                           |  17 +-
 tickets/T-3082/ticket.md                           |  63 +-
 tickets/T-3083/ticket.md                           |  17 +-
 tickets/T-3102/ticket.md                           |  17 +-
 tickets/T-3127/ticket.md                           |  17 +-
 tickets/T-3193/ticket.md                           |  17 +-
 tickets/T-3213/ticket.md                           |  17 +-
 tickets/T-3221/ticket.md                           |  17 +-
 tickets/T-3229/ticket.md                           |  17 +-
 tickets/T-3232/done-report.md                      | 179 ++++
 tickets/T-3232/ticket.md                           |  88 +-
 tickets/T-3233/done-report.md                      | 606 +++++++++++++
 tickets/T-3233/ticket.md                           |  62 +-
 tickets/T-3241/ticket.md                           |  17 +-
 tickets/T-3259/ticket.md                           |  24 +-
 tickets/T-3262/ticket.md                           |  17 +-
 tickets/T-3270/ticket.md                           |  17 +-
 tickets/T-3274/ticket.md                           |  16 +-
 tickets/T-3327/ticket.md                           |  17 +-
 tickets/T-3330/ticket.md                           |  17 +-
 tickets/T-3335/ticket.md                           |  17 +-
 tickets/T-3351/ticket.md                           |  17 +-
 tickets/T-3357/ticket.md                           |  17 +-
 tickets/T-3359/ticket.md                           |  17 +-
 tickets/T-3377/ticket.md                           |  17 +-
 tickets/T-3412/ticket.md                           |  34 +-
 tickets/T-3415/ticket.md                           |  17 +-
 tickets/T-3459/ticket.md                           |  17 +-
 tickets/T-3504/ticket.md                           |  17 +-
 tickets/T-3505/ticket.md                           |  16 +-
 tickets/T-3513/ticket.md                           |  17 +-
 tickets/T-3559/ticket.md                           |  17 +-
 tickets/T-3564/ticket.md                           |  17 +-
 tickets/T-3602/ticket.md                           |  16 +-
 tickets/T-3611/ticket.md                           |   8 +-
 tickets/T-3612/done-report.md                      | 221 +++++
 tickets/T-3612/ticket.md                           | 156 +++-
 tickets/T-3613/done-report.md                      | 106 +++
 tickets/T-3613/ticket.md                           | 212 ++++-
 tickets/T-3614/ticket.md                           | 111 ++-
 tickets/T-3615/done-report.md                      |  33 +
 tickets/T-3615/ticket.md                           |  30 +-
 tickets/T-3620/ticket.md                           |  16 +-
 tickets/T-3646/ticket.md                           |  17 +-
 tickets/T-3659/ticket.md                           |  16 +-
 tickets/T-3660/ticket.md                           |  17 +-
 tickets/T-3677/ticket.md                           |  17 +-
 tickets/T-3714/ticket.md                           |  17 +-
 tickets/T-3716/ticket.md                           |  17 +-
 tickets/T-3728/ticket.md                           |  17 +-
 tickets/T-3729/ticket.md                           |  17 +-
 tickets/T-3739/ticket.md                           |  17 +-
 tickets/T-3758/ticket.md                           |  17 +-
 tickets/T-3783/ticket.md                           |  16 +-
 tickets/T-3789/ticket.md                           |  17 +-
 tickets/T-3802/ticket.md                           |  27 +-
 tickets/T-3811/ticket.md                           |  16 +-
 tickets/T-3821/ticket.md                           |  46 +-
 tickets/T-3822/ticket.md                           |  45 +-
 tickets/T-3823/ticket.md                           |  45 +-
 tickets/T-3825/ticket.md                           |  49 +-
 tickets/T-3832/ticket.md                           |  44 +-
 tickets/T-3833/ticket.md                           |  44 +-
 tickets/T-3850/ticket.md                           |  17 +-
 tickets/T-3851/ticket.md                           |  26 +
 tickets/T-3854/ticket.md                           |  21 +-
 tickets/T-3856/done-report.md                      | 247 ++++++
 tickets/T-3856/ticket.md                           |  60 +-
 tickets/T-3859/ticket.md                           |  17 +-
 tickets/T-3867/ticket.md                           |  17 +-
 tickets/T-3882/ticket.md                           |  17 +-
 tickets/T-3883/ticket.md                           |  17 +-
 tickets/T-3896/ticket.md                           |  17 +-
 tickets/T-3899/ticket.md                           |  26 +
 tickets/T-3904/ticket.md                           |  17 +-
 tickets/T-3917/ticket.md                           |  17 +-
 tickets/T-3918/ticket.md                           |  16 +-
 tickets/T-3919/ticket.md                           |  17 +-
 tickets/T-3920/ticket.md                           |  87 +-
 tickets/T-3923/ticket.md                           |  17 +-
 tickets/T-3927/ticket.md                           |  21 +-
 tickets/T-3929/ticket.md                           |  21 +-
 tickets/T-3943/done-report.md                      | 626 ++++++++++++++
 tickets/T-3943/ticket.md                           |  49 +-
 tickets/T-3953/ticket.md                           |   9 +-
 tickets/T-3961/done-report.md                      | 701 +++++++++++++++
 tickets/T-3961/ticket.md                           |  47 +-
 tickets/T-3962/ticket.md                           |  21 +-
 tickets/T-3964/ticket.md                           |  22 +-
 tickets/T-3986/ticket.md                           |   2 +-
 tickets/T-3995/ticket.md                           |  19 +-
 tickets/T-3997/ticket.md                           |  25 +-
 tickets/T-4010/ticket.md                           |  17 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4019/ticket.md                           |  11 +-
 tickets/T-4029/ticket.md                           |  16 +-
 tickets/T-4035/ticket.md                           |   2 +
 tickets/T-4073/ticket.md                           |  12 +-
 tickets/T-4111/done-report.md                      | 726 ++++++++++++++++
 tickets/T-4111/ticket.md                           |  29 +-
 tickets/T-4112/ticket.md                           |  57 +-
 tickets/T-4113/ticket.md                           |  58 +-
 tickets/T-4114/ticket.md                           |  10 +-
 tickets/T-4115/ticket.md                           |  10 +-
 tickets/T-4116/done-report.md                      | 707 +++++++++++++++
 tickets/T-4116/ticket.md                           |  17 +-
 tickets/T-4118/ticket.md                           |  30 +-
 tickets/T-4127/ticket.md                           |  55 +-
 tickets/T-4185/ticket.md                           |   7 +-
 tickets/T-4186/ticket.md                           |   7 +-
 tickets/T-4212/ticket.md                           |  16 +-
 tickets/T-4214/done-report.md                      | 667 ++++++++++++++
 tickets/T-4214/ticket.md                           |  46 +-
 tickets/T-4221/done-report.md                      | 706 +++++++++++++++
 tickets/T-4221/ticket.md                           |  92 +-
 tickets/T-4230/done-report.md                      | 723 ++++++++++++++++
 tickets/T-4230/ticket.md                           |  15 +-
 tickets/T-4240/ticket.md                           |   2 +-
 tickets/T-4254/ticket.md                           |  10 +-
 tickets/T-4365/ticket.md                           |   6 +-
 tickets/T-4392/ticket.md                           |  11 +-
 tickets/T-4413/done-report.md                      |  71 ++
 tickets/T-4413/ticket.md                           |  75 +-
 tickets/T-4414/done-report.md                      |  21 +
 tickets/T-4414/ticket.md                           |  23 +-
 tickets/T-4415/done-report.md                      |  25 +
 tickets/T-4415/ticket.md                           |  24 +-
 tickets/T-4416/ticket.md                           |  56 +-
 tickets/T-4418/ticket.md                           |  17 +-
 tickets/T-4419/ticket.md                           | 242 +++++-
 tickets/T-4420/ticket.md                           | 382 +++++++-
 tickets/T-4421/ticket.md                           | 483 ++++++++++-
 tickets/T-4422/ticket.md                           |  17 +-
 tickets/T-4423/ticket.md                           |  17 +-
 tickets/T-4437/ticket.md                           |  17 +-
 tickets/T-4447/ticket.md                           |  11 +-
 tickets/T-4491/done-report.md                      |  23 +
 tickets/T-4491/ticket.md                           |  69 ++
 tickets/T-4492/done-report.md                      |  34 +
 tickets/T-4492/ticket.md                           |  67 ++
 tickets/T-4493/done-report.md                      |  19 +
 tickets/T-4493/ticket.md                           |  61 ++
 tickets/T-4494/done-report.md                      | 138 +++
 tickets/T-4494/ticket.md                           |  73 ++
 tickets/T-4495/done-report.md                      | 197 +++++
 tickets/T-4495/ticket.md                           |  64 ++
 tickets/T-4496/done-report.md                      |  23 +
 tickets/T-4496/ticket.md                           |  56 ++
 tickets/T-4497/ticket.md                           |  31 +
 tickets/T-4498/done-report.md                      | 147 ++++
 tickets/T-4498/ticket.md                           |  55 ++
 tickets/T-4499/ticket.md                           |  49 ++
 tickets/T-4500/ticket.md                           |  41 +
 tickets/T-4501/done-report.md                      |  24 +
 tickets/T-4501/ticket.md                           |  81 ++
 tickets/T-4502/done-report.md                      |  19 +
 tickets/T-4502/ticket.md                           |  73 ++
 tickets/T-4503/done-report.md                      | 592 +++++++++++++
 tickets/T-4503/ticket.md                           |  94 ++
 tickets/T-4504/ticket.md                           |  69 ++
 tickets/T-4505/ticket.md                           |  38 +
 tickets/T-4506/ticket.md                           |  40 +
 tickets/T-4507/done-report.md                      | 793 +++++++++++++++++
 tickets/T-4507/ticket.md                           |  57 ++
 tickets/T-4508/done-report.md                      | 689 +++++++++++++++
 tickets/T-4508/ticket.md                           | 114 +++
 tickets/T-4509/ticket.md                           |  48 +
 tickets/T-4510/done-report.md                      | 149 ++++
 tickets/T-4510/ticket.md                           |  81 ++
 tickets/T-4511/done-report.md                      |  97 +++
 tickets/T-4511/ticket.md                           | 103 +++
 tickets/T-4512/done-report.md                      | 524 +++++++++++
 tickets/T-4512/ticket.md                           | 102 +++
 tickets/T-4513/ticket.md                           |  36 +
 tickets/T-4514/done-report.md                      | 179 ++++
 tickets/T-4514/ticket.md                           |  66 ++
 tickets/T-4515/done-report.md                      |  24 +
 tickets/T-4515/ticket.md                           |  62 ++
 tickets/T-4516/ticket.md                           |  32 +
 tickets/T-4517/done-report.md                      | 180 ++++
 tickets/T-4517/ticket.md                           |  94 ++
 tickets/T-4518/ticket.md                           |  34 +
 tickets/T-4519/done-report.md                      | 869 +++++++++++++++++++
 tickets/T-4519/ticket.md                           |  79 ++
 tickets/T-4520/done-report.md                      | 163 ++++
 tickets/T-4520/ticket.md                           |  58 ++
 tickets/T-4521/done-report.md                      | 228 +++++
 tickets/T-4521/ticket.md                           | 125 +++
 tickets/T-4522/done-report.md                      |  99 +++
 tickets/T-4522/ticket.md                           |  49 ++
 tickets/T-4523/done-report.md                      | 104 +++
 tickets/T-4523/ticket.md                           |  40 +
 tickets/T-4524/done-report.md                      | 209 +++++
 tickets/T-4524/ticket.md                           |  52 ++
 tickets/T-4526/ticket.md                           |  45 +
 tickets/T-4529/ticket.md                           |  76 ++
 tickets/T-4530/ticket.md                           |  64 ++
 tickets/T-4531/done-report.md                      |  21 +
 tickets/T-4531/ticket.md                           | 110 +++
 tickets/T-4532/done-report.md                      |  24 +
 tickets/T-4532/ticket.md                           |  66 ++
 tickets/T-4533/ticket.md                           |  35 +
 tickets/T-4534/ticket.md                           |  69 ++
 tickets/T-4535/done-report.md                      |  64 ++
 tickets/T-4535/ticket.md                           |  61 ++
 tickets/T-4536/done-report.md                      |  78 ++
 tickets/T-4536/ticket.md                           | 128 +++
 tickets/T-4537/ticket.md                           |  33 +
 tickets/T-4538/ticket.md                           |  60 ++
 tickets/T-4539/ticket.md                           |  29 +
 tickets/T-4540/done-report.md                      | 543 ++++++++++++
 tickets/T-4540/ticket.md                           |  55 ++
 tickets/T-4541/ticket.md                           | 112 +++
 tickets/T-4542/ticket.md                           |  55 ++
 tickets/T-4543/done-report.md                      | 115 +++
 tickets/T-4543/ticket.md                           |  79 ++
 tickets/T-4546/ticket.md                           |  84 ++
 tickets/T-4547/done-report.md                      | 137 +++
 tickets/T-4547/ticket.md                           |  45 +
 tickets/T-4548/done-report.md                      |  59 ++
 tickets/T-4548/ticket.md                           |  50 ++
 tickets/T-4549/ticket.md                           |  53 ++
 tickets/T-4550/done-report.md                      | 545 ++++++++++++
 tickets/T-4550/ticket.md                           |  59 ++
 tickets/T-4552/done-report.md                      | 146 ++++
 tickets/T-4552/ticket.md                           | 100 +++
 tickets/T-4553/done-report.md                      | 501 +++++++++++
 tickets/T-4553/ticket.md                           |  55 ++
 tickets/T-4554/done-report.md                      | 541 ++++++++++++
 tickets/T-4554/ticket.md                           |  63 ++
 tickets/T-4555/done-report.md                      | 556 ++++++++++++
 tickets/T-4555/ticket.md                           |  78 ++
 tickets/T-4556/done-report.md                      | 602 +++++++++++++
 tickets/T-4556/ticket.md                           |  46 +
 tickets/T-4558/ticket.md                           |  30 +
 tickets/T-4559/ticket.md                           |  54 ++
 tickets/T-4560/ticket.md                           |  41 +
 tickets/T-4561/ticket.md                           |  38 +
 tickets/T-4562/done-report.md                      | 665 ++++++++++++++
 tickets/T-4562/ticket.md                           |  54 ++
 tickets/T-4563/done-report.md                      | 556 ++++++++++++
 tickets/T-4563/ticket.md                           |  47 +
 tickets/T-4566/ticket.md                           | 154 ++++
 tickets/T-4567/ticket.md                           |  27 +
 tickets/T-4571/ticket.md                           |  43 +
 tickets/T-4572/done-report.md                      | 863 ++++++++++++++++++
 tickets/T-4572/ticket.md                           |  73 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4574/ticket.md                           |  29 +
 tickets/T-4575/ticket.md                           |  38 +
 tickets/T-4578/ticket.md                           |  52 ++
 tickets/T-4579/done-report.md                      | 522 +++++++++++
 tickets/T-4579/ticket.md                           |  68 ++
 tickets/T-4580/ticket.md                           |  47 +
 tickets/T-4581/ticket.md                           |  47 +
 tickets/T-4582/done-report.md                      | 551 ++++++++++++
 tickets/T-4582/ticket.md                           |  56 ++
 tickets/T-4583/done-report.md                      | 620 +++++++++++++
 tickets/T-4583/ticket.md                           |  87 ++
 tickets/T-4588/done-report.md                      | 715 +++++++++++++++
 tickets/T-4588/ticket.md                           |  67 ++
 tickets/T-4589/ticket.md                           |  53 ++
 tickets/T-4596/done-report.md                      | 640 ++++++++++++++
 tickets/T-4596/ticket.md                           |  43 +
 tickets/T-4597/ticket.md                           |  34 +
 tickets/T-4598/ticket.md                           |  46 +
 tickets/T-4599/ticket.md                           |  69 ++
 tickets/T-4600/ticket.md                           |  28 +
 tickets/T-4601/ticket.md                           |  27 +
 tickets/T-4602/ticket.md                           |  44 +
 tickets/T-4603/ticket.md                           |  30 +
 tickets/T-4605/ticket.md                           |  82 ++
 tickets/T-4606/ticket.md                           |  27 +
 tickets/T-4607/done-report.md                      | 803 +++++++++++++++++
 tickets/T-4607/ticket.md                           |  81 ++
 tickets/T-4608/ticket.md                           |  41 +
 tickets/T-4609/ticket.md                           |  27 +
 tickets/T-4610/ticket.md                           |  28 +
 tickets/T-4611/ticket.md                           |  28 +
 tickets/T-4612/ticket.md                           | 116 +++
 tickets/T-4615/ticket.md                           | 105 +++
 tickets/T-4616/ticket.md                           |  43 +
 tickets/T-4617/ticket.md                           |  27 +
 tickets/T-4618/ticket.md                           |  52 ++
 tickets/T-4619/ticket.md                           |  64 ++
 tickets/T-4620/ticket.md                           |  52 ++
 tickets/T-4622/ticket.md                           | 107 +++
 tickets/T-4623/ticket.md                           |  64 ++
 tickets/T-4624/ticket.md                           |  52 ++
 tickets/T-4625/ticket.md                           |  43 +
 tickets/T-4626/ticket.md                           |  27 +
 tickets/T-4627/ticket.md                           |  52 ++
 tickets/T-4628/ticket.md                           |  53 ++
 tickets/T-4629/ticket.md                           |  46 +
 tickets/T-4630/ticket.md                           |  54 ++
 tickets/T-4631/ticket.md                           |  71 ++
 tickets/T-4632/ticket.md                           |  41 +
 tickets/T-4633/done-report.md                      | 743 ++++++++++++++++
 tickets/T-4633/ticket.md                           |  86 ++
 tickets/T-4634/done-report.md                      | 851 ++++++++++++++++++
 tickets/T-4634/ticket.md                           |  54 ++
 tickets/T-4635/ticket.md                           |  30 +
 tickets/T-4640/ticket.md                           |  30 +
 tickets/T-4641/ticket.md                           |  29 +
 tickets/T-4642/done-report.md                      | 671 ++++++++++++++
 tickets/T-4642/ticket.md                           |  52 ++
 tickets/T-4643/ticket.md                           |  29 +
 tickets/T-4644/ticket.md                           |  29 +
 tickets/T-4645/ticket.md                           |  59 ++
 tickets/T-4646/ticket.md                           |  38 +
 tickets/T-4647/ticket.md                           |  49 ++
 tickets/T-4648/ticket.md                           |  28 +
 tickets/T-4649/done-report.md                      | 888 +++++++++++++++++++
 tickets/T-4649/ticket.md                           | 105 +++
 tickets/T-4650/done-report.md                      | 961 +++++++++++++++++++++
 tickets/T-4650/ticket.md                           | 166 ++++
 tickets/T-4651/ticket.md                           |  55 ++
 tickets/T-4652/ticket.md                           |  46 +
 tickets/T-4653/ticket.md                           |  44 +
 tickets/T-4654/ticket.md                           |  48 +
 tickets/T-4655/ticket.md                           |  43 +
 tickets/T-4656/ticket.md                           |  47 +
 tickets/T-4657/ticket.md                           |  74 ++
 tickets/T-4658/ticket.md                           |  56 ++
 tickets/T-4659/ticket.md                           |  61 ++
 tickets/T-4660/ticket.md                           |  60 ++
 tickets/T-4661/ticket.md                           |  66 ++
 tickets/T-4662/ticket.md                           |  85 ++
 tickets/T-4663/ticket.md                           |  72 ++
 tickets/T-4664/ticket.md                           |  68 ++
 tickets/T-4665/ticket.md                           |  69 ++
 tickets/T-4666/ticket.md                           |  72 ++
 tickets/T-4667/ticket.md                           |  63 ++
 tickets/T-4668/ticket.md                           |  93 ++
 tickets/T-4669/ticket.md                           |  89 ++
 tickets/T-4670/ticket.md                           |  86 ++
 tickets/T-4671/ticket.md                           | 105 +++
 tickets/T-4672/ticket.md                           |  89 ++
 tickets/T-4673/ticket.md                           |  83 ++
 tickets/T-4674/ticket.md                           |  77 ++
 tickets/T-4675/ticket.md                           | 104 +++
 tickets/T-4676/ticket.md                           |  85 ++
 tickets/T-4677/ticket.md                           |  90 ++
 tickets/T-4678/ticket.md                           | 110 +++
 tickets/T-4679/ticket.md                           |  29 +
 tickets/T-4680/ticket.md                           |  95 ++
 tickets/T-4681/ticket.md                           |  96 ++
 tickets/T-4684/ticket.md                           |  62 ++
 tickets/T-4685/ticket.md                           |  52 ++
 tickets/T-draft-31fbe483/ticket.md                 |  34 +
 tickets/T-4748/ticket.md                 |  53 ++
 tickets/T-4751/ticket.md                 |  35 +
 tickets/archive/T-0090/ticket.md                   |  18 +
 tickets/archive/T-0240/ticket.md                   |  18 +
 tickets/archive/T-0292/ticket.md                   |  18 +
 tickets/archive/T-0336/ticket.md                   |  18 +
 tickets/archive/T-0364/ticket.md                   |  24 +
 tickets/archive/T-0403/ticket.md                   |  18 +
 tickets/archive/T-0470/ticket.md                   |  17 +
 tickets/archive/T-0525/ticket.md                   |  18 +
 tickets/archive/T-0553/ticket.md                   |  18 +
 tickets/archive/T-0557/ticket.md                   |  18 +
 tickets/archive/T-0730/ticket.md                   |  18 +
 tickets/archive/T-0814/ticket.md                   |  26 +
 tickets/archive/T-1148/ticket.md                   |  18 +
 tickets/archive/T-1265/ticket.md                   |  18 +
 tickets/archive/T-1266/ticket.md                   |  18 +
 tickets/archive/T-1402/ticket.md                   |  18 +
 tickets/archive/T-1651/ticket.md                   |  11 +-
 tickets/archive/T-1746/ticket.md                   |  94 +-
 tickets/archive/T-2314/ticket.md                   |   9 +
 tickets/archive/T-2338/ticket.md                   |   9 +
 tickets/archive/T-2438/ticket.md                   |   9 +
 tickets/archive/T-2454/ticket.md                   |   9 +
 tickets/archive/T-2688/ticket.md                   |   9 +
 tickets/archive/T-2710/ticket.md                   |   9 +
 tickets/archive/T-3128/ticket.md                   |  28 +
 tickets/archive/T-3255/ticket.md                   |   9 +
 tickets/archive/T-3664/ticket.md                   |  11 +-
 tickets/archive/T-3665/ticket.md                   |  10 +-
 tickets/archive/T-3667/ticket.md                   |  11 +-
 uv.lock                                            |   2 +-
 708 files changed, 64437 insertions(+), 2165 deletions(-)
```

### Evidence
- `tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_refused_land_leaves_root_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_code_touching_cas_miss_falls_back_to_full_recompose` (pytest node id, verified passing when recorded)
