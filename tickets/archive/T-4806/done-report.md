## Done report

# T-4806 -- ci: bump pinned GitHub Actions from Dependabot PRs 6-10 on dev in one commit and retarget Dependabot to dev

## What changed

- .github/workflows/ci.yml
  - actions/checkout 4.4.0 (11d5960a326750d5838078e36cf38b85af677262) -> 7.0.1
    (3d3c42e5aac5ba805825da76410c181273ba90b1), 2 occurrences.
  - astral-sh/setup-uv 5.4.2 (d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86) -> 10.0.1
    (20cfd1bf945f4377ade1205e4dbc17946fc9a30d), 2 occurrences.
  - actions/cache 4.3.0 (0057852bfaa89a56745cba8c7296529d2fc39830) -> 6.1.0
    (55cc8345863c7cc4c66a329aec7e433d2d1c52a9), 1 occurrence.
  - Added a T-4806 comment on the first checkout/setup-uv block recording the
    breaking-change check (Node 24 runtime is already the GitHub-hosted
    default; UV_VERSION is pinned independently of setup-uv's own cache
    defaults).

- .github/workflows/release.yml
  - Same actions/checkout and astral-sh/setup-uv bumps as ci.yml, applied at
    every one of their occurrences (5 checkout, 5 setup-uv).
  - actions/upload-artifact 4.6.2 (ea165f8d65b6e75b540449e92b4886f43607fa02) ->
    7.0.1 (043fb46d1a93c77aae656e7c1c64a875d1fc6a0a), 5 occurrences.
  - actions/download-artifact 4.3.0 (d3f86a106a0bac45b974a628896c90dbdf5c8093)
    -> 8.0.1 (3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c), 5 occurrences.
  - Added a T-4806 comment on the first job recording the breaking-change
    check: every multi-artifact download here already passes
    `merge-multiple: true` (required by download-artifact when `pattern:`
    can match more than one artifact), `retention-days` is still a supported
    upload-artifact v7 input, and setup-uv is never given cache inputs here
    so its v10 cache-default change is inert.
  - All SHAs and trailing `# vX.Y.Z` comments were copied verbatim from
    `gh pr diff <6|7|8|9|10>` -- not hand-typed.

- .github/dependabot.yml
  - Added `target-branch: "dev"` under the github-actions ecosystem entry so
    future Dependabot PRs open against dev instead of the frozen main.

## Why

Owner decision: main is frozen, so the five open Dependabot PRs (#6-#10,
all targeting main) can never merge there. Landing their content as one
ticket/commit on dev keeps the pins current without touching main, and
retargeting Dependabot's `target-branch` stops it from opening more PRs
against a branch nothing lands to.

## Acceptance criteria and how each is proven

1. All actions/checkout, actions/cache, actions/upload-artifact,
   actions/download-artifact and astral-sh/setup-uv `uses:` refs in
   .github/workflows/*.yml are 40-hex SHA pins with matching trailing
   version comments, bumped per Dependabot PRs 6-10.
   - Evidence: tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_ci_workflow_uses_are_all_sha_pinned
   - Evidence: tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_release_workflow_uses_are_all_sha_pinned
   - Evidence: tests/test_ci_workflow_toolchain_pins.py::TestUvVersionIsPinned::test_every_setup_uv_step_pins_the_shared_version
   - All three pass (12/12 collected in this run, 0 failed).

2. dependabot.yml declares target-branch: dev for the github-actions
   ecosystem.
   - Evidence: cmd:grep -n "target-branch: \"dev\"" .github/dependabot.yml
     (exit=0, sha256=3ff22f8116b6)

3. release.yml's artifact-download steps using `pattern:` still pass
   merge-multiple: true and upload-artifact's retention-days input is
   preserved across the version bump (no silent breaking-change
   regression).
   - Evidence: cmd:bash /tmp/verify_ac3.sh (exit=0, sha256=8eec9caf6cb7)
     -- asserts merge-multiple: true appears 4 times and retention-days: 90
     appears 5 times in release.yml, matching the pre-bump counts.

Test node ids (rerun standalone to reproduce):
`PYTHONPATH=$(pwd)/src /home/logan/projects/frob/.claude/worktrees/t-4806/.venv/bin/python -m pytest tests/test_ci_workflow_actions_pinned.py tests/test_ci_workflow_toolchain_pins.py -p no:cacheprovider -q`
-> `SUITE-RESULT: exitstatus=0 collected=12 failed=0`

Commit: 43fccdc9d "chore(ci): bump pinned GitHub Actions from Dependabot PRs 6-10"
(worktree /home/logan/projects/frob/.claude/worktrees/t-4806, branch t-4806)

Evidence was bound to T-4806 AFTER this commit (no commits followed the
evidence binding).

## Filed

None. No out-of-scope work discovered; all edits stayed inside
.github/workflows/*.yml and .github/dependabot.yml.

## For the coordinator: PR closure (do NOT run these yourself -- pushes
cancel running CI on these PR branches)

gh pr close 6 --comment "superseded by 43fccdc9d on dev"
gh pr close 7 --comment "superseded by 43fccdc9d on dev"
gh pr close 8 --comment "superseded by 43fccdc9d on dev"
gh pr close 9 --comment "superseded by 43fccdc9d on dev"
gh pr close 10 --comment "superseded by 43fccdc9d on dev"

(Replace 43fccdc9d with the final landed dev SHA if it differs after land's
rebase/merge.)

## Notes for the coordinator

- Ticket T-4806 had no acceptance criteria at file time; I added 3 via
  `frob ticket accept` before binding evidence (the ledger's structured
  acceptance list, not the markdown "## Acceptance" body section, which the
  evidence verb does not parse). The `frob ticket accept` write reported it
  could not mirror onto the ROOT checkout ("git add failed" -- fleet
  contention) -- the acceptance criteria and evidence are both live and
  correct in this worktree's ticket.md; the ROOT mirror may need a
  `frob ticket sweep`/re-run once the repo is quiet if the fleet needs to
  see them before this ticket lands.
- `.github/workflows/ci.yml` is also named in a STALE lease file
  (.git/frob-leases/T-4490.json, worktree .claude/worktrees/t-draft-926571db,
  recorded 2026-09-15). `frob ticket show T-4490` returns "no ticket
  T-4490" -- it does not resolve in the active ledger, so this is not a
  live in-progress conflict, just dead lease state the coordinator may want
  to clean up (that worktree directory still exists on disk).
- `git diff --name-only dev...HEAD` = exactly the 3 files in this ticket's
  own lease plus tickets/T-4806/ticket.md (the ticket's own file, not a
  cross-ticket concern).

## Pre-READY checks

- `frob check --only sys --files .github/workflows/ci.yml --files .github/workflows/release.yml --files .github/dependabot.yml --base dev`:
  Tool summary: FAIL gate:DRIFT 6 errors (5 waived, 1 in
  src/frob/tickets/_evidence.py with no coverage of dependent doc left
  unwaived -- pre-existing, unrelated to this change, none in
  .github/*), FAIL gate:DSL 1 error (tests/test_app.py:387, pre-existing
  "# noqa: E501" malformed directive, unrelated to this change, not in
  .github/*), pass gate:DOCARCH/PROFILE/WAIVE. Zero SELFAUDIT001 and zero
  findings of any kind attributable to .github/workflows/ci.yml,
  .github/workflows/release.yml, or .github/dependabot.yml.

- `frob check --only arch --files .github/workflows/ci.yml --files .github/workflows/release.yml --files .github/dependabot.yml --base dev`:
  Tool summary: pass frob-arch (21 warnings, 546 suggestions, all
  pre-existing pattern-recommendations in src/frob/*.py and scripts/*.py --
  none in .github/*). No ARCH001, no LARGE001.

- `frob check --only coverage --files .github/workflows/ci.yml --files .github/workflows/release.yml --files .github/dependabot.yml --base dev`:
  Tool summary: FAIL gate:COV (10 errors, all pre-existing COV006/COV007
  in src/frob/vet/*.py and tests/gates_suite/*.py, unrelated, none in
  .github/*), FAIL gate:DRIFT/DSL/TODO (same pre-existing findings as the
  sys check above, none in .github/* or naming this ticket's files).
  No COV002 anywhere in the output (this change adds no Python public
  symbols -- YAML/config only).

- `ruff check <touched>` / `ty check <touched>`: N/A -- this ticket
  touches only .github/workflows/ci.yml, .github/workflows/release.yml
  and .github/dependabot.yml; no Python files were added or changed, so
  there is nothing for ruff or ty to lint/typecheck.

- `frob vet` (bare, since VET009 is not an `--only` stage name): exited 0.
  Output was entirely uv.lock dependency-obfuscation-heuristic and
  VET-SOURCE-UNAVAILABLE findings unrelated to GitHub Actions pinning; no
  VET009 (unpinned CI action) finding appeared anywhere, consistent with
  every `uses:` in both workflow files remaining a full 40-hex SHA after
  the bump.

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 ++-
 .frob-release.json                                 |   2 +-
 .github/dependabot.yml                             |   1 +
 .github/workflows/ci.yml                           | 123 ++-
 .github/workflows/release.yml                      |  45 +-
 CHANGELOG.md                                       |  71 ++
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
 changelog.d/T-4572.md                              |   2 +
 changelog.d/T-4579.md                              |   2 +
 changelog.d/T-4582.md                              |   2 +
 changelog.d/T-4583.md                              |   2 +
 changelog.d/T-4588.md                              |   2 +
 changelog.d/T-4596.md                              |   2 +
 changelog.d/T-4607.md                              |   2 +
 changelog.d/T-4633.md                              |   2 +
 changelog.d/T-4634.md                              |   2 +
 changelog.d/T-4642.md                              |   2 +
 changelog.d/T-4646.md                              |   2 +
 changelog.d/T-4649.md                              |   2 +
 changelog.d/T-4650.md                              |   2 +
 changelog.d/T-4659.md                              |   2 +
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
 docs/modules/tickets-lifecycle.md                  |  58 ++
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
 src/frob/app/ticket_runner/_land_cmd.py            | 532 ++++++++++-
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
 src/frob/lang/_nodes.py                            | 159 +++-
 src/frob/lang/_project_detect.py                   | 147 ++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 ++-
 src/frob/scaffold/_unity_project.py                | 193 ++++
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
 src/frob/tickets/_land_compose.py                  | 209 +++--
 src/frob/tickets/_land_git_ops.py                  | 149 +++-
 src/frob/tickets/_land_queue.py                    | 151 +++-
 src/frob/tickets/_land_squash.py                   | 263 +++++-
 src/frob/tickets/_leases.py                        | 617 +++++++++----
 src/frob/tickets/_models.py                        |  80 +-
 src/frob/tickets/_registry_files.py                | 145 +++
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
 tests/test_waive_gate.py                           | 145 +++
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
 tests/unit/test_dotnet_runner.py                   | 194 ++++
 tests/unit/test_land_cas_ledger_retry.py           | 312 +++++++
 tests/unit/test_land_default_queue.py              | 128 +++
 tests/unit/test_land_in_progress_window.py         | 351 ++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 ++
 tests/unit/test_land_merge_conflict_drop.py        | 198 +++++
 tests/unit/test_land_queue.py                      | 114 +++
 tests/unit/test_land_stackdump.py                  | 321 +++++++
 tests/unit/test_lang_project_detect.py             | 108 +++
 tests/unit/test_lease_lifecycle.py                 | 180 ++++
 tests/unit/test_leases_staleness_perf.py           | 310 +++++++
 tests/unit/test_lifecycle_work_base.py             | 217 +++++
 tests/unit/test_pyproject_data_memoization.py      | 124 +++
 tests/unit/test_rel002_dev_suffix.py               | 113 +++
 tests/unit/test_scaffold_unity_project.py          | 128 +++
 tests/unit/test_store_mode_memoization.py          | 110 +++
 tests/unit/test_support_csharp.py                  | 190 ++++
 tests/unit/test_suppress_worktree_path.py          |  87 ++
 tests/unit/test_ticket_cli_surface.py              | 182 ++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_unity_batchmode.py                 | 194 ++++
 tests/unit/test_xref.py                            | 118 +++
 tests/vet_suite/test_capability_registry_unity.py  | 130 +++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 ++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py | 119 +++
 tickets/T-1382/ticket.md                           |   8 +-
 tickets/T-1597/ticket.md                           |   9 +-
 tickets/T-1661/ticket.md                           |  23 +-
 tickets/T-1686/ticket.md                           |  14 +-
 tickets/T-1778/ticket.md                           |  17 +-
 tickets/T-1820/ticket.md                           |  17 +-
 tickets/T-1831/ticket.md                           |  17 +-
 tickets/T-2451/ticket.md                           |  17 +-
 tickets/T-2752/ticket.md                           |  17 +-
 tickets/T-2803/ticket.md                           |  17 +-
 tickets/T-2835/ticket.md                           |  17 +-
 tickets/T-2837/ticket.md                           |  17 +-
 tickets/T-2856/ticket.md                           |  17 +-
 tickets/T-2886/ticket.md                           |  29 +-
 tickets/T-2889/ticket.md                           |  35 +-
 tickets/T-2939/ticket.md                           |  17 +-
 tickets/T-2962/ticket.md                           |  17 +-
 tickets/T-2964/ticket.md                           |   9 +-
 tickets/T-2965/done-report.md                      | 149 ++++
 tickets/T-2965/ticket.md                           |  52 +-
 tickets/T-2987/ticket.md                           |   8 +-
 tickets/T-2994/ticket.md                           |  16 +-
 tickets/T-2998/ticket.md                           |  14 +-
 tickets/T-3020/done-report.md                      | 578 ++++++++++++
 tickets/T-3020/ticket.md                           |  50 +-
 tickets/T-3022/ticket.md                           |  16 +-
 tickets/T-3032/ticket.md                           |  89 +-
 tickets/T-3053/ticket.md                           |  32 +-
 tickets/T-3063/ticket.md                           |  17 +-
 tickets/T-3067/ticket.md                           |  23 +-
 tickets/T-3073/ticket.md                           |   9 +-
 tickets/T-3082/ticket.md                           |  63 +-
 tickets/T-3083/ticket.md                           |  17 +-
 tickets/T-3102/ticket.md                           |  23 +-
 tickets/T-3127/ticket.md                           |  23 +-
 tickets/T-3193/ticket.md                           |  29 +-
 tickets/T-3213/ticket.md                           |  17 +-
 tickets/T-3221/ticket.md                           |  17 +-
 tickets/T-3229/ticket.md                           |  23 +-
 tickets/T-3232/done-report.md                      | 179 ++++
 tickets/T-3232/ticket.md                           |  88 +-
 tickets/T-3233/done-report.md                      | 606 +++++++++++++
 tickets/T-3233/ticket.md                           |  62 +-
 tickets/T-3241/ticket.md                           |  17 +-
 tickets/T-3259/ticket.md                           |  24 +-
 tickets/T-3262/ticket.md                           |  23 +-
 tickets/T-3269/ticket.md                           |   9 +-
 tickets/T-3270/ticket.md                           |  23 +-
 tickets/T-3274/ticket.md                           |  16 +-
 tickets/T-3282/ticket.md                           |   8 +-
 tickets/T-3284/ticket.md                           |   9 +-
 tickets/T-3299/ticket.md                           |   9 +-
 tickets/T-3304/ticket.md                           |   9 +-
 tickets/T-3306/ticket.md                           |   9 +-
 tickets/T-3307/ticket.md                           |   9 +-
 tickets/T-3312/ticket.md                           |   9 +-
 tickets/T-3313/ticket.md                           |   9 +-
 tickets/T-3319/ticket.md                           |   9 +-
 tickets/T-3321/ticket.md                           |   9 +-
 tickets/T-3327/ticket.md                           |  17 +-
 tickets/T-3330/ticket.md                           |  17 +-
 tickets/T-3331/ticket.md                           |   9 +-
 tickets/T-3332/ticket.md                           |   9 +-
 tickets/T-3333/ticket.md                           |   9 +-
 tickets/T-3334/ticket.md                           |   9 +-
 tickets/T-3335/ticket.md                           |  23 +-
 tickets/T-3340/ticket.md                           |  15 +-
 tickets/T-3351/ticket.md                           |  17 +-
 tickets/T-3357/ticket.md                           |  17 +-
 tickets/T-3359/ticket.md                           |  17 +-
 tickets/T-3377/ticket.md                           |  17 +-
 tickets/T-3412/ticket.md                           |  40 +-
 tickets/T-3415/ticket.md                           |  23 +-
 tickets/T-3459/ticket.md                           |  23 +-
 tickets/T-3504/ticket.md                           |  23 +-
 tickets/T-3505/ticket.md                           |  16 +-
 tickets/T-3513/ticket.md                           |  17 +-
 tickets/T-3559/ticket.md                           |  23 +-
 tickets/T-3564/ticket.md                           |  23 +-
 tickets/T-3602/ticket.md                           |  16 +-
 tickets/T-3611/ticket.md                           |   8 +-
 tickets/T-3612/done-report.md                      | 221 +++++
 tickets/T-3612/ticket.md                           | 156 +++-
 tickets/T-3613/done-report.md                      | 106 +++
 tickets/T-3613/ticket.md                           | 212 ++++-
 tickets/T-3614/ticket.md                           | 117 ++-
 tickets/T-3615/done-report.md                      |  33 +
 tickets/T-3615/ticket.md                           |  30 +-
 tickets/T-3620/ticket.md                           |  16 +-
 tickets/T-3639/ticket.md                           |   9 +-
 tickets/T-3646/ticket.md                           |  17 +-
 tickets/T-3659/ticket.md                           |  16 +-
 tickets/T-3660/ticket.md                           |  17 +-
 tickets/T-3677/ticket.md                           |  17 +-
 tickets/T-3710/ticket.md                           |   9 +-
 tickets/T-3714/ticket.md                           |  23 +-
 tickets/T-3716/ticket.md                           |  23 +-
 tickets/T-3717/ticket.md                           |   9 +-
 tickets/T-3718/ticket.md                           |   9 +-
 tickets/T-3719/ticket.md                           |   9 +-
 tickets/T-3728/ticket.md                           |  17 +-
 tickets/T-3729/ticket.md                           |  17 +-
 tickets/T-3739/ticket.md                           |  17 +-
 tickets/T-3758/ticket.md                           |  17 +-
 tickets/T-3783/ticket.md                           |  16 +-
 tickets/T-3789/ticket.md                           |  17 +-
 tickets/T-3802/ticket.md                           |  27 +-
 tickets/T-3803/ticket.md                           |   9 +-
 tickets/T-3804/ticket.md                           |   9 +-
 tickets/T-3805/ticket.md                           |   9 +-
 tickets/T-3806/ticket.md                           |   9 +-
 tickets/T-3807/ticket.md                           |  15 +-
 tickets/T-3808/ticket.md                           |   9 +-
 tickets/T-3811/ticket.md                           |  16 +-
 tickets/T-3817/ticket.md                           |  21 +-
 tickets/T-3821/ticket.md                           |  46 +-
 tickets/T-3822/ticket.md                           | 147 +++-
 tickets/T-3823/ticket.md                           | 154 +++-
 tickets/T-3824/ticket.md                           |   9 +-
 tickets/T-3825/ticket.md                           |  57 +-
 tickets/T-3826/ticket.md                           |   9 +-
 tickets/T-3827/ticket.md                           |   9 +-
 tickets/T-3828/ticket.md                           |   9 +-
 tickets/T-3831/ticket.md                           |   9 +-
 tickets/T-3832/ticket.md                           |  52 +-
 tickets/T-3833/ticket.md                           |  44 +-
 tickets/T-3835/ticket.md                           |   9 +-
 tickets/T-3836/ticket.md                           |   9 +-
 tickets/T-3838/ticket.md                           |   9 +-
 tickets/T-3839/ticket.md                           |   9 +-
 tickets/T-3840/ticket.md                           |   9 +-
 tickets/T-3841/ticket.md                           |   9 +-
 tickets/T-3842/ticket.md                           |   9 +-
 tickets/T-3843/ticket.md                           |  18 +-
 tickets/T-3849/ticket.md                           |   9 +-
 tickets/T-3850/ticket.md                           |  23 +-
 tickets/T-3851/ticket.md                           |  26 +
 tickets/T-3853/ticket.md                           |   9 +-
 tickets/T-3854/ticket.md                           |  21 +-
 tickets/T-3856/done-report.md                      | 247 ++++++
 tickets/T-3856/ticket.md                           |  60 +-
 tickets/T-3859/ticket.md                           |  23 +-
 tickets/T-3867/ticket.md                           |  17 +-
 tickets/T-3873/ticket.md                           |   9 +-
 tickets/T-3879/ticket.md                           |   9 +-
 tickets/T-3882/ticket.md                           |  23 +-
 tickets/T-3883/ticket.md                           |  17 +-
 tickets/T-3896/ticket.md                           |  17 +-
 tickets/T-3898/ticket.md                           |   9 +-
 tickets/T-3899/ticket.md                           |  26 +
 tickets/T-3902/ticket.md                           |   8 +-
 tickets/T-3904/ticket.md                           |  23 +-
 tickets/T-3911/ticket.md                           |   9 +-
 tickets/T-3917/ticket.md                           |  17 +-
 tickets/T-3918/ticket.md                           |  16 +-
 tickets/T-3919/ticket.md                           |  17 +-
 tickets/T-3920/ticket.md                           |  95 +-
 tickets/T-3923/ticket.md                           |  17 +-
 tickets/T-3924/ticket.md                           |   9 +-
 tickets/T-3926/ticket.md                           |   9 +-
 tickets/T-3927/ticket.md                           |  21 +-
 tickets/T-3929/ticket.md                           |  22 +-
 tickets/T-3943/done-report.md                      | 626 +++++++++++++
 tickets/T-3943/ticket.md                           |  49 +-
 tickets/T-3944/ticket.md                           |   9 +-
 tickets/T-3946/ticket.md                           |   9 +-
 tickets/T-3949/ticket.md                           |   9 +-
 tickets/T-3950/ticket.md                           |   9 +-
 tickets/T-3951/ticket.md                           |   9 +-
 tickets/T-3953/ticket.md                           |   9 +-
 tickets/T-3957/ticket.md                           |   9 +-
 tickets/T-3958/ticket.md                           |   9 +-
 tickets/T-3961/done-report.md                      | 701 +++++++++++++++
 tickets/T-3961/ticket.md                           |  47 +-
 tickets/T-3962/ticket.md                           |  21 +-
 tickets/T-3964/ticket.md                           |  22 +-
 tickets/T-3973/ticket.md                           |   9 +-
 tickets/T-3974/ticket.md                           |   9 +-
 tickets/T-3978/ticket.md                           |   8 +-
 tickets/T-3979/ticket.md                           |  39 +-
 tickets/T-3981/ticket.md                           |   9 +-
 tickets/T-3983/ticket.md                           |   8 +-
 tickets/T-3986/ticket.md                           |  17 +-
 tickets/T-3987/ticket.md                           |   9 +-
 tickets/T-3988/ticket.md                           |   9 +-
 tickets/T-3989/ticket.md                           |   9 +-
 tickets/T-3990/ticket.md                           |   9 +-
 tickets/T-3991/ticket.md                           |   9 +-
 tickets/T-3992/ticket.md                           |   9 +-
 tickets/T-3993/ticket.md                           |   9 +-
 tickets/T-3994/ticket.md                           |   9 +-
 tickets/T-3995/ticket.md                           |  28 +-
 tickets/T-3996/ticket.md                           |   9 +-
 tickets/T-3997/ticket.md                           |  25 +-
 tickets/T-4002/ticket.md                           |   8 +-
 tickets/T-4006/ticket.md                           |  15 +-
 tickets/T-4010/ticket.md                           |  23 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4019/ticket.md                           |  27 +-
 tickets/T-4021/ticket.md                           |   9 +-
 tickets/T-4022/ticket.md                           |   8 +-
 tickets/T-4025/ticket.md                           |   9 +-
 tickets/T-4029/ticket.md                           |  16 +-
 tickets/T-4030/ticket.md                           |   9 +-
 tickets/T-4033/ticket.md                           |   9 +-
 tickets/T-4034/ticket.md                           |   9 +-
 tickets/T-4035/ticket.md                           |  11 +-
 tickets/T-4036/ticket.md                           |   9 +-
 tickets/T-4038/ticket.md                           |   9 +-
 tickets/T-4039/ticket.md                           |   9 +-
 tickets/T-4044/ticket.md                           |   8 +-
 tickets/T-4045/ticket.md                           |   8 +-
 tickets/T-4048/ticket.md                           |   8 +-
 tickets/T-4049/ticket.md                           |   8 +-
 tickets/T-4050/ticket.md                           |  15 +-
 tickets/T-4051/ticket.md                           |   8 +-
 tickets/T-4052/ticket.md                           |   9 +-
 tickets/T-4053/ticket.md                           |   8 +-
 tickets/T-4054/ticket.md                           |   8 +-
 tickets/T-4061/ticket.md                           |   9 +-
 tickets/T-4062/ticket.md                           |   9 +-
 tickets/T-4063/ticket.md                           |   9 +-
 tickets/T-4068/ticket.md                           |   9 +-
 tickets/T-4072/ticket.md                           |   9 +-
 tickets/T-4073/ticket.md                           |  21 +-
 tickets/T-4074/ticket.md                           |   9 +-
 tickets/T-4075/ticket.md                           |   9 +-
 tickets/T-4077/ticket.md                           |   9 +-
 tickets/T-4078/ticket.md                           |   9 +-
 tickets/T-4079/ticket.md                           |   9 +-
 tickets/T-4080/ticket.md                           |   9 +-
 tickets/T-4081/ticket.md                           |   9 +-
 tickets/T-4082/ticket.md                           |   9 +-
 tickets/T-4084/ticket.md                           |   9 +-
 tickets/T-4089/ticket.md                           |   9 +-
 tickets/T-4090/ticket.md                           |   9 +-
 tickets/T-4091/ticket.md                           |   9 +-
 tickets/T-4092/ticket.md                           |   9 +-
 tickets/T-4093/ticket.md                           |   9 +-
 tickets/T-4094/ticket.md                           |   9 +-
 tickets/T-4095/ticket.md                           |   9 +-
 tickets/T-4096/ticket.md                           |   9 +-
 tickets/T-4097/ticket.md                           |   9 +-
 tickets/T-4098/ticket.md                           |   9 +-
 tickets/T-4100/ticket.md                           |   9 +-
 tickets/T-4101/ticket.md                           |   9 +-
 tickets/T-4109/ticket.md                           |   9 +-
 tickets/T-4111/done-report.md                      | 726 +++++++++++++++
 tickets/T-4111/ticket.md                           |  29 +-
 tickets/T-4112/ticket.md                           |  57 +-
 tickets/T-4113/ticket.md                           |  58 +-
 tickets/T-4114/ticket.md                           |  18 +-
 tickets/T-4115/ticket.md                           |  18 +-
 tickets/T-4116/done-report.md                      | 707 +++++++++++++++
 tickets/T-4116/ticket.md                           |  17 +-
 tickets/T-4117/ticket.md                           |   8 +-
 tickets/T-4118/ticket.md                           |  38 +-
 tickets/T-4119/ticket.md                           |   9 +-
 tickets/T-4120/ticket.md                           |   9 +-
 tickets/T-4123/ticket.md                           |   9 +-
 tickets/T-4126/ticket.md                           |   9 +-
 tickets/T-4127/ticket.md                           |  63 +-
 tickets/T-4128/ticket.md                           |   9 +-
 tickets/T-4129/ticket.md                           |   9 +-
 tickets/T-4134/ticket.md                           |   9 +-
 tickets/T-4135/ticket.md                           |   9 +-
 tickets/T-4140/ticket.md                           |   9 +-
 tickets/T-4141/ticket.md                           |   9 +-
 tickets/T-4144/ticket.md                           |   9 +-
 tickets/T-4145/ticket.md                           |  35 +-
 tickets/T-4147/ticket.md                           |  19 +-
 tickets/T-4152/ticket.md                           |   9 +-
 tickets/T-4153/ticket.md                           |  23 +-
 tickets/T-4156/ticket.md                           |   9 +-
 tickets/T-4157/ticket.md                           |   9 +-
 tickets/T-4164/ticket.md                           |   9 +-
 tickets/T-4166/ticket.md                           |   9 +-
 tickets/T-4174/ticket.md                           |   9 +-
 tickets/T-4175/ticket.md                           |   9 +-
 tickets/T-4181/ticket.md                           |   9 +-
 tickets/T-4182/ticket.md                           |   9 +-
 tickets/T-4185/ticket.md                           |   7 +-
 tickets/T-4186/ticket.md                           |   7 +-
 tickets/T-4187/ticket.md                           |   9 +-
 tickets/T-4188/ticket.md                           |   9 +-
 tickets/T-4189/ticket.md                           |   9 +-
 tickets/T-4190/ticket.md                           |   9 +-
 tickets/T-4192/ticket.md                           |   9 +-
 tickets/T-4193/ticket.md                           |   9 +-
 tickets/T-4194/ticket.md                           |   9 +-
 tickets/T-4198/ticket.md                           |   9 +-
 tickets/T-4199/ticket.md                           |   9 +-
 tickets/T-4200/ticket.md                           |   9 +-
 tickets/T-4202/ticket.md                           |   9 +-
 tickets/T-4203/ticket.md                           |   9 +-
 tickets/T-4204/ticket.md                           |   9 +-
 tickets/T-4205/ticket.md                           |   9 +-
 tickets/T-4206/ticket.md                           |   9 +-
 tickets/T-4211/ticket.md                           |   9 +-
 tickets/T-4212/ticket.md                           |  25 +-
 tickets/T-4214/done-report.md                      | 667 ++++++++++++++
 tickets/T-4214/ticket.md                           |  46 +-
 tickets/T-4215/ticket.md                           |   9 +-
 tickets/T-4216/ticket.md                           |   9 +-
 tickets/T-4217/ticket.md                           |   9 +-
 tickets/T-4218/ticket.md                           |   9 +-
 tickets/T-4220/ticket.md                           |   9 +-
 tickets/T-4221/done-report.md                      | 706 +++++++++++++++
 tickets/T-4221/ticket.md                           |  92 +-
 tickets/T-4222/ticket.md                           |   9 +-
 tickets/T-4223/ticket.md                           |   9 +-
 tickets/T-4224/ticket.md                           |   9 +-
 tickets/T-4225/ticket.md                           |   9 +-
 tickets/T-4226/ticket.md                           |   9 +-
 tickets/T-4227/ticket.md                           |   9 +-
 tickets/T-4228/ticket.md                           |   9 +-
 tickets/T-4229/ticket.md                           |   9 +-
 tickets/T-4230/done-report.md                      | 723 +++++++++++++++
 tickets/T-4230/ticket.md                           |  15 +-
 tickets/T-4231/ticket.md                           |   9 +-
 tickets/T-4232/ticket.md                           |   9 +-
 tickets/T-4233/ticket.md                           |   9 +-
 tickets/T-4237/ticket.md                           |   9 +-
 tickets/T-4238/ticket.md                           |   9 +-
 tickets/T-4239/ticket.md                           |   9 +-
 tickets/T-4240/ticket.md                           |  11 +-
 tickets/T-4242/ticket.md                           |   9 +-
 tickets/T-4245/ticket.md                           |   9 +-
 tickets/T-4248/ticket.md                           |   9 +-
 tickets/T-4249/ticket.md                           |   9 +-
 tickets/T-4250/ticket.md                           |   9 +-
 tickets/T-4252/ticket.md                           |   9 +-
 tickets/T-4253/ticket.md                           |   9 +-
 tickets/T-4254/ticket.md                           |  19 +-
 tickets/T-4259/ticket.md                           |   9 +-
 tickets/T-4261/ticket.md                           |   9 +-
 tickets/T-4296/ticket.md                           |   9 +-
 tickets/T-4303/ticket.md                           |  25 +-
 tickets/T-4311/ticket.md                           |   9 +-
 tickets/T-4330/ticket.md                           |   9 +-
 tickets/T-4362/ticket.md                           |  10 +-
 tickets/T-4365/ticket.md                           |   6 +-
 tickets/T-4379/ticket.md                           |   9 +-
 tickets/T-4383/ticket.md                           |   9 +-
 tickets/T-4392/ticket.md                           |  11 +-
 tickets/T-4410/ticket.md                           |   9 +-
 tickets/T-4413/done-report.md                      |  71 ++
 tickets/T-4413/ticket.md                           |  75 +-
 tickets/T-4414/done-report.md                      |  21 +
 tickets/T-4414/ticket.md                           |  23 +-
 tickets/T-4415/done-report.md                      |  25 +
 tickets/T-4415/ticket.md                           |  24 +-
 tickets/T-4416/ticket.md                           |  65 +-
 tickets/T-4418/ticket.md                           |  17 +-
 tickets/T-4419/ticket.md                           | 242 ++++-
 tickets/T-4420/ticket.md                           | 382 +++++++-
 tickets/T-4421/ticket.md                           | 490 ++++++++++-
 tickets/T-4422/ticket.md                           |  17 +-
 tickets/T-4423/ticket.md                           |  17 +-
 tickets/T-4437/ticket.md                           |  23 +-
 tickets/T-4438/ticket.md                           |   7 +-
 tickets/T-4447/ticket.md                           |  11 +-
 tickets/T-4469/ticket.md                           |   7 +-
 tickets/T-4471/ticket.md                           |   7 +-
 tickets/T-4473/ticket.md                           |  18 +-
 tickets/T-4484/ticket.md                           |   9 +-
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
 tickets/T-4499/ticket.md                           |  52 ++
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
 tickets/T-4511/done-report.md                      |  97 ++
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
 tickets/T-4519/done-report.md                      | 869 ++++++++++++++++++
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
 tickets/T-4530/ticket.md                           |  71 ++
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
 tickets/T-4538/ticket.md                           |  63 ++
 tickets/T-4539/ticket.md                           |  29 +
 tickets/T-4540/done-report.md                      | 543 ++++++++++++
 tickets/T-4540/ticket.md                           |  55 ++
 tickets/T-4541/ticket.md                           | 112 +++
 tickets/T-4542/ticket.md                           |  58 ++
 tickets/T-4543/done-report.md                      | 115 +++
 tickets/T-4543/ticket.md                           |  79 ++
 tickets/T-4546/ticket.md                           |  91 ++
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
 tickets/T-4559/ticket.md                           |  57 ++
 tickets/T-4560/ticket.md                           |  48 +
 tickets/T-4561/ticket.md                           |  38 +
 tickets/T-4562/done-report.md                      | 665 ++++++++++++++
 tickets/T-4562/ticket.md                           |  54 ++
 tickets/T-4563/done-report.md                      | 556 ++++++++++++
 tickets/T-4563/ticket.md                           |  47 +
 tickets/T-4566/ticket.md                           | 157 ++++
 tickets/T-4567/ticket.md                           |  34 +
 tickets/T-4571/ticket.md                           |  50 ++
 tickets/T-4572/done-report.md                      | 972 +++++++++++++++++++++
 tickets/T-4572/ticket.md                           |  73 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4574/ticket.md                           |  36 +
 tickets/T-4575/ticket.md                           |  44 +
 tickets/T-4578/ticket.md                           |  59 ++
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
 tickets/T-4589/ticket.md                           |  56 ++
 tickets/T-4596/done-report.md                      | 640 ++++++++++++++
 tickets/T-4596/ticket.md                           |  43 +
 tickets/T-4597/ticket.md                           |  34 +
 tickets/T-4598/ticket.md                           |  46 +
 tickets/T-4599/ticket.md                           |  76 ++
 tickets/T-4600/ticket.md                           |  28 +
 tickets/T-4601/ticket.md                           |  27 +
 tickets/T-4602/ticket.md                           |  44 +
 tickets/T-4603/ticket.md                           |  30 +
 tickets/T-4605/ticket.md                           |  82 ++
 tickets/T-4606/ticket.md                           |  27 +
 tickets/T-4607/done-report.md                      | 803 +++++++++++++++++
 tickets/T-4607/ticket.md                           |  96 ++
 tickets/T-4608/ticket.md                           |  41 +
 tickets/T-4609/ticket.md                           |  34 +
 tickets/T-4610/ticket.md                           |  28 +
 tickets/T-4611/ticket.md                           |  28 +
 tickets/T-4612/ticket.md                           | 122 +++
 tickets/T-4615/ticket.md                           | 107 +++
 tickets/T-4616/ticket.md                           |  49 ++
 tickets/T-4617/ticket.md                           |  27 +
 tickets/T-4618/ticket.md                           |  58 ++
 tickets/T-4619/ticket.md                           |  70 ++
 tickets/T-4620/ticket.md                           |  58 ++
 tickets/T-4622/ticket.md                           | 107 +++
 tickets/T-4623/ticket.md                           |  70 ++
 tickets/T-4624/ticket.md                           |  52 ++
 tickets/T-4625/ticket.md                           |  43 +
 tickets/T-4626/ticket.md                           |  27 +
 tickets/T-4627/ticket.md                           |  58 ++
 tickets/T-4628/ticket.md                           |  60 ++
 tickets/T-4629/ticket.md                           |  53 ++
 tickets/T-4630/ticket.md                           |  61 ++
 tickets/T-4631/ticket.md                           |  78 ++
 tickets/T-4632/ticket.md                           |  48 +
 tickets/T-4633/done-report.md                      | 743 ++++++++++++++++
 tickets/T-4633/ticket.md                           |  86 ++
 tickets/T-4634/done-report.md                      | 851 ++++++++++++++++++
 tickets/T-4634/ticket.md                           |  54 ++
 tickets/T-4635/ticket.md                           |  30 +
 tickets/T-4640/ticket.md                           |  37 +
 tickets/T-4641/ticket.md                           |  29 +
 tickets/T-4642/done-report.md                      | 671 ++++++++++++++
 tickets/T-4642/ticket.md                           |  52 ++
 tickets/T-4643/ticket.md                           |  29 +
 tickets/T-4644/ticket.md                           |  29 +
 tickets/T-4645/ticket.md                           |  66 ++
 tickets/T-4646/done-report.md                      | 914 +++++++++++++++++++
 tickets/T-4646/ticket.md                           |  43 +
 tickets/T-4647/ticket.md                           |  49 ++
 tickets/T-4648/ticket.md                           |  35 +
 tickets/T-4649/done-report.md                      | 888 +++++++++++++++++++
 tickets/T-4649/ticket.md                           | 105 +++
 tickets/T-4650/done-report.md                      | 961 ++++++++++++++++++++
 tickets/T-4650/ticket.md                           | 166 ++++
 tickets/T-4651/ticket.md                           |  55 ++
 tickets/T-4652/ticket.md                           |  46 +
 tickets/T-4653/ticket.md                           |  44 +
 tickets/T-4654/ticket.md                           |  48 +
 tickets/T-4655/ticket.md                           |  43 +
 tickets/T-4656/ticket.md                           |  47 +
 tickets/T-4657/ticket.md                           |  74 ++
 tickets/T-4658/ticket.md                           |  65 ++
 tickets/T-4659/done-report.md                      | 962 ++++++++++++++++++++
 tickets/T-4659/ticket.md                           |  92 ++
 tickets/T-4660/ticket.md                           |  60 ++
 tickets/T-4661/ticket.md                           |  66 ++
 tickets/T-4662/ticket.md                           |  85 ++
 tickets/T-4663/ticket.md                           |  88 ++
 tickets/T-4664/ticket.md                           |  68 ++
 tickets/T-4665/ticket.md                           |  69 ++
 tickets/T-4666/ticket.md                           |  72 ++
 tickets/T-4667/ticket.md                           |  63 ++
 tickets/T-4668/ticket.md                           | 146 ++++
 tickets/T-4669/ticket.md                           |  89 ++
 tickets/T-4670/ticket.md                           |  86 ++
 tickets/T-4671/ticket.md                           | 105 +++
 tickets/T-4672/ticket.md                           | 139 +++
 tickets/T-4673/ticket.md                           |  83 ++
 tickets/T-4674/ticket.md                           |  90 ++
 tickets/T-4675/ticket.md                           | 104 +++
 tickets/T-4676/ticket.md                           |  91 ++
 tickets/T-4677/done-report.md                      |  40 +
 tickets/T-4677/ticket.md                           | 173 ++++
 tickets/T-4678/done-report.md                      |  48 +
 tickets/T-4678/ticket.md                           | 201 +++++
 tickets/T-4679/ticket.md                           |  29 +
 tickets/T-4680/done-report.md                      |  55 ++
 tickets/T-4680/ticket.md                           | 211 +++++
 tickets/T-4681/ticket.md                           | 226 +++++
 tickets/T-4684/ticket.md                           |  65 ++
 tickets/T-4685/ticket.md                           |  59 ++
 tickets/T-4686/ticket.md                           |  40 +
 tickets/T-4687/ticket.md                           | 225 +++++
 tickets/T-4688/ticket.md                           | 149 ++++
 tickets/T-4689/ticket.md                           |  99 +++
 tickets/T-4690/ticket.md                           | 214 +++++
 tickets/T-4691/ticket.md                           | 143 +++
 tickets/T-4692/ticket.md                           | 208 +++++
 tickets/T-4693/ticket.md                           | 138 +++
 tickets/T-4694/ticket.md                           | 127 +++
 tickets/T-4695/ticket.md                           | 181 ++++
 tickets/T-4696/ticket.md                           | 162 ++++
 tickets/T-4697/ticket.md                           | 120 +++
 tickets/T-4698/ticket.md                           | 165 ++++
 tickets/T-4702/ticket.md                           | 104 +++
 tickets/T-4703/ticket.md                           | 122 +++
 tickets/T-4709/ticket.md                           | 158 ++++
 tickets/T-4710/ticket.md                           | 116 +++
 tickets/T-4711/ticket.md                           |  80 ++
 tickets/T-4712/ticket.md                           |  78 ++
 tickets/T-4713/ticket.md                           |  90 ++
 tickets/T-4714/ticket.md                           |  86 ++
 tickets/T-4715/ticket.md                           | 175 ++++
 tickets/T-4716/ticket.md                           |  47 +
 tickets/T-4717/ticket.md                           |  75 ++
 tickets/T-4718/ticket.md                           | 163 ++++
 tickets/T-4719/ticket.md                           | 189 ++++
 tickets/T-4720/ticket.md                           |  36 +
 tickets/T-4721/ticket.md                           |  36 +
 tickets/T-4722/ticket.md                           | 183 ++++
 tickets/T-4723/ticket.md                           | 191 ++++
 tickets/T-4724/ticket.md                           |  42 +
 tickets/T-4735/ticket.md                           |  62 ++
 tickets/T-4736/ticket.md                           |  63 ++
 tickets/T-4737/ticket.md                           | 113 +++
 tickets/T-4738/ticket.md                           |  62 ++
 tickets/T-4739/ticket.md                           |  58 ++
 tickets/T-4740/ticket.md                           |  60 ++
 tickets/T-4741/ticket.md                           | 179 ++++
 tickets/T-4742/ticket.md                           |  79 ++
 tickets/T-4743/ticket.md                           |  80 ++
 tickets/T-4757/ticket.md                           |  87 ++
 tickets/T-4758/ticket.md                           |  94 ++
 tickets/T-4759/ticket.md                           | 106 +++
 tickets/T-4760/ticket.md                           | 116 +++
 tickets/T-4761/ticket.md                           | 126 +++
 tickets/T-4762/ticket.md                           |  69 ++
 tickets/T-4763/ticket.md                           |  64 ++
 tickets/T-4764/ticket.md                           |  79 ++
 tickets/T-4765/ticket.md                           | 108 +++
 tickets/T-4766/ticket.md                           |  84 ++
 tickets/T-4767/ticket.md                           | 173 ++++
 tickets/T-4768/ticket.md                           |  84 ++
 tickets/T-4769/ticket.md                           |  74 ++
 tickets/T-4770/ticket.md                           | 157 ++++
 tickets/T-4771/ticket.md                           |  77 ++
 tickets/T-4772/ticket.md                           |  97 ++
 tickets/T-4773/ticket.md                           | 109 +++
 tickets/T-4774/ticket.md                           |  82 ++
 tickets/T-4804/ticket.md                           | 180 ++++
 tickets/T-4805/ticket.md                           | 114 +++
 tickets/T-4806/ticket.md                           |  64 ++
 tickets/T-4807/ticket.md                           | 108 +++
 tickets/T-4808/ticket.md                           | 155 ++++
 tickets/T-4809/ticket.md                           |  75 ++
 tickets/T-4810/ticket.md                           |  92 ++
 tickets/T-4811/ticket.md                           |  31 +
 tickets/T-4848/ticket.md                           |  84 ++
 tickets/T-4853/ticket.md                           |  96 ++
 tickets/T-4855/ticket.md                           |  84 ++
 tickets/T-4856/ticket.md                           |  97 ++
 tickets/T-4857/ticket.md                           |  84 ++
 tickets/T-4863/ticket.md                           |  84 ++
 tickets/T-4869/ticket.md                           |  84 ++
 tickets/T-4870/ticket.md                           |  84 ++
 tickets/T-4871/ticket.md                           |  85 ++
 tickets/T-4874/ticket.md                           |  84 ++
 tickets/T-4910/ticket.md                           |  31 +
 tickets/T-4911/ticket.md                           | 114 +++
 tickets/T-4912/ticket.md                           |  42 +
 tickets/T-4913/ticket.md                           |  34 +
 tickets/T-4950/ticket.md                           |  34 +
 tickets/T-4951/ticket.md                           | 113 +++
 tickets/T-4952/ticket.md                           | 112 +++
 tickets/T-4953/ticket.md                           |  34 +
 tickets/T-4989/ticket.md                           |  30 +
 tickets/T-4990/ticket.md                           |  34 +
 tickets/T-4991/ticket.md                           |  33 +
 tickets/T-4992/ticket.md                           |  37 +
 tickets/T-4993/ticket.md                           | 110 +++
 tickets/T-4994/ticket.md                           |  93 ++
 tickets/T-4995/ticket.md                           |  91 ++
 tickets/T-4996/ticket.md                           |  90 ++
 tickets/T-4997/ticket.md                           |  86 ++
 tickets/T-draft-0a0c7b43/ticket.md                 | 125 +++
 tickets/T-draft-0bcabfa4/done-report.md            |  38 +
 tickets/T-draft-0bcabfa4/ticket.md                 | 345 ++++++++
 tickets/T-draft-12bce48e/ticket.md                 |  87 ++
 tickets/T-draft-14fb5072/ticket.md                 |  29 +
 tickets/T-draft-16d31169/ticket.md                 |  99 +++
 tickets/T-draft-1f0f55cb/ticket.md                 |  65 ++
 tickets/T-draft-22cc8b71/ticket.md                 |  99 +++
 tickets/T-draft-27d3ece1/ticket.md                 | 123 +++
 tickets/T-draft-2eeb3c7b/ticket.md                 |  36 +
 tickets/T-draft-31fbe483/ticket.md                 |  34 +
 tickets/T-draft-36c347fe/ticket.md                 |  68 ++
 tickets/T-draft-52ad62d5/ticket.md                 |  73 ++
 tickets/T-draft-538a0625/ticket.md                 |  38 +
 tickets/T-draft-54ccb3cd/ticket.md                 |  99 +++
 tickets/T-draft-5658939f/ticket.md                 |  60 ++
 tickets/T-draft-5b9f1e10/ticket.md                 |  99 +++
 tickets/T-draft-5cac4632/ticket.md                 | 107 +++
 tickets/T-draft-5df98ed9/ticket.md                 |  30 +
 tickets/T-draft-65fc375e/ticket.md                 |  33 +
 tickets/T-draft-6e70e293/ticket.md                 | 106 +++
 tickets/T-draft-706ae266/ticket.md                 |  52 ++
 tickets/T-draft-7755815c/ticket.md                 |  52 ++
 tickets/T-draft-8c1c8d09/ticket.md                 |  35 +
 tickets/T-draft-8c7e665d/ticket.md                 |  45 +
 tickets/T-draft-9d041fdf/ticket.md                 |  74 ++
 tickets/T-draft-a379c28b/ticket.md                 | 120 +++
 tickets/T-draft-a38af1c4/ticket.md                 |  77 ++
 tickets/T-draft-a693d397/ticket.md                 |  61 ++
 tickets/T-draft-af37d815/ticket.md                 |  78 ++
 tickets/T-draft-b835a81a/ticket.md                 |  37 +
 tickets/T-draft-cab0639b/ticket.md                 |  37 +
 tickets/T-draft-cd9fd605/ticket.md                 |  35 +
 tickets/T-draft-d4a0057c/ticket.md                 |  99 +++
 tickets/T-draft-d97a3de1/ticket.md                 |  99 +++
 tickets/T-draft-dd69498c/ticket.md                 |  99 +++
 tickets/T-draft-e51e8f8d/ticket.md                 | 100 +++
 tickets/T-draft-f24022de/ticket.md                 |  50 ++
 tickets/T-draft-f3b28013/ticket.md                 |  68 ++
 tickets/T-draft-f78b975b/ticket.md                 | 106 +++
 tickets/T-draft-ff65ecc5/ticket.md                 |  73 ++
 tickets/archive/T-0090/ticket.md                   |  18 +
 tickets/archive/T-0240/ticket.md                   |  18 +
 tickets/archive/T-0292/ticket.md                   |  18 +
 tickets/archive/T-0336/ticket.md                   |  18 +
 tickets/archive/T-0364/ticket.md                   |  24 +
 tickets/archive/T-0396/ticket.md                   |  39 +-
 tickets/archive/T-0403/ticket.md                   |  18 +
 tickets/archive/T-0441/ticket.md                   |  26 +-
 tickets/archive/T-0467/ticket.md                   |  24 +
 tickets/archive/T-0470/ticket.md                   |  35 +
 tickets/archive/T-0525/ticket.md                   |  18 +
 tickets/archive/T-0540/ticket.md                   |  38 +-
 tickets/archive/T-0553/ticket.md                   |  18 +
 tickets/archive/T-0557/ticket.md                   |  18 +
 tickets/archive/T-0576/ticket.md                   |  29 +
 tickets/archive/T-0639/ticket.md                   |  25 +
 tickets/archive/T-0730/ticket.md                   |  18 +
 tickets/archive/T-0731/ticket.md                   |  27 +
 tickets/archive/T-0747/ticket.md                   |  27 +
 tickets/archive/T-0779/ticket.md                   |  53 +-
 tickets/archive/T-0808/ticket.md                   |  31 +-
 tickets/archive/T-0814/ticket.md                   |  26 +
 tickets/archive/T-0968/ticket.md                   |  25 +
 tickets/archive/T-0971/ticket.md                   |  45 +-
 tickets/archive/T-0978/ticket.md                   |  48 +-
 tickets/archive/T-1148/ticket.md                   |  18 +
 tickets/archive/T-1211/ticket.md                   |  36 +-
 tickets/archive/T-1234/ticket.md                   |  31 +-
 tickets/archive/T-1261/ticket.md                   |  32 +
 tickets/archive/T-1265/ticket.md                   |  18 +
 tickets/archive/T-1266/ticket.md                   |  18 +
 tickets/archive/T-1341/ticket.md                   |  28 +-
 tickets/archive/T-1391/ticket.md                   |  33 +-
 tickets/archive/T-1402/ticket.md                   |  18 +
 tickets/archive/T-1421/ticket.md                   |  31 +-
 tickets/archive/T-1428/ticket.md                   |  31 +
 tickets/archive/T-1548/ticket.md                   |  30 +-
 tickets/archive/T-1599/ticket.md                   |  22 +-
 tickets/archive/T-1606/ticket.md                   |  23 +-
 tickets/archive/T-1614/ticket.md                   |  16 +-
 tickets/archive/T-1616/ticket.md                   |  29 +-
 tickets/archive/T-1620/ticket.md                   | 137 +--
 tickets/archive/T-1651/ticket.md                   |  11 +-
 tickets/archive/T-1665/ticket.md                   |  17 +-
 tickets/archive/T-1684/ticket.md                   |  32 +
 tickets/archive/T-1700/ticket.md                   |  26 +
 tickets/archive/T-1725/ticket.md                   | 104 +--
 tickets/archive/T-1746/ticket.md                   |  94 +-
 tickets/archive/T-1748/ticket.md                   |  36 +
 tickets/archive/T-1870/ticket.md                   |  26 +-
 tickets/archive/T-1886/ticket.md                   |  24 +
 tickets/archive/T-1916/ticket.md                   |  19 +-
 tickets/archive/T-2001/ticket.md                   |  16 +
 tickets/archive/T-2011/ticket.md                   |  19 +-
 tickets/archive/T-2025/ticket.md                   |  26 +-
 tickets/archive/T-2069/ticket.md                   |  23 +-
 tickets/archive/T-2131/ticket.md                   |  17 +-
 tickets/archive/T-2193/ticket.md                   |  20 +
 tickets/archive/T-2231/ticket.md                   |  19 +-
 tickets/archive/T-2284/ticket.md                   |  16 +
 tickets/archive/T-2314/ticket.md                   |   9 +
 tickets/archive/T-2338/ticket.md                   |   9 +
 tickets/archive/T-2365/ticket.md                   |  17 +-
 tickets/archive/T-2374/ticket.md                   |  18 +-
 tickets/archive/T-2400/ticket.md                   |  18 +
 tickets/archive/T-2438/ticket.md                   |   9 +
 tickets/archive/T-2454/ticket.md                   |   9 +
 tickets/archive/T-2480/ticket.md                   |  20 +-
 tickets/archive/T-2532/ticket.md                   |  18 +-
 tickets/archive/T-2682/ticket.md                   |  33 +-
 tickets/archive/T-2688/ticket.md                   |   9 +
 tickets/archive/T-2698/ticket.md                   |  27 +-
 tickets/archive/T-2703/ticket.md                   |  20 +-
 tickets/archive/T-2710/ticket.md                   |   9 +
 tickets/archive/T-2922/ticket.md                   |  43 +
 tickets/archive/T-2931/ticket.md                   |  22 +-
 tickets/archive/T-2934/ticket.md                   |  20 +
 tickets/archive/T-2935/ticket.md                   |  20 +-
 tickets/archive/T-3019/ticket.md                   |  23 +-
 tickets/archive/T-3104/ticket.md                   |  39 +-
 tickets/archive/T-3115/ticket.md                   |  17 +
 tickets/archive/T-3128/ticket.md                   |  28 +
 tickets/archive/T-3255/ticket.md                   |   9 +
 tickets/archive/T-3489/ticket.md                   |  18 +-
 tickets/archive/T-3541/ticket.md                   |  20 +-
 tickets/archive/T-3664/ticket.md                   |  11 +-
 tickets/archive/T-3665/ticket.md                   |  10 +-
 tickets/archive/T-3667/ticket.md                   |  28 +-
 uv.lock                                            |   2 +-
 1119 files changed, 84237 insertions(+), 2741 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_ci_workflow_uses_are_all_sha_pinned` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_release_workflow_uses_are_all_sha_pinned` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_toolchain_pins.py::TestUvVersionIsPinned::test_every_setup_uv_step_pins_the_shared_version` (pytest node id, verified passing when recorded)
- `cmd:grep -n "target-branch: \"dev\"" .github/dependabot.yml exit=0 sha256=3ff22f8116b6` (cmd evidence, exit=0)
- `cmd:bash /tmp/verify_ac3.sh exit=0 sha256=8eec9caf6cb7` (cmd evidence, exit=0)
