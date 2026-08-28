## Done report

Audited all 12 candidate `test_cli_*.py` files named in T-2969's body for
the T-2943 missing-git-init pattern (fixture writes to `tmp_path` without
`git_init_and_config`, feeding a path that a CLI subcommand resolves a
project root against via `frob.gitio.repo_root`, which then fails
"not a git repository" and the subcommand exits nonzero fatally instead
of degrading).

Per-file table (all measured on this worktree, natives-built, Linux,
current main tip merged in):

| candidate file              | git_init_and_config calls | subcommand(s) under test | root-resolution call in its runner | pattern present | local pass/fail (before) | local pass/fail (after) |
|---|---|---|---|---|---|---|
| test_cli_arch.py            | 0 | arch  | none (arch_runner.py never calls repo_root/resolve_project_root) | No | 21/21 pass | 21/21 pass |
| test_cli_dup.py             | 0 | dup   | none | No | 16/16 pass | 16/16 pass |
| test_cli_exports.py         | 0 | exports | repo_root called, but only inside `_try_exports_via_daemon`'s daemon-fastpath probe, which treats `repo_root().is_err` as a soft `return False` fallback to the in-process (non-daemon) path -- never fatal | No | 18/18 pass | 18/18 pass |
| test_cli_map.py             | 0 | map   | none | No | 19/19 pass | 19/19 pass |
| test_cli_outline.py         | 0 | outline | none | No | 33/33 pass | 33/33 pass |
| test_cli_parse.py           | 0 | parse | none | No | 44/44 pass | 44/44 pass |
| test_cli_render_golden.py   | 0 | doctor, map | none required fatally (doctor/map degrade without a repo) | No | 6/6 pass | 6/6 pass |
| test_cli_scale.py           | 0 | arch, dup, map | none | No | 7/7 pass | 7/7 pass |
| test_cli_sys_export.py      | 0 | sys export | none -- operates on a fixed checked-in model path, not `tmp_path` | No | 6/6 pass | 6/6 pass |
| test_cli_sys_plan.py        | 0 (uses `init_repo(tmp_path, model)` instead, which DOES git-init + commit) | sys plan | resolves root via the fixture's own already-committed repo | No | 7/7 pass | 7/7 pass |
| test_cli_vet.py             | 0 | vet   | none | No | 5/5 pass | 5/5 pass |
| test_cli_xref.py            | 0 | xref  | none | No | 16/16 pass | 16/16 pass |

Conclusion: NONE of the 12 candidates carry the T-2943 pattern as a live
failure. `frob cycle` is fatal on an unresolvable root because
`cycle_runner._resolve_project_root` raises the walk on `repo_root().ok`
being `None`; every other runner among these 12 either never calls
`repo_root`/`resolve_project_root` at all, or (exports' daemon fastpath)
treats a resolution failure as a soft fallback rather than a hard error.
`test_cli_sys_plan.py` already uses the correct fixture pattern
(`init_repo`, which both git-inits AND commits, matching the T-2943
remedy) -- it was flagged as a candidate only because it does not call
`git_init_and_config` BY NAME, not because it is missing the git
groundwork.

No fix was needed or applied -- 12/12 files pass 12/12 (baseline) local
runs before this ticket and after (unchanged, since no code was touched).

Acceptance item 2 (a real macOS CI run re-measured post-T-2943's land,
checking whether the 156-failure macOS baseline shrank as expected) is
NOT addressed by this ticket -- it requires an actual macOS CI run, which
this worktree agent has no access to trigger or observe. Left UNBOUND;
flagging for the coordinator/next macOS CI run rather than fabricating a
number.

Changed: none (no source files modified -- audit-only ticket, negative
result).
Evidence: 12 pytest node ids (one representative per candidate file,
--accepts 0) --
tests/system/test_cli_arch.py::test_exit_zero,
tests/system/test_cli_dup.py::test_exit_zero_on_fixture,
tests/system/test_cli_exports.py::TestExportsBasic::test_shows_import_line,
tests/system/test_cli_map.py::test_exit_code_zero,
tests/system/test_cli_outline.py::test_exit_code_zero_on_valid_python,
tests/system/test_cli_parse.py::test_pytest_exit_zero_with_exit_code_0,
tests/system/test_cli_render_golden.py::TestDoctorGolden::test_doctor_plain_mode_has_no_ansi,
tests/system/test_cli_scale.py::test_map_50_files_json_lists_all,
tests/system/test_cli_sys_export.py::TestCliSysExport::test_k8s_export_is_valid_yaml,
tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_dry_run_prints_tree_without_writing,
tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero,
tests/system/test_cli_xref.py::test_exit_zero_found_symbol
(all 12 files' FULL suites also run and pass in full: 21/21, 16/16,
18/18, 19/19, 33/33, 44/44, 6/6, 7/7, 6/6, 7/7, 5/5, 16/16 -- 198/198
total).
Filed: T-2971 (renumbers at land) -- coordinator-only follow-up
to trigger a macOS CI run on current main and re-measure whether the
156-failure macOS baseline shrank as T-2943 expected, since a worktree
agent cannot trigger/observe CI runs. No new failure class was found in
this ticket's own audit requiring a separate ticket.
Gates: no source changed; frob:tests directives not applicable (no public
symbol touched). Acceptance item 2 (macOS CI re-measurement) left UNBOUND
-- requires coordinator/CI access this worktree does not have.

### Changed
```
 tickets/T-2969/done-report.md      | 97 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2969/ticket.md           | 29 +++++++++++-
 tickets/T-2971/ticket.md | 38 +++++++++++++++
 3 files changed, 162 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_cli_arch.py::test_exit_zero` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_dup.py::test_exit_zero_on_fixture` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_exports.py::TestExportsBasic::test_shows_import_line` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_map.py::test_exit_code_zero` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_outline.py::test_exit_code_zero_on_valid_python` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_parse.py::test_pytest_exit_zero_with_exit_code_0` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_render_golden.py::TestDoctorGolden::test_doctor_plain_mode_has_no_ansi` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_scale.py::test_map_50_files_json_lists_all` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_sys_export.py::TestCliSysExport::test_k8s_export_is_valid_yaml` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_dry_run_prints_tree_without_writing` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_xref.py::test_exit_zero_found_symbol` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 27 error(s), 482 warning(s), 853 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
