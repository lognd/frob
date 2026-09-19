## Done report

T-4111: H3-1 GUARD001 -- lockout read/write class-closure gate

WHAT changed
------------
- src/frob/gates/_guard_closure.py (NEW): GUARD001. Bespoke, class-scoped
  BFS closure check over parsed `ast` nodes (never a text scan like
  WIRE001, never routed through frob.graph.callgraph's private-symbol-only
  resolver, per T-4111's own verified investigation that both existing
  substrates structurally cannot see this class of gap). Public API:
  `guard_closure_gate(root)`, `GuardClosurePair`, `load_guard_closure_pairs`.
  Configuration: `[[guard_closure.pairs]]` (`read=`/`write=`) and
  `[guard_closure] route_decorator_markers` in frob.toml, defaulting to
  the one pair (`retry_after_seconds`/`record_failure`) and route-decorator
  set (`route`/`get`/`post`/`put`/`patch`/`delete`/`websocket`) the
  motivating F-307 H3-1 report named -- naming-convention-generic, not
  hardcoded to one consumer.
- tests/gates_suite/test_guard_closure.py (NEW): 8 tests, including the
  three synthetic must-fire/must-stay-quiet/must-fire fixtures the
  ticket's own Fixture note demanded (a real must-fire/must-stay-quiet
  pair cannot be drawn from frob's own tree, which has no route/guard/
  lockout shape -- confirmed, so every fixture here is a small synthetic
  git-tracked package under tmp_path, not wired into frob's runtime).
- docs/modules/gates.md: new "## GUARD001 (T-4111)" row (anchor
  `guard001-t-4111`) documenting the algorithm, config surface, and that
  wiring into `run_gates`'s dispatch table is explicitly left as follow-up
  (src/frob/gates/__init__.py is outside this ticket's declared scope).
- design/frob.strata: added `src/frob/gates/_guard_closure.py` to the
  `gates` node's `fs.read` via-list (it reads `frob.toml` and every `.py`
  file GUARD001 walks).
- docs/design/registry/capability-via-ratchet.lock.json: `gates::fs.read`
  accepted_count 56 -> 58 (two new real sites: `load_guard_closure_pairs`'s
  frob.toml read, `_classes_in_file`'s per-file read), with a T-4111 reason
  entry naming the sites.

WHY
---
F-307 H3-1: a guard that reads a lockout primitive but has no
route-reachable write-primitive caller in its own class is a control that
fires on nothing -- the gap was disguised by a test calling the write
primitive directly instead of through a real caller. WIRE001 only answers
"is this diff-added symbol reached at all" (not this closure question);
DEAD001/build_call_graph only resolve edges to PRIVATE symbols (their own
module docstring's rule), while route handlers and lockout primitives are
routinely public -- both are structurally blind to this class, confirmed
by reading src/frob/gates/_wire.py and src/frob/graph/callgraph.py
directly before implementing (per the ticket's own VERIFIED/REFUTED
instruction). GUARD001 fills that gap with a bespoke per-class closure
check, decided from parsed ast call/decorator nodes.

How each acceptance criterion is proven
----------------------------------------
- must-fire (a), total absence of a write caller:
  test_guard001_fires_when_no_writer_reachable
- must-stay-quiet (b), a real route-reachable caller in the same class:
  test_guard001_quiet_when_writer_reachable_from_same_class_route
- must-fire (c), a write caller that IS route-reachable but only from a
  DIFFERENT class (the class-scoping false-negative shape):
  test_guard001_fires_when_writer_reachable_only_from_a_different_class
- a class with no route entry point at all has no opinion (a different
  gate's job): test_guard001_quiet_when_read_only_reachable_from_class_with_no_route
- config loader defaults / frob.toml override:
  test_load_guard_closure_pairs_defaults_when_unconfigured,
  test_load_guard_closure_pairs_reads_frob_toml
- end-to-end with a non-default pair/marker (proves the closure logic
  itself, not just the loader, is generic):
  test_guard001_honors_configured_pair_and_route_marker
- a tests/ directory caller does not satisfy closure (production
  reachability only): test_guard001_ignores_tests_directory

Test node ids (all bound as evidence, --base-ref dev)
-------------------------------------------------------
tests/gates_suite/test_guard_closure.py::test_guard001_fires_when_no_writer_reachable
tests/gates_suite/test_guard_closure.py::test_guard001_quiet_when_writer_reachable_from_same_class_route
tests/gates_suite/test_guard_closure.py::test_guard001_fires_when_writer_reachable_only_from_a_different_class
tests/gates_suite/test_guard_closure.py::test_guard001_quiet_when_read_only_reachable_from_class_with_no_route
tests/gates_suite/test_guard_closure.py::test_load_guard_closure_pairs_defaults_when_unconfigured
tests/gates_suite/test_guard_closure.py::test_load_guard_closure_pairs_reads_frob_toml
tests/gates_suite/test_guard_closure.py::test_guard001_honors_configured_pair_and_route_marker
tests/gates_suite/test_guard_closure.py::test_guard001_ignores_tests_directory

All 8/8 pass (PYTHONPATH pytest run, exitstatus=0 collected=8 failed=0).
ruff check/format: clean. ty check: clean (0 errors).

Commit shas
-----------
94fcd4627  feat(gates): add GUARD001 lockout-read/write class closure check
a2ea3cb6d  chore(tickets): record evidence for T-4111
8b0982d1a  fix(gates): add missing COV002 frob:doc anchors on GuardClosurePair
74f657ef6  fix(tickets): resync gates fs.read ratchet ceiling for T-4111 land (HEAD)

POST-LAND-REFUSAL FIX (round 2)
--------------------------------
The first land attempt was refused by COV002: `GuardClosurePair` (no
frob:doc/frob:tests at all) and `load_guard_closure_pairs` (frob:tests
present, frob:doc missing) were both public with no doc anchor -- my
original PRE-READY coverage check (`--only coverage --files
src/frob/gates/_guard_closure.py --base dev`) did not catch this before
the first READY, evidently reading clean when it should have flagged
both. Re-ran the EXACT same command after adding both directives
(pointing at the same `docs/modules/gates.md#guard001-t-4111` row this
module already documents under, matching `load_guard_closure_pairs`'s
existing frob:tests bindings and adding new ones for `GuardClosurePair`)
-- confirmed CLEAN this time, zero COV findings attributable to
`_guard_closure.py` in the full `--only coverage` output. ruff check/
format and the 8/8 pytest suite re-verified clean on the new HEAD.
Node ids unchanged (no new tests added), so evidence was NOT re-bound
per the coordinator's instruction.

POST-LAND-REFUSAL FIX (round 3)
--------------------------------
The second land attempt was refused by SELFAUDIT001 SYS111: dev's OWN
gates::fs.read via-list count had moved independently since this
ticket's first ratchet bump (56 -> 58), leaving the committed ceiling
stale relative to the merged tree again -- `git merge dev` reported
"Already up to date" (the automated land process had already fast-
forwarded this worktree's HEAD onto dev), and the ratchet file's
committed `accepted_count` for `gates::fs.read` had reverted to 56 (the
pre-T-4111 value) as a side effect of dev's own intervening lands also
touching this same shared lock file. Re-ran `frob check --only sys
--files src/frob/gates/_guard_closure.py --base dev` against the merged
tree: observed "gates fs.read grew to 57 site(s), above the committed
ceiling of 56". Set `docs/design/registry/capability-via-ratchet.lock.json`'s
`gates::fs.read.accepted_count` to 57 (the live observed count) with a
fresh T-4111 reason explaining the resync. Re-ran the identical --only
sys command again: SELFAUDIT gate family no longer appears in the FAIL
list at all (0 findings attributable, confirmed against the full output).
Left `tickets/T-4605/ticket.md`'s unstaged modification untouched --
unrelated scope-mirror noise from another ticket's renumbering, not part
of this ticket's lease.

Gate checks run (--only, --files, --base dev, per BRIEF)
----------------------------------------------------------
- coverage: no COV002/finding attributable to
  src/frob/gates/_guard_closure.py, tests/gates_suite/test_guard_closure.py,
  or docs/modules/gates.md (repo-wide pre-existing COV007/DRIFT001/DSL/
  TODO findings in unrelated files remain, untouched by this ticket).
- arch: pass, 0 findings against my file (541 repo-wide pattern
  suggestions and 19 pre-existing warnings, none naming _guard_closure.py).
- sys (SELFAUDIT001): FIRST run found 2 real, correctly-attributed
  undeclared fs.read sites at _guard_closure.py:110/186 -- fixed by adding
  the file to design/frob.strata's gates fs.read via-list and bumping
  docs/design/registry/capability-via-ratchet.lock.json's gates::fs.read
  ceiling 56 -> 58. SECOND run: 0 findings naming guard_closure; the one
  remaining SELFAUDIT001 (testsuite fs.write pending-auto-accept, T-4563)
  is pre-existing and unrelated.
- ty check / ruff check / ruff format: clean on both touched files.

Scope
-----
Started scope: src/frob/gates/_guard_closure.py,
tests/gates_suite/test_guard_closure.py. Added via `frob ticket scope
--add` (with --reason each time, per T-3404's one-reason-per-glob rule):
docs/modules/gates.md, design/frob.strata,
docs/design/registry/capability-via-ratchet.lock.json. Scope-closure WARN
noise on design/frob.strata (500+ doc-anchor cross-references) is the
shared-file-is-huge shape this repo already documents elsewhere (WARN
only, not a refusal) -- not acted on, out of this ticket's leaf.

Known follow-up (explicitly NOT done, out of this ticket's declared scope)
----------------------------------------------------------------------------
GUARD001 is NOT yet wired into `run_gates`'s dispatch table in
src/frob/gates/__init__.py -- that file is outside T-4111's lease. Call
`guard_closure_gate(root)` directly today. Noted in docs/modules/gates.md's
new row. Whoever next touches src/frob/gates/__init__.py's dispatch table
(or a fresh ticket) should wire it in; not filing a new ticket for this
since it is a straightforward one-line dispatch addition the coordinator
can fold into any nearby gates/__init__.py-scoped ticket, but flagging it
here per the BRIEF's out-of-scope-discovery instruction.

Filed: none (the only out-of-scope item found -- gates/__init__.py wiring
-- is noted above rather than filed as a fresh ticket, since it is a
trivial one-line addition better folded into the next gates/__init__.py
touch than queued on its own).

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 +++-
 .frob-release.json                                 |   2 +-
 .github/workflows/ci.yml                           | 107 ++-
 CHANGELOG.md                                       |  55 ++
 changelog.d/T-2965.md                              |   2 +
 changelog.d/T-3020.md                              |   2 +
 changelog.d/T-3232.md                              |   2 +
 changelog.d/T-3233.md                              |   2 +
 changelog.d/T-3612.md                              |   2 +
 changelog.d/T-3613.md                              |   2 +
 changelog.d/T-3615.md                              |   2 +
 changelog.d/T-3856.md                              |   2 +
 changelog.d/T-3943.md                              |   2 +
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
 changelog.d/T-4503.md                              |   2 +
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
 changelog.d/T-4596.md                              |   2 +
 changelog.d/T-4607.md                              |   2 +
 design/frob.strata                                 | 135 ++--
 docs/commands/check.md                             |  15 +
 docs/commands/narrative.md                         |   8 +
 docs/commands/scaffold.md                          |  50 +-
 docs/commands/ticket.md                            |  72 ++
 docs/commands/xref.md                              |  16 +-
 docs/design/cli-regrouping.md                      |  73 ++
 .../registry/capability-via-ratchet.lock.json      |  75 +-
 docs/design/registry/check-coverage.yaml           |   7 +-
 docs/guides/install.md                             |  40 +
 docs/guides/release.md                             |  37 +
 docs/modules/app.md                                |  20 +
 docs/modules/dup.md                                |  12 +
 docs/modules/gates.md                              |  45 +-
 docs/modules/graph.md                              |  39 +
 docs/modules/lang.md                               |  33 +
 docs/modules/testing.md                            |  16 +
 docs/modules/tickets-data-storage.md               |   8 +
 docs/modules/tickets-landing.md                    | 188 ++++-
 docs/modules/tickets.md                            |   9 +-
 docs/strata/surface.md                             |  40 +
 frob.lock                                          |  42 +-
 pyproject.toml                                     |  22 +-
 src/frob/__init__.py                               |   2 +
 src/frob/__main__.py                               |  26 +-
 src/frob/_cli_parsers/_check.py                    |  16 +
 src/frob/_cli_parsers/_core.py                     |  33 +-
 src/frob/_cli_parsers/_design.py                   |  24 +-
 src/frob/_cli_parsers/_explore.py                  | 102 ++-
 src/frob/_cli_parsers/_misc.py                     |  56 +-
 src/frob/_cli_parsers/_ops.py                      |  38 +-
 src/frob/_cli_parsers/_root.py                     |  20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |  55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |  21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |  53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         | 144 +++-
 src/frob/app/_config_external.py                   |  19 +
 src/frob/app/check_runner.py                       |  51 +-
 src/frob/app/config.py                             |  92 ++-
 src/frob/app/ticket_runner/__init__.py             | 125 ++--
 src/frob/app/ticket_runner/_close_cmd.py           |  10 +-
 src/frob/app/ticket_runner/_land_cmd.py            | 532 +++++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  79 +-
 src/frob/app/ticket_runner/_mutate.py              |  39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         | 664 ++++++++++++++++-
 src/frob/app/ticket_runner/_verify.py              | 245 ++++++-
 src/frob/check/__init__.py                         | 244 ++++---
 src/frob/check/_python.py                          | 152 ++--
 src/frob/docs/__init__.py                          |  64 +-
 src/frob/doctor.py                                 | 227 +++++-
 src/frob/dup/_legacy.py                            |  60 +-
 src/frob/dup/_legacy_cs.py                         | 207 ++++++
 src/frob/excludes.py                               |  83 ++-
 src/frob/gates/__init__.py                         | 263 ++++---
 src/frob/gates/_fix_engine_sync.py                 |  69 +-
 src/frob/gates/_guard_closure.py                   | 301 ++++++++
 src/frob/gates/_lang_conformance.py                |  36 +-
 src/frob/gates/_models.py                          |   7 +
 src/frob/gates/_narrative_blocks.py                |  28 +-
 src/frob/gates/_suppress.py                        |  46 +-
 src/frob/gates/_waive.py                           | 170 ++++-
 src/frob/graph/affects.py                          |  53 ++
 src/frob/graph/dsl.py                              | 101 ++-
 src/frob/lang/__init__.py                          |  17 +-
 src/frob/lang/_extract.py                          |  13 +
 src/frob/lang/_project_detect.py                   | 147 ++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 ++-
 src/frob/scaffold/_unity_project.py                | 193 +++++
 .../scaffold/data/types/unity-project/frob.toml.j2 |  64 ++
 src/frob/scaffold/project.py                       |   6 +-
 src/frob/strata/_effects.py                        | 494 +++++++++++--
 src/frob/strata/_unity_asmdef.py                   | 412 +++++++++++
 src/frob/testing/__init__.py                       |   9 +
 src/frob/testing/_collect.py                       |  21 +-
 src/frob/testing/_collect_csharp.py                | 327 +++++++++
 src/frob/testing/_stackdump.py                     |  68 +-
 src/frob/tickets/__init__.py                       |   2 +
 src/frob/tickets/_land.py                          | 122 +++-
 src/frob/tickets/_land_git_ops.py                  | 149 +++-
 src/frob/tickets/_land_queue.py                    | 151 +++-
 src/frob/tickets/_land_squash.py                   |  48 +-
 src/frob/tickets/_leases.py                        | 552 ++++++++++----
 src/frob/tickets/_models.py                        |  42 +-
 src/frob/tickets/_setters.py                       | 113 ++-
 src/frob/tickets/_store.py                         |  42 +-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 ++++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 ++++++
 src/frob/vet/_capability_registry/_matrix.py       |  13 +-
 src/frob/vet/_capability_registry/_unity_api.py    | 305 ++++++++
 src/frob/vet/_capability_scan.py                   |  13 +-
 src/frob/xref/__init__.py                          |  54 +-
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
 tests/gates_suite/test_fix_engine.py               |  63 ++
 tests/gates_suite/test_guard_closure.py            | 228 ++++++
 tests/test_check_gate_base.py                      |  54 ++
 tests/test_excludes.py                             |  75 ++
 tests/test_gates_suppress.py                       |  34 +-
 tests/test_hook_frob_suggest.py                    |  47 ++
 tests/test_hook_frob_timeout_guard.py              |  54 ++
 tests/test_hook_root_write_guard.py                |  89 +++
 tests/test_lang.py                                 |  90 +++
 tests/test_lang_conformance_gate.py                |  81 ++-
 tests/test_narrative_blocks.py                     |  27 +
 tests/test_testing.py                              | 106 ++-
 tests/test_ticket_leases.py                        | 313 +++++---
 tests/test_ticket_work_and_land_finish.py          | 206 +++---
 tests/test_tickets_migration.py                    | 121 ++--
 tests/test_tickets_parent.py                       | 208 ++++++
 tests/test_waive_gate.py                           | 145 ++++
 tests/unit/graph/test_dsl.py                       | 164 ++++-
 tests/unit/rapid_sweep_suite/test_dispose.py       |  39 +
 tests/unit/rapid_sweep_suite/test_filing.py        |  33 +
 tests/unit/rapid_sweep_suite/test_window.py        | 457 ++++++++++++
 tests/unit/strata/test_effects.py                  |  44 ++
 tests/unit/strata/test_selfconform.py              | 263 ++++++-
 tests/unit/strata/test_unity_asmdef.py             | 160 ++++
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |  57 ++
 tests/unit/test_app_runners_batch7.py              | 128 ++--
 tests/unit/test_check_scoped_files.py              | 566 +++++++++++++++
 tests/unit/test_ci_self_gate_unscoped.py           | 189 +++++
 tests/unit/test_cli_group_parity.py                | 220 ++++++
 tests/unit/test_cli_lang_choices_drift.py          | 113 +++
 tests/unit/test_cli_single_child_groups.py         | 106 +++
 tests/unit/test_dev_branch_workflow.py             |  50 ++
 tests/unit/test_docs_module.py                     |  35 +-
 tests/unit/test_doctor.py                          | 115 +++
 tests/unit/test_done_report_check_scope.py         | 177 +++++
 tests/unit/test_land_default_queue.py              | 128 ++++
 tests/unit/test_land_in_progress_window.py         | 351 +++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 +++
 tests/unit/test_land_merge_conflict_drop.py        | 198 +++++
 tests/unit/test_land_queue.py                      | 114 +++
 tests/unit/test_land_stackdump.py                  | 321 ++++++++
 tests/unit/test_lang_project_detect.py             | 108 +++
 tests/unit/test_leases_staleness_perf.py           | 310 ++++++++
 tests/unit/test_lifecycle_work_base.py             | 217 ++++++
 tests/unit/test_rel002_dev_suffix.py               | 113 +++
 tests/unit/test_scaffold_unity_project.py          | 128 ++++
 tests/unit/test_support_csharp.py                  | 190 +++++
 tests/unit/test_suppress_worktree_path.py          |  87 +++
 tests/unit/test_ticket_cli_surface.py              | 182 +++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_xref.py                            |  40 +
 tests/vet_suite/test_capability_registry_unity.py  | 130 ++++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 +++
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
 tickets/T-3020/done-report.md                      | 578 +++++++++++++++
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
 tickets/T-3232/done-report.md                      | 179 +++++
 tickets/T-3232/ticket.md                           |  88 ++-
 tickets/T-3233/done-report.md                      | 606 ++++++++++++++++
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
 tickets/T-3412/ticket.md                           |  34 +-
 tickets/T-3415/ticket.md                           |  17 +-
 tickets/T-3459/ticket.md                           |  17 +-
 tickets/T-3504/ticket.md                           |  17 +-
 tickets/T-3505/ticket.md                           |  16 +-
 tickets/T-3513/ticket.md                           |  17 +-
 tickets/T-3559/ticket.md                           |  17 +-
 tickets/T-3564/ticket.md                           |  17 +-
 tickets/T-3602/ticket.md                           |  16 +-
 tickets/T-3612/done-report.md                      | 221 ++++++
 tickets/T-3612/ticket.md                           | 156 +++-
 tickets/T-3613/done-report.md                      | 106 +++
 tickets/T-3613/ticket.md                           | 212 +++++-
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
 tickets/T-3802/ticket.md                           |  17 +-
 tickets/T-3811/ticket.md                           |  16 +-
 tickets/T-3850/ticket.md                           |  17 +-
 tickets/T-3851/ticket.md                           |  26 +
 tickets/T-3856/done-report.md                      | 247 +++++++
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
 tickets/T-3943/done-report.md                      | 626 ++++++++++++++++
 tickets/T-3943/ticket.md                           |  49 +-
 tickets/T-3961/ticket.md                           |  23 +-
 tickets/T-3962/ticket.md                           |  21 +-
 tickets/T-3986/ticket.md                           |   2 +-
 tickets/T-3995/ticket.md                           |  19 +-
 tickets/T-4010/ticket.md                           |  17 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4029/ticket.md                           |  16 +-
 tickets/T-4035/ticket.md                           |   2 +
 tickets/T-4073/ticket.md                           |  12 +-
 tickets/T-4111/done-report.md                      | 695 ++++++++++++++++++
 tickets/T-4111/ticket.md                           |  29 +-
 tickets/T-4112/ticket.md                           |  33 +-
 tickets/T-4113/ticket.md                           |  33 +-
 tickets/T-4114/ticket.md                           |  10 +-
 tickets/T-4115/ticket.md                           |  10 +-
 tickets/T-4116/ticket.md                           |   2 +-
 tickets/T-4118/ticket.md                           |  30 +-
 tickets/T-4185/ticket.md                           |   7 +-
 tickets/T-4186/ticket.md                           |   7 +-
 tickets/T-4212/ticket.md                           |  16 +-
 tickets/T-4214/done-report.md                      | 667 +++++++++++++++++
 tickets/T-4214/ticket.md                           |  46 +-
 tickets/T-4221/ticket.md                           |  80 +-
 tickets/T-4230/ticket.md                           |  15 +-
 tickets/T-4240/ticket.md                           |   2 +-
 tickets/T-4254/ticket.md                           |  10 +-
 tickets/T-4365/ticket.md                           |   6 +-
 tickets/T-4413/done-report.md                      |  71 ++
 tickets/T-4413/ticket.md                           |  75 +-
 tickets/T-4414/done-report.md                      |  21 +
 tickets/T-4414/ticket.md                           |  23 +-
 tickets/T-4415/done-report.md                      |  25 +
 tickets/T-4415/ticket.md                           |  24 +-
 tickets/T-4416/ticket.md                           |  56 +-
 tickets/T-4418/ticket.md                           |  17 +-
 tickets/T-4419/ticket.md                           |  17 +-
 tickets/T-4420/ticket.md                           |  17 +-
 tickets/T-4421/ticket.md                           | 464 +++++++++++-
 tickets/T-4422/ticket.md                           |  17 +-
 tickets/T-4423/ticket.md                           |  17 +-
 tickets/T-4437/ticket.md                           |  17 +-
 tickets/T-4491/done-report.md                      |  23 +
 tickets/T-4491/ticket.md                           |  69 ++
 tickets/T-4492/done-report.md                      |  34 +
 tickets/T-4492/ticket.md                           |  67 ++
 tickets/T-4493/done-report.md                      |  19 +
 tickets/T-4493/ticket.md                           |  61 ++
 tickets/T-4494/done-report.md                      | 138 ++++
 tickets/T-4494/ticket.md                           |  73 ++
 tickets/T-4495/done-report.md                      | 197 +++++
 tickets/T-4495/ticket.md                           |  64 ++
 tickets/T-4496/done-report.md                      |  23 +
 tickets/T-4496/ticket.md                           |  56 ++
 tickets/T-4497/ticket.md                           |  31 +
 tickets/T-4498/done-report.md                      | 147 ++++
 tickets/T-4498/ticket.md                           |  55 ++
 tickets/T-4499/ticket.md                           |  49 ++
 tickets/T-4500/ticket.md                           |  41 ++
 tickets/T-4501/done-report.md                      |  24 +
 tickets/T-4501/ticket.md                           |  81 +++
 tickets/T-4502/done-report.md                      |  19 +
 tickets/T-4502/ticket.md                           |  73 ++
 tickets/T-4503/done-report.md                      | 592 +++++++++++++++
 tickets/T-4503/ticket.md                           |  94 +++
 tickets/T-4504/ticket.md                           |  69 ++
 tickets/T-4505/ticket.md                           |  38 +
 tickets/T-4506/ticket.md                           |  40 +
 tickets/T-4507/ticket.md                           |  37 +
 tickets/T-4508/ticket.md                           | 114 +++
 tickets/T-4509/ticket.md                           |  47 ++
 tickets/T-4510/done-report.md                      | 149 ++++
 tickets/T-4510/ticket.md                           |  81 +++
 tickets/T-4511/done-report.md                      |  97 +++
 tickets/T-4511/ticket.md                           | 103 +++
 tickets/T-4512/done-report.md                      | 524 ++++++++++++++
 tickets/T-4512/ticket.md                           | 102 +++
 tickets/T-4513/ticket.md                           |  36 +
 tickets/T-4514/done-report.md                      | 179 +++++
 tickets/T-4514/ticket.md                           |  66 ++
 tickets/T-4515/done-report.md                      |  24 +
 tickets/T-4515/ticket.md                           |  62 ++
 tickets/T-4516/ticket.md                           |  32 +
 tickets/T-4517/done-report.md                      | 180 +++++
 tickets/T-4517/ticket.md                           |  94 +++
 tickets/T-4518/ticket.md                           |  34 +
 tickets/T-4519/ticket.md                           |  67 ++
 tickets/T-4520/done-report.md                      | 163 +++++
 tickets/T-4520/ticket.md                           |  58 ++
 tickets/T-4521/done-report.md                      | 228 ++++++
 tickets/T-4521/ticket.md                           | 125 ++++
 tickets/T-4522/done-report.md                      |  99 +++
 tickets/T-4522/ticket.md                           |  49 ++
 tickets/T-4523/done-report.md                      | 104 +++
 tickets/T-4523/ticket.md                           |  40 +
 tickets/T-4524/ticket.md                           |  45 ++
 tickets/T-4526/ticket.md                           |  45 ++
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
 tickets/T-4536/ticket.md                           | 128 ++++
 tickets/T-4537/ticket.md                           |  33 +
 tickets/T-4538/ticket.md                           |  60 ++
 tickets/T-4539/ticket.md                           |  29 +
 tickets/T-4540/done-report.md                      | 543 ++++++++++++++
 tickets/T-4540/ticket.md                           |  55 ++
 tickets/T-4541/ticket.md                           | 112 +++
 tickets/T-4542/ticket.md                           |  55 ++
 tickets/T-4543/done-report.md                      | 115 +++
 tickets/T-4543/ticket.md                           |  79 ++
 tickets/T-4546/ticket.md                           |  84 +++
 tickets/T-4547/done-report.md                      | 137 ++++
 tickets/T-4547/ticket.md                           |  45 ++
 tickets/T-4548/done-report.md                      |  59 ++
 tickets/T-4548/ticket.md                           |  50 ++
 tickets/T-4549/ticket.md                           |  53 ++
 tickets/T-4550/done-report.md                      | 545 ++++++++++++++
 tickets/T-4550/ticket.md                           |  59 ++
 tickets/T-4552/done-report.md                      | 146 ++++
 tickets/T-4552/ticket.md                           | 100 +++
 tickets/T-4553/done-report.md                      | 501 +++++++++++++
 tickets/T-4553/ticket.md                           |  55 ++
 tickets/T-4554/done-report.md                      | 541 ++++++++++++++
 tickets/T-4554/ticket.md                           |  63 ++
 tickets/T-4555/done-report.md                      | 556 ++++++++++++++
 tickets/T-4555/ticket.md                           |  78 ++
 tickets/T-4556/done-report.md                      | 602 +++++++++++++++
 tickets/T-4556/ticket.md                           |  46 ++
 tickets/T-4558/ticket.md                           |  30 +
 tickets/T-4559/ticket.md                           |  54 ++
 tickets/T-4560/ticket.md                           |  41 ++
 tickets/T-4561/ticket.md                           |  38 +
 tickets/T-4562/ticket.md                           |  35 +
 tickets/T-4563/done-report.md                      | 556 ++++++++++++++
 tickets/T-4563/ticket.md                           |  47 ++
 tickets/T-4566/ticket.md                           | 154 ++++
 tickets/T-4567/ticket.md                           |  27 +
 tickets/T-4571/ticket.md                           |  43 ++
 tickets/T-4572/ticket.md                           |  43 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4574/ticket.md                           |  29 +
 tickets/T-4575/ticket.md                           |  38 +
 tickets/T-4578/ticket.md                           |  32 +
 tickets/T-4579/done-report.md                      | 522 ++++++++++++++
 tickets/T-4579/ticket.md                           |  68 ++
 tickets/T-4580/ticket.md                           |  47 ++
 tickets/T-4581/ticket.md                           |  47 ++
 tickets/T-4582/done-report.md                      | 551 ++++++++++++++
 tickets/T-4582/ticket.md                           |  56 ++
 tickets/T-4583/done-report.md                      | 620 ++++++++++++++++
 tickets/T-4583/ticket.md                           |  87 +++
 tickets/T-4588/ticket.md                           |  41 ++
 tickets/T-4589/ticket.md                           |  53 ++
 tickets/T-4596/done-report.md                      | 640 ++++++++++++++++
 tickets/T-4596/ticket.md                           |  43 ++
 tickets/T-4597/ticket.md                           |  34 +
 tickets/T-4598/ticket.md                           |  29 +
 tickets/T-4599/ticket.md                           |  69 ++
 tickets/T-4600/ticket.md                           |  28 +
 tickets/T-4601/ticket.md                           |  27 +
 tickets/T-4602/ticket.md                           |  44 ++
 tickets/T-4603/ticket.md                           |  30 +
 tickets/T-4605/ticket.md                           |  72 ++
 tickets/T-4606/ticket.md                           |  27 +
 tickets/T-4607/done-report.md                      | 803 +++++++++++++++++++++
 tickets/T-4607/ticket.md                           |  81 +++
 tickets/T-4608/ticket.md                           |  41 ++
 tickets/T-4609/ticket.md                           |  27 +
 tickets/T-4610/ticket.md                           |  28 +
 tickets/T-4611/ticket.md                           |  28 +
 tickets/T-4612/ticket.md                           |  69 ++
 tickets/T-4622/ticket.md                 | 105 +++
 tickets/T-4633/ticket.md                 |  69 ++
 tickets/T-4623/ticket.md                 |  64 ++
 tickets/T-4624/ticket.md                 |  52 ++
 tickets/T-4625/ticket.md                 |  43 ++
 tickets/T-4626/ticket.md                 |  27 +
 tickets/T-4627/ticket.md                 |  52 ++
 uv.lock                                            |   2 +-
 536 files changed, 40997 insertions(+), 1832 deletions(-)
```

### Evidence
- `tests/gates_suite/test_guard_closure.py::test_guard001_fires_when_no_writer_reachable` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_guard_closure.py::test_guard001_quiet_when_writer_reachable_from_same_class_route` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_guard_closure.py::test_guard001_fires_when_writer_reachable_only_from_a_different_class` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_guard_closure.py::test_guard001_quiet_when_read_only_reachable_from_class_with_no_route` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_guard_closure.py::test_load_guard_closure_pairs_defaults_when_unconfigured` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_guard_closure.py::test_load_guard_closure_pairs_reads_frob_toml` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_guard_closure.py::test_guard001_honors_configured_pair_and_route_marker` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_guard_closure.py::test_guard001_ignores_tests_directory` (pytest node id, verified passing when recorded)
