## Done report

-- T-4596 (full history)

WHAT changed:
- src/frob/tickets/_land_squash.py: `_refuse_if_selfaudit_findings_in_touched_files`
  (T-3324) now accepts an optional `land_lock_root: Path | None = None`. When given, it
  temporarily writes `FROB_LAND_LOCK_ROOT` into THIS process's `os.environ` (via/finally
  restore of the prior value) for the duration of its in-process calls to
  `selfaudit_findings_touching`/`sys111_findings_touching`/`docptr_findings_touching`, and
  logs the decision (`_log.info`) either way. `_run_pre_commit_checks` gained the same
  optional param and forwards it. `_land_squash_apply_finish` (which already has `root`,
  the primary checkout) now passes `land_lock_root=root` at its `_run_pre_commit_checks`
  call site.
- src/frob/strata/_effects.py: `_land_commit_in_progress` gained two `_log.info` calls --
  one logging which env var value / probe root it resolved to before the file check, one
  logging the file-exists result -- so a real land's log now names exactly which branch
  fired and why.
- tests/test_ticket_work_and_land_finish.py: two new tests in
  `TestSelfauditFindingsInTouchedFiles` that reproduce the land-context path end to end
  (in-process, no subprocess) -- one proves `FROB_LAND_LOCK_ROOT` is visible to
  `os.environ` from INSIDE the mocked gate call when `land_lock_root` is passed, and
  restored after; one proves the default (no `land_lock_root`, every pre-existing caller's
  shape) leaves the environment untouched.

WHY (answers to the coordinator's three questions):
(a) The composed-tree check that actually evaluates SELFAUDIT001/SYS111 for a land runs
    TWO different ways depending on which check this is. T-4583 fixed the SPAWNED
    subprocess path: `_pre_commit_unscoped_error_sweep` (src/frob/app/ticket_runner/
    _land_cmd.py:1919) builds a `lock_env` dict with `FROB_LAND_LOCK_ROOT` and passes it
    as `env=` to the spawned `frob check` subprocess. But the SELFAUDIT001/SYS111 finding
    that actually blocked T-4508 comes from a DIFFERENT function entirely:
    `_refuse_if_selfaudit_findings_in_touched_files` (src/frob/tickets/_land_squash.py:1578,
    T-3324), which calls `frob.gates._sys.sys111_findings_touching` directly, IN-PROCESS --
    no subprocess spawn at all, so there is no child environ to set. T-4583 never touched
    this call site. A rapid-profile land makes this worse, not better: the log confirms
    T-4508's land was running RAPID with the pre-commit sweep OFF (T-1575), but
    `_refuse_if_selfaudit_findings_in_touched_files` runs UNCONDITIONALLY regardless of
    profile (by design, T-3324's own docstring) -- it is the ONLY self-conformance check
    still active on a rapid land, and it is exactly the one T-4583 missed.
(b) `_land_commit_in_progress` (src/frob/strata/_effects.py:1249) probes
    `os.environ.get(FROB_LAND_LOCK_ROOT_ENV)` first; when absent/blank it falls back to
    `root / LAND_LOCK_REL` where `root` is whatever the CALLER passed as `root` to the
    capability-ratchet check -- for `_refuse_if_selfaudit_findings_in_touched_files` that is
    `stage` (the squash worktree / warm-sweep-stage), never the primary checkout.
    `_land_lock` (frob.tickets._leases) actually creates `LAND_LOCK_REL` under the PRIMARY
    checkout the `frob ticket land` command was invoked against, not under `stage`, so the
    fallback probe against `stage / LAND_LOCK_REL` never finds a file -- it doesn't exist
    there. With `FROB_LAND_LOCK_ROOT` unset (this process's real environ, since no
    subprocess sets it here), both signals report "no land in progress", so
    `_land_commit_in_progress` returns `False` and the auto-accept write is correctly (per
    its own contract) refused every time.
(c) Confirmed via the two new tests: the write path itself is not the problem (it is
    exactly as documented -- refusing to write when it cannot prove a land is in progress
    is the SAFE, intended behavior); the bug is that the process never had grounds to
    believe a land was in progress, because the one signal it trusts was never set on this
    call path. Not a read-only-stage or wrong-relative-path issue on the write side itself.

Acceptance criterion: "GIVEN a land with a land_lock_root and a real SYS111
testsuite-glob-growth finding in touched files, WHEN _refuse_if_selfaudit_findings_in_
touched_files runs its in-process gate calls, THEN FROB_LAND_LOCK_ROOT is set in
os.environ for the duration of that call and restored afterward" -- proven by:
- tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_land_lock_root_sets_env_for_the_in_process_gate_call
- tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_no_land_lock_root_leaves_env_untouched
Ran: `PYTHONPATH=$(pwd)/src python -m pytest tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles -q`
-> SUITE-RESULT: exitstatus=0 collected=7 failed=0 (5 pre-existing + 2 new, all green).
Also re-ran tests/unit/strata/test_selfconform.py -k TestTestsuiteViaGlobRatchet (the
T-4563/T-4583 regression tests for the sibling spawned-subprocess path) to confirm no
regression there: SUITE-RESULT: exitstatus=0 collected=6 failed=0.
`ruff check` and `ruff format --check` both clean on the three touched files.

Commit shas: 0637584a1 (the fix itself), d52a197e8 (ticket start transition),
15da915dc (ticket filed), e5d2ed847 (accept), 84d962e2c (evidence),
cb6e9ce2b (ARCH001 follow-up, see below) -- HEAD=cb6e9ce2bf7a9c74e116b0e1edd727bd0c365206.

ARCH001 follow-up (land refusal at /tmp/land-T-4596.log): the first land attempt
was refused because `_refuse_if_selfaudit_findings_in_touched_files` grew to 109 lines
(past ARCH001's long-and-complex threshold) after inlining the env-set/restore dance.
Extracted a shared `land_lock_root_env(land_lock_root)` context manager into
`frob.strata._effects` (next to `FROB_LAND_LOCK_ROOT_ENV`/`_land_commit_in_progress`,
its natural home, and explicitly documented as reusable by T-4583's subprocess-env-
building path too) that sets `FROB_LAND_LOCK_ROOT` for the `with` block and restores it
(or no-ops when `land_lock_root is None`). `_refuse_if_selfaudit_findings_in_touched_files`
now just does `with land_lock_root_env(land_lock_root): findings = (...)`, dropping to 97
lines and a much shorter docstring. Re-ran both test files green (7/7 and 6/6). `ruff
check`/`format` clean. `frob check --only arch --files src/frob/tickets/_land_squash.py
--base dev` -> `pass gate:ARCH: 19 warnings (36 waived), 541 suggestions` -- no ARCH001 on
this function or file; every warning is unrelated repo-wide pattern-recommendation noise
(one WARN, `lock-identity-unresolved` on the new `land_lock_root_env(...)` call, is
expected/harmless -- the naming heuristic can't resolve a plain context-manager call to a
class-level lock construction, and it does not fail the gate).

Filed: none beyond this ticket itself (T-4596). No out-of-scope work discovered.

Follow-up fix (COV002): the extracted context manager was renamed private
(`_land_lock_root_env`) -- only one caller exists and T-4583's subprocess spawn does not
reuse it, so a doc anchor for an unreused public API would have been premature. Docstring
updated accordingly. Commit 842afa4d5 (pre-rename sha; content now folded into this
worktree's history).

Follow-up fix (SELFAUDIT001 SYS100 node=stratamod): `_land_lock_root_env`'s
`os.environ[...] = ...` / `os.environ.pop` set/restore is a genuinely new `env.write` site
on `stratamod`, sibling of the existing T-4573/T-4583 `env.read` declaration for the same
file. Declared `may "env.write" via "src/frob/strata/_effects.py";` in `design/frob.strata`
and added the matching new `stratamod::env.write` lock entry (accepted_count=1, no prior
kind on this node, reason naming this ticket). Also re-acked `_refuse_if_selfaudit_
findings_in_touched_files`'s DRIFT001 digest move from the ARCH001 extraction.
Verified via `frob check --only sys --files src/frob/strata/_effects.py --files
src/frob/tickets/_land_squash.py --base dev`: zero SELFAUDIT001 findings name either file
afterward.

Follow-up fix (deadlock break): this ticket's own land was refused by the exact bug it
fixes -- the land-side SYS111 auto-accept never fires (that's the root cause), so
`testsuite::env.read`/`fs.write`'s pending glob growth (49->50, 536->537) could never
self-clear through the normal land path. Hand-wrote both bumps in
`capability-via-ratchet.lock.json` with reason "pre-accepted by hand because the land-side
auto-accept is the defect this ticket fixes". Verified via `frob check --only sys --base
dev`: `gate:SELFAUDIT` no longer appears in the FAIL list at all.

Ticket id history: filed as T-draft-76fef001, land-side renumbered to T-4596 on this
branch while dev independently promoted the SAME draft to T-4596 -- a rename/rename race.
Per the coordinator's corrected standing rule (dev's promoted id always wins), adopted
T-4596: `git mv`'d the ticket directory, fixed the `id:` line, every `frob:ticket`
directive in src/frob/tickets/_land_squash.py, src/frob/strata/_effects.py and
tests/test_ticket_work_and_land_finish.py, the done-report, and this why-file's own name
and body (T-4596/T-draft-76fef001 -> T-4596 throughout, including the two leftover
references in design/frob.strata and capability-via-ratchet.lock.json missed by the first
pass). No dev ticket directory was deleted -- only the branch's own stale T-4596 dir (a
rename this branch itself introduced, never dev's).

Commit shas (this worktree's full history for the fix): 0637584a1 (core fix),
842afa4d5 (COV002 private rename), 0fb5c62eb (env.write declare), 517b702c5 (finalize as
T-4596), 61b74efcd (T-4596 done-report), a35741103 (merge dev), 77f79c632 (hand-accept
deadlock break), 412a5d7d6 (adopt T-4596), 1cf225152 (finish adopting T-4596, leftover
refs) -- HEAD=1cf225152.

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 ++--
 .frob-release.json                                 |   2 +-
 .github/workflows/ci.yml                           | 107 +++-
 CHANGELOG.md                                       |  51 ++
 changelog.d/T-2965.md                              |   2 +
 changelog.d/T-3020.md                              |   2 +
 changelog.d/T-3232.md                              |   2 +
 changelog.d/T-3233.md                              |   2 +
 changelog.d/T-3612.md                              |   2 +
 changelog.d/T-3613.md                              |   2 +
 changelog.d/T-3615.md                              |   2 +
 changelog.d/T-3856.md                              |   2 +
 changelog.d/T-4214.md                              |   2 +
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
 changelog.d/T-4510.md                              |   2 +
 changelog.d/T-4511.md                              |   2 +
 changelog.d/T-4512.md                              |   2 +
 changelog.d/T-4514.md                              |   2 +
 changelog.d/T-4517.md                              |   2 +
 changelog.d/T-4520.md                              |   2 +
 changelog.d/T-4521.md                              |   2 +
 changelog.d/T-4522.md                              |   2 +
 changelog.d/T-4523.md                              |   2 +
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
 changelog.d/T-4563.md                              |   2 +
 changelog.d/T-4579.md                              |   2 +
 changelog.d/T-4582.md                              |   2 +
 changelog.d/T-4583.md                              |   2 +
 design/frob.strata                                 | 129 ++--
 docs/commands/check.md                             |  15 +
 docs/commands/narrative.md                         |   8 +
 docs/commands/scaffold.md                          |  15 +
 docs/commands/ticket.md                            |  72 +++
 docs/commands/xref.md                              |  16 +-
 docs/design/cli-regrouping.md                      |  73 +++
 .../registry/capability-via-ratchet.lock.json      |  70 ++-
 docs/design/registry/check-coverage.yaml           |   7 +-
 docs/guides/install.md                             |  40 ++
 docs/guides/release.md                             |  37 ++
 docs/modules/app.md                                |  20 +
 docs/modules/dup.md                                |  12 +
 docs/modules/gates.md                              |   3 +-
 docs/modules/graph.md                              |  39 ++
 docs/modules/lang.md                               |  33 +
 docs/modules/testing.md                            |  16 +
 docs/modules/tickets-data-storage.md               |   8 +
 docs/modules/tickets-landing.md                    | 188 +++++-
 docs/modules/tickets.md                            |   9 +-
 docs/strata/surface.md                             |  40 ++
 frob.lock                                          |  42 +-
 pyproject.toml                                     |  22 +-
 src/frob/__init__.py                               |   2 +
 src/frob/__main__.py                               |  26 +-
 src/frob/_cli_parsers/_check.py                    |  16 +
 src/frob/_cli_parsers/_core.py                     |  33 +-
 src/frob/_cli_parsers/_design.py                   |  24 +-
 src/frob/_cli_parsers/_explore.py                  | 102 ++--
 src/frob/_cli_parsers/_misc.py                     |  56 +-
 src/frob/_cli_parsers/_ops.py                      |  38 +-
 src/frob/_cli_parsers/_root.py                     |  20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |  55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |  21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |  53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         | 144 ++++-
 src/frob/app/_config_external.py                   |  19 +
 src/frob/app/check_runner.py                       |  23 +-
 src/frob/app/config.py                             |  92 ++-
 src/frob/app/ticket_runner/__init__.py             | 125 ++--
 src/frob/app/ticket_runner/_land_cmd.py            | 532 +++++++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  79 ++-
 src/frob/app/ticket_runner/_mutate.py              |  39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         | 568 +++++++++++++++++-
 src/frob/app/ticket_runner/_verify.py              | 235 ++++++--
 src/frob/check/__init__.py                         | 244 +++++---
 src/frob/check/_python.py                          | 136 +++--
 src/frob/docs/__init__.py                          |  64 +-
 src/frob/doctor.py                                 | 227 ++++++-
 src/frob/dup/_legacy.py                            |  60 +-
 src/frob/dup/_legacy_cs.py                         | 207 +++++++
 src/frob/excludes.py                               |  83 ++-
 src/frob/gates/__init__.py                         | 263 ++++----
 src/frob/gates/_lang_conformance.py                |  36 +-
 src/frob/gates/_models.py                          |   7 +
 src/frob/gates/_narrative_blocks.py                |  28 +-
 src/frob/gates/_suppress.py                        |  46 +-
 src/frob/gates/_waive.py                           | 170 +++++-
 src/frob/graph/affects.py                          |  53 ++
 src/frob/graph/dsl.py                              | 101 +++-
 src/frob/lang/__init__.py                          |  17 +-
 src/frob/lang/_extract.py                          |  13 +
 src/frob/lang/_project_detect.py                   | 147 +++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 +++-
 src/frob/strata/_effects.py                        | 494 +++++++++++++--
 src/frob/strata/_unity_asmdef.py                   | 412 +++++++++++++
 src/frob/testing/__init__.py                       |   9 +
 src/frob/testing/_collect.py                       |  21 +-
 src/frob/testing/_collect_csharp.py                | 327 ++++++++++
 src/frob/testing/_stackdump.py                     |  68 ++-
 src/frob/tickets/__init__.py                       |   2 +
 src/frob/tickets/_land.py                          | 122 +++-
 src/frob/tickets/_land_git_ops.py                  | 149 ++++-
 src/frob/tickets/_land_queue.py                    | 151 ++++-
 src/frob/tickets/_land_squash.py                   |  48 +-
 src/frob/tickets/_leases.py                        | 552 ++++++++++++-----
 src/frob/tickets/_models.py                        |  42 +-
 src/frob/tickets/_setters.py                       | 113 ++--
 src/frob/tickets/_store.py                         |  42 +-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 ++++++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 +++++++
 src/frob/vet/_capability_registry/_matrix.py       |  13 +-
 src/frob/vet/_capability_registry/_unity_api.py    | 305 ++++++++++
 src/frob/vet/_capability_scan.py                   |  13 +-
 src/frob/xref/__init__.py                          |  54 +-
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |  37 ++
 tests/fixtures/csharp_dup_docblock/guide.md        |  36 ++
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
 tests/fixtures/lang/csharp/no_dangerous_apis.cs    |  17 +
 tests/fixtures/lang/csharp/plain_using_fs_write.cs |  12 +
 tests/fixtures/lang/csharp/static_using_console.cs |  12 +
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |  30 +
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |  15 +
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
 tests/test_excludes.py                             |  75 +++
 tests/test_gates_suppress.py                       |  34 +-
 tests/test_hook_frob_suggest.py                    |  47 ++
 tests/test_hook_frob_timeout_guard.py              |  54 ++
 tests/test_hook_root_write_guard.py                |  89 +++
 tests/test_lang.py                                 |  90 +++
 tests/test_lang_conformance_gate.py                |  81 ++-
 tests/test_narrative_blocks.py                     |  27 +
 tests/test_testing.py                              | 106 +++-
 tests/test_ticket_leases.py                        | 313 ++++++----
 tests/test_ticket_work_and_land_finish.py          | 206 ++++---
 tests/test_tickets_migration.py                    | 121 ++--
 tests/test_tickets_parent.py                       | 208 +++++++
 tests/test_waive_gate.py                           | 145 +++++
 tests/unit/graph/test_dsl.py                       | 164 ++++-
 tests/unit/rapid_sweep_suite/test_window.py        | 457 ++++++++++++++
 tests/unit/strata/test_effects.py                  |  44 ++
 tests/unit/strata/test_selfconform.py              | 263 +++++++-
 tests/unit/strata/test_unity_asmdef.py             | 160 +++++
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |  57 ++
 tests/unit/test_app_runners_batch7.py              | 128 ++--
 tests/unit/test_check_scoped_files.py              | 566 +++++++++++++++++
 tests/unit/test_ci_self_gate_unscoped.py           | 189 ++++++
 tests/unit/test_cli_group_parity.py                | 220 +++++++
 tests/unit/test_cli_lang_choices_drift.py          | 113 ++++
 tests/unit/test_cli_single_child_groups.py         | 106 ++++
 tests/unit/test_dev_branch_workflow.py             |  50 ++
 tests/unit/test_docs_module.py                     |  35 +-
 tests/unit/test_doctor.py                          | 115 ++++
 tests/unit/test_done_report_check_scope.py         | 177 ++++++
 tests/unit/test_land_default_queue.py              | 128 ++++
 tests/unit/test_land_in_progress_window.py         | 351 +++++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 +++
 tests/unit/test_land_merge_conflict_drop.py        | 198 ++++++
 tests/unit/test_land_queue.py                      | 114 ++++
 tests/unit/test_land_stackdump.py                  | 321 ++++++++++
 tests/unit/test_lang_project_detect.py             | 108 ++++
 tests/unit/test_leases_staleness_perf.py           | 310 ++++++++++
 tests/unit/test_lifecycle_work_base.py             | 217 +++++++
 tests/unit/test_rel002_dev_suffix.py               | 113 ++++
 tests/unit/test_support_csharp.py                  | 190 ++++++
 tests/unit/test_suppress_worktree_path.py          |  87 +++
 tests/unit/test_ticket_cli_surface.py              | 182 ++++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_xref.py                            |  40 ++
 tests/vet_suite/test_capability_registry_unity.py  | 130 ++++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 +++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py | 119 ++++
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
 tickets/T-2965/done-report.md                      | 149 +++++
 tickets/T-2965/ticket.md                           |  41 +-
 tickets/T-2994/ticket.md                           |  16 +-
 tickets/T-3020/done-report.md                      | 578 ++++++++++++++++++
 tickets/T-3020/ticket.md                           |  50 +-
 tickets/T-3022/ticket.md                           |  16 +-
 tickets/T-3032/ticket.md                           |  17 +-
 tickets/T-3053/ticket.md                           |  16 +-
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
 tickets/T-3232/done-report.md                      | 179 ++++++
 tickets/T-3232/ticket.md                           |  88 ++-
 tickets/T-3233/done-report.md                      | 606 +++++++++++++++++++
 tickets/T-3233/ticket.md                           |  62 +-
 tickets/T-3241/ticket.md                           |  17 +-
 tickets/T-3259/ticket.md                           |  17 +-
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
 tickets/T-3412/ticket.md                           |  17 +-
 tickets/T-3415/ticket.md                           |  17 +-
 tickets/T-3459/ticket.md                           |  17 +-
 tickets/T-3504/ticket.md                           |  17 +-
 tickets/T-3505/ticket.md                           |  16 +-
 tickets/T-3513/ticket.md                           |  17 +-
 tickets/T-3559/ticket.md                           |  17 +-
 tickets/T-3564/ticket.md                           |  17 +-
 tickets/T-3602/ticket.md                           |  16 +-
 tickets/T-3612/done-report.md                      | 221 +++++++
 tickets/T-3612/ticket.md                           | 156 ++++-
 tickets/T-3613/done-report.md                      | 106 ++++
 tickets/T-3613/ticket.md                           | 212 ++++++-
 tickets/T-3614/ticket.md                           | 111 +++-
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
 tickets/T-3802/ticket.md                           |  17 +-
 tickets/T-3811/ticket.md                           |  16 +-
 tickets/T-3850/ticket.md                           |  17 +-
 tickets/T-3851/ticket.md                           |  26 +
 tickets/T-3856/done-report.md                      | 247 ++++++++
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
 tickets/T-3923/ticket.md                           |  17 +-
 tickets/T-3943/ticket.md                           |  40 +-
 tickets/T-3995/ticket.md                           |   2 +
 tickets/T-4010/ticket.md                           |  17 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4029/ticket.md                           |  16 +-
 tickets/T-4111/ticket.md                           |  20 +-
 tickets/T-4112/ticket.md                           |  33 +-
 tickets/T-4113/ticket.md                           |  33 +-
 tickets/T-4114/ticket.md                           |  10 +-
 tickets/T-4115/ticket.md                           |  10 +-
 tickets/T-4116/ticket.md                           |   2 +-
 tickets/T-4118/ticket.md                           |  30 +-
 tickets/T-4185/ticket.md                           |   7 +-
 tickets/T-4186/ticket.md                           |   7 +-
 tickets/T-4212/ticket.md                           |  16 +-
 tickets/T-4214/done-report.md                      | 667 +++++++++++++++++++++
 tickets/T-4214/ticket.md                           |  46 +-
 tickets/T-4221/ticket.md                           |  80 ++-
 tickets/T-4230/ticket.md                           |  15 +-
 tickets/T-4240/ticket.md                           |   2 +-
 tickets/T-4254/ticket.md                           |  10 +-
 tickets/T-4365/ticket.md                           |   6 +-
 tickets/T-4413/done-report.md                      |  71 +++
 tickets/T-4413/ticket.md                           |  75 ++-
 tickets/T-4414/done-report.md                      |  21 +
 tickets/T-4414/ticket.md                           |  23 +-
 tickets/T-4415/done-report.md                      |  25 +
 tickets/T-4415/ticket.md                           |  24 +-
 tickets/T-4416/ticket.md                           |  56 +-
 tickets/T-4418/ticket.md                           |  17 +-
 tickets/T-4419/ticket.md                           |  17 +-
 tickets/T-4420/ticket.md                           |  17 +-
 tickets/T-4421/ticket.md                           |  17 +-
 tickets/T-4422/ticket.md                           |  17 +-
 tickets/T-4423/ticket.md                           |  17 +-
 tickets/T-4437/ticket.md                           |  17 +-
 tickets/T-4491/done-report.md                      |  23 +
 tickets/T-4491/ticket.md                           |  69 +++
 tickets/T-4492/done-report.md                      |  34 ++
 tickets/T-4492/ticket.md                           |  67 +++
 tickets/T-4493/done-report.md                      |  19 +
 tickets/T-4493/ticket.md                           |  61 ++
 tickets/T-4494/done-report.md                      | 138 +++++
 tickets/T-4494/ticket.md                           |  73 +++
 tickets/T-4495/done-report.md                      | 197 ++++++
 tickets/T-4495/ticket.md                           |  64 ++
 tickets/T-4496/done-report.md                      |  23 +
 tickets/T-4496/ticket.md                           |  56 ++
 tickets/T-4497/ticket.md                           |  31 +
 tickets/T-4498/done-report.md                      | 147 +++++
 tickets/T-4498/ticket.md                           |  55 ++
 tickets/T-4499/ticket.md                           |  49 ++
 tickets/T-4500/ticket.md                           |  41 ++
 tickets/T-4501/done-report.md                      |  24 +
 tickets/T-4501/ticket.md                           |  81 +++
 tickets/T-4502/done-report.md                      |  19 +
 tickets/T-4502/ticket.md                           |  73 +++
 tickets/T-4503/ticket.md                           |  94 +++
 tickets/T-4504/ticket.md                           |  69 +++
 tickets/T-4505/ticket.md                           |  38 ++
 tickets/T-4506/ticket.md                           |  40 ++
 tickets/T-4507/ticket.md                           |  37 ++
 tickets/T-4508/ticket.md                           | 114 ++++
 tickets/T-4509/ticket.md                           |  47 ++
 tickets/T-4510/done-report.md                      | 149 +++++
 tickets/T-4510/ticket.md                           |  81 +++
 tickets/T-4511/done-report.md                      |  97 +++
 tickets/T-4511/ticket.md                           | 103 ++++
 tickets/T-4512/done-report.md                      | 524 ++++++++++++++++
 tickets/T-4512/ticket.md                           | 102 ++++
 tickets/T-4513/ticket.md                           |  36 ++
 tickets/T-4514/done-report.md                      | 179 ++++++
 tickets/T-4514/ticket.md                           |  66 ++
 tickets/T-4515/done-report.md                      |  24 +
 tickets/T-4515/ticket.md                           |  62 ++
 tickets/T-4516/ticket.md                           |  32 +
 tickets/T-4517/done-report.md                      | 180 ++++++
 tickets/T-4517/ticket.md                           |  94 +++
 tickets/T-4518/ticket.md                           |  34 ++
 tickets/T-4519/ticket.md                           |  67 +++
 tickets/T-4520/done-report.md                      | 163 +++++
 tickets/T-4520/ticket.md                           |  58 ++
 tickets/T-4521/done-report.md                      | 228 +++++++
 tickets/T-4521/ticket.md                           | 125 ++++
 tickets/T-4522/done-report.md                      |  99 +++
 tickets/T-4522/ticket.md                           |  49 ++
 tickets/T-4523/done-report.md                      | 104 ++++
 tickets/T-4523/ticket.md                           |  40 ++
 tickets/T-4524/ticket.md                           |  45 ++
 tickets/T-4526/ticket.md                           |  45 ++
 tickets/T-4529/ticket.md                           |  76 +++
 tickets/T-4530/ticket.md                           |  64 ++
 tickets/T-4531/done-report.md                      |  21 +
 tickets/T-4531/ticket.md                           | 110 ++++
 tickets/T-4532/done-report.md                      |  24 +
 tickets/T-4532/ticket.md                           |  66 ++
 tickets/T-4533/ticket.md                           |  35 ++
 tickets/T-4534/ticket.md                           |  69 +++
 tickets/T-4535/done-report.md                      |  64 ++
 tickets/T-4535/ticket.md                           |  61 ++
 tickets/T-4536/done-report.md                      |  78 +++
 tickets/T-4536/ticket.md                           | 128 ++++
 tickets/T-4537/ticket.md                           |  33 +
 tickets/T-4538/ticket.md                           |  60 ++
 tickets/T-4539/ticket.md                           |  29 +
 tickets/T-4540/done-report.md                      | 543 +++++++++++++++++
 tickets/T-4540/ticket.md                           |  55 ++
 tickets/T-4541/ticket.md                           | 112 ++++
 tickets/T-4542/ticket.md                           |  55 ++
 tickets/T-4543/done-report.md                      | 115 ++++
 tickets/T-4543/ticket.md                           |  79 +++
 tickets/T-4546/ticket.md                           |  84 +++
 tickets/T-4547/done-report.md                      | 137 +++++
 tickets/T-4547/ticket.md                           |  45 ++
 tickets/T-4548/done-report.md                      |  59 ++
 tickets/T-4548/ticket.md                           |  50 ++
 tickets/T-4549/ticket.md                           |  53 ++
 tickets/T-4550/done-report.md                      | 545 +++++++++++++++++
 tickets/T-4550/ticket.md                           |  59 ++
 tickets/T-4552/done-report.md                      | 146 +++++
 tickets/T-4552/ticket.md                           | 100 +++
 tickets/T-4553/done-report.md                      | 501 ++++++++++++++++
 tickets/T-4553/ticket.md                           |  55 ++
 tickets/T-4554/done-report.md                      | 541 +++++++++++++++++
 tickets/T-4554/ticket.md                           |  63 ++
 tickets/T-4555/done-report.md                      | 556 +++++++++++++++++
 tickets/T-4555/ticket.md                           |  78 +++
 tickets/T-4556/done-report.md                      | 602 +++++++++++++++++++
 tickets/T-4556/ticket.md                           |  46 ++
 tickets/T-4558/ticket.md                           |  30 +
 tickets/T-4559/ticket.md                           |  54 ++
 tickets/T-4560/ticket.md                           |  41 ++
 tickets/T-4561/ticket.md                           |  38 ++
 tickets/T-4562/ticket.md                           |  35 ++
 tickets/T-4563/done-report.md                      | 556 +++++++++++++++++
 tickets/T-4563/ticket.md                           |  47 ++
 tickets/T-4566/ticket.md                           | 154 +++++
 tickets/T-4567/ticket.md                           |  27 +
 tickets/T-4571/ticket.md                           |  43 ++
 tickets/T-4572/ticket.md                           |  43 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4574/ticket.md                           |  29 +
 tickets/T-4575/ticket.md                           |  38 ++
 tickets/T-4579/done-report.md                      | 522 ++++++++++++++++
 tickets/T-4579/ticket.md                           |  68 +++
 tickets/T-4580/ticket.md                           |  47 ++
 tickets/T-4581/ticket.md                           |  47 ++
 tickets/T-4582/done-report.md                      | 551 +++++++++++++++++
 tickets/T-4582/ticket.md                           |  56 ++
 tickets/T-4583/done-report.md                      | 620 +++++++++++++++++++
 tickets/T-4583/ticket.md                           |  87 +++
 tickets/T-4588/ticket.md                           |  41 ++
 tickets/T-4589/ticket.md                           |  53 ++
 tickets/T-4596/done-report.md                      | 637 ++++++++++++++++++++
 tickets/T-4596/ticket.md                           |  43 ++
 tickets/T-4597/ticket.md                           |  31 +
 tickets/T-4598/ticket.md                           |  29 +
 tickets/T-4599/ticket.md                           |  69 +++
 tickets/T-4600/ticket.md                           |  28 +
 tickets/T-4601/ticket.md                 |  27 +
 tickets/T-4607/ticket.md                 |  81 +++
 tickets/T-4602/ticket.md                 |  41 ++
 tickets/T-4603/ticket.md                 |  30 +
 uv.lock                                            |   2 +-
 496 files changed, 35578 insertions(+), 1793 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_land_lock_root_sets_env_for_the_in_process_gate_call` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_no_land_lock_root_leaves_env_untouched` (pytest node id, verified passing when recorded)
