## Done report

T-4554: T-4536 regression -- TestExtendedKindsDriftLock fails
(_PATTERNS/_KIND_MAP/_EXTENDED_KINDS drift from the C# resolver)

WHAT changed (worktree /home/logan/projects/frob/.claude/worktrees/t-4554,
branch t-4554, HEAD 16cdad545b4493349489c9db4357579d57c5abf0):

1. tests/unit/strata/test_effects.py
   Added TestNoRetiredBareKindEmitted::test_no_registry_entry_emits_a_retired_bare_kind,
   a regression guard asserting no capability-registry entry (across all
   registered languages, including C#) emits the retired bare `net`
   capability_kind -- the class of bug T-4536 introduced.

2. src/frob/vet/_capability_registry/_unity_api.py
   T-4514's Unity entries for UnityWebRequest, WWW, NetworkManager, and
   Application.OpenURL used the bare retired capability_kind=net.
   Recategorized all four to net-connect (the live, non-retired kind),
   consistent with every other entry in the registry. No resolver
   behaviour change -- purely a capability_kind classification fix on
   these four entries.

3. tests/vet_suite/test_capability_registry_unity.py
   Updated the 4 existing assertions that asserted kind==net for these
   same entries to kind==net-connect, matching the corrected
   classification. Same test coverage, same entries, no rename/delete.

4. src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py
   Scope was granted for this file (per the ticket's original repro
   trace) but no additional bash/csharp dangerous-ops entries needed a
   kind fix beyond the Unity API entries above; left unmodified beyond
   what the C# resolver work already carried on dev.

WHY: T-4536 (the C# capability resolver) added _PATTERNS entries whose
resolved kinds overlapped _EXTENDED_KINDS/_KIND_MAP, and T-4514's Unity
API entries specifically used the bare, retired "net" capability_kind
that _EXTENDED_KINDS/_KIND_MAP's disjointness invariant forbids. Fixing
the registry data (not the drift lock or the resolver itself) closes the
gap with no behaviour change to the resolver, per the ticket's own
constraint.

Acceptance criterion (from `frob ticket show T-4554`):
  GIVEN dev WHEN tests/unit/strata/test_effects.py runs THEN
  TestExtendedKindsDriftLock passes
  Bound evidence:
    - tests/unit/strata/test_effects.py::TestNoRetiredBareKindEmitted::test_no_registry_entry_emits_a_retired_bare_kind
    - tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
  (TestExtendedKindsDriftLock itself lives in test_selfconform.py, not
  test_effects.py, on current dev -- test_effects.py carries the
  designated repro test plus the cross-reference comment pointing at the
  drift-lock class; both node ids are the ticket's own bound evidence.)

PROOF -- both node ids pass after merging dev into this worktree:

  $ PYTHONPATH=$(pwd)/src /home/logan/projects/frob/.venv/bin/python -m pytest \
      tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map \
      tests/unit/strata/test_effects.py::TestNoRetiredBareKindEmitted::test_no_registry_entry_emits_a_retired_bare_kind \
      tests/vet_suite/test_capability_registry_unity.py \
      -p no:cacheprovider -q
  ................                                                         [100%]
  SUITE-RESULT: exitstatus=0 collected=16 failed=0

Merge: dev merged clean into t-4554 (merge commit 16cdad545, no conflicts
requiring dev-side resolution) -- HEAD now carries dev through
"3a913ade3 chore(tickets): mirror accept T-4508 from worktree".

Gates: `frob check --only gates --ticket T-4554 --files
src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py --files
tests/unit/strata/test_effects.py --files
src/frob/vet/_capability_registry/_unity_api.py --files
tests/vet_suite/test_capability_registry_unity.py --base dev`, run from
inside the worktree with the venv binary. `frob ticket sweep T-4554` was
re-run first (pre-work sweep was stale against the post-merge scope);
gate:PRE and gate:SCOPE both report 0 errors afterward. Per the tool's
own scope-note, only gate:SCOPE/gate:PREWORK and the diff-driven COV002/
TODO001/FMT/AFFECT checks are ticket-scoped -- every other gate family's
counts are repo-wide, not filtered to this diff. Grepping the full gate
output for our 4 touched files specifically:
  - No DOC/DSL/LANG/PERF/REF/CROSSTICKET/ARCH/DRIFT/TODO/WIRE finding
    names any of the 4 touched files.
  - COV006 (call-graph reachability, best-effort, informational) fires
    on the updated test_capability_registry_unity.py assertions against
    _UNITY_OPERATIONS, a module-level dict never "called" -- the same
    known false-positive shape this repo already waives elsewhere for
    module-constant assertions (T-0536 precedent); no COV001 (missing
    doc) fires because no new public symbol was added.
  - DOCARCH001 warnings on two pre-existing test_effects.py docstrings
    (TestDeployServeMutateNodeSplitConformance, TestStaleViaSymbol) and
    NARR001 on a pre-existing comment block are untouched by this diff
    and gate:DOCARCH/gate:NARR both report 0 errors overall.
  - The repo-wide FAIL gates (ARCH, COV, CROSSTICKET, DOC, DRIFT, DSL,
    LANG, PERF, TICK, TODO, WIRE) all locate their errors in files this
    ticket never touched (e.g. src/frob/dup/_legacy_cs.py's WIRE002,
    src/frob/tickets/_leases.py's COV001) -- pre-existing repo state,
    not introduced by this change.

Evidence: already bound in tickets/T-4554/ticket.md (recorded by the
prior agent before the session died) --
  tests/unit/strata/test_effects.py::TestNoRetiredBareKindEmitted::test_no_registry_entry_emits_a_retired_bare_kind
  tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
Both re-verified passing after the dev merge above; no re-recording
needed.

Commits (t-4554, in order):
  fb01fbc74 chore(tickets): scope T-4554
  6461f2b7f chore(tickets): record T-4554 start transition
  9728085b4 chore(tickets): scope T-4554
  5a4b370d7 chore(tickets): scope T-4554
  5068af8a8 test(vet): add regression guard for retired bare capability kinds
  07ccdd7a6 fix(vet): recategorize Unity net entries from retired bare net to net-connect
  9c67a02fb chore(tickets): record evidence for T-4554
  15e02ef6f chore(tickets): record evidence for T-4554
  fb1943c47 chore(tickets): record evidence for T-4554
  16cdad545 Merge branch 'dev' into t-4554  <- HEAD

Filed: none (no out-of-scope work discovered).

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 +++--
 .frob-release.json                                 |   2 +-
 .github/workflows/ci.yml                           | 107 +++-
 CHANGELOG.md                                       |  37 ++
 changelog.d/T-2965.md                              |   2 +
 changelog.d/T-3232.md                              |   2 +
 changelog.d/T-3612.md                              |   2 +
 changelog.d/T-3613.md                              |   2 +
 changelog.d/T-3615.md                              |   2 +
 changelog.d/T-3856.md                              |   2 +
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
 changelog.d/T-4543.md                              |   2 +
 changelog.d/T-4547.md                              |   2 +
 changelog.d/T-4548.md                              |   2 +
 changelog.d/T-4550.md                              |   2 +
 changelog.d/T-4552.md                              |   2 +
 changelog.d/T-4553.md                              |   2 +
 changelog.d/T-4555.md                              |   2 +
 design/frob.strata                                 | 116 +++--
 docs/commands/check.md                             |  15 +
 docs/commands/scaffold.md                          |  15 +
 docs/commands/ticket.md                            |  72 +++
 docs/commands/xref.md                              |   4 +-
 docs/design/cli-regrouping.md                      |  73 +++
 .../registry/capability-via-ratchet.lock.json      |  52 +-
 docs/guides/install.md                             |  40 ++
 docs/guides/release.md                             |  37 ++
 docs/modules/app.md                                |  20 +
 docs/modules/dup.md                                |  12 +
 docs/modules/graph.md                              |  39 ++
 docs/modules/lang.md                               |  33 ++
 docs/modules/testing.md                            |  16 +
 docs/modules/tickets-data-storage.md               |   8 +
 docs/modules/tickets-landing.md                    | 188 ++++++-
 docs/modules/tickets.md                            |   9 +-
 frob.lock                                          |  20 +-
 pyproject.toml                                     |  22 +-
 src/frob/__main__.py                               |  16 +-
 src/frob/_cli_parsers/_check.py                    |  16 +
 src/frob/_cli_parsers/_design.py                   |  24 +-
 src/frob/_cli_parsers/_explore.py                  | 102 ++--
 src/frob/_cli_parsers/_misc.py                     |  56 +-
 src/frob/_cli_parsers/_ops.py                      |  38 +-
 src/frob/_cli_parsers/_root.py                     |  20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |  55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |  21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |  53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         | 144 ++++--
 src/frob/app/_config_external.py                   |  19 +
 src/frob/app/check_runner.py                       |  23 +-
 src/frob/app/config.py                             |  92 +++-
 src/frob/app/ticket_runner/__init__.py             |  88 ++--
 src/frob/app/ticket_runner/_land_cmd.py            | 480 ++++++++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  79 ++-
 src/frob/app/ticket_runner/_mutate.py              |  39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         | 568 ++++++++++++++++++++-
 src/frob/app/ticket_runner/_verify.py              | 235 +++++++--
 src/frob/check/__init__.py                         | 244 +++++----
 src/frob/check/_python.py                          | 136 +++--
 src/frob/docs/__init__.py                          |  64 ++-
 src/frob/doctor.py                                 | 227 +++++++-
 src/frob/dup/_legacy.py                            |  60 ++-
 src/frob/dup/_legacy_cs.py                         | 207 ++++++++
 src/frob/excludes.py                               |  83 ++-
 src/frob/gates/__init__.py                         | 213 ++++----
 src/frob/gates/_models.py                          |   7 +
 src/frob/gates/_suppress.py                        |  46 +-
 src/frob/graph/affects.py                          |  53 ++
 src/frob/graph/dsl.py                              |  69 ++-
 src/frob/lang/_extract.py                          |  13 +
 src/frob/lang/_project_detect.py                   | 147 ++++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 +++-
 src/frob/strata/_effects.py                        | 306 +++++++++--
 src/frob/testing/__init__.py                       |   2 +
 src/frob/testing/_collect.py                       |  21 +-
 src/frob/testing/_collect_csharp.py                | 327 ++++++++++++
 src/frob/testing/_stackdump.py                     |  68 ++-
 src/frob/tickets/__init__.py                       |   2 +
 src/frob/tickets/_land.py                          | 122 ++++-
 src/frob/tickets/_land_git_ops.py                  | 149 ++++--
 src/frob/tickets/_land_queue.py                    | 151 +++++-
 src/frob/tickets/_leases.py                        | 518 +++++++++++++------
 src/frob/tickets/_models.py                        |  42 +-
 src/frob/tickets/_setters.py                       | 113 ++--
 src/frob/tickets/_store.py                         |  42 +-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 +++++++++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 ++++++++
 src/frob/vet/_capability_registry/_matrix.py       |  13 +-
 src/frob/vet/_capability_registry/_unity_api.py    | 305 +++++++++++
 src/frob/vet/_capability_scan.py                   |  13 +-
 src/frob/xref/__init__.py                          |  54 +-
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |  37 ++
 tests/fixtures/csharp_dup_docblock/guide.md        |  36 ++
 .../python_control/duplicate.py                    |  29 ++
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
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |  30 ++
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |  15 +
 tests/fixtures/lang/csharp/unity/coroutine.cs      |  20 +
 .../lang/csharp/unity/lifecycle_methods.cs         |  21 +
 tests/fixtures/lang/csharp/unity/menu_item.cs      |  18 +
 tests/fixtures/lang/csharp/var_local_httpclient.cs |  12 +
 tests/test_excludes.py                             |  75 +++
 tests/test_gates_suppress.py                       |  34 +-
 tests/test_hook_frob_suggest.py                    |  47 ++
 tests/test_hook_frob_timeout_guard.py              |  54 ++
 tests/test_hook_root_write_guard.py                |  89 ++++
 tests/test_lang.py                                 |  90 ++++
 tests/test_testing.py                              | 106 +++-
 tests/test_ticket_leases.py                        | 313 ++++++++----
 tests/test_tickets_migration.py                    | 121 +++--
 tests/test_tickets_parent.py                       | 208 ++++++++
 tests/unit/graph/test_dsl.py                       | 164 +++++-
 tests/unit/rapid_sweep_suite/test_window.py        | 457 +++++++++++++++++
 tests/unit/strata/test_effects.py                  |  44 ++
 tests/unit/strata/test_selfconform.py              | 154 +++++-
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |  57 +++
 tests/unit/test_app_runners_batch7.py              | 128 +++--
 tests/unit/test_check_scoped_files.py              | 566 ++++++++++++++++++++
 tests/unit/test_ci_self_gate_unscoped.py           | 189 +++++++
 tests/unit/test_cli_group_parity.py                | 220 ++++++++
 tests/unit/test_cli_single_child_groups.py         | 106 ++++
 tests/unit/test_dev_branch_workflow.py             |  50 ++
 tests/unit/test_docs_module.py                     |  35 +-
 tests/unit/test_doctor.py                          | 115 +++++
 tests/unit/test_done_report_check_scope.py         | 177 +++++++
 tests/unit/test_land_default_queue.py              | 128 +++++
 tests/unit/test_land_in_progress_window.py         | 227 ++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 ++++
 tests/unit/test_land_merge_conflict_drop.py        | 198 +++++++
 tests/unit/test_land_queue.py                      | 114 +++++
 tests/unit/test_land_stackdump.py                  | 321 ++++++++++++
 tests/unit/test_lang_project_detect.py             | 108 ++++
 tests/unit/test_leases_staleness_perf.py           | 310 +++++++++++
 tests/unit/test_lifecycle_work_base.py             | 217 ++++++++
 tests/unit/test_support_csharp.py                  | 190 +++++++
 tests/unit/test_suppress_worktree_path.py          |  87 ++++
 tests/unit/test_ticket_cli_surface.py              | 182 +++++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_xref.py                            |  40 ++
 tests/vet_suite/test_capability_registry_unity.py  | 130 +++++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 +++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py | 119 +++++
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
 tickets/T-2965/done-report.md                      | 149 ++++++
 tickets/T-2965/ticket.md                           |  41 +-
 tickets/T-2994/ticket.md                           |  16 +-
 tickets/T-3020/ticket.md                           |  41 +-
 tickets/T-3022/ticket.md                           |  16 +-
 tickets/T-3032/ticket.md                           |  17 +-
 tickets/T-3053/ticket.md                           |  16 +-
 tickets/T-3063/ticket.md                           |  17 +-
 tickets/T-3067/ticket.md                           |  17 +-
 tickets/T-3082/ticket.md                           |  51 +-
 tickets/T-3083/ticket.md                           |  17 +-
 tickets/T-3102/ticket.md                           |  17 +-
 tickets/T-3127/ticket.md                           |  17 +-
 tickets/T-3193/ticket.md                           |  17 +-
 tickets/T-3213/ticket.md                           |  17 +-
 tickets/T-3221/ticket.md                           |  17 +-
 tickets/T-3229/ticket.md                           |  17 +-
 tickets/T-3232/done-report.md                      | 179 +++++++
 tickets/T-3232/ticket.md                           |  88 +++-
 tickets/T-3233/ticket.md                           |  51 +-
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
 tickets/T-3612/done-report.md                      | 221 ++++++++
 tickets/T-3612/ticket.md                           | 156 +++++-
 tickets/T-3613/done-report.md                      | 106 ++++
 tickets/T-3613/ticket.md                           | 212 +++++++-
 tickets/T-3614/ticket.md                           | 111 +++-
 tickets/T-3615/done-report.md                      |  33 ++
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
 tickets/T-3856/done-report.md                      | 247 +++++++++
 tickets/T-3856/ticket.md                           |  60 ++-
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
 tickets/T-4010/ticket.md                           |  17 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4029/ticket.md                           |  16 +-
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
 tickets/T-4493/ticket.md                           |  61 +++
 tickets/T-4494/done-report.md                      | 138 +++++
 tickets/T-4494/ticket.md                           |  73 +++
 tickets/T-4495/done-report.md                      | 197 +++++++
 tickets/T-4495/ticket.md                           |  64 +++
 tickets/T-4496/done-report.md                      |  23 +
 tickets/T-4496/ticket.md                           |  56 ++
 tickets/T-4497/ticket.md                           |  31 ++
 tickets/T-4498/done-report.md                      | 147 ++++++
 tickets/T-4498/ticket.md                           |  55 ++
 tickets/T-4499/ticket.md                           |  49 ++
 tickets/T-4500/ticket.md                           |  41 ++
 tickets/T-4501/done-report.md                      |  24 +
 tickets/T-4501/ticket.md                           |  81 +++
 tickets/T-4502/done-report.md                      |  19 +
 tickets/T-4502/ticket.md                           |  73 +++
 tickets/T-4503/ticket.md                           |  38 ++
 tickets/T-4504/ticket.md                           |  69 +++
 tickets/T-4505/ticket.md                           |  38 ++
 tickets/T-4506/ticket.md                           |  40 ++
 tickets/T-4507/ticket.md                           |  37 ++
 tickets/T-4508/ticket.md                           |  98 ++++
 tickets/T-4509/ticket.md                           |  47 ++
 tickets/T-4510/done-report.md                      | 149 ++++++
 tickets/T-4510/ticket.md                           |  81 +++
 tickets/T-4511/done-report.md                      |  97 ++++
 tickets/T-4511/ticket.md                           | 103 ++++
 tickets/T-4512/ticket.md                           |  86 ++++
 tickets/T-4513/ticket.md                           |  36 ++
 tickets/T-4514/done-report.md                      | 179 +++++++
 tickets/T-4514/ticket.md                           |  66 +++
 tickets/T-4515/done-report.md                      |  24 +
 tickets/T-4515/ticket.md                           |  62 +++
 tickets/T-4516/ticket.md                           |  32 ++
 tickets/T-4517/done-report.md                      | 180 +++++++
 tickets/T-4517/ticket.md                           |  94 ++++
 tickets/T-4518/ticket.md                           |  34 ++
 tickets/T-4519/ticket.md                           |  67 +++
 tickets/T-4520/done-report.md                      | 163 ++++++
 tickets/T-4520/ticket.md                           |  58 +++
 tickets/T-4521/done-report.md                      | 228 +++++++++
 tickets/T-4521/ticket.md                           | 125 +++++
 tickets/T-4522/done-report.md                      |  99 ++++
 tickets/T-4522/ticket.md                           |  49 ++
 tickets/T-4523/done-report.md                      | 104 ++++
 tickets/T-4523/ticket.md                           |  40 ++
 tickets/T-4524/ticket.md                           |  45 ++
 tickets/T-4526/ticket.md                           |  45 ++
 tickets/T-4529/ticket.md                           |  76 +++
 tickets/T-4530/ticket.md                           |  64 +++
 tickets/T-4531/done-report.md                      |  21 +
 tickets/T-4531/ticket.md                           | 110 ++++
 tickets/T-4532/done-report.md                      |  24 +
 tickets/T-4532/ticket.md                           |  66 +++
 tickets/T-4533/ticket.md                           |  35 ++
 tickets/T-4534/ticket.md                           |  69 +++
 tickets/T-4535/done-report.md                      |  64 +++
 tickets/T-4535/ticket.md                           |  61 +++
 tickets/T-4536/done-report.md                      |  78 +++
 tickets/T-4536/ticket.md                           | 128 +++++
 tickets/T-4537/ticket.md                           |  33 ++
 tickets/T-4538/ticket.md                           |  60 +++
 tickets/T-4539/ticket.md                           |  29 ++
 tickets/T-4540/ticket.md                           |  49 ++
 tickets/T-4541/ticket.md                           | 112 ++++
 tickets/T-4542/ticket.md                           |  55 ++
 tickets/T-4543/done-report.md                      | 115 +++++
 tickets/T-4543/ticket.md                           |  79 +++
 tickets/T-4546/ticket.md                           |  38 ++
 tickets/T-4547/done-report.md                      | 137 +++++
 tickets/T-4547/ticket.md                           |  45 ++
 tickets/T-4548/done-report.md                      |  59 +++
 tickets/T-4548/ticket.md                           |  50 ++
 tickets/T-4549/ticket.md                           |  53 ++
 tickets/T-4550/done-report.md                      | 545 ++++++++++++++++++++
 tickets/T-4550/ticket.md                           |  59 +++
 tickets/T-4552/done-report.md                      | 146 ++++++
 tickets/T-4552/ticket.md                           | 100 ++++
 tickets/T-4553/done-report.md                      | 501 ++++++++++++++++++
 tickets/T-4553/ticket.md                           |  55 ++
 tickets/T-4554/ticket.md                           |  63 +++
 tickets/T-4555/done-report.md                      | 556 ++++++++++++++++++++
 tickets/T-4555/ticket.md                           |  73 +++
 tickets/T-4556/ticket.md                           |  37 ++
 tickets/T-4558/ticket.md                           |  30 ++
 tickets/T-4559/ticket.md                           |  54 ++
 tickets/T-4560/ticket.md                           |  41 ++
 tickets/T-4561/ticket.md                           |  38 ++
 tickets/T-4562/ticket.md                           |  35 ++
 tickets/T-4563/ticket.md                           |  42 ++
 tickets/T-4566/ticket.md                           | 154 ++++++
 tickets/T-4567/ticket.md                           |  27 +
 tickets/T-4571/ticket.md                           |  43 ++
 tickets/T-4572/ticket.md                           |  43 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4579/ticket.md                 |  65 +++
 tickets/T-4588/ticket.md                 |  41 ++
 tickets/T-4581/ticket.md                 |  47 ++
 tickets/T-4582/ticket.md                 |  49 ++
 uv.lock                                            |   2 +-
 412 files changed, 25199 insertions(+), 1610 deletions(-)
```

### Evidence
- `tests/unit/strata/test_effects.py::TestNoRetiredBareKindEmitted::test_no_registry_entry_emits_a_retired_bare_kind` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
